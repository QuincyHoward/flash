#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flash_inputs.py — 生成 thin_layer_sandwich (si) 场景 FLASH 仿真输入文件
==========================================================================

仓库只发布 py 代码; 非 py 输入文件 (Config / *.F90 / Makefile / run 脚本 /
*.cn4 / *.par / 预诊断图) 均为本脚本的生成物, 不入库 (见 .gitignore)。

来源约定:
  - 文本文件 → sim_input_src.py 内嵌内容 (唯一事实来源, 内容零改动);
  - Z 系列 *.cn4 (自研 ionmix 表) → 包内中央表库
    flash/input_gen/gen_eos_op/eos_op_data/Gen_eos_op_data/;
  - grid_rede.par → par_builder.build_par (defaults_si 默认参数);
  - initial_density.png / laser_pulse.png → viz.pre_diagnose 预诊断图。

用法:
  python gen_flash_inputs.py             # 检查, 缺失则生成 (幂等)
  python gen_flash_inputs.py --check     # 仅检查 (退出码 0=就绪 / 1=缺失)
  python gen_flash_inputs.py --force     # 强制重新生成
  python gen_flash_inputs.py --status    # 仅打印检查摘要
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EOS_OP_DATA = SCRIPT_DIR.parents[2] / "input_gen" / "gen_eos_op" / "eos_op_data"

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


def _scenario():
    """加载场景包并返回 SimulationScenario 实例。"""
    import flash.scenarios.sandwich.thin_layer_sandwich as pkg
    return pkg.scenario_si


SIM_INPUT_DIRNAME = "sim_input_si"


def check_input_files() -> list:
    """返回缺失的必须文件名列表 (文本 9 项 + cn4 + par; 预诊断图可选)。"""
    src = _load("_thin_sim_input_src", "sim_input_src.py")
    d = SCRIPT_DIR / SIM_INPUT_DIRNAME
    required = REQUIRED_TEXT + list(src.CN4_TABLE_SOURCES) + ["grid_rede.par"]
    return [f for f in required if not (d / f).exists()]


def generate_input_files(force: bool = False) -> None:
    """写出全部 sim_input_si 文件 (幂等: force=False 时已存在则跳过)。"""
    src = _load("_thin_sim_input_src", "sim_input_src.py")
    dirname = SIM_INPUT_DIRNAME
    d = SCRIPT_DIR / dirname
    d.mkdir(parents=True, exist_ok=True)

    # 1) 文本文件 (LF)
    for name, content in src.SIM_INPUT_FILES_SI.items():
        dst = d / name
        if dst.exists() and not force:
            continue
        dst.write_text(content, encoding="utf-8", newline="\n")
        print(f"  [gen] {dirname}/{name}")

    # 2) cn4 表: 自研 Z 系列从包内中央表库复制
    for name, rel in src.CN4_TABLE_SOURCES.items():
        dst = d / name
        if dst.exists() and not force:
            continue
        table = EOS_OP_DATA / rel
        if not table.exists():
            raise FileNotFoundError(f"中央表库缺少 {name}: {table}")
        shutil.copy2(table, dst)
        print(f"  [gen] {dirname}/{name} (from eos_op_data)")

    # 3) .par: par_builder 按对应 defaults 默认参数生成
    dst = d / "grid_rede.par"
    if force or not dst.exists():
        sc = _scenario()
        par = sc.build_par(dict(sc.default_params))
        dst.write_text(par, encoding="utf-8", newline="\n")
        print(f"  [gen] {dirname}/grid_rede.par (par_builder, 默认参数)")

    # 4) 预诊断图 (可选: matplotlib 缺失时跳过, 不阻塞仿真)
    if not all((d / png).exists() for png in PRE_DIAG_PLOTS):
        try:
            _generate_plots(d)
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] 预诊断图跳过 ({type(exc).__name__}: {exc})")


def _generate_plots(d: Path) -> None:
    """调用 viz.pre_diagnose 生成两张预诊断图。"""
    sc = _scenario()
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


def ensure_generated(force: bool = False) -> bool:
    """确保输入就绪: 检查 → 缺失则生成 → 复查。供 ensure_sim_input 复用。"""
    missing = check_input_files()
    if missing and not force:
        print(f"[gen] thin_layer_sandwich_si 缺失 {len(missing)} 项输入文件, 生成中 ...")
        generate_input_files(force=False)
    elif force:
        print("[gen] --force: 强制重新生成 thin_layer_sandwich_si 全部输入 ...")
        generate_input_files(force=True)
    else:
        return True
    missing2 = check_input_files()
    if missing2:
        print(f"[FAIL] 生成后仍缺失: {missing2}")
        return False
    print("[OK] thin_layer_sandwich_si 仿真输入文件已全部就绪")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="thin_layer_sandwich sim_input 生成器")
    ap.add_argument("--check", action="store_true", help="仅检查, 缺失退出码 1")
    ap.add_argument("--force", action="store_true", help="强制重新生成")
    ap.add_argument("--status", action="store_true", help="仅打印检查摘要")
    args = ap.parse_args()

    missing = check_input_files()
    print(f"sim_input: {SCRIPT_DIR / SIM_INPUT_DIRNAME}"
          f" — 缺失 {len(missing)} 项" + (f": {missing}" if missing else " (全部就绪)"))
    if args.check:
        return 1 if missing else 0
    if args.status:
        return 0
    return 0 if ensure_generated(force=args.force) else 1


if __name__ == "__main__":
    sys.exit(main())
