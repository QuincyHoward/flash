#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_mode_test.py — ch_center 子场景「同一算例 × 多种执行模式」测试驱动
====================================================================

背景
----
ch_center 子场景本身只关心**物理搭建**（靶/激光/EOS/网格），执行方式由
运行模式参数控制，默认 ``auto`` 按平台自适应（判定表唯一实现在
``flash.flash_run.execution.resolve_target``）。本驱动把五种执行路径
固化为可重复的测试：

  key          驱动进程所在平台   场景运行模式    说明
  -----------  ----------------  --------------  --------------------------------
  win-wsl      Windows           wsl             Windows python -> WSL FLASH
  win-hpc      Windows           hpc-remote      Windows python -> 超算（上传/提交/分析/下载）
  wsl-wsl      WSL               wsl             WSL python -> WSL FLASH
  wsl-hpc      WSL               hpc-remote      WSL python -> 超算（上传/提交/分析/下载）
  hpc-insitu   超算登录节点      hpc-insitu      超算 python -> 超算（就地 sbatch）

五种路径共用**同一份** flash_input（只改终止时间 tmax，物理设置逐字不变），
产物按模式分目录收纳，供 analyze_modes.py 做 dens/nele 时序对比。

用法
----
  # Windows 上一键跑本地 WSL 模式（驱动进程在 Windows）
  .venv\\Scripts\\python.exe flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py --mode-key win-wsl --tmax 2e-10

  # wsl-* 模式在 Windows 上调用时会自动转投 WSL 执行（驱动进程必须真的在 WSL 里）
  ... run_mode_test.py --mode-key wsl-hpc --tmax 2e-10

  # hpc-insitu：先同步本目录到超算仓库，再在超算上执行（见 README.md）
  ~/PhySimX/.../flash_sim/.venv-hpc-nce/bin/python <repo>/flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py --mode-key hpc-insitu --tmax 2e-10

  # 从 Windows/WSL 回传 hpc-insitu 的 chk/日志/摘要到本地 results/
  ... run_mode_test.py fetch-insitu

环境约定（由本驱动设置，场景与 run_flash.sh 读取）
  FLASH_COLLECT_DIR   每轮独立 chk 收纳目录（results/<key>/chk）
  FLASH_RUN_WORKDIR   每轮独立运行工作目录（WSL 侧防历史 chk 污染）
  FLASH_FETCH_LIMIT   0 = 回传全部帧（批量矩阵对比需要全时序）
  FLASH_LS_LIMIT      远端 ls 列文件上限（默认 50，批量模式放大）
  FLASH_NO_MODULE_PURGE=1  超算三模式：二进制已预置，禁 module purge 继承 oneAPI
  FLASH_SSH_BACKEND=paramiko  wsl-hpc：WSL 内 paramiko 直连（凭据经 HOME 指向 Windows 主目录）
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DRIVER_DIR = Path(__file__).resolve().parent          # .../ch_center/modes_test
SCENARIO_DIR = DRIVER_DIR.parent                       # .../ch_center
RESULTS_DIR = DRIVER_DIR / "results"

#: 驱动进程平台词表（**执行目标**词表是 flash_run.execution 的
#: local/wsl/hpc-remote/hpc-insitu，此处是"驱动跑在哪"的内部词汇，
#: 用命名常量表达，避免与模式名字面量混淆——R-SCENE-07 护栏）。
_PLAT_WIN = "windows"
_PLAT_WSL = "wsl"
_PLAT_HPC = "hpc"

