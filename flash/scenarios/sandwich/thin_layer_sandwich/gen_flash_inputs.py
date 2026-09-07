#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flash_inputs.py — 生成 thin_layer_sandwich (si/al) 场景 FLASH 仿真输入文件
============================================================================

仓库只发布 py 代码; 非 py 输入文件 (Config / *.F90 / Makefile / run 脚本 /
*.cn4 / *.par / 预诊断图) 均为本脚本的生成物, 不入库 (见 .gitignore)。

来源约定:
  - 文本文件 → sim_input_src.py 内嵌内容 (SI/AL 两变体, 唯一事实来源, 内容零改动);
  - Z 系列 *.cn4 → 包内中央表库 flash/input_gen/gen_eos_op/eos_op_data/;
  - *-imx-*.cn4 (仓库不分发) → tables_imx.py base64 解码;
  - grid_rede.par → par_builder.build_par (defaults_si/defaults_al 默认参数);
  - initial_density.png / laser_pulse.png → viz.pre_diagnose 预诊断图。

用法:
  python gen_flash_inputs.py [--variant si|al]      # 检查, 缺失则生成 (幂等)
  python gen_flash_inputs.py --check [--variant ..] # 仅检查 (0=就绪 / 1=缺失)
  python gen_flash_inputs.py --force [--variant ..] # 强制重新生成
  python gen_flash_inputs.py --status [--variant ..]
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EOS_OP_DATA = SCRIPT_DIR.parents[2] / "input_gen" / "gen_eos_op" / "eos_op_data"

VARIANTS = {
    "si": ("sim_input_si", "SIM_INPUT_FILES_SI", "grid_rede_si"),
    "al": ("sim_input_al", "SIM_INPUT_FILES_AL", "grid_rede"),
}

REQUIRED_TEXT = [
    "Config", "Grid_markRefineDerefine.F90", "Makefile",
    "Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90",
    "run_flash.sh", "run_flash.bat", "submit_flash.sh",
]

PRE_DIAG_PLOTS = ["initial_density.png", "laser_pulse.png"]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _scenario(variant: str):
    """加载场景包并返回对应 SimulationScenario 实例。"""
    import flash.scenarios.sandwich.thin_layer_sandwich as pkg
    return pkg.scenario_si if variant == "si" else pkg.scenario_al


def check_input_files(variant: str) -> list:
    """返回缺失的必须文件名列表 (文本 9 项 + cn4 + par; 预诊断图可选)。"""
    src = _load("_thin_sim_input_src", "sim_input_src.py")
    tables = _load("_thin_tables_imx", "tables_imx.py")
    dirname, _, _ = VARIANTS[variant]
    d = SCRIPT_DIR / dirname
    if variant == "si":
        cn4 = list(src.CN4_TABLE_SOURCES)   # si 变体仅用 Z 系列表
    else:
        cn4 = list(tables.IMX_TABLES_B64)   # al 变体仅用 imx 系列表
    required = REQUIRED_TEXT + cn4 + ["grid_rede.par"]
    return [f for f in required if not (d / f).exists()]


