#!/usr/bin/env python3
"""SNB 场景运行驱动 —— 部署 → setup → make → run → 收集（校验后删）
═══════════════════════════════════════════════════════════════════════════════

**本脚本不含 F90 源码文本**（只做文件复制与命令编排）→ 可分享（docs/06）。

配套 `scripts/generate/gen_scene.py` 生成的场景目录使用。

用法
----
    # 全流程 (SNB + 限流 SH 两条腿)
    python scripts/run/run_scene.py --scene ../my_scene

    # 只跑 SNB 腿; 复用已编译二进制
    python scripts/run/run_scene.py --scene ../my_scene --side snb \
        --skip-setup --skip-make

    # 只做前置检查 (树/源文件/表/补丁)
    python scripts/run/run_scene.py --scene ../my_scene --check-only

关键设计（均为踩坑后加固）
- **树自动探测**：SNB 腿找 FLASHSNB，限流 SH 腿找标准 FLASH
- **部署前清空单元**：避免残留覆盖件污染另一腿
- **★ 构建指纹 → 首次使用场景强制重编译**：objdir 名由 `LEG_SPECS` 固定，
  **不同场景会复用同一 objdir**；沿用上次的 `flash4` 会把"别的场景的二进制"
  当成当前场景结果（FLASH 的 par 是运行时读的，不匹配也不报错 → 静默错误）。
  故把 `flash_input/` 全文件内容 + setup 参数的 SHA256 记入 objdir，
  **指纹不一致或 `flash4` 缺失 → 无视 `--skip-setup/--skip-make` 强制 setup+make**。
- **make 判据**：用退出码 / `test -x flash4`，**不**用 `grep error`
- **收集先校验后删**：以本地 chk 帧数 > 0 为成功判据，成功后才删 WSL 侧
- **日志名带腿标识**：避免不同批次日志同名互相污染判读
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_SNB_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SNB_DIR / "scripts"))

import snb_params as P  # noqa: E402
from generate.gen_scene import LEG_SPECS, SNB_F90, SHARED, DIFF_THERM  # noqa: E402

# 树级补丁（按文件名判定是否已打；补丁内容不在此描述）
TREE_PATCHES = (
    "physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",
    "physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",
)


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


# ══════════════════════════════════════════════════════════════
def wsl(cmd: str, distro: str = "Ubuntu-22.04",
        timeout: int = 7200) -> Tuple[int, str]:
    """执行 WSL 命令。

    ★ 铁律: 内联命令**不得依赖 shell 变量**（双层展开会使其为空）。
      调用方须把路径/取值在 Python 端完全展开; 需要变量时把脚本落盘再执行。
    """
    try:
        p = subprocess.run(["wsl", "-d", distro, "bash", "-lc", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout {timeout}s]"


def to_wsl(p: Path) -> str:
    s = Path(p).resolve().as_posix()
    drive, rest = s.split(":", 1)
    return f"/mnt/{drive.lower()}/{rest.lstrip('/')}"


# ══════════════════════════════════════════════════════════════
# ★★ 构建指纹 —— "首次使用场景默认必须重新编译(setup+make)"
# ══════════════════════════════════════════════════════════════
# 动机: objdir 名由 LEG_SPECS 固定 (`SNB_SCENE_obj` / `FLSH_SCENE_obj`),
#   因此**不同场景会复用同一个 objdir**。若沿用上一次留下的 flash4,
#   就会把"别的场景的二进制"当成当前场景的结果 —— 属静默错误, 极难发现
#   (FLASH 的 flash.par 是运行时读的, 二进制不匹配也不会报错)。
# 做法: 对 `flash_input/` 全部文件内容 + setup 参数取 SHA256; 与 objdir 里
#   记录的指纹比对。不一致(或 flash4 缺失) → **强制重新 setup+make**,
#   即使调用方传了 --skip-setup/--skip-make 也一律忽略。
BUILD_FP_FILE = ".snb_build_fp"


def build_fingerprint(scene: Path, side: str, nxb: int, iprocs: int,
                      species: List[str], ng: int) -> str:
    """场景源码指纹 = flash_input 全文件内容 + setup 参数。"""
    h = hashlib.sha256()
    inp = scene / f"sim_{side}" / "flash_input"
    if not inp.is_dir():
        return ""
    for p in sorted(inp.rglob("*")):
        if p.is_file():
            h.update(p.name.encode("utf-8", "replace"))
            h.update(hashlib.sha256(p.read_bytes()).digest())
    spec = LEG_SPECS[side]
    h.update(f"|{spec['sim_name']}|{spec['objdir']}|nxb={nxb}|ip={iprocs}"
             f"|ng={ng}|sp={','.join(species)}".encode("utf-8", "replace"))
    return h.hexdigest()[:32]


def read_fingerprint(obj: str, distro: str) -> str:
    _, out = wsl(f'cat "{obj}/{BUILD_FP_FILE}" 2>/dev/null', distro, 60)
    for ln in out.splitlines():
        s = ln.strip()
        if re.fullmatch(r"[0-9a-f]{32}", s):
            return s
    return ""


def has_flash4(obj: str, distro: str) -> bool:
    _, out = wsl(f'test -x "{obj}/flash4" && echo YES || echo NO', distro, 60)
    return "YES" in out


def find_tree(side: str, distro: str) -> Optional[str]:
    """SNB 腿 → FLASHSNB; 限流 SH 腿 → 标准 FLASH。"""
    if side == "snb":
        for _ in range(3):
            code, out = wsl('find "$HOME" -maxdepth 4 -type d -name FLASHSNB '
                            '2>/dev/null', distro, 120)
            for line in out.splitlines():
                s = line.strip()
                if s.startswith("/") and s.endswith("FLASHSNB"):
                    cand = f"{s}/FLASH4.8"
                    _, o2 = wsl(f'test -d "{cand}" && echo OK', distro, 60)
                    if "OK" in o2:
                        return cand
            if code != 124:
                break
        return None
    for _ in range(3):
        code, out = wsl('ls -d "$HOME"/*/FLASH/FLASH4.8 2>/dev/null', distro, 120)
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("/"):
                return s
        if code != 124:
            break
    return None


# ══════════════════════════════════════════════════════════════
def precheck(scene: Path, sides: List[str], distro: str,
             par_map: Optional[Dict[str, str]] = None,
             tables: Optional[List[str]] = None) -> bool:
    print("\n  ── 前置检查 ────────────────────────────────────────")
    ok = True
    par_map = par_map or {}
    # ★ 表清单可由调用方指定 —— 场景的物种组合不必与 snb_params.SPECIES 相同
    #   (如 2 标记场景 cham+targ 用 He-BADGER + CH-QC-1-001)。
    need_tables = set(tables) if tables else {P.SPECIES[k]["cn4"] for k in P.SPECIES}
    for side in sides:
        d = scene / f"sim_{side}" / "flash_input"
        if not d.is_dir():
            log(f"[{side}] flash_input 缺失: {d}", "ERROR")
            ok = False
            continue
        files = {p.name for p in d.iterdir() if p.is_file()}
        par_name = par_map.get(side) or LEG_SPECS[side]["par"]
        need = set(SHARED) | set(need_tables)
        need.add(par_name)
        if LEG_SPECS[side]["has_snb"]:
            need |= set(SNB_F90)
        miss = sorted(need - files)
        log(f"[{side}] {len(files)} 文件; 缺: {miss or '无'}",
            "WARN" if miss else "OK")
        ok &= not miss
        # 表群数一致性 (只提示)
        tabs = sorted(f for f in files if f.endswith(".cn4"))
        log(f"[{side}] 表: {tabs}")
        t = find_tree(side, distro)
        log(f"[{side}] 树: {t or '未找到'}", "OK" if t else "ERROR")
        ok &= bool(t)
    return ok


def deploy(side: str, scene: Path, tree: str, distro: str) -> bool:
    spec = LEG_SPECS[side]
    inp = scene / f"sim_{side}" / "flash_input"
    unit = f"{tree}/source/Simulation/SimulationMain/{spec['sim_name']}"
    wsl(f'rm -rf "{unit}" && mkdir -p "{unit}"', distro, 60)
    cmd = ""
    for p in sorted(inp.iterdir()):
        if p.is_file():
            cmd += f'cp -f {to_wsl(p)} "{unit}/{p.name}" && '
    cmd += f'ls "{unit}" | wc -l && echo DEPLOY_OK'
    _, out = wsl(cmd, distro, 600)
    if "DEPLOY_OK" not in out:
        log(f"[{side}] 部署失败: {out[-500:]}", "ERROR")
        return False
    log(f"[{side}] 单元已部署: {spec['sim_name']}", "OK")
    return True


def do_setup(side: str, scene: Path, tree: str, distro: str,
             nxb: int, iprocs: int, species: List[str], ng: int,
             pulse_sections: int = 300) -> bool:
    spec = LEG_SPECS[side]
    obj = f"{tree}/{spec['objdir']}"
    # ★ ed_maxPulseSections: 多段激光脉冲(如 82 段)必须显式抬高,
    #   否则 setup 阶段即因段数超限而失败。默认 300 与 tracer 家族一致。
    flags = (f"-1d +cartesian +ug -nxb={nxb} +hdf5typeio "
             f"species={','.join(species)} +mtmmmt +laser +uhd3t +mgd "
             f"mgd_meshgroups={ng} ed_maxPulseSections={pulse_sections}")
    cmd = (f'cd "{tree}" && rm -rf "{obj}" && '
           f'./setup -auto {spec["sim_name"]} {flags} -objdir={spec["objdir"]} '
           f'> setup_{side}.log 2>&1; '
           f'test -d "{obj}" && echo OBJ_OK || '
           f'(tail -40 setup_{side}.log; echo OBJ_FAIL)')
    _, out = wsl(cmd, distro, 1800)
    if "OBJ_OK" not in out:
        log(f"[{side}] setup 失败:\n{out[-1500:]}", "ERROR")
        return False
    log(f"[{side}] setup 完成", "OK")
    return True


def do_make(side: str, tree: str, distro: str, jobs: int = 4) -> bool:
    spec = LEG_SPECS[side]
    obj = f"{tree}/{spec['objdir']}"
    pre = ("make Conductivity_interface.o Conductivity_fullState.o "
           "mgd_qesh.o 2>&1 | tail -3; ") if spec["has_snb"] else ""
    cmd = (f'cd "{obj}" && {pre}'
           f'if make -j{jobs} > make_scene.log 2>&1; then echo MAKE_OK; '
           f'else echo MAKE_FAIL; fi; tail -25 make_scene.log; '
           f'test -x ./flash4 && echo FLASH4_OK || echo NO_FLASH4')
    _, out = wsl(cmd, distro, 5400)
    ok = "MAKE_OK" in out and "FLASH4_OK" in out
    if ok:
        log(f"[{side}] 编译完成", "OK")
    else:
        log(f"[{side}] 编译失败:\n{out[-2000:]}", "ERROR")
    return ok


def run_leg(side: str, scene: Path, tree: str, distro: str, nproc: int,
            tag: str, out_root: Path, par_name: Optional[str] = None,
            basenm: Optional[str] = None,
            log_file: Optional[str] = None) -> Tuple[bool, float]:
    """跑一条腿(一个辐射状态)。

    ★ 2×2 矩阵下同一 objdir 要跑两次: par_name/basenm/log_file 三者
      随辐射状态不同, 否则输出会互相覆盖 (basenm 从 par 中解析)。
    """
    spec = LEG_SPECS[side]
    obj = f"{tree}/{spec['objdir']}"
    out_dir = out_root / f"sim_{side}" / (tag or "default")
    out_dir.mkdir(parents=True, exist_ok=True)

    # basenm/log_file 以 **par 内实际值** 为准 (由 gen_scene 写入, 带辐射标记)
    par_src = scene / f"sim_{side}" / "flash_input" / (par_name or spec["par"])
    ptext = par_src.read_text(encoding="utf-8", errors="replace")
    def _pick(key: str, default: str) -> str:
        for ln in ptext.splitlines():
            t = ln.split("#", 1)[0].strip()
            if t.startswith(f"{key} ") or t.startswith(f"{key}="):
                v = t.split("=", 1)[1].strip().strip('"') if "=" in t else default
                return v or default
        return default
    bnm = basenm or _pick("basenm", spec["basenm"])
    lgf = log_file or _pick("log_file", spec["log_file"])
    par_local = out_dir / f"par_{side}{('_' + tag) if tag else ''}.par"
    par_local.write_text(ptext, encoding="utf-8", newline="\n")
    wsl(f'cp -f {to_wsl(par_local)} "{obj}/flash.par"', distro, 120)

    # 落盘确认关键设置
    _, chk = wsl(f'grep -nE "^(dtmax|tmax|iProcs|diff_eleFlMode|rt_useMGD|'
                 f'useOpacity|useRadTrans|checkpointFileIntervalTime)" '
                 f'"{obj}/flash.par"', distro, 120)
    print("    " + chk.strip().replace("\n", "\n    "))

    run_log = f"wsl_run_{side}{('_' + tag) if tag else ''}.log"
    log(f"[{side}] mpiexec -n {nproc} ./flash4 ...", "STEP")
    t0 = time.time()
    wsl(f'cd "{obj}" && rm -f {spec["basenm"]}* {run_log} && '
        f'if mpiexec -n {nproc} ./flash4 > {run_log} 2>&1; then '
        f'echo RUN_EXIT=0 >> {run_log}; else echo RUN_EXIT_NZ >> {run_log}; fi',
        distro, 21600)
    wall = time.time() - t0

    _, out = wsl(f'cd "{obj}" && grep -E "exiting|ABORT|Negative|Newton" '
                 f'{run_log} | tail -3; echo "--- chk ---"; '
                 f'ls {bnm}hdf5_chk_* 2>/dev/null | wc -l', distro, 180)
    print(out)

    # ★ 收集: 先校验后删
    out_wsl = to_wsl(out_dir)
    wsl(f'mkdir -p "{out_wsl}"', distro, 60)
    wsl(f'cp -f "{obj}"/{bnm}* "{out_wsl}"/ 2>&1 | head -3; '
        f'cp -f "{obj}"/{lgf} "{obj}"/{run_log} "{out_wsl}"/ 2>&1 | head -3',
        distro, 1200)
    n_local = len(list(out_dir.glob(f"{bnm}*hdf5_chk_*")))
    if n_local == 0:
        log(f"[{side}] 收集校验失败 (本地 chk=0), **保留** WSL 侧现场", "ERROR")
        return False, wall
    wsl(f'rm -f "{obj}"/{bnm}* 2>/dev/null', distro, 300)
    log(f"[{side}{('/' + tag) if tag else ''}] 收集 OK ({n_local} 帧) — "
        f"墙钟 {wall:.1f} s", "OK")

    # ★ 运行后健康检查: 以 chk 的 dt 实测值判定 dtmax 是否生效 (docs/08)
    exp_dtmax: Optional[float] = None
    try:
        exp_dtmax = float(_pick("dtmax", ""))
    except (TypeError, ValueError):
        exp_dtmax = None
    healthy = verify_run_health(out_dir, bnm, exp_dtmax, distro)
    if not healthy:
        log(f"[{side}] 健康检查**未通过** —— 见上方 dt / 守恒告警", "ERROR")

    with (out_dir / "walltime.txt").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{side}\t{tag}\t{nproc}\t{wall:.2f}\n")
    return healthy, wall


# ══════════════════════════════════════════════════════════════
def verify_run_health(out_dir: Path, bnm: str, expect_dtmax: Optional[float],
                      distro: str) -> bool:
    """★ 运行后健康检查: 以 chk 的 `dt` 实测值判定 `dtmax` 是否生效。

    铁律 (docs/08): `dtmax` **不能**看 par 文本判定(会被命令行覆写),
    必须读 chk 里 `real scalars` 的 `dt`:
        dt 全程钉死 == dtmax  → 生效 ✓
        dt 随步进增长          → 未生效 ✗ → 必崩
    """
    chks = sorted(out_dir.glob(f"{bnm}*hdf5_chk_*"))
    if not chks:
        return True                                   # 无 chk 则跳过 (上层已判)
    try:
        import h5py  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
    except ImportError:
        log("未安装 h5py, 跳过 dt 健康检查", "WARN")
        return True

    dts, rmax, rsum = [], [], []
    for c in chks:
        try:
            with h5py.File(c, "r") as f:
                # 'real scalars' 是复合 Dataset 非 Group
                for row in f["real scalars"][()]:
                    nm = row["name"]
                    nm = nm.decode().strip() if isinstance(nm, bytes) else str(nm).strip()
                    if nm == "dt":
                        dts.append(float(row["value"]))
                d = f["dens"]
                a = (np.concatenate([np.asarray(d[k][()]).ravel() for k in d.keys()])
                     if hasattr(d, "keys") else np.asarray(d[()]).ravel())
                rmax.append(float(a.max()))
                rsum.append(float(a.sum()))
        except Exception:                             # noqa: BLE001
            continue

    if len(dts) < 2:
        return True
    body = dts[1:]                                    # 跳过首帧 dtinit
    ok = True

    # ① dt 钳位
    if expect_dtmax:
        rel = max(abs(x - expect_dtmax) / expect_dtmax for x in body)
        if rel < 1e-6:
            log(f"dt 全程钳位 = {expect_dtmax:.3e} ✓", "OK")
        else:
            log(f"dt **未**全程钳位! 期望 {expect_dtmax:.3e}, "
                f"实测 {body[0]:.3e} → {body[-1]:.3e} (最大偏差 {rel:.2e})", "ERROR")
            ok = False
    grew = body[-1] / body[0] if body[0] > 0 else 1.0
    if len(body) > 3 and grew > 1.05:
        log(f"dt 单调增长 {body[0]:.3e} → {body[-1]:.3e} ({grew:.2f}×) "
            f"—— 崩塌特征, 请检查 dtmax", "ERROR")
        ok = False

    # ② 守恒 / 崩塌
    if not all(x == x and abs(x) != float("inf") for x in rsum):   # NaN/Inf
        log("总质量出现 NaN/Inf → 守恒破裂", "ERROR")
        ok = False
    if rmax and len(rmax) > 3:
        pk = max(rmax)
        i_pk = rmax.index(pk)
        if pk > 2 and rmax[-1] < pk * 0.5:
            # ★★ 必须区分「物理稀疏化」与「数值跌崖」——
            #   物理: 冲击波过后靶膨胀稀疏化 → ρmax **平滑单调**下降（单帧跌幅小）；
            #         实测 1.6 ns 场景: SNB 6.57→1.97、FL-SH 8.10→1.93（**两模型一致**，
            #         且 FL-SH 跌得更多）⇒ 与热传导模型无关, 属物理。
            #   数值: 单帧**断崖**式下跌（曾见一步 10.5→0.25）。
            #   判据: 看峰值之后的**单帧最大相对跌幅**。
            seg = rmax[i_pk:]
            steps = [(seg[j] - seg[j + 1]) / seg[j]
                     for j in range(len(seg) - 1) if seg[j] > 0]
            worst = max(steps) if steps else 0.0
            if worst > 0.30:
                log(f"ρmax 峰值 {pk:.3f} → 末值 {rmax[-1]:.3f}，单帧最大跌幅 "
                    f"{worst * 100:.1f}% → **断崖式下跌, 判为崩塌**", "ERROR")
                ok = False
            else:
                log(f"ρmax 峰值 {pk:.3f} → 末值 {rmax[-1]:.3f}"
                    f"（{rmax[-1] / pk:.2f}×）为**平滑衰减**（单帧最大跌幅 "
                    f"{worst * 100:.1f}%）—— 长时冲击波过后的靶稀疏化, "
                    f"**非数值崩塌**（与 FL-SH 侧同窗口行为一致）", "WARN")
    return ok


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 场景运行驱动")
    ap.add_argument("--scene", required=True, help="gen_scene.py 生成的场景目录")
    ap.add_argument("--side", choices=["snb", "flsh", "both"], default="both")
    ap.add_argument("--tag", default="", help="输出子目录名")
    ap.add_argument("--par", default=None,
                    help="指定要跑的 par 文件名 (默认 <leg>.par); "
                         "2×2 矩阵下用 <leg>_radon.par / <leg>_radoff.par")
    ap.add_argument("--out-root", default=None,
                    help="输出根目录 (默认 = 场景目录/flash_output)")
    ap.add_argument("--nxb", type=int, default=P.GRID_REFERENCE["nxb"])
    ap.add_argument("--iprocs", type=int, default=P.GRID_REFERENCE["iprocs"])
    ap.add_argument("--species", default="cham,tar1,tar2,tar3")
    ap.add_argument("--tables", default=None,
                    help="场景用到的 .cn4 表清单 (逗号分隔); "
                         "默认取 snb_params.SPECIES —— 2 标记场景"
                         "(cham+targ) 需显式指定")
    ap.add_argument("--pulse-sections", type=int, default=300,
                    help="setup 的 ed_maxPulseSections (多段激光脉冲必需, 默认 300)")
    ap.add_argument("--ng", type=int, default=P.RADIATION["rt_mgdNumGroups"])
    ap.add_argument("--distro", default="Ubuntu-22.04")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    scene = Path(args.scene).resolve()
    out_root = Path(args.out_root).resolve() if args.out_root else scene / "flash_output"
    sides = ["snb", "flsh"] if args.side == "both" else [args.side]
    species = [x.strip() for x in args.species.split(",") if x.strip()]
    tables = [x.strip() for x in args.tables.split(",") if x.strip()] \
        if args.tables else None

    print("\n" + "=" * 78)
    print(" SNB 场景运行驱动")
    print(f" 场景: {scene}")
    print(f" 腿: {sides}   网格: iProcs={args.iprocs} × nxb={args.nxb} = "
          f"{args.iprocs*args.nxb} 格")
    print("=" * 78)

    par_map = {s_: args.par for s_ in sides} if args.par else {}

    if args.check_only:
        ok = precheck(scene, sides, args.distro, par_map, tables)
        print()
        log("前置检查通过 ✓" if ok else "前置检查未通过", "OK" if ok else "ERROR")
        return 0 if ok else 1

    if not precheck(scene, sides, args.distro, par_map, tables):
        return 1

    results: Dict[str, bool] = {}
    for side in sides:
        tree = find_tree(side, args.distro)
        if not tree:
            log(f"[{side}] 未找到 FLASH 树", "ERROR")
            results[side] = False
            continue
        print(f"\n{'─'*78}\n [{side}] 树 = {tree}\n{'─'*78}")
        obj = f"{tree}/{LEG_SPECS[side]['objdir']}"

        # ── ★★ 首次使用场景 (或换了场景) 必须重新编译 ──────────────
        #    objdir 名固定 → 不同场景会复用同一 objdir; 沿用旧 flash4 会把
        #    别的场景的二进制当成当前场景结果 (静默错误)。用构建指纹判定。
        fp_now = build_fingerprint(scene, side, args.nxb, args.iprocs,
                                   species, args.ng)
        fp_old = read_fingerprint(obj, args.distro)
        built = has_flash4(obj, args.distro)
        skip_setup, skip_make = args.skip_setup, args.skip_make
        if not built:
            log(f"[{side}] objdir 无可用 flash4 → 必须 setup+make", "WARN")
            skip_setup = skip_make = False
        elif fp_now and fp_old != fp_now:
            why = "无构建指纹记录" if not fp_old else "源码/参数已变化"
            log(f"[{side}] 构建指纹不匹配（{why}）→ **强制重新 setup+make**"
                f"（忽略 --skip-setup/--skip-make）", "WARN")
            log(f"      记录 {fp_old[:12] or '(无)'}…  当前 {fp_now[:12]}…", "INFO")
            skip_setup = skip_make = False
        else:
            log(f"[{side}] 构建指纹一致 ({fp_now[:12]}…) → 可复用已编译二进制", "OK")

        if not args.skip_deploy and not deploy(side, scene, tree, args.distro):
            results[side] = False
            continue
        if not skip_setup and not do_setup(side, scene, tree, args.distro,
                                           args.nxb, args.iprocs,
                                           species, args.ng,
                                           args.pulse_sections):
            results[side] = False
            continue
        if not skip_make and not do_make(side, tree, args.distro, args.jobs):
            results[side] = False
            continue
        if not skip_make and fp_now:
            wsl(f'echo "{fp_now}" > "{obj}/{BUILD_FP_FILE}"', args.distro, 60)
            log(f"[{side}] 构建指纹已记录 ({fp_now[:12]}…) —— 下次同源可跳过重编",
                "OK")
        ok, _ = run_leg(side, scene, tree, args.distro, args.iprocs,
                        args.tag, out_root, par_name=args.par)
        results[side] = ok

    print("\n" + "=" * 78)
    for s, ok in results.items():
        log(f"{s}: {'完成' if ok else '失败'}", "OK" if ok else "ERROR")
    print("=" * 78)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
