"""SNBOneCH_ml NC-E 核数短时仿真 —— **并行多作业**提交 (2026-09-12)。

背景
----
`SNBOneCH_ml.py --probe-cores` 是**单作业内串行**跑各核数 (总时长 = 各核数之和),
而用户要求「**并行提交几个不同的任务进行短时仿真测试**」→ 本脚本独立实现:
**每个核数一个独立 sbatch 作业**, 同时入队、各自独立 objdir、互不干扰。

★ 为什么必须独立 objdir
    `--ug` 下 `dx = 域宽/(nproc × nxb)`, 且 objdir 名固定 → 多作业共用同一 objdir
    会互相覆盖 `flash.par` 与 chk → **静默错误**。故本脚本为每个核数建
    `${OBJDIR}_n${nproc}` 独立 objdir, 各自 setup + make + run。

设计 (与既有机制对齐)
--------------------
* 复用 `run_hpc` 的既有约定: 部署目录 `resolve_deploy_dir()`,
  环境块 `_hpc_env_block()` (NC-E 禁 module purge + 补 HDF5 运行库),
  分区探测 `_hpc_detect_partition()`, 单元包上传 `unit.tar.gz`,
  "场景自包含优先 → 回落参考单元" 的 F90 复制分支。
* ★ `nxb` 由 `build_setup_flags_ug(nproc, xmin, xmax)` 按核数推导 —— **修掉**
  `run_hpc` 里 `SETUP_FLAGS` 硬编码 `-nxb=128` 的隐患 (131 核恰好巧合一致)。
* 提交前硬闸门: 远端 par 必须含 `gr_hypreUseFloor=.false.` (否则拒绝烧机时)。

用法
----
  python run_cores_parallel.py --cores 131,192,256 --tmax 2.0e-10
  python run_cores_parallel.py --cores 131,192,256 --tmax 2.0e-10 --dry-run
  python run_cores_parallel.py --submit-only      # 只提交不收集
  python run_cores_parallel.py --collect           # 只收集已完成的作业

依赖: 凭据 `flash_ssh` (NC-E); 远端 FLASHSNB 树与 flash4 已存在。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
# 仓库根: .../flash  (本文件在 flash/scenarios/private/tracer/SNB/SNBOneCH_ml/)
ROOT = SCRIPT_DIR.parents[4]

# ── 直接复用核心模块的既有函数与常量 (禁止重写) ─────────────
import SNBOneCH_ml as M  # noqa: E402

ACCOUNT = "flash_ssh"          # NC-E scfa2696
TMAX_DEFAULT = "2.0e-10"       # 短时; 与上一轮 131 核基线同 tmax, 便于时间戳配对比对
CORES_DEFAULT = "131,192,256"
PARTITION_FALLBACK = "v5_192"


def _sh(msg: str) -> None:
    print(f"\n{'=' * 70}\n {msg}\n{'=' * 70}", flush=True)


def _state_file() -> Path:
    return SCRIPT_DIR / "cores_parallel_jobs.json"


def _load_state() -> dict:
    p = _state_file()
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def _save_state(st: dict) -> None:
    _state_file().write_text(
        json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


# ────────────────────────────────────────────────────────────
# 单元包: 一个共享包 (所有核数相同), 只上传一次
# ────────────────────────────────────────────────────────────
def _build_unit_package(deploy_upload_fn) -> bool:
    """打包并上传单元文件 (复用 run_hpc 的文件清单与缺失策略)。"""
    import tempfile
    unit_files = (["Config", "Makefile", "Simulation_data.F90",
                   "Simulation_init.F90", "Simulation_initBlock.F90",
                   M.PAR_FILENAME,
                   "He-BADGER-TOPS-Final.cn4", "CH-QC-1-001.cn4",
                   "CH-BADGER-TOPS-Final.cn4"]
                  + list(M.SNB_OVERRIDE_FILES))
    present, missing_ovr, hard_missing = [], [], []
    for f in unit_files:
        if (M.INPUT_DIR / f).exists():
            present.append(f)
        elif f in M.SNB_OVERRIDE_FILES:
            missing_ovr.append(f)
        else:
            hard_missing.append(f)
    if hard_missing:
        M.log(f"单元必需文件缺失: {hard_missing}", "ERROR")
        return False
    # ★ 直接用 tarfile 追加, 不写中间文件到 INPUT_DIR (保持目录整洁)
    tmp = Path(tempfile.mkdtemp(prefix="snb_unit_")) / "unit.tar.gz"
    with tarfile.open(tmp, "w:gz") as tf:
        for f in present:
            tf.add(M.INPUT_DIR / f, arcname=f)
    ok = deploy_upload_fn(str(tmp), "unit.tar.gz")
    try:
        tmp.unlink()
        tmp.parent.rmdir()
    except OSError:
        pass
    if not ok:
        M.log("单元包上传失败", "ERROR")
        return False
    M.log(f"单元包已上传 ({len(present)} 本地文件"
          + (f" + {len(missing_ovr)} 远端兜底" if missing_ovr else "") + ")", "OK")
    return True


# ────────────────────────────────────────────────────────────
# 单个核数的作业脚本 (独立 objdir)
# ────────────────────────────────────────────────────────────
def _make_job_sh(nproc: int, tmax: str, snb_home: str, deploy_dir: str,
                 env_block: str, partition: str, nxb: int, dx_um: float,
                 nodes: int, overrides: str, sim_name: str,
                 flags: str) -> str:
    obj = f"{M.OBJDIR}_n{nproc}"
    return f"""#!/bin/bash
