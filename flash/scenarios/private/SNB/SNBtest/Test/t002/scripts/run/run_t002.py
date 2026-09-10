"""t002 单腿构建运行驱动 —— 部署 → setup → make → mpiexec → 收集

用法 (在 t002 目录下):
    # WSL 本地跑一条腿 (默认用 flash_input 里已生成的 par)
    python scripts/run/run_t002.py --model flsh --tmax 2.0e-10
    python scripts/run/run_t002.py --model snb  --tmax 2.0e-10

    # 用不同网格重建 (会重新生成 par + 完整重编)
    python scripts/run/run_t002.py --model flsh --nxb 128 --iprocs 8 --rebuild

    # 非固定块模式 (不给 -nxb, 由 par 的 iGridSize 决定全局格数)
    python scripts/run/run_t002.py --model flsh --no-nxb --igridsize 1024 --rebuild

    # 复用已编译的 flash4, 只换 par 重跑
    python scripts/run/run_t002.py --model snb --tmax 2.0e-10 --skip-setup --skip-make

输出: sim_<model>/flash_output/[<tag>/]  (plt/chk/log + walltime.txt)
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_T002 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T002 / "common"))
sys.path.insert(0, str(_T002 / "scripts" / "generate"))

import t002_common as C          # noqa: E402
import gen_t002_inputs as GEN    # noqa: E402


# ══════════════════════════════════════════════════════════════
def ensure_unit_deployed(model: str, tree: str, distro: str) -> bool:
    """把 flash_input/ 的内容部署到 <tree>/source/Simulation/SimulationMain/<SIM>。"""
    leg = C.LEGS[model]
    inp = C.leg_input_dir(model)
    unit = f"{tree}/source/Simulation/SimulationMain/{leg['sim_name']}"
    files = ["Config", "Makefile", "Simulation_data.F90", "Simulation_init.F90",
             "Simulation_initBlock.F90"]
    cmd = (f'mkdir -p "{unit}" && '
           + "".join(f'cp -f {C.wsl_path(inp / f)} "{unit}/{f}" && ' for f in files)
           + f'cp -f {C.wsl_path(inp)}/*.cn4 "{unit}/" && ')
    if leg["has_snb"]:
        for f in C.SNB_OVERRIDE_FILES:
            local = inp / f
            cmd += (f'( test -f {C.wsl_path(local)} && '
                    f'cp -f {C.wsl_path(local)} "{unit}/{f}" || '
                    f'cp -f "{tree}/source/Simulation/SimulationMain/SNB_1D_laser/{f}" '
                    f'"{unit}/{f}" ) && ')
    cmd += f'ls "{unit}" | wc -l && echo DEPLOY_OK'
    code, out = C.run_wsl(cmd, distro, timeout=300)
    if "DEPLOY_OK" not in out:
        C.log(f"单元部署失败: {out[-500:]}", "ERROR")
        return False
    C.log(f"单元已部署: {unit} ({out.strip().splitlines()[-2] if len(out.strip().splitlines())>1 else '?'} 文件)", "OK")
    return True


def ensure_tree_patches(tree: str, distro: str) -> None:
    """FLASHSNB 树级 physics 补丁 (#3/#4 of t001 六补丁基线; 幂等)。"""
    t001 = C.wsl_path(_T002 / ".." / "t001" / "source_patches")
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


def do_setup(model: str, tree: str, nxb: int, iprocs: int, distro: str,
             fixed_bs: bool = True) -> bool:
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    flags = C.setup_flags(nxb if fixed_bs else None)
    cmd = (f'cd "{tree}" && rm -rf "{obj}" && '
           f'./setup -auto {leg["sim_name"]} {flags} -objdir={leg["objdir"]} '
           f'> setup_{leg["model"]}.log 2>&1; '
           f'test -d "{obj}" && echo OBJ_OK || (tail -30 setup_{leg["model"]}.log; echo OBJ_FAIL)')
    code, out = C.run_wsl(cmd, distro, timeout=1800)
    if "OBJ_OK" not in out:
        C.log(f"setup 失败:\n{out[-1500:]}", "ERROR")
        return False
    C.log(f"setup 完成 ({flags})", "OK")
    if leg["has_snb"]:
        C.run_wsl(f'cd "{obj}" && ln -sf ../source/Simulation/SimulationMain/'
                  f'{leg["sim_name"]}/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null; true',
                  distro, timeout=60)
    return True


def do_make(model: str, tree: str, distro: str, jobs: int = 4,
            timeout: int = 5400) -> bool:
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    pre = ("make hy_slopeLimiters.o Conductivity_interface.o "
           "Conductivity_fullState.o 2>&1 | tail -3; ") if leg["has_snb"] else ""
    cmd = (f'cd "{obj}" && {pre}'
           f'if make -j{jobs} > make_t002.log 2>&1; then echo MAKE_OK; '
           f'else echo MAKE_FAIL; fi; tail -25 make_t002.log; '
           f'test -x ./flash4 && echo FLASH4_OK || echo NO_FLASH4')
    code, out = C.run_wsl(cmd, distro, timeout=timeout)
    ok = "MAKE_OK" in out and "FLASH4_OK" in out
    if ok:
        mtime = C.run_wsl(f'stat -c %y "{obj}/flash4" 2>/dev/null', distro, timeout=60)[1].strip()
        C.log(f"编译完成 (flash4: {mtime})", "OK")
    else:
        C.log(f"编译失败: {out[-2000:]}", "ERROR")
    return ok


def do_run(model: str, tree: str, distro: str, nproc: int,
           tmax: Optional[str], out_dir: Path, tag: str = "",
           run_timeout: int = 7200) -> Tuple[bool, float]:
    """跑一次仿真并把输出收到 out_dir。返回 (成功, 墙钟秒)。"""
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_log = f"wsl_run_{leg['model']}.log"

    # par → objdir (台账归档副本, 供人工核查)
    par_src = C.leg_input_dir(model) / leg["par_file"]
    par_text = par_src.read_text(encoding="utf-8")
    if tmax:
        par_text = re.sub(r"(?m)^tmax\s*=.*$",
                          f"tmax = {float(tmax):.15e}   # [t002] run override",
                          par_text)
    par_local = out_dir / f"par_{leg['model']}{('_' + tag) if tag else ''}.par"
    par_local.write_text(par_text, encoding="utf-8", newline="\n")
    code, out = C.run_wsl(
        f'cp -f {C.wsl_path(par_local)} "{obj}/flash.par" && '
        f'grep -n "^tmax\\|^iProcs\\|^iGridSize\\|^diff_eleFlMode" "{obj}/flash.par"',
        distro, timeout=120)
    print("    " + out.strip().replace("\n", "\n    "))

    C.log(f"运行 mpiexec -n {nproc} ./flash4 (tmax={tmax or 'par 默认'}) ...", "STEP")
    t0 = time.time()
    C.run_wsl(
        f'cd "{obj}" && rm -f {leg["basenm"]}* {run_log} && '
        f'if mpiexec -n {nproc} ./flash4 > {run_log} 2>&1; then '
        f'echo RUN_EXIT=0 >> {run_log}; else echo RUN_EXIT_NZ >> {run_log}; fi',
        distro, timeout=run_timeout)
    wall = time.time() - t0

    code, out = C.run_wsl(
        f'cd "{obj}" && tail -5 {run_log}; echo "--- plt/chk ---"; '
        f'ls {leg["basenm"]}hdf5_plt_cnt_* 2>/dev/null | wc -l; '
        f'ls {leg["basenm"]}hdf5_chk_* 2>/dev/null | wc -l', distro, timeout=120)
    print(out)
    C.collect_outputs(obj, leg["basenm"], leg["log_file"], out_dir, run_log, distro)

    ok = ("RUN_EXIT=0" in out) or ("reached max SimTime" in out)
    C.log(f"{'成功' if ok else '异常'} — 墙钟 {wall:.1f} s", "OK" if ok else "ERROR")
    with (out_dir / "walltime.txt").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{model}\t{nproc}\t{tmax}\t{wall:.2f}\t{'OK' if ok else 'FAIL'}\n")
    return ok, wall


# ══════════════════════════════════════════════════════════════
def run_leg(model: str, distro: str, nxb: int, iprocs: int, igridsize: int,
            fixed_bs: bool, tmax: Optional[str], tag: str,
            skip_deploy: bool, skip_setup: bool, skip_make: bool,
            jobs: int = 4) -> bool:
    leg = C.LEGS[model]
    print("\n" + "=" * 72)
    print(f" t002 {leg['label']}  ({leg['desc']})")
    print(f" 树上: {'FLASHSNB' if leg['tree'] == 'snb' else '标准 FLASH'}   "
          f"限流: {leg['diff_eleFlMode']}/{leg['diff_eleFlCoef']}")
    grid_desc = (f"固定块 nxb={nxb} × iProcs={iprocs} → {nxb*iprocs} 格, "
                 f"dx≈{C.dx_um(nxb, iprocs):.4f} µm" if fixed_bs
                 else f"非固定块 iGridSize={igridsize}, iProcs={iprocs} → "
                      f"{igridsize} 格, dx≈{C.dx_um_from_igridsize(igridsize):.4f} µm")
    print(f" 网格 +ug: {grid_desc}")
    print(f" tmax={tmax or C.PARAMS['tmax']}")
    print("=" * 72)

    tree = C.find_tree(model, distro)
    if not tree:
        C.log(f"未找到 {'FLASHSNB' if leg['tree'] == 'snb' else '标准 FLASH'} 树", "ERROR")
        return False
    if not C.tree_exists(tree, distro):
        C.log(f"树结构不完整 (缺 setup/source): {tree}", "ERROR")
        return False
    C.log(f"FLASH 树: {tree}", "OK")

    if not skip_deploy:
        if leg["has_snb"]:
            ensure_tree_patches(tree, distro)
        if not ensure_unit_deployed(model, tree, distro):
            return False
    if not skip_setup:
        if not do_setup(model, tree, nxb, iprocs, distro, fixed_bs):
            return False
    if not skip_make:
        if not do_make(model, tree, distro, jobs=jobs):
            return False

    out_dir = C.leg_output_dir(model) / tag if tag else C.leg_output_dir(model)
    nproc = iprocs
    ok, _ = do_run(model, tree, distro, nproc, tmax, out_dir, tag)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="t002 单腿/双臂构建运行驱动")
    ap.add_argument("--model", choices=["flsh", "snb", "both"], default="both")
    ap.add_argument("--tmax", default=None, help=f"默认 {C.PARAMS['tmax']:.1e} s")
    ap.add_argument("--nxb", type=int, default=None,
                    help=f"每块格数 (默认 {C.GRID['nxb']})")
    ap.add_argument("--iprocs", type=int, default=None,
                    help=f"iProcs = MPI 进程数 (默认 {C.GRID['iprocs']})")
    ap.add_argument("--no-nxb", action="store_true",
                    help="非固定块模式 (不给 -nxb, 用 par 的 iGridSize)")
    ap.add_argument("--igridsize", type=int, default=None,
                    help="非固定块模式的全局格数")
    ap.add_argument("--rebuild", action="store_true",
                    help="先重新生成 par (载荷网格参数变更)")
    ap.add_argument("--tag", default="", help="输出子目录名 (如 cmp_2e-10)")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    ap.add_argument("--jobs", type=int, default=4, help="make -j 并行度")
    ap.add_argument("--fl-mode", default=None,
                    help="覆盖两腿的 diff_eleFlMode (如 fl_harmonic / fl_minmax / "
                         "fl_none), 仅改 par 不需重编")
    ap.add_argument("--fl-coef", type=float, default=None,
                    help="覆盖两腿的 diff_eleFlCoef (如 0.06)")
    ap.add_argument("--distro", default="Ubuntu-22.04")
    args = ap.parse_args()

    if args.fl_mode or args.fl_coef is not None:
        for m in ("flsh", "snb"):
            if args.fl_mode:
                C.LEGS[m]["diff_eleFlMode"] = args.fl_mode
            if args.fl_coef is not None:
                C.LEGS[m]["diff_eleFlCoef"] = args.fl_coef
        C.log(f"限流器覆盖: mode={args.fl_mode}, coef={args.fl_coef} "
              f"(两腿同步生效)", "OK")

    nxb = C.GRID["nxb"] if args.nxb is None else int(args.nxb)
    iprocs = C.GRID["iprocs"] if args.iprocs is None else int(args.iprocs)
    igs = C.GRID["iGridSize"] if args.igridsize is None else int(args.igridsize)
    fixed_bs = not args.no_nxb
    if not fixed_bs:
        nxb = 0
        if not igs:
            igs = iprocs * C.GRID["nxb"]
    tmax = None if args.tmax is None else float(args.tmax)

    models = ["flsh", "snb"] if args.model == "both" else [args.model]

    if args.rebuild:
        for m in models:
            GEN.generate(m, nxb, iprocs, igs, tmax)
        if len(models) == 2:
            GEN.check_consistency()

    results: Dict[str, bool] = {}
    for m in models:
        results[m] = run_leg(m, args.distro, nxb, iprocs, igs, fixed_bs, tmax,
                             args.tag, args.skip_deploy, args.skip_setup,
                             args.skip_make, args.jobs)

    print("\n" + "=" * 72)
    for m, ok in results.items():
        C.log(f"{C.LEGS[m]['label']}: {'完成' if ok else '失败'}", "OK" if ok else "ERROR")
    print("=" * 72)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
