"""t003 单腿构建运行驱动 —— 部署 → setup → make → mpiexec → 收集

用法 (在 t003 目录下):
    # 短时快速验证 (推荐先跑)
    python scripts/run/run_t003.py --model both --tmax 1.0e-11 --tag smoke

    # 完整时间 (示例 par 的 tmax=0.8 ns)
    python scripts/run/run_t003.py --model both --tag full \
        --skip-deploy --skip-setup --skip-make

    # 单腿
    python scripts/run/run_t003.py --model snb --tmax 1.0e-11 --tag smoke_snb

输出: sim_<model>/flash_output/[<tag>/]  (chk/plt/log + par 台账副本 + walltime.txt)

★ 部署内容
   两腿共享: Config Makefile Simulation_*.F90 mgd_qesh.F90 + 2 张 cn4
   SNB 腿额外: 作者 8 个覆盖 F90 (含 SNB 版 diff_advanceTherm.F90)
   FL-SH 腿  : **不部署**任何覆盖件 → 标准树原生纯限流 SH
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

_T003 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T003 / "common"))

import t003_common as C  # noqa: E402


# ══════════════════════════════════════════════════════════════
def ensure_tree_patches(tree: str, distro: str) -> None:
    """FLASHSNB 树级 physics 补丁 (t001 六补丁基线 #3/#4; 幂等)。"""
    t001 = C.wsl_path(C.SNBTEST_DIR / "Test" / "t001" / "source_patches")
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


def ensure_unit_deployed(model: str, tree: str, distro: str,
                         therm_variant: str = "example",
                         driver_variant: str = "example") -> bool:
    """把 flash_input/ 的内容部署到 <tree>/source/Simulation/SimulationMain/<SIM>。

    两腿都部署共享件 (Config/Makefile/Simulation_*/mgd_qesh/cn4), 使 Config 与
    NUNK 布局完全相同; SNB 腿额外部署 8 个作者覆盖 F90。

    Args:
        therm_variant: 仅 SNB 腿有效。
            "example" → 作者原版 diff_advanceTherm.F90 (1D 分支 λ_g 限制被旁路)
            "limiter" → 诊断变体 (恢复 1D 分支 λ_g 限制; 见 docs §D1)
        driver_variant: 仅 SNB 腿有效。
            "example" → 作者原版 Driver_evolveFlash.F90 (**call RadTrans 被注释**)
            "radon"   → 诊断变体 (恢复 2 处 RadTrans 调用; 见 docs §D3')
    """
    leg = C.LEGS[model]
    inp = C.leg_input_dir(model)
    unit = f"{tree}/source/Simulation/SimulationMain/{leg['sim_name']}"

    # 清理旧单元, 避免残留覆盖件污染另一腿
    C.run_wsl(f'rm -rf "{unit}" && mkdir -p "{unit}"', distro, timeout=60)

    files = list(C.SHARED_FILES) + list(C.SHARED_CN4)
    cmd = ("".join(f'cp -f {C.wsl_path(inp / f)} "{unit}/{f}" && ' for f in files))
    if leg["has_snb"]:
        for f in C.SNB_OVERRIDES:
            # Driver 单独处理 (可换成辐射开启变体)
            if f == "Driver_evolveFlash.F90" and driver_variant == "radon":
                continue
            cmd += f'cp -f {C.wsl_path(inp / f)} "{unit}/{f}" && '
        if driver_variant == "radon":
            dv = _T003 / "variants" / "Driver_evolveFlash_radON.F90"
            if not dv.exists():
                C.log(f"辐射变体缺失: {dv} (先跑 make_therm_variant.py)", "ERROR")
                return False
            cmd += f'cp -f {C.wsl_path(dv)} "{unit}/Driver_evolveFlash.F90" && '
            C.log("驱动源 = 辐射开启变体 radON (**call RadTrans 已恢复**)", "WARN")
        else:
            C.log("驱动源 = 作者原版 (call RadTrans **被注释** → 辐射关闭)", "WARN")
        # diff_advanceTherm.F90: 按变体选择来源
        if therm_variant == "limiter":
            var = _T003 / "variants" / "diff_advanceTherm_limiterON.F90"
            if not var.exists():
                C.log(f"变体缺失: {var} (先跑 make_therm_variant.py)", "ERROR")
                return False
            src = var
            C.log("热传导源 = 诊断变体 limiterON (1D λ_g 限制**启用**)", "WARN")
        else:
            src = inp / C.DIFF_THERM_FILE
            C.log("热传导源 = 作者原版 (1D λ_g 限制**被旁路**)")
        cmd += f'cp -f {C.wsl_path(src)} "{unit}/{C.DIFF_THERM_FILE}" && '
    else:
        cmd += f'rm -f "{unit}"/{C.DIFF_THERM_FILE} 2>/dev/null; '
    cmd += f'ls "{unit}" | wc -l && echo DEPLOY_OK'

    code, out = C.run_wsl(cmd, distro, timeout=600)
    if "DEPLOY_OK" not in out:
        C.log(f"单元部署失败: {out[-600:]}", "ERROR")
        return False
    n = out.strip().splitlines()[-2] if len(out.strip().splitlines()) > 1 else "?"
    C.log(f"单元已部署: {leg['sim_name']} ({n} 文件, "
          f"{'含 SNB 覆盖' if leg['has_snb'] else '无覆盖=原生实现'})", "OK")
    return True


def do_setup(model: str, tree: str, nxb: int, distro: str) -> bool:
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    flags = C.setup_flags(nxb)
    cmd = (f'cd "{tree}" && rm -rf "{obj}" && '
           f'./setup -auto {leg["sim_name"]} {flags} -objdir={leg["objdir"]} '
           f'> setup_{leg["model"]}.log 2>&1; '
           f'test -d "{obj}" && echo OBJ_OK || '
           f'(tail -40 setup_{leg["model"]}.log; echo OBJ_FAIL)')
    code, out = C.run_wsl(cmd, distro, timeout=1800)
    if "OBJ_OK" not in out:
        C.log(f"setup 失败:\n{out[-2000:]}", "ERROR")
        return False
    C.log(f"setup 完成 ({flags})", "OK")
    return True


def do_make(model: str, tree: str, distro: str, jobs: int = 4,
            timeout: int = 5400) -> bool:
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    # SNB 腿: 先单独编几个关键模块, 规避 -j 竞态 (t001/t002 教训)
    pre = ("make Conductivity_interface.o Conductivity_fullState.o "
           "mgd_qesh.o 2>&1 | tail -3; ") if leg["has_snb"] else ""
    cmd = (f'cd "{obj}" && {pre}'
           f'if make -j{jobs} > make_t003.log 2>&1; then echo MAKE_OK; '
           f'else echo MAKE_FAIL; fi; tail -30 make_t003.log; '
           f'test -x ./flash4 && echo FLASH4_OK || echo NO_FLASH4')
    code, out = C.run_wsl(cmd, distro, timeout=timeout)
    ok = "MAKE_OK" in out and "FLASH4_OK" in out
    if ok:
        mtime = C.run_wsl(f'stat -c %y "{obj}/flash4" 2>/dev/null',
                          distro, timeout=60)[1].strip()
        C.log(f"编译完成 (flash4: {mtime})", "OK")
    else:
        C.log(f"编译失败: {out[-2500:]}", "ERROR")
    return ok


def do_run(model: str, tree: str, distro: str, nproc: int,
           tmax: Optional[float], out_dir: Path, tag: str = "",
           run_timeout: int = 21600,
           par_overrides: Optional[Dict[str, Any]] = None) -> Tuple[bool, float]:
    leg = C.LEGS[model]
    obj = f"{tree}/{leg['objdir']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_log = f"wsl_run_{leg['model']}.log"

    par_src = C.leg_input_dir(model) / leg["par_file"]
    par_text = par_src.read_text(encoding="utf-8")
    if tmax:
        par_text = re.sub(r"(?m)^tmax\s*=.*$",
                          f"tmax = {float(tmax):.10e}   # [t003] run override",
                          par_text)
    # 数值稳定性实验用的 par 覆写 (dtmax / tstep_change_factor / cfl ...)
    for key, val in (par_overrides or {}).items():
        if isinstance(val, float):
            rep = f"{key} = {val:.10e}   # [t003] diag override"
        else:
            rep = f"{key} = {val}   # [t003] diag override"
        new_text, n = re.subn(rf"(?m)^{key}\s*=.*$", rep, par_text)
        if n == 0:                                  # par 中不存在 → 追加
            new_text = par_text.rstrip("\n") + f"\n{rep}\n"
        par_text = new_text
    if par_overrides:
        C.log(f"par 诊断覆写: {par_overrides}", "WARN")

    par_local = out_dir / f"par_{leg['model']}{('_' + tag) if tag else ''}.par"
    par_local.write_text(par_text, encoding="utf-8", newline="\n")
    code, out = C.run_wsl(
        f'cp -f {C.wsl_path(par_local)} "{obj}/flash.par" && '
        f'grep -n "^tmax\\|^iProcs\\|^iGridSize\\|^diff_eleFlMode\\|^xmin\\|^xmax'
        f'\\|^dtmax\\|^tstep_change_factor\\|^cfl" '
        f'"{obj}/flash.par"', distro, timeout=180)
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
        f'cd "{obj}" && grep -E "exiting|SimTime|ERROR|ABORT" {run_log} | tail -4; '
        f'echo "--- chk/plt ---"; '
        f'ls {leg["basenm"]}hdf5_chk_* 2>/dev/null | wc -l; '
        f'ls {leg["basenm"]}hdf5_plt_cnt_* 2>/dev/null | wc -l', distro, timeout=180)
    print(out)
    C.collect_outputs(obj, leg["basenm"], leg["log_file"], out_dir, run_log, distro)

    ok = ("RUN_EXIT=0" in out) or ("reached max SimTime" in out)
    C.log(f"{'成功' if ok else '异常'} — 墙钟 {wall:.1f} s", "OK" if ok else "ERROR")
    with (out_dir / "walltime.txt").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{model}\t{nproc}\t{tmax}\t{tag}\t{wall:.2f}\t{'OK' if ok else 'FAIL'}\n")
    return ok, wall