#: 模式 key -> (驱动进程应处平台, 场景运行模式, 中文说明)
MODE_KEYS: Dict[str, Dict[str, str]] = {
    "win-wsl": {"platform": _PLAT_WIN, "mode": "wsl",
                "desc": "Windows python -> WSL FLASH"},
    "win-hpc": {"platform": _PLAT_WIN, "mode": "hpc-remote",
                "desc": "Windows python -> HPC (upload/submit/analyze/download)"},
    "wsl-wsl": {"platform": _PLAT_WSL, "mode": "wsl",
                "desc": "WSL python -> WSL FLASH"},
    "wsl-hpc": {"platform": _PLAT_WSL, "mode": "hpc-remote",
                "desc": "WSL python -> HPC (upload/submit/analyze/download)"},
    "hpc-insitu": {"platform": _PLAT_HPC, "mode": "hpc-insitu",
                   "desc": "HPC python -> HPC (insitu sbatch)"},
}

#: WSL 内可见的 Windows 用户主目录（凭据 ~/.physimx 的来源；只读使用）
WIN_HOME = Path("/mnt/c/Users/Administrator")
#: WSL 内的 Linux venv（含 paramiko/h5py/yt/matplotlib）
WSL_PY_REL = ".venv-linux/bin/python"
#: WSL 运行的本地工作目录根（**必须是 WSL 原生 ext4，禁用 /mnt/*）——
#: 2026-10-24 实测：FLASH 的 HDF5 MPI-IO 写 /mnt/e（drvfs）会间歇失败
#: （ADIOI_GEN_READCONTIG: No data available → SIGABRT exit 134），
#: 短跑偶然通过、全长跑必崩；产物收集目录仍在 /mnt/e（普通 cp，非 MPI-IO）。
WSL_WORK_ROOT = os.environ.get("FLASH_WSL_WORK_ROOT", "/root/flash_modes_work")

_ORIG_ARGV = list(sys.argv[1:])


# ═══════════════════════════════════════════════════════════════
# 平台探测
# ═══════════════════════════════════════════════════════════════

def detect_platform() -> str:
    """windows / wsl / hpc / linux。

    hpc 判据：POSIX + 非 WSL + sbatch 可用（超算登录节点）。
    """
    if os.name == "nt":
        return _PLAT_WIN
    kernel = ""
    try:
        kernel = Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        pass
    if "microsoft" in kernel:
        return _PLAT_WSL
    if shutil.which("sbatch"):
        return _PLAT_HPC
    return "linux"


def repo_root() -> Path:
    """从本文件向上找 pyproject.toml + start_flash.py（flash 包根）。"""
    p = DRIVER_DIR
    for _ in range(12):
        if (p / "pyproject.toml").is_file() and (p / "start_flash.py").is_file():
            return p
        p = p.parent
    raise RuntimeError(f"Cannot locate flash repo root above {DRIVER_DIR}")


def _to_posix(p: Path) -> str:
    s = str(p)
    if s.startswith("/"):
        return s
    if ":" not in s:
        return s.replace("\\", "/")
    drive, rest = s.split(":", 1)
    return "/mnt/" + drive.lower() + rest.replace("\\", "/")


# ═══════════════════════════════════════════════════════════════
# 日志（stdout + 文件双写）
# ═══════════════════════════════════════════════════════════════

class Tee:
    """stdout + 文件双写，并**接管 sys.stdout**。

    ★ 2026-10-24：超算 nohup 启动时若再把 shell stdout 重定向到同一文件，
      两个独立偏移的写会互相覆盖（日志错乱、内容丢失）。现由本类统一接管
      sys.stdout —— 驱动与场景的 print 全部进同一日志；外层启动只需把
      stdout 导向**另一个**文件（或 /dev/null）。
    """

    def __init__(self, path: Optional[Path]):
        self._file = None
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(path, "w", encoding="utf-8", errors="replace")
        self._orig_stdout = sys.stdout
        sys.stdout = self

    def write(self, msg: str) -> None:
        self._orig_stdout.write(msg)
        if self._file:
            self._file.write(msg)

    def flush(self) -> None:
        self._orig_stdout.flush()
        if self._file:
            self._file.flush()

    def log(self, msg: str = "") -> None:
        self.write(msg + "\n")
        self.flush()

    def close(self) -> None:
        try:
            sys.stdout = self._orig_stdout
        finally:
            if self._file:
                self._file.close()
                self._file = None


