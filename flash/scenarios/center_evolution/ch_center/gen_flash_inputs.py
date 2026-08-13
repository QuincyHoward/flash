#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flash_inputs.py — 生成 ch_center 场景的 FLASH 仿真必须文件
================================================================

使用 flash.input_gen 包（gen_par / gen_config / gen_makefile / gen_sim_data /
gen_sim_init / gen_sim_initblock / gen_eos_op / gen_shell_script）生成
``flash_input/`` 目录下 FLASH 仿真所需的全部文件：

    .par / Config / Makefile / Simulation_data.F90 / Simulation_init.F90 /
    Simulation_initBlock.F90 / run_flash.sh / submit_flash.sh / *.cn4 (EOS 表)

设计原则（与 output_processors 的 inputfiles/ 同一模式）：
  - 仓库**不发布** par/Makefile/Config/F90/cn4 等生成文件
    （``flash_input/`` 被 .gitignore 排除），本脚本是这些文件的唯一生成入口，
    任何克隆环境均可一键生成，保证开箱即用。
  - cn4 EOS 表源文件存放于 ``flash/input_gen/gen_eos_op/eos_op_data/``，
    由 EOSOpacityGenerator 复制到 ``flash_input/``（仓库只发布生成器代码）。
  - 执行前通过 ``gen_checker.DependencyChecker`` 检查 7 项必须文件，
    缺失才生成；已就绪则跳过（幂等）。

用法：
  python gen_flash_inputs.py             # 检查必须文件，缺失则生成
  python gen_flash_inputs.py --check     # 仅检查（不生成），退出码 0=就绪 / 1=缺失
  python gen_flash_inputs.py --force     # 强制重新生成全部输入文件
  python gen_flash_inputs.py --status    # 仅打印检查摘要
"""

import argparse
import sys
from pathlib import Path

# 复用同目录场景脚本的参数与生成逻辑。
# laserslab1d_local_custom.py 顶层导入无副作用（main 受 __main__ 保护），可安全复用。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from laserslab1d_local_custom import (  # noqa: E402
    INPUT_DIR,
    config_constants,
    generate_input_files,
)


def check_input_files() -> list:
    """检查 7 项 FLASH 仿真必须文件，返回缺失项名称列表。"""
    from flash.input_gen.gen_checker import DependencyChecker

    checker = DependencyChecker(INPUT_DIR)
    missing = checker.missing_standard()
    summary = checker.summary()
    print(summary)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="生成 ch_center 场景的 FLASH 仿真必须文件（经 input_gen 包）")
    parser.add_argument("--check", action="store_true",
                        help="仅检查必须文件是否就绪（不生成）；退出码 0=就绪 / 1=缺失")
    parser.add_argument("--force", action="store_true",
                        help="强制重新生成全部输入文件（覆盖已存在文件）")
    parser.add_argument("--status", action="store_true",
                        help="仅打印检查摘要")
    args = parser.parse_args()

    print("=" * 60)
    print(" gen_flash_inputs.py — FLASH 仿真必须文件生成器")
    print(f" 输入目录: {INPUT_DIR}")
    print("=" * 60)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 检查
    print("\n[1/2] 检查 FLASH 仿真必须文件（gen_checker）...")
    missing = check_input_files()

    if args.status:
        print(f"\n[status] 缺失 {len(missing)} 项必须文件"
              f"{': ' + ', '.join(missing) if missing else '（全部就绪）'}")
        return 0 if not missing else 1

    if args.check:
        print(f"\n[check] {'✅ 全部就绪（缺失 0 项）' if not missing else '⚠ 缺失 ' + str(len(missing)) + ' 项: ' + ', '.join(missing)}")
        return 0 if not missing else 1

    if missing and not args.force:
        print(f"\n[2/2] 缺失 {len(missing)} 项必须文件，调用 input_gen 生成器生成 ...")
        generate_input_files(dict(config_constants))
    elif args.force:
        print("\n[2/2] --force：强制重新生成全部输入文件 ...")
        generate_input_files(dict(config_constants))
    else:
        print("\n[2/2] 全部必须文件已就绪，无需生成（幂等跳过）。")
        print("       如需重新生成: python gen_flash_inputs.py --force")
        return 0

    # 生成后复查
    print("\n[复查] 生成后再次检查必须文件 ...")
    missing2 = check_input_files()
    if missing2:
        print(f"\n[FAIL] 生成后仍有 {len(missing2)} 项缺失: {missing2}")
        print("       请检查上方生成日志中的错误（ERROR 行）。")
        return 1
    print("\n[OK] FLASH 仿真必须文件已全部就绪 ✓")
    print(f"     目录: {INPUT_DIR}")
    print(f"     文件: .par / Config / Makefile / F90×3 / run_flash.sh / submit_flash.sh / *.cn4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