#SBATCH --job-name=SNB1CH_c{nproc}_{ACCOUNT and 'nce'}
#SBATCH -p {partition}
#SBATCH -N {nodes}
#SBATCH --ntasks={nproc}
#SBATCH --output=c{nproc}_%j_out.txt
#SBATCH --error=c{nproc}_%j_err.txt
set -e
{env_block}cd {deploy_dir} && tar xzf unit.tar.gz -C _unit_{nproc} --strip-components=0 2>/dev/null || {{
  mkdir -p _unit_{nproc} && cd _unit_{nproc} && tar xzf ../unit.tar.gz; }}
cd {deploy_dir}/_unit_{nproc}
UNIT={snb_home}/source/Simulation/SimulationMain/{sim_name}
REF={snb_home}/source/Simulation/SimulationMain/SNB_1D_laser
mkdir -p "$UNIT"
cp -f Config Makefile Simulation_data.F90 Simulation_init.F90 \\
      Simulation_initBlock.F90 *.cn4 "$UNIT"/
for f in {overrides}; do
  if [ -f "$f" ]; then cp -f "$f" "$UNIT/$f" || exit 9;   # 场景自包含优先
  else cp -f "$REF/$f" "$UNIT/$f" || exit 9; fi           # 回落参考单元
done
echo UNIT_DEPLOYED $(ls "$UNIT" | wc -l)
# Makefile.h 防御 (与既有 run_hpc 同策略; 已备份则跳过)
NORM=~/{M.SIM_USER_DIR}/FLASH/FLASH4.8
if [ -f "$NORM/Makefile.h" ] && [ ! -f {snb_home}/Makefile.h.hpc_bak ]; then
  cp {snb_home}/Makefile.h {snb_home}/Makefile.h.hpc_bak
  cp "$NORM/Makefile.h" {snb_home}/Makefile.h
  echo MAKEFILE_H_FROM_NORMAL
fi
# ★ 独立 objdir: 多作业不共享 → 不会互相覆盖 par / chk
cd {snb_home} && rm -rf {obj}
./setup -auto {sim_name} {flags} -objdir={obj} > setup_{nproc}.log 2>&1 || {{
  tail -25 setup_{nproc}.log; echo SETUP_FAIL; exit 2; }}