# ═══════════════════════════════════════════════════════════════
# 子命令：run
# ═══════════════════════════════════════════════════════════════

def _setup_env(key: str, chk_dir: Path, work_dir: Path, tee: Tee) -> None:
    """在 import 场景**之前**设置全部环境变量（场景在 import 时读 SIM_USER_DIR）。"""
    os.environ["FLASH_COLLECT_DIR"] = str(chk_dir)
    os.environ["FLASH_FETCH_LIMIT"] = "0"
    os.environ["FLASH_LS_LIMIT"] = "2000"
    if key in ("win-wsl", "wsl-wsl"):
        # ★ WSL 两条路径：运行工作目录落 WSL 原生 ext4（见 WSL_WORK_ROOT 注释）。
        #   _to_wsl_path 对 "/..." 幂等，Windows 驱动设的路径在 WSL 内原样生效。
        os.environ["FLASH_RUN_WORKDIR"] = f"{WSL_WORK_ROOT}/{key}"
        tee.log(f"[env] FLASH_RUN_WORKDIR={WSL_WORK_ROOT}/{key}（WSL 原生 ext4，避 drvfs MPI-IO）")
    else:
        os.environ["FLASH_RUN_WORKDIR"] = str(work_dir)
    if key in ("win-hpc", "wsl-hpc", "hpc-insitu"):
        # ★ 2026-10-24 实测：ch_center 二进制已预置（QC/LaserSlab_ChCenter，
        #   insitu 为 hello/...）⇒ 作业跳过 setup+make。此时必须让 submit 脚本的
        #   module 行生效（mpich/3.2-gcc9.3 + hdf5/1.8.18）：
        #     · hdf5 模块提供 libhdf5.so.10（计算节点 ambient 环境没有！）；
        #     · mpich 模块的 soname 是 libmpi.so/libmpifort.so（无 .12 后缀），
        #       不与二进制链接的 Intel libmpi.so.12/libmpifort.so.12 冲突，
        #       后者仍由 ambient oneAPI 路径解析（lib/release 提供 MPII_F_TRUE）。
        #   FLASH_NO_MODULE_PURGE=1 是"objdir 需重新编译"场景的补丁（禁 purge
        #   保 oneAPI 链接栈），对已预置二进制反而因缺 libhdf5 直接加载失败
        #   （诊断作业实测：7 种 LD_LIBRARY_PATH 组合全部 libhdf5.so.10 not found）。
        tee.log("[env] 超算三模式：不设 FLASH_NO_MODULE_PURGE（二进制预置，走 module 路径）")
    if key == "wsl-hpc":
        if not WIN_HOME.is_dir():
            raise RuntimeError(
                f"wsl-hpc 需要 Windows 主目录可见（凭据来源）: {WIN_HOME} 不存在")
        os.environ["HOME"] = str(WIN_HOME)          # Path.home() -> ~/.physimx
        os.environ["FLASH_SSH_BACKEND"] = "paramiko"
        tee.log(f"[env] HOME={WIN_HOME}（凭据只读引用），FLASH_SSH_BACKEND=paramiko")


def _last_chk_time(chk_dir: Path) -> Optional[float]:
    """读最后一个 chk 的仿真时间（real scalars.time）；失败返回 None。"""
    files = sorted(chk_dir.glob("*chk*"))
    if not files:
        return None
    try:
        import h5py
        with h5py.File(files[-1], "r") as f:
            if "real scalars" not in f:
                return None
            for rec in f["real scalars"][:]:
                name = rec["name"]
                name = name.decode() if isinstance(name, bytes) else str(name)
                if name.strip() == "time":
                    return float(rec["value"])
    except Exception:  # noqa: BLE001
        return None
    return None