def generate_input_files(variant: str, force: bool = False) -> None:
    """写出指定变体的全部 sim_input 文件 (幂等: force=False 时已存在则跳过)。"""
    src = _load("_thin_sim_input_src", "sim_input_src.py")
    tables = _load("_thin_tables_imx", "tables_imx.py")
    dirname, files_var, _ = VARIANTS[variant]
    d = SCRIPT_DIR / dirname
    d.mkdir(parents=True, exist_ok=True)

    # 1) 文本文件 (LF)
    for name, content in getattr(src, files_var).items():
        dst = d / name
        if dst.exists() and not force:
            continue
        dst.write_text(content, encoding="utf-8", newline="\n")
        print(f"  [gen] {dirname}/{name}")

    # 2) cn4 表: Z 系列从中央表库复制; imx 系列从 base64 解码
    if variant == "si":
        cn4_sources = list(src.CN4_TABLE_SOURCES)
    else:
        cn4_sources = list(tables.IMX_TABLES_B64)
    for name in cn4_sources:
        dst = d / name
        if dst.exists() and not force:
            continue
        if name in tables.IMX_TABLES_B64:
            dst.write_bytes(base64.b64decode(tables.IMX_TABLES_B64[name]))
            print(f"  [gen] {dirname}/{name} (base64)")
        else:
            table = EOS_OP_DATA / src.CN4_TABLE_SOURCES[name]
            if not table.exists():
                raise FileNotFoundError(f"中央表库缺少 {name}: {table}")
            shutil.copy2(table, dst)
            print(f"  [gen] {dirname}/{name} (from eos_op_data)")

    # 3) .par: par_builder 按对应 defaults 默认参数生成
    dst = d / "grid_rede.par"
    if force or not dst.exists():
        sc = _scenario(variant)
        par = sc.build_par(dict(sc.default_params))
        dst.write_text(par, encoding="utf-8", newline="\n")
        print(f"  [gen] {dirname}/grid_rede.par (par_builder, 默认参数)")

    # 4) 预诊断图 (可选: matplotlib 缺失时跳过, 不阻塞仿真)
    if not all((d / png).exists() for png in PRE_DIAG_PLOTS):
        try:
            _generate_plots(variant, d)
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] 预诊断图跳过 ({type(exc).__name__}: {exc})")


def _generate_plots(variant: str, d: Path) -> None:
    """调用 viz.pre_diagnose 生成两张预诊断图。"""
    sc = _scenario(variant)
    params = dict(sc.default_params)
    import sys as _s
    viz_dir = SCRIPT_DIR / "viz"
    if str(viz_dir) not in _s.path:
        _s.path.insert(0, str(viz_dir))
    try:
        from pre_diagnose import generate_pre_diagnosis_pair
    except ImportError:
        from viz.pre_diagnose import generate_pre_diagnosis_pair
    generate_pre_diagnosis_pair(params, d)
    print(f"  [gen] {d.name}/initial_density.png + laser_pulse.png")


def ensure_generated(variant: str, force: bool = False) -> bool:
    """确保输入就绪: 检查 → 缺失则生成 → 复查。供 ensure_sim_input 复用。"""
    missing = check_input_files(variant)
    if missing and not force:
        print(f"[gen] thin_layer_sandwich_{variant} 缺失 {len(missing)} 项输入文件, 生成中 ...")
        generate_input_files(variant, force=False)
    elif force:
        print(f"[gen] --force: 强制重新生成 thin_layer_sandwich_{variant} 全部输入 ...")
        generate_input_files(variant, force=True)
    else:
        return True
    missing2 = check_input_files(variant)
    if missing2:
        print(f"[FAIL] 生成后仍缺失: {missing2}")
        return False
    print(f"[OK] thin_layer_sandwich_{variant} 仿真输入文件已全部就绪")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="thin_layer_sandwich sim_input 生成器")
    ap.add_argument("--variant", choices=["si", "al", "both"], default="both")
    ap.add_argument("--check", action="store_true", help="仅检查, 缺失退出码 1")
    ap.add_argument("--force", action="store_true", help="强制重新生成")
    ap.add_argument("--status", action="store_true", help="仅打印检查摘要")
    args = ap.parse_args()

    variants = ["si", "al"] if args.variant == "both" else [args.variant]
    rc = 0
    for v in variants:
        missing = check_input_files(v)
        d = SCRIPT_DIR / VARIANTS[v][0]
        print(f"[{v}] sim_input: {d} — 缺失 {len(missing)} 项"
              + (f": {missing}" if missing else " (全部就绪)"))
        if args.check:
            rc |= (1 if missing else 0)
            continue
        if args.status:
            continue
        if not ensure_generated(v, force=args.force):
            rc |= 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