ls -d {obj} && echo SETUP_OK
cd {obj}
ln -sf ../source/Simulation/SimulationMain/{sim_name}/mgd_qesh.F90 mgd_qesh.F90 || true
# ★★ 防御 (同 SNBOneCH_ml.py 的既有铁律): setup 只为"当时已知"的表建软链;
#   本场景 par 引用 CH-BADGER-TOPS-Final.cn4, 若它未被链接 → 运行时报
#   "[eos_tabBrowseIonmix4Tables] ERROR: IONMIX4 file not found: CH-BADGER-...".
#   故**无条件**把单元目录下全部 *.cn4 软链进 objdir。
#   铁律: 不在命令串内联含变量的 for 循环 ($f 会被 shell 展开吞掉);
#   此处为单层远端脚本, $f 安全。
for f in {snb_home}/source/Simulation/SimulationMain/{sim_name}/*.cn4; do
  ln -sf "$f" "./$(basename "$f")"
done
echo "CN4_LINKED=$(ls -1 ./*.cn4 2>/dev/null | wc -l)"
for t in $(grep -oE '(eos_|op_)[a-z0-9]+(TableFile|FileName)[[:space:]]*=[[:space:]]*\"[^\"]+\"' flash.par | sed 's/.*\"\\(.*\\)\"/\\1/' | sort -u); do
  if [ -e "$t" ]; then echo "TABLE_OK $t"; else echo "TABLE_MISSING $t"; fi
done
make hy_slopeLimiters.o Conductivity_interface.o Conductivity_fullState.o 2>&1 | tail -2
if make -j8 > make_{nproc}.log 2>&1; then echo MAKE_OK; else
  echo MAKE_FAIL; tail -30 make_{nproc}.log; exit 3; fi
test -x flash4 && echo BUILD_OK
# ── 运行 ──
rm -f {M.BASENM}* wsl_run_{nproc}.log
cp -f {deploy_dir}/_unit_{nproc}/{M.PAR_FILENAME} flash.par
sed -i "s/^iProcs.*/iProcs = {nproc}/" flash.par
sed -i 's/^tmax.*/tmax           = {tmax}/' flash.par
echo "JOB_NPROC={nproc} NXB={nxb} DX_UM={dx_um}"
grep -E '^(iProcs|tmax|dtmax|gr_hypreUseFloor|diff_eleFlMode|rt_mgdNumGroups)' flash.par
date +%s.%N > _t_start
if mpiexec -n {nproc} ./flash4 > wsl_run_{nproc}.log 2>&1; then
  echo RUN_EXIT=0 >> wsl_run_{nproc}.log
else
  echo RUN_EXIT_NZ >> wsl_run_{nproc}.log