def _prune_plt(chk_dir: Path, tee: Tee) -> int:
    """chk-only 回传策略（fetch_policy）：plt 不在跨模式对比保留范围。

    run_flash.sh Step 6 对本地模式会连 plt 一起 cp 进 FLASH_COLLECT_DIR
    （plot_interval_step=5 ⇒ 全时长约 1360 个 plt，~400 MB/模式），
    超算三条路径本就过滤 plt（with_plt=False），本地两条路径在此对齐。
    """
    n = 0
    for p in list(chk_dir.glob("*plt*")):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    if n:
        tee.log(f"[prune] 按 chk-only 策略移除 {n} 个 plt 文件")
    return n


def _copy_scene_artifacts(key: str, chk_dir: Path, logs_dir: Path,
                          plots_dir: Path, tee: Tee) -> Dict[str, int]:
    """把场景共享目录里的本轮日志/诊断图拷贝到 results/<key>/ 下（防下一模式覆盖）。"""
    n = {"logs": 0, "plots": 0}
    suffix = "wsl" if key.endswith("wsl") else "hpc"
    # WSL 运行日志（main_wsl 写在 flash_input/ 下）
    for name in ("wsl_console.log", "wsl_run.log"):
        src = SCENARIO_DIR / "flash_input" / name
        if src.is_file():
            dst = logs_dir / f"{key}__{name}"
            shutil.copy2(src, dst)
            n["logs"] += 1
    # 场景本地/远端分析 PNG（*_wsl.png / *_hpc.png）
    plots_src = SCENARIO_DIR / "flash_output" / "plots"
    if plots_src.is_dir():
        for p in sorted(plots_src.glob(f"*_{suffix}.png")):
            shutil.copy2(p, plots_dir / f"{key}__{p.name}")
            n["plots"] += 1
    tee.log(f"[collect] 日志 {n['logs']} 个、诊断图 {n['plots']} 张 -> results/{key}/")
    return n


