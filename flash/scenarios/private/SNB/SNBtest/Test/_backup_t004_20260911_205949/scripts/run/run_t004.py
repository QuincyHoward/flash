"""t004 运行驱动 —— 「辐射开关」2×2 矩阵的四腿执行

用法 (在 t004 目录下):
    # 短时验证 (先跑这个)
    python scripts/run/run_t004.py --tmax 1.0e-11 --tag smoke

    # 完整四腿 (两侧)
    # ★ dtmax 必须用 2e-14 —— 判据来自 t004 自身 chk 内 real scalars 的 dt 实测值:
    #   最终帧 dt = 2.000e-14 全程钉死 (说明实际就是以 --dtmax 2e-14 覆写运行,
    #   尽管作者 objdir 的 flash.par 文本写的是 2.0e-12)。
    #   若改成 2e-12, dt 会增长到 ~4.6e-14 → SNB 腿非物理崩塌 (t005 实测 ρmax→0.26)。
    python scripts/run/run_t004.py --tmax 0.8e-9 --dtmax 2.0e-14

    # 单侧 (供并行两侧用)
    python scripts/run/run_t004.py --side flsh --tmax 0.8e-9 --dtmax 2.0e-14
    python scripts/run/run_t004.py --side snb  --tmax 0.8e-9 --dtmax 2.0e-14

★ 效率设计: **同侧两腿共用 objdir 与二进制** (辐射是纯 par 开关) →
  每侧只 deploy/setup/make **一次**, 然后换 par 跑两次。
  故 `--side` 可分两侧并行 (不同树/不同 objdir, 互不干扰)。

输出: t004/sim_<model>/flash_output/<radon|radoff>/
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_T004 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T004 / "common"))

import t004_common as C  # noqa: E402


# ══════════════════════════════════════════════════════════════
def ensure_tree_patches(tree: str, distro: str) -> None:
    t001 = C.wsl_path(C.T004_DIR.parent / "t001" / "source_patches")
    for rel in C.TREE_PATCHES:
        code, out = C.run_wsl(
            f'test -f "{tree}/source/{rel}" && echo HAVE || '
            f'( test -f "{t001}/{rel}" && mkdir -p "{tree}/source/{Path(rel).parent}" && '
            f'cp -f "{t001}/{rel}" "{tree}/source/{rel}" && echo SYNCED ) || echo MISSING',
            distro, timeout=90)
        if "HAVE" in out:
            C.log(f"树补丁已存在: {Path(rel).name}", "OK")
        elif "SYNCED" in out:
            C.log(f"树补丁同步: {Path(rel).name}", "OK")
        else:
            C.log(f"树补丁缺失且无归档: {rel}", "WARN")


def deploy_unit(side: str, tree: str, distro: str,
                driver_variant: str = "example") -> bool:
    """部署一侧单元 (两腿共用)。"""
    leg = C.leg_cfg(side, True)                 # 同侧两腿单元相同
    inp = C.leg_input_dir(side)
    unit = f"{tree}/source/Simulation/SimulationMain/{leg['sim_name']}"
    C.run_wsl(f'rm -rf "{unit}" && mkdir -p "{unit}"', distro, timeout=60)

    files = list(C.SHARED_FILES) + list(C.SHARED_CN4)
    cmd = "".join(f'cp -f {C.wsl_path(inp / f)} "{unit}/{f}" && ' for f in files)
    if side == "snb":
        for f in C.SNB_OVERRIDES:
            if f == "Driver_evolveFlash.F90" and driver_variant == "radon":
                continue
            cmd += f'cp -f {C.wsl_path(inp / f)} "{unit}/{f}" && '
        if driver_variant == "radon":
            dv = C.T004_DIR / "variants" / "Driver_evolveFlash_radON.F90"
            if not dv.exists():
                C.log(f"radON 变体缺失: {dv}", "ERROR")
                return False
            cmd += f'cp -f {C.wsl_path(dv)} "{unit}/Driver_evolveFlash.F90" && '
            C.log("SNB 驱动源 = radON 变体 (call RadTrans **已恢复**) → "
                  "par 三开关才能真正生效", "WARN")
        else:
            C.log("SNB 驱动源 = 作者原版 (call RadTrans 被注释 → 无法开辐射)", "WARN")
        cmd += f'cp -f {C.wsl_path(inp / C.DIFF_THERM_FILE)} "{unit}/{C.DIFF_THERM_FILE}" && '
    else:
        C.log("FL-SH 驱动源 = 标准树原生 (本就调用 RadTrans)", "OK")

    cmd += f'ls "{unit}" | wc -l && echo DEPLOY_OK'
    code, out = C.run_wsl(cmd, distro, timeout=600)
    if "DEPLOY_OK" not in out:
        C.log(f"单元部署失败: {out[-600:]}", "ERROR")
        return False
    n = out.strip().splitlines()[-2] if len(out.strip().splitlines()) > 1 else "?"
    C.log(f"单元已部署: {leg['sim_name']} ({n} 文件)", "OK")
    return True


def do_setup(side: str, tree: str, nxb: int, distro: str) -> bool:
    leg = C.leg_cfg(side, True)
    obj = f"{tree}/{leg['objdir']}"
    flags = C.setup_flags(nxb)
    cmd = (f'cd "{tree}" && rm -rf "{obj}" && '
           f'./setup -auto {leg["sim_name"]} {flags} -objdir={leg["objdir"]} '
           f'> setup_{side}.log 2>&1; '
           f'test -d "{obj}" && echo OBJ_OK || (tail -40 setup_{side}.log; echo OBJ_FAIL)')
    code, out = C.run_wsl(cmd, distro, timeout=1800)
    if "OBJ_OK" not in out:
        C.log(f"setup 失败:\n{out[-2000:]}", "ERROR")
        return False
    C.log(f"setup 完成 ({flags})", "OK")
    return True


def do_make(side: str, tree: str, distro: str, jobs: int = 4) -> bool:
    leg = C.leg_cfg(side, True)
    obj = f"{tree}/{leg['objdir']}"
    pre = ("make Conductivity_interface.o Conductivity_fullState.o "
           "mgd_qesh.o 2>&1 | tail -3; ") if side == "snb" else ""
    cmd = (f'cd "{obj}" && {pre}'
           f'if make -j{jobs} > make_t004.log 2>&1; then echo MAKE_OK; '
           f'else echo MAKE_FAIL; fi; tail -30 make_t004.log; '
           f'test -x ./flash4 && echo FLASH4_OK || echo NO_FLASH4')
    code, out = C.run_wsl(cmd, distro, timeout=5400)
    ok = "MAKE_OK" in out and "FLASH4_OK" in out
    if ok:
        mtime = C.run_wsl(f'stat -c %y "{obj}/flash4" 2>/dev/null',
                          distro, timeout=60)[1].strip()
        C.log(f"编译完成 (flash4: {mtime})", "OK")
    else:
        C.log(f"编译失败: {out[-2500:]}", "ERROR")
    return ok


def collect_verified(objdir: str, basenm: str, log_file: str, out_dir: Path,
                     run_log: str, distro: str = "Ubuntu-22.04") -> bool:
    """收集输出并以**本地 chk 帧数**校验; 仅在确认落盘后才删除 WSL 侧。

    ★ 血泪教训: 原 collect_outputs 用 `2>/dev/null` 静默吞错 + 复制完立即 rm,
      一旦路径/权限有问题就会**静默丢数据**。此处改为:
        ① 复制时不再吞错;
        ② 以本地 chk 计数作为成功判据 (n>0);
        ③ 只有成功才 rm WSL 侧, 否则保留现场供人工恢复。
    """
    out_wsl = C.wsl_path(out_dir)
    C.run_wsl(f'mkdir -p "{out_wsl}"', distro, timeout=60)
    code, out = C.run_wsl(
        f'cp -f "{objdir}"/{basenm}* "{out_wsl}"/ 2>&1 | head -5; '
        f'cp -f "{objdir}"/{log_file} "{objdir}"/{run_log} "{out_wsl}"/ 2>&1 | head -5; '
        f'echo "--- copied ---"; ls "{out_wsl}" | wc -l', distro, timeout=1200)
    n_local = len(list(out_dir.glob(f"{basenm}*hdf5_chk_*")))
    if n_local == 0:
        C.log(f"收集校验失败 (本地 chk=0), **保留** WSL 侧输出以便恢复:\n{out[-500:]}",
              "ERROR")
        return False
    C.run_wsl(f'rm -f "{objdir}"/{basenm}* 2>/dev/null; echo CLEANED', distro, timeout=300)
    C.log(f"收集校验通过: 本地 {n_local} 帧 chk ✓", "OK")
    return True


def run_one(side: str, rad_on: bool, tree: str, distro: str, nproc: int,
            tmax: Optional[float], tag_prefix: str,
            par_overrides: Optional[Dict[str, Any]] = None,
            run_timeout: int = 21600) -> Tuple[bool, float]:
    """跑一侧的一个辐射变体。tag = <tag_prefix>radon|radoff (前缀可为空)。"""
    leg = C.leg_cfg(side, rad_on)
    obj = f"{tree}/{leg['objdir']}"
    tag = f"{tag_prefix}{leg['tag']}"
    out_dir = C.leg_output_dir(side) / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    # ★ run_log 必须带 tag_prefix: 否则 smoke 与 full 共用日志名, 旧日志的
    #   RUN_EXIT=0 会被误读为本次运行已完成 (曾导致误判)。
    run_log = f"wsl_run_{side}_{tag}.log"

    par_src = C.leg_input_dir(side) / leg["par_file"]
    par_text = par_src.read_text(encoding="utf-8")
    if tmax:
        par_text = re.sub(r"(?m)^tmax\s*=.*$",
                          f"tmax = {float(tmax):.10e}   # [t004] run override",
                          par_text)
    for key, val in (par_overrides or {}).items():
        rep = (f"{key} = {val:.10e}   # [t004] diag override"
               if isinstance(val, float) else f"{key} = {val}   # [t004] diag override")
        new_text, n = re.subn(rf"(?m)^{key}\s*=.*$", rep, par_text)
        par_text = new_text if n else par_text.rstrip("\n") + f"\n{rep}\n"
    if par_overrides:
        C.log(f"par 诊断覆写: {par_overrides}", "WARN")

    par_local = out_dir / f"par_{side}_{tag}.par"
    par_local.write_text(par_text, encoding="utf-8", newline="\n")
    C.run_wsl(f'cp -f {C.wsl_path(par_local)} "{obj}/flash.par"', distro, timeout=180)

    # 落盘确认: 辐射三开关的实际生效值 + 关键控制量
    code, chk = C.run_wsl(
        f'grep -nE "^(rt_useMGD|useOpacity|useRadTrans|dtmax|tmax|diff_eleFlMode)" '
        f'"{obj}/flash.par"', distro, timeout=120)
    print("    " + chk.strip().replace("\n", "\n    "))

    C.log(f"[{side}/{'radON' if rad_on else 'radOFF'}] mpiexec -n {nproc} ...", "STEP")
    t0 = time.time()
    C.run_wsl(
        f'cd "{obj}" && rm -f {leg["basenm"]}* {run_log} && '
        f'if mpiexec -n {nproc} ./flash4 > {run_log} 2>&1; then '
        f'echo RUN_EXIT=0 >> {run_log}; else echo RUN_EXIT_NZ >> {run_log}; fi',
        distro, timeout=run_timeout)
    wall = time.time() - t0

    code, out = C.run_wsl(
        f'cd "{obj}" && grep -E "exiting|ERROR|ABORT|Negative" {run_log} | tail -3; '
        f'echo "--- chk/plt ---"; '
        f'ls {leg["basenm"]}hdf5_chk_* 2>/dev/null | wc -l; '
        f'ls {leg["basenm"]}hdf5_plt_cnt_* 2>/dev/null | wc -l', distro, timeout=180)
    print(out)
    collect_verified(obj, leg["basenm"], leg["log_file"], out_dir, run_log, distro)

    ok = ("RUN_EXIT=0" in out) or ("reached max SimTime" in out)
    C.log(f"[{side}/{'radON' if rad_on else 'radOFF'}] "
          f"{'成功' if ok else '异常'} — 墙钟 {wall:.1f} s", "OK" if ok else "ERROR")
    with (out_dir / "walltime.txt").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{side}\t{'radon' if rad_on else 'radoff'}\t{nproc}\t{tmax}\t"
                 f"{wall:.2f}\t{'OK' if ok else 'FAIL'}\n")
    return ok, wall


# ══════════════════════════════════════════════════════════════
def run_side(side: str, distro: str, nxb: int, iprocs: int,
             tmax: Optional[float], tag_prefix: str,
             skip_deploy: bool, skip_setup: bool, skip_make: bool,
             jobs: int, par_overrides: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    leg = C.leg_cfg(side, True)
    print("\n" + "=" * 78)
    print(f" t004 {leg['label'].split(' / ')[0]} 侧 —— 辐射开 / 关 两腿")
    print(f" 树: {'FLASHSNB' if leg['tree'] == 'snb' else '标准 FLASH'}   "
          f"驱动: {leg['driver_variant']}   objdir: {leg['objdir']} (两腿共用)")
    print(f" 网格 +ug: iProcs={iprocs} × nxb={nxb} = {nxb*iprocs} 格, "
          f"dx≈{C.dx_um(nxb, iprocs):.4f} µm")
    print("=" * 78)

    tree = C.find_tree(side, distro)
    if not tree or not C.tree_exists(tree, distro):
        C.log(f"FLASH 树不可用 (side={side})", "ERROR")
        return {"radon": False, "radoff": False}
    C.log(f"FLASH 树: {tree}", "OK")

    if not skip_deploy:
        if side == "snb":
            ensure_tree_patches(tree, distro)
        if not deploy_unit(side, tree, distro, leg["driver_variant"]):
            return {"radon": False, "radoff": False}
    if not skip_setup:
        if not do_setup(side, tree, nxb, distro):
            return {"radon": False, "radoff": False}
    if not skip_make:
        if not do_make(side, tree, distro, jobs=jobs):
            return {"radon": False, "radoff": False}

    res: Dict[str, bool] = {}
    # 辐射开在前 (与 t003 的 radON 结论对齐)
    for rad_on in (True, False):
        ok, _ = run_one(side, rad_on, tree, distro, iprocs, tmax,
                        tag_prefix, par_overrides)
        res["radon" if rad_on else "radoff"] = ok
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="t004 四腿运行驱动 (辐射 2×2)")
    ap.add_argument("--side", choices=["flsh", "snb", "both"], default="both")
    ap.add_argument("--tmax", type=float, default=None,
                    help=f"默认 {C.PARAMS['tmax']:.1e} s (示例值)")
    ap.add_argument("--nxb", type=int, default=None)
    ap.add_argument("--iprocs", type=int, default=None)
    ap.add_argument("--tag-prefix", default="",
                    help="输出子目录前缀 (如 smoke_ → smoke_radon/smoke_radoff)")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--distro", default="Ubuntu-22.04")
    ap.add_argument("--dtmax", type=float, default=None)
    ap.add_argument("--tstep", type=float, default=None)
    ap.add_argument("--cfl", type=float, default=None)
    args = ap.parse_args()

    ov: Dict[str, Any] = {}
    if args.dtmax is not None:
        ov["dtmax"] = args.dtmax
    if args.tstep is not None:
        ov["tstep_change_factor"] = args.tstep
    if args.cfl is not None:
        ov["cfl"] = args.cfl

    nxb = C.GRID["nxb"] if args.nxb is None else int(args.nxb)
    iprocs = C.GRID["iprocs"] if args.iprocs is None else int(args.iprocs)
    sides = ["flsh", "snb"] if args.side == "both" else [args.side]

    results: Dict[str, Dict[str, bool]] = {}
    for s in sides:
        results[s] = run_side(s, args.distro, nxb, iprocs, args.tmax,
                              args.tag_prefix, args.skip_deploy, args.skip_setup,
                              args.skip_make, args.jobs, ov)

    print("\n" + "=" * 78)
    for s, r in results.items():
        for rad, ok in r.items():
            C.log(f"{s}/{rad}: {'完成' if ok else '失败'}", "OK" if ok else "ERROR")
    print("=" * 78)
    return 0 if all(v for r in results.values() for v in r.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