fi
date +%s.%N > _t_end
W=$(echo "$(cat _t_end) - $(cat _t_start)" | bc -l)
echo "WALL_SECONDS=$W" >> wsl_run_{nproc}.log
tail -5 wsl_run_{nproc}.log
echo RUN_DONE
"""


def submit_all(args) -> dict:
    cores = [int(c) for c in re.split(r"[,\s]+", args.cores.strip()) if c]
    st = _load_state()
    results = {}

    with M._HpcRemote(ACCOUNT) as remote:
        out, _, _ = remote.run(
            "which sbatch >/dev/null 2>&1 && echo SBATCH_OK; echo USER=$(whoami)",
            timeout=30)
        M.log(f"远端: {out.strip()[:120]}", "OK")
        snb_home = M._remote_snb_home()
        deploy_dir = M.resolve_deploy_dir(remote, cache_key=ACCOUNT)
        M.log(f"部署目录: {deploy_dir}", "OK")

        out, _, _ = remote.run(f"ls -d {snb_home}/setup 2>/dev/null || echo NO_SETUP",
                               timeout=30)
        if "NO_SETUP" in out:
            M.log(f"远端 FLASHSNB 树不存在: {snb_home}", "ERROR")
            return {}

        partition = args.partition or M._hpc_detect_partition(remote, ACCOUNT)
        M.log(f"SLURM 分区: {partition}", "OK")
        out, _, _ = remote.run(
            f"sinfo -h -p {partition} -o \"%c\" | head -1", timeout=30)
        try:
            cpn = int(out.strip().splitlines()[0])
        except (ValueError, IndexError):
            cpn = 48
        M.log(f"每节点核数: {cpn}", "OK")

        # ★ 单元包只上传一次 (所有核数共用)
        _sh("STEP 1: 打包并上传单元文件")
        if not _build_unit_package(
                lambda l, r: remote.upload(l, f"{deploy_dir}/{r}")):
            return {}

        # ★ 提交前闸门: 远端 par 必须含 SNB 关键键
        chk, _, _ = remote.run(
            f"grep -E '^gr_hypreUseFloor[[:space:]]*=' "
            f"{deploy_dir}/unit.tar.gz 2>/dev/null; "
            f"cd {deploy_dir} && mkdir -p _gate && tar xzf unit.tar.gz -C _gate "
            f"&& grep -E '^gr_hypreUseFloor[[:space:]]*=' "
            f"_gate/{M.PAR_FILENAME} || echo MISSING", timeout=120)
        if "MISSING" in chk or ".false." not in chk:
            M.log(f"提交前闸门失败: 单元包 par 缺 gr_hypreUseFloor=.false. "
                  f"(got: {chk.strip()[-120:]}); 拒绝提交", "ERROR")
            return {}
        M.log(f"提交前闸门通过: {chk.strip().splitlines()[-1][:60]}", "OK")

        env_block = M._hpc_env_block(snb_home, ACCOUNT)
        overrides = " ".join(M.SNB_OVERRIDE_FILES)

        _sh(f"STEP 2: 并行提交 {len(cores)} 个独立作业 (cores={cores})")
        for nproc in cores:
            _flags, nxb, dx_cm = M.build_setup_flags_ug(
                nproc, M.config_constants["xmin"], M.config_constants["xmax"])
            dx_um = dx_cm * 1e4
            cpL = 1.0e-5 / dx_cm
            nodes = max(1, -(-nproc // cpn))
            if dx_cm > M.UG_DX_MAX_CM:
                M.log(f"  nproc={nproc}: dx={dx_um:.5f}µm **超过 0.03µm 门槛** — 跳过",
                      "ERROR")
                continue
            M.log(f"  nproc={nproc}: nxb={nxb}, dx={dx_um:.5f}µm "
                  f"({cpL:.2f} 格/0.1µm 层), -N {nodes}", "STEP")

            sh = _make_job_sh(nproc, args.tmax, snb_home, deploy_dir, env_block,
                              partition, nxb, dx_um, nodes, overrides,
                              M.SIM_NAME, _flags)
            local_sh = M.INPUT_DIR / f"_hpc_coretest_{nproc}.sh"
            local_sh.write_text(sh, encoding="utf-8", newline="\n")
            if args.dry_run:
                M.log(f"  [dry-run] 脚本已写 {local_sh.name} (未上传/未提交)", "INFO")
                continue
            remote_sh = f"{deploy_dir}/coretest_{nproc}.sh"
            if not remote.upload(str(local_sh), remote_sh):
                M.log(f"  nproc={nproc} 脚本上传失败", "ERROR")
                continue
            local_sh.unlink(missing_ok=True)
            out, _, _ = remote.run(
                f"chmod +x {remote_sh} && bash -n {remote_sh} && echo SCRIPT_OK",
                timeout=30)
            if "SCRIPT_OK" not in out:
                M.log(f"  nproc={nproc} 脚本语法校验失败: {out[-200:]}", "ERROR")
                continue
            # ★ 先清理旧的同核数输出, 避免读到上一轮
            remote.run(f"cd {deploy_dir} && rm -f c{nproc}_*_out.txt "
                       f"c{nproc}_*_err.txt", timeout=30)
            out, _, _ = remote.run(
                f"cd {deploy_dir} && sbatch {remote_sh} 2>&1", timeout=60)
            m = re.search(r"Submitted batch job (\d+)", out)
            if not m:
                M.log(f"  nproc={nproc} sbatch 提交失败: {out[-250:]}", "ERROR")
                continue
            jid = m.group(1)
            M.log(f"  ✓ nproc={nproc} → JobID={jid}", "OK")
            results[str(nproc)] = {"jobid": jid, "nxb": nxb, "dx_um": dx_um,
                                   "cells_per_layer": cpL, "nodes": nodes,
                                   "objdir": f"{M.OBJDIR}_n{nproc}"}
            st[str(nproc)] = results[str(nproc)]

    st["_submitted_at"] = datetime.now().strftime("%F %T")
    st["_tmax"] = args.tmax
    st["_partition"] = partition if results else st.get("_partition", "")
    _save_state(st)
    _sh("提交汇总")
    for n, v in sorted(results.items(), key=lambda kv: int(kv[0])):
        print(f"  nproc={n:>4}  JobID={v['jobid']:<10} nxb={v['nxb']:<5} "
              f"dx={v['dx_um']:.5f}µm  {v['cells_per_layer']:.2f} 格/层")
    print(f"\n  状态文件: {_state_file()}")
    return results


def poll_and_collect(args) -> int:
    st = _load_state()
    cores = [k for k in st if not k.startswith("_")]
    if not cores:
        M.log("无可收集作业 (先 --submit-only 或直接提交)", "ERROR")
        return 1
    deploy_dir_cached = st.get("_deploy_dir")

    with M._HpcRemote(ACCOUNT) as remote:
        # ★★ 铁律: paramiko SFTP **不展开 `~`** (仓库既有约定, 见 SNBOneCH_ml.py:1082)。
        #   `M._remote_snb_home()` 返回的是 `~/QC/FLASH/FLASHSNB/FLASH4.8` **字面**形式,
        #   直接喂给 remote.download() 会 stat 失败 → 返回 False → **0 字节静默失败**
        #   (2026-09-12 事故: 21 个文件全部 0 字节, 汇总显示 "收集 0/8")。
        #   SNBOneCH_ml.py 自身走 session._res() 展开; 本脚本必须显式解析成绝对路径。
        snb_home = _abs_snb_home(remote)
        deploy_dir = deploy_dir_cached or M.resolve_deploy_dir(
            remote, cache_key=ACCOUNT)
        st["_deploy_dir"] = deploy_dir
        _save_state(st)
        out_dir = M.OUTPUT_DIR / f"hpc_{ACCOUNT}" / "cores_parallel"
        out_dir.mkdir(parents=True, exist_ok=True)

        # ── 等待全部作业结束 (每 60s 轮询) ──
        _sh(f"STEP 3: 轮询 {len(cores)} 个作业")
        allowed = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL",
                   "OUT_OF_MEMORY"}
        deadline = time.time() + args.poll_timeout
        done: dict = {}
        while time.time() < deadline:
            line_parts, all_done = [], True
            for n in sorted(cores, key=int):
                jid = st[n]["jobid"]
                o, _, _ = remote.run(
                    f"sacct -j {jid} --format=State --noheader 2>/dev/null "
                    f"| head -1", timeout=30)
                s = (o.strip().splitlines() or [""])[0].strip()
                s = s.rstrip("+")
                line_parts.append(f"{n}:{s or '?'}")
                if s not in allowed:
                    all_done = False
            print(f"  [{datetime.now():%H:%M:%S}] " + "  ".join(line_parts),
                  flush=True)
            if all_done:
                done = {n: "done" for n in cores}
                break
            time.sleep(60)
        if not done:
            M.log(f"轮询超时 ({args.poll_timeout}s) — 仍可稍后 --collect", "WARN")
            return 1

        # ── 收集 ──
        _sh("STEP 4: 收集各核数输出")
        summary = []
        for n in sorted(cores, key=int):
            info = st[n]
            obj = info["objdir"]
            job_out = f"{deploy_dir}/c{n}_*_out.txt"
            o, _, _ = remote.run(
                f"grep -E 'RUN_EXIT|WALL_SECONDS|JOB_NPROC|SETUP_OK|MAKE_OK|BUILD_OK' "
                f"{job_out} 2>/dev/null | tail -8", timeout=30)
            o2, _, _ = remote.run(
                f"cd {snb_home}/{obj} 2>/dev/null && "
                f"grep -E 'tmax|dtmax|iProcs' flash.par 2>/dev/null | head -5; "
                f"echo ---; ls {M.BASENM}* 2>/dev/null | wc -l", timeout=30)
            # 从 wsl_run log 抓墙钟
            o3, _, _ = remote.run(
                f"cd {snb_home}/{obj} 2>/dev/null && "
                f"grep -E 'WALL_SECONDS|RUN_EXIT' wsl_run_{n}.log 2>/dev/null",
                timeout=30)
            info["job_tail"] = o.strip()
            info["run_tail"] = o3.strip()
            wall = None
            mw = re.search(r"WALL_SECONDS=([\d.]+)", o3)
            if mw:
                wall = float(mw.group(1))
            nplots = 0
            mo = re.search(r"^(\d+)$", o2.strip().splitlines()[-1]
                           if o2.strip() else "")
            # 收集文件 (禁 rm: 幂等重跑)
            names_out, _, _ = remote.run(
                f"cd {snb_home}/{obj} 2>/dev/null && ls {M.BASENM}* "
                f"wsl_run_{n}.log 2>/dev/null; echo LIST_END", timeout=30)
            names = [l.strip() for l in names_out.splitlines()
                     if l.strip() and l.strip() != "LIST_END"]
            sub = out_dir / f"n{nproc_str(n)}"
            sub.mkdir(parents=True, exist_ok=True)
            got = _fetch_parallel(remote, f"{snb_home}/{obj}", names, sub)
            M.log(f"  nproc={n}: 收集 {got}/{len(names)} 文件 → {sub.name}/, "
                  f"墙钟={wall if wall else 'N/A'}", "OK")
            summary.append({"nproc": int(n), "nxb": info["nxb"],
                            "dx_um": info["dx_um"],
                            "cells_per_layer": info["cells_per_layer"],
                            "wall_s": wall, "files": got, "total": len(names),
                            "job_tail": o.strip()})
        (out_dir / "cores_parallel_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        _sh("核数短时测试汇总")
        hdr = f"  {'nproc':>6} {'nxb':>6} {'dx[µm]':>9} {'格/0.1µm层':>11} {'墙钟[s]':>10} {'文件':>8}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))
        for s in summary:
            ws = f"{s['wall_s']:.1f}" if s["wall_s"] else "N/A"
            print(f"  {s['nproc']:>6} {s['nxb']:>6} {s['dx_um']:>9.5f} "
                  f"{s['cells_per_layer']:>11.2f} {ws:>10} "
                  f"{s['files']:>3}/{s['total']:<4}")
        print(f"\n  汇总: {out_dir / 'cores_parallel_summary.json'}")
    return 0


def _abs_snb_home(remote) -> str:
    """把 `~/<user>/FLASH/FLASHSNB/FLASH4.8` 解析成远端**绝对**路径。

    ★ 必需: paramiko SFTP 不展开 `~` (仓库铁律), 直接传 `~/...` 会 stat 失败。
    ★★ 稳健性: 用户网络经常瞬断 → 单次探测可能返回空。多命令 × 多轮重试,
       任一成功即用; 全失败才抛错 (并给出手动诊断路径)。
    """
    lit = M._remote_snb_home()          # ~/QC/FLASH/FLASHSNB/FLASH4.8
    probes = ('printf %s "$HOME"', 'echo $HOME', 'cd ~ && pwd')
    home = ""
    for attempt in range(3):
        for pc in probes:
            try:
                out, _, _ = remote.run(pc, timeout=30)
            except Exception:  # noqa: BLE001
                continue
            cand = (out or "").strip()
            if cand.startswith("/"):
                home = cand
                break
        if home:
            break
        M.log(f"  $HOME 探测第 {attempt + 1} 轮为空, 5s 后重试 (网络瞬断?)", "WARN")
        time.sleep(5)
    if not home.startswith("/"):
        raise RuntimeError(
            f"远端 $HOME 探测失败 (3 轮 × 3 命令均为空); 无法解析 {lit} 为绝对路径。"
            f"手动诊断: ssh <host> -p <port> 'echo $HOME'")
    abs_home = home.rstrip("/") + "/" + lit[2:]        # 去掉 "~/"
    M.log(f"  snb_home(abs) = {abs_home}")
    return abs_home


def _fetch_parallel(remote, remote_dir: str, names: list, sub: Path) -> int:
    """并行下载 remote_dir 下的 names 到 sub/。

    ★ 为何并行: 单流实测仅 **~20 KB/s** (318 KB/15.6 s); 10 MB 的 chk 单流需
      ~500 s, 三档共 21 文件 ~200 MB → 串行约 2.7 h。每文件独立建连 (SFTP
      会话不可并发复用) + 逐文件字节数校验 + 已存在且大小匹配则跳过 (幂等)。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    sess = remote.session
    route = getattr(sess, "_route", None)
    _lock = threading.Lock()

    def _remote_size(rp: str):
        """取远端文件大小 (供幂等跳过 + 字节校验)。失败返回 None。

        ★ 不可用 sess.sftp: `RemoteSession` 的后端是 scp/paramiko 工厂函数,
          **没有** `sftp` 属性 (2026-09-12 实测 AttributeError)。走 SSH `stat`。
        """
        try:
            o, _, _ = remote.run(f"stat -c %s {rp} 2>/dev/null", timeout=40)
            v = (o or "").strip()
            return int(v) if v.isdigit() else None
        except Exception:  # noqa: BLE001
            return None

    def _remote_md5(rp: str):
        """★★ 完整性**唯一**可靠判据 (2026-09-12 定案)。

        实测: FLASH +ug chk **并非全部**能被 h5py 打开 —— 有文件 md5 与远端
        逐字节相同, 但 `h5py.File()` 抛 `OSError: file signature not found`。
        ⇒ 不可用 h5py 可打开性判定完整性; 字节数亦不足 (截断恰好等长概率低但
          传输层重试可能写出等长的坏数据)。此处在字节数之上再加 md5。
        """
        try:
            o, _, _ = remote.run(f"md5sum {rp} 2>/dev/null", timeout=90)
            v = (o or "").strip().split()[0] if o and o.strip() else ""
            return v if len(v) == 32 else None
        except Exception:  # noqa: BLE001
            return None

    def _local_md5(lp: Path):
        import hashlib
        try:
            h = hashlib.md5()
            with open(lp, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:  # noqa: BLE001
            return None

    def _one(nm: str):
        rp = f"{remote_dir}/{nm}"
        lp = sub / nm
        # 幂等: 本地已存在、远端大小一致、且 md5 相同 → 跳过
        exp = _remote_size(rp)
        if lp.exists() and exp is not None and lp.stat().st_size == exp and exp > 0:
            rm, lm = _remote_md5(rp), _local_md5(lp)
            if rm and lm and rm == lm:
                return nm, True, exp, exp, 0.0, "cache"
        t0 = time.time()
        ok = remote.download(rp, str(lp))
        dt = time.time() - t0
        act = lp.stat().st_size if lp.exists() else -1
        good = bool(ok) and act > 0 and (exp is None or act == exp)
        # ★★ 二次闸门: 字节数通过后仍须 md5 一致 (D2: _paramiko_get 截断时返回 True)
        verify = "size-only"
        if good and exp is not None:
            rm, lm = _remote_md5(rp), _local_md5(lp)
            if rm and lm:
                good = (rm == lm)
                verify = "md5-ok" if good else f"md5-FAIL(local={lm[:8]} remote={rm[:8]})"
        return nm, good, exp, act, dt, verify

    got = 0
    jobs = min(6, max(1, len(names)))
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(_one, nm): nm for nm in names}
        for fu in as_completed(futs):
            try:
                nm, good, exp, act, dt, verify = fu.result()
            except Exception as e:  # noqa: BLE001
                with _lock:
                    M.log(f"    ✗ {futs[fu]}: {type(e).__name__}: {e}", "WARN")
                continue
            if good:
                got += 1
                rate = (act / 1e6 / dt) if dt > 0 and act > 0 else 0.0
                with _lock:
                    M.log(f"    ✓ {nm}  {act:,} B  {dt:.1f}s  {rate:.2f} MB/s  [{verify}]")
            else:
                with _lock:
                    M.log(f"    ✗ {nm} (exp={exp} act={act} {verify})", "WARN")
    return got