def cmd_run(args: argparse.Namespace) -> int:
    key = args.mode_key
    spec = MODE_KEYS[key]
    tee = Tee(RESULTS_DIR / key / "logs" / f"driver_{key}.log")

    plat = detect_platform()
    tee.log("=" * 68)
    tee.log(f" ch_center 模式测试 — key={key}  ({spec['desc']})")
    tee.log(f" 驱动平台: {plat} | 场景模式: {spec['mode']} | tmax={args.tmax}")
    tee.log(f" 开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tee.log("=" * 68)

    if plat != spec["platform"]:
        tee.log(f"[X] 平台不匹配：本驱动进程在 {plat}，而 {key} 要求 {spec['platform']}。")
        if spec["platform"] == _PLAT_WSL:
            tee.log("    在 Windows 上直接调用即可自动转投 WSL；或进入 WSL 手动执行：")
            tee.log(f"    cd {_to_posix(repo_root())} && {WSL_PY_REL} "
                    f"{_to_posix(DRIVER_DIR / 'run_mode_test.py')} --mode-key {key} "
                    f"--tmax {args.tmax}")
        elif spec["platform"] == _PLAT_HPC:
            tee.log("    请按 README.md 把本目录同步到超算后，在超算登录节点执行。")
        tee.close()
        return 2

    res_dir = RESULTS_DIR / key
    chk_dir = Path(args.collect_dir).resolve() if args.collect_dir else res_dir / "chk"
    work_dir = res_dir / "wsl_work"
    logs_dir, plots_dir = res_dir / "logs", res_dir / "plots"
    for d in (chk_dir, work_dir, logs_dir, plots_dir):
        d.mkdir(parents=True, exist_ok=True)

    _setup_env(key, chk_dir, work_dir, tee)

    # ── import 场景（环境已就位）──
    root = repo_root()
    for p in (str(root), str(SCENARIO_DIR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import laserslab1d_local_custom as scene  # noqa: E402

    from flash.flash_run.execution import (  # noqa: E402
        DEFAULT_POLICY,
        ExecutionTargetError,
        resolve_target,
    )
    try:
        target, trace = resolve_target(spec["mode"], DEFAULT_POLICY)
    except ExecutionTargetError as exc:
        tee.log(f"[X] 目标解析失败:\n{exc}")
        tee.close()
        return 3
    for line in trace:
        tee.log("  " + line)

    if args.dry_run:
        tee.log(f"[dry-run] 将在 target={target} 执行；chk -> {chk_dir}")
        tee.close()
        return 0

    tee.log(f"[run] target={target}  chk_dir={chk_dir}")
    t0 = time.time()
    ok = False
    err = ""
    try:
        ok = bool(scene.main(credential_name=None, mode=spec["mode"], tmax=args.tmax))
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        tee.log(f"[X] 场景 main() 抛出异常: {err}")
    wall = time.time() - t0

    n_chk = len(sorted(chk_dir.glob("*chk*")))
    _prune_plt(chk_dir, tee)
    art = _copy_scene_artifacts(key, chk_dir, logs_dir, plots_dir, tee)

    # ── 完整性校验：产物必须跑到 tmax（防"崩溃后部分 chk 报成功"）──
    # 2026-10-24 首跑教训：FLASH 在 ~1140 步崩溃（exit 134），仍回收 57 个
    # chk，旧判据（n_chk>0）判成功。现要求末 chk 时间 >= 98% tmax。
    t_end = _last_chk_time(chk_dir)
    complete = t_end is not None and t_end >= 0.98 * args.tmax
    if t_end is not None and not complete:
        tee.log(f"[X] 产物不完整: 末 chk t={t_end:.3e} < 0.98*tmax={0.98*args.tmax:.3e}"
                f"（FLASH 中途崩溃？）")

    summary: Dict[str, Any] = {
        "key": key, "desc": spec["desc"],
        "driver_platform": plat, "scenario_mode": spec["mode"],
        "resolved_target": target,
        "ok": bool(ok and n_chk > 0 and complete),
        "scene_main_returned": ok,
        "run_complete": bool(complete),
        "t_end_s": t_end,
        "error": err,
        "n_chk": n_chk,
        "tmax_s": args.tmax,
        "wall_s": round(wall, 1),
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "collect_dir": str(chk_dir),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "artifacts": art,
    }
    (res_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    tee.log("-" * 68)
    t_end_txt = f"{t_end:.3e}" if t_end is not None else "None"
    tee.log(f"[done] ok={summary['ok']}  n_chk={n_chk}  t_end={t_end_txt}  wall={wall:.0f}s")
    if not summary["ok"]:
        tee.log(f"[X] 失败原因: scene_main={ok}, n_chk={n_chk}, "
                f"complete={complete}, t_end={t_end_txt}, err={err or '-'}")
    tee.close()
    return 0 if summary["ok"] else 4


# ═══════════════════════════════════════════════════════════════
# 子命令：fetch-insitu（从 Windows/WSL 回传超算 insitu 产物）
# ═══════════════════════════════════════════════════════════════

def cmd_fetch_insitu(args: argparse.Namespace) -> int:
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    key = "hpc-insitu"
    local_dir = RESULTS_DIR / key
    for d in (local_dir / "chk", local_dir / "logs", local_dir / "plots"):
        d.mkdir(parents=True, exist_ok=True)

    with RemoteSession(credential_name=None, verbose=True) as s:
        home = (s.run("printf '%s' \"$HOME\"", timeout=15)[0] or "").strip()
        pkg_root = os.environ.get("FLASH_HPC_PKG_ROOT", "").strip() or \
            f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim"
        remote = f"{pkg_root}/flash/scenarios/public/center_evolution/ch_center/modes_test/results/{key}"
        print(f"[fetch] 远端: {remote}")

        out, _, rc = s.run(
            f"ls {remote}/chk/*chk* {remote}/logs/* {remote}/plots/*.png "
            f"{remote}/summary.json 2>/dev/null | sort", timeout=60)
        files = [l.strip() for l in (out or "").splitlines() if l.strip()]
        if not files:
            print("[fetch] 远端无产物（insitu 尚未运行或路径不对）")
            return 1
        n = 0
        for rf in files:
            name = Path(rf).name
            if rf.endswith("summary.json"):
                dst = local_dir / "summary.json"
            elif "/logs/" in rf:
                dst = local_dir / "logs" / name
            elif "/plots/" in rf:
                dst = local_dir / "plots" / name
            else:
                dst = local_dir / "chk" / name
            if s.download(rf, str(dst)):
                n += 1
        print(f"[fetch] 已回传 {n}/{len(files)} 个文件 -> {local_dir}")
        # 超算侧 plots 还可能在 runs 契约目录（main_hpc_insitu 的 run_dir/plots）
        out2, _, _ = s.run(
            f"ls -t {pkg_root}/flash_sim_runs/ch_center/run_*/plots/*.png 2>/dev/null "
            f"| head -6", timeout=30)
        for rf in [l.strip() for l in (out2 or "").splitlines() if l.strip()]:
            s.download(rf, str(local_dir / "plots" / f"{key}__runs__{Path(rf).name}"))
    return 0


# ═══════════════════════════════════════════════════════════════
# WSL 自动转投
# ═══════════════════════════════════════════════════════════════

def maybe_reexec_wsl(args: argparse.Namespace) -> Optional[int]:
    """wsl-* 模式在 Windows 上被调用时，转投 WSL 执行后原样退出。

    驱动进程必须真的运行在 WSL 里（用户的模式定义 b：WSL 中执行 python 脚本），
    Windows 上的一键调用只是 convenience wrapper。

    ★ R-SCENE-03：wsl 启动器构造下沉 `flash_run.remote.executors.WslExecutor`
      （哨兵取退出码），场景层不得自建 `wsl bash -c`。
    ★ 命令串必须是**单条简单命令**（无顶层 `;`/`&&`/`||`）—— 本机 wsl.exe
      会按这些分隔符拆成多次独立执行（见 README 维护要点 0）。脚本路径用
      绝对路径，不需要 `cd`。
    """
    if "--no-reexec" in _ORIG_ARGV or os.name != "nt":
        return None
    if MODE_KEYS[args.mode_key]["platform"] != _PLAT_WSL:
        return None
    from flash.flash_run.remote.executors import WslExecutor

    root = repo_root()
    wsl_py = f"{_to_posix(root)}/{WSL_PY_REL}"
    script = _to_posix(DRIVER_DIR / "run_mode_test.py")
    fwd = [a for a in _ORIG_ARGV if a != "--no-reexec"]
    inner = " ".join([wsl_py, script, "--no-reexec"] + fwd)
    print(f"[reexec] Windows -> WSL: {inner}")
    out, err, rc = WslExecutor().run(inner, timeout=7200)
    for line in (out or "").strip().splitlines()[-8:]:
        print("  " + line)
    if (err or "").strip():
        print(f"[reexec] stderr: {err.strip()[:500]}")
    print(f"[reexec] WSL 侧返回码: {rc}")
    return rc


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(
        description="ch_center 多执行模式测试驱动",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="run",
                    choices=["run", "fetch-insitu"], help="子命令")
    ap.add_argument("--mode-key", default="win-wsl", choices=sorted(MODE_KEYS),
                    help="执行模式 key（默认 win-wsl）")
    ap.add_argument("--tmax", type=float, default=2e-10,
                    help="终止时间 (s)，只改终止时间不改物理设置（默认 2e-10）")
    ap.add_argument("--collect-dir", default="",
                    help="覆盖 chk 收纳目录（冒烟测试用；默认 results/<key>/chk）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只解析目标并打印计划，不执行 FLASH")
    ap.add_argument("--no-reexec", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.command == "fetch-insitu":
        return cmd_fetch_insitu(args)

    rc = maybe_reexec_wsl(args)
    if rc is not None:
        return rc
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
