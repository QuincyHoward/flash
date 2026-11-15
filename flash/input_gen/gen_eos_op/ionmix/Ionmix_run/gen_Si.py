#!/usr/bin/env python3
"""
gen_mywork.py — 用户自定义 IONMIX 生成模板

【使用说明】
1. 将此文件复制为 gen_myjob.py（或其他你喜欢的名字）
2. 修改下方 build_params_list() 中的参数字典
3. 运行: python gen_myjob.py
4. 输出文件位于: outputfiles/cn4/gen_myjob/Z{izgas}_{fracsp}-{timestamp}.cn4

【参数字典说明】
每个字典 = 一次 IONMIX 运行，支持以下 key:
  - '_name':   任务名称（仅用于显示）
  - 'ngases':  气体种类数
  - 'izgas':   {1: Z1, 2: Z2, ...}  原子序数
  - 'atomwt':  {1: A1, 2: A2, ...}  原子量 (amu)
  - 'fracsp':  {1: f1, 2: f2, ...}  相对丰度
  - 'ntemp':   温度点数
  - 'dlgtmp':  温度对数增量
  - 'tplsma':  {1: T_start}  起始温度 (eV)
  - 'ndens':   密度点数
  - 'dlgden':  密度对数增量
  - 'densnn':  起始数密度 (cm⁻³)
  - 'ntrad':   辐射温度变温点数（0=固定）
  - 'nptspg':  每个能群网格点数
  - 'nfrqbb':  线中心附近网格点数
  - 'dtheat':  热容导数计算的温度增量分数
  - 'iplot':   {1: 0/1, 2: 0/1, ...}  绘图控制
  - 'isw':     {1: val, 6: val, ...}  控制开关
  - 'grupbd':  [边界1, 边界2, ...]  能群边界 (eV)
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from ionmix_core import IONMIXInputGen


# ================================================================
# ★ 在这里修改参数字典，添加/删除任务
# ================================================================
def build_params_list() -> list:
    """
    构建参数字典列表

    提示:
    - 每个字典 = 一次独立的 IONMIX 计算
    - 可添加多个，批量运行
    - 复制粘贴后修改 izgas/atomwt/fracsp/ntemp/densnn 等
    """
    params_list = []

    # ================================================================
    # 示例: 纯金等离子体 (高 Z, 21×21 网格)
    # ================================================================
    params_list.append({
        '_name': 'Au 金 (isw21=1, 21×21)',
        'ngases': 1,
        'izgas': {1: 79},
        'atomwt': {1: 196.97},
        'fracsp': {1: 1.0},
        'ntemp': 21,
        'dlgtmp': 0.1,
        'tplsma': {1: 500.0},
        'ndens': 21,
        'dlgden': 0.1,
        'densnn': 1.0e23,
        'ntrad': 0,
        'trad': 100.0,
        'nptspg': 5,
        'nfrqbb': 5,
        'dtheat': 0.01,
        'iplot': {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        'isw': {
            5: 0, 6: 3, 8: 3, 13: 1, 15: 5,
            21: 1, 24: 1, 25: 1
        },
        'grupbd': [
            1.0e-1, 1.0e+0, 1.0e+1, 1.0e+2,
            1.0e+3, 1.0e+4, 1.0e+5
        ]
    })

    # ================================================================
    # 示例: 纯氮等离子体 (低密度, 宽温区)
    # ================================================================
    params_list.append({
        '_name': 'N 氮 (低密度, 20点)',
        'ngases': 1,
        'izgas': {1: 7},
        'atomwt': {1: 14.0067},
        'fracsp': {1: 1.0},
        'ntemp': 20,
        'dlgtmp': 0.2,
        'tplsma': {1: 1.0},
        'ndens': 1,
        'densnn': 1.0e14,
        'ntrad': 0,
        'nptspg': 50,
        'nfrqbb': 5,
        'dtheat': 0.01,
        'iplot': {1: 1, 2: 1, 3: 1, 4: 0, 5: 1, 6: 0},
        'isw': {
            1: 0, 6: 3, 8: 0, 13: 0, 14: 0, 15: 3,
            16: 0, 17: 0, 18: 0, 19: 0, 20: 0,
            21: 1, 24: 1, 25: 1
        },
        'grupbd': [0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0]
    })

    # ================================================================
    # ★ 在此添加更多自定义任务
    # ★ 复制上面某个示例，修改参数即可
    # ================================================================

    return params_list


def main():
    print("=" * 60)
    print("IONMIX 自定义生成器")
    print("修改 gen_mywork.py 中的 build_params_list() 来定制参数")
    print("=" * 60)
    print()

    # 输出目录: 自动根据脚本文件名确定
    caller = os.path.splitext(os.path.basename(__file__))[0]
    output_dir = os.path.join(_SCRIPT_DIR, "outputfiles", "cn4", caller)
    print(f"输出目录: {output_dir}")
    print()

    gen = IONMIXInputGen()
    params_list = build_params_list()
    results = gen.batch_run(params_list, output_dir)

    print("=" * 60)
    print("生成汇总:")
    for r in results:
        if r and os.path.exists(r):
            basename = os.path.basename(os.path.dirname(r))
            cn4_name = os.path.basename(r)
            size = os.path.getsize(r)
            print(f"  [+] {basename}/")
            print(f"      ├── ionmxinp")
            print(f"      └── {cn4_name}  ({size:,} bytes)")
        else:
            print(f"  [!] 失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
