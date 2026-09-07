#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flash_inputs.py — 生成 grad_dens_sandwich 场景 FLASH 仿真输入文件
====================================================================

仓库只发布 py 代码; 非 py 输入文件 (Config / *.F90 / Makefile / run 脚本 /
*.cn4 / *.par) 均为本脚本的生成物, 不入库 (见 .gitignore)。

来源约定:
  - 文本文件 (Config / Grid_markRefineDerefine.F90 / Makefile /
    Simulation_data.F90 / Simulation_init.F90 / Simulation_initBlock.F90 /
    run_flash.sh / run_flash.bat / submit_flash.sh)
    → sim_input_src.py 内嵌内容 (唯一事实来源, 内容零改动);
  - *.cn4 EOS/opacity 表 → 包内中央表库 flash/input_gen/gen_eos_op/eos_op_data/;
  - grid_rede.par → par_builder.build_par (defaults.py 默认参数)。

用法:
  python gen_flash_inputs.py             # 检查必须文件, 缺失则生成 (幂等)
  python gen_flash_inputs.py --check     # 仅检查 (退出码 0=就绪 / 1=缺失)
  python gen_flash_inputs.py --force     # 强制重新生成全部
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

SIM_INPUT_DIR = SCRIPT_DIR / "sim_input"
PAR_NAME = "grid_rede.par"

REQUIRED_TEXT = [
    "Config", "Grid_markRefineDerefine.F90", "Makefile",
    "Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90",
    "run_flash.sh", "run_flash.bat", "submit_flash.sh",
]


def _scenario():
    """加载场景包 (注册 + 默认参数), 返回 SimulationScenario 实例。"""
    mod = importlib.import_module("flash.scenarios.sandwich.grad_dens_sandwich")
    return mod.scenario_grad


def _load_src():
    spec = importlib.util.spec_from_file_location(
        "_grad_sim_input_src", SCRIPT_DIR / "sim_input_src.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["_grad_sim_input_src"] = m
    spec.loader.exec_module(m)
    return m


def check_input_files() -> list:
    """返回缺失的必须文件名列表 (文本 9 项 + cn4 3 项 + par 1 项)。"""
    src = _load_src()
    required = REQUIRED_TEXT + list(src.CN4_TABLE_SOURCES) + [PAR_NAME]
    return [f for f in required if not (SIM_INPUT_DIR / f).exists()]


def generate_input_files(force: bool = False) -> None:
    """写出全部 sim_input 文件 (幂等: force=False 时已存在则跳过)。"""
    src = _load_src()
    SIM_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 文本文件 (LF)
    for name, content in src.SIM_INPUT_FILES.items():
        dst = SIM_INPUT_DIR / name
        if dst.exists() and not force:
            continue
        dst.write_text(content, encoding="utf-8", newline="\n")
        print(f"  [gen] {name}")

    # 2) cn4 表: 从包内中央表库复制
    for name, rel in src.CN4_TABLE_SOURCES.items():
        dst = SIM_INPUT_DIR / name
        if dst.exists() and not force:
            continue
        table = EOS_OP_DATA / rel
        if not table.exists():
            raise FileNotFoundError(f"中央表库缺少 {name}: {table}")
        shutil.copy2(table, dst)
        print(f"  [gen] {name} (from eos_op_data/{rel})")

    # 3) .par: 由 par_builder 按默认参数生成
    dst = SIM_INPUT_DIR / PAR_NAME
    if force or not dst.exists():
        sc = _scenario()
        par = sc.build_par(dict(sc.default_params))
        dst.write_text(par, encoding="utf-8", newline="\n")
        print(f"  [gen] {PAR_NAME} (par_builder, 默认参数)")


def ensure_generated(force: bool = False) -> bool:
    """确保输入就绪: 检查 → 缺失则生成 → 复查。供 ensure_sim_input 复用。"""
    missing = check_input_files()
    if missing and not force:
        print(f"[gen] grad_dens_sandwich 缺失 {len(missing)} 项输入文件, 生成中 ...")
        generate_input_files(force=False)
    elif force:
        print("[gen] --force: 强制重新生成全部输入文件 ...")
        generate_input_files(force=True)
    else:
        return True
    missing2 = check_input_files()
    if missing2:
        print(f"[FAIL] 生成后仍缺失: {missing2}")
        return False
    print("[OK] grad_dens_sandwich 仿真输入文件已全部就绪")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="grad_dens_sandwich sim_input 生成器")
    ap.add_argument("--check", action="store_true", help="仅检查, 缺失退出码 1")
    ap.add_argument("--force", action="store_true", help="强制重新生成")
    ap.add_argument("--status", action="store_true", help="仅打印检查摘要")
    args = ap.parse_args()

    missing = check_input_files()
    print(f"sim_input: {SIM_INPUT_DIR}")
    print(f"缺失 {len(missing)} 项" + (f": {missing}" if missing else " (全部就绪)"))
    if args.check:
        return 1 if missing else 0
    if args.status:
        return 0
    return 0 if ensure_generated(force=args.force) else 1


if __name__ == "__main__":
    sys.exit(main())