def nproc_str(n) -> str:
    return str(n)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="NC-E 核数短时仿真 —— 并行多作业提交 (每核数独立 objdir)")
    ap.add_argument("--cores", default=CORES_DEFAULT,
                    help=f"逗号分隔核数 (默认 {CORES_DEFAULT})")
    ap.add_argument("--tmax", default=TMAX_DEFAULT,
                    help=f"结束时间 (默认 {TMAX_DEFAULT})")
    ap.add_argument("--partition", default="", help="SLURM 分区 (默认自动探测)")
    ap.add_argument("--poll-timeout", type=int, default=10800,
                    help="轮询上限秒 (默认 10800 = 3h)")
    ap.add_argument("--dry-run", action="store_true",
                    help="只生成脚本与打印配置, 不提交")
    ap.add_argument("--submit-only", action="store_true", help="只提交不收集")
    ap.add_argument("--collect", action="store_true", help="只收集已完成作业")
    args = ap.parse_args()

    print("#" * 70)
    print(f"# SNBOneCH_ml NC-E 核数并行短时测试  {datetime.now():%F %T}")
    print(f"# cores={args.cores}  tmax={args.tmax}  account={ACCOUNT}")
    print("#" * 70, flush=True)

    if args.collect:
        return poll_and_collect(args)

    res = submit_all(args)
    if not res:
        M.log("未成功提交任何作业", "ERROR")
        return 1
    if args.dry_run or args.submit_only:
        M.log(f"提交 {len(res)} 个作业; 稍后用 --collect 收集", "OK")
        return 0
    return poll_and_collect(args)


if __name__ == "__main__":
    sys.exit(main())