# ══════════════════════════════════════════════════════════════
def run_leg(model: str, distro: str, nxb: int, iprocs: int,
            tmax: Optional[float], tag: str,
            skip_deploy: bool, skip_setup: bool, skip_make: bool,
            jobs: int = 4, therm_variant: str = "example",
            driver_variant: str = "example",
            par_overrides: Optional[Dict[str, Any]] = None) -> bool:
    leg = C.LEGS[model]
    print("\n" + "=" * 74)
    print(f" t003 {leg['label']}  ({leg['desc']})")
    print(f" 树上: {'FLASHSNB' if leg['tree'] == 'snb' else '标准 FLASH'}   "
          f"限流: {leg['diff_eleFlMode']}/{leg['diff_eleFlCoef']}  (两腿一致)")
    print(f" 网格 +ug: 固定块 nxb={nxb} × iProcs={iprocs} → {nxb*iprocs} 格, "
          f"dx≈{C.dx_um(nxb, iprocs):.4f} µm")
    print(f" tmax={tmax if tmax else C.PARAMS['tmax']}")
    if leg["has_snb"]:
        print(f" 热传导源: {therm_variant}   驱动源: {driver_variant}")
    if par_overrides:
        print(f" par 诊断覆写: {par_overrides}")
    print("=" * 74)

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
        if not ensure_unit_deployed(model, tree, distro, therm_variant, driver_variant):
            return False
    if not skip_setup:
        if not do_setup(model, tree, nxb, distro):
            return False
    if not skip_make:
        if not do_make(model, tree, distro, jobs=jobs):
            return False

    out_dir = C.leg_output_dir(model) / tag if tag else C.leg_output_dir(model)
    ok, _ = do_run(model, tree, distro, iprocs, tmax, out_dir, tag,
                   par_overrides=par_overrides)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="t003 单腿/双臂构建运行驱动")
    ap.add_argument("--model", choices=["flsh", "snb", "both"], default="both")
    ap.add_argument("--tmax", type=float, default=None,
                    help=f"默认 {C.PARAMS['tmax']:.1e} s (示例值)")
    ap.add_argument("--nxb", type=int, default=None)
    ap.add_argument("--iprocs", type=int, default=None)
    ap.add_argument("--tag", default="", help="输出子目录名 (如 smoke / full)")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--distro", default="Ubuntu-22.04")
    ap.add_argument("--therm-variant", choices=["example", "limiter"],
                    default="example",
                    help="SNB 腿热传导源: example=作者原版(1D λ_g 限制被旁路); "
                         "limiter=诊断变体(恢复限制)")
    ap.add_argument("--driver-variant", choices=["example", "radon"],
                    default="example",
                    help="SNB 腿驱动源: example=作者原版(call RadTrans 被注释, 辐射关闭); "
                         "radon=诊断变体(恢复 RadTrans, 辐射开启)")
    ap.add_argument("--dtmax", type=float, default=None, help="覆写 dtmax (s)")
    ap.add_argument("--tstep", type=float, default=None,
                    help="覆写 tstep_change_factor")
    ap.add_argument("--cfl", type=float, default=None, help="覆写 cfl")
    args = ap.parse_args()

    par_overrides: Dict[str, Any] = {}
    if args.dtmax is not None:
        par_overrides["dtmax"] = args.dtmax
    if args.tstep is not None:
        par_overrides["tstep_change_factor"] = args.tstep
    if args.cfl is not None:
        par_overrides["cfl"] = args.cfl

    nxb = C.GRID["nxb"] if args.nxb is None else int(args.nxb)
    iprocs = C.GRID["iprocs"] if args.iprocs is None else int(args.iprocs)

    models = ["flsh", "snb"] if args.model == "both" else [args.model]
    results: Dict[str, bool] = {}
    for m in models:
        # ★ 必须用关键字传参: run_leg 的可选参数顺序曾因新增 driver_variant 而位移,
        #   位置传参会让 par_overrides 落到 driver_variant 上 (静默失效)。
        results[m] = run_leg(
            m, args.distro, nxb, iprocs, args.tmax, args.tag,
            args.skip_deploy, args.skip_setup, args.skip_make, args.jobs,
            therm_variant=args.therm_variant,
            driver_variant=args.driver_variant,
            par_overrides=par_overrides)

    print("\n" + "=" * 74)
    for m, ok in results.items():
        C.log(f"{C.LEGS[m]['label']}: {'完成' if ok else '失败'}", "OK" if ok else "ERROR")
    print("=" * 74)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
