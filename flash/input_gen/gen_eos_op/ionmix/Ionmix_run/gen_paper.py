#!/usr/bin/env python3
"""
gen_paper.py — 文献示例生成脚本

基于 MacFarlane (1989) 论文的 3 个典型示例：
1. 低密度氮等离子体（图6-8）
2. 高密度 SiO₂ 等离子体（图9-10）
3. 太阳成分等离子体

用法:
    python gen_paper.py

输出:
    outputfiles/cn4/gen_paper/Z{izgas}_{fracsp}-{timestamp}/
        ├── ionmxinp
        ├── Z{basename}_{timestamp}.cn4
        └── abjt_03
"""

import os
import sys

# 将当前目录加入 sys.path，使 ionmix_core 可导入
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from ionmix_core import IONMIXInputGen


def build_params_list() -> list:
    """
    构建文献示例的参数字典列表

    每个字典包含 IONMIX 完整参数，支持三种 value 类型:
    - 标量: {'ntemp': 20}
    - 索引字典: {'izgas': {1: 7, 2: 8}}  → set_parameter(name, val, idx)
    - 列表（仅 grupbd）: {'grupbd': [0.1, 1.0]}  → set_grupbd()
    - '_name': 标识该任务的名称
    """
    params_list = []

    # ================================================================
    # 示例 1: 低密度氮等离子体（论文 Section 9, Fig.6-8）
    # 单元素，温度扫描，非LTE条件
    # ================================================================
    params_list.append({
        '_name': '低密度氮等离子体（Fig.6-8）',
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
    # 示例 2: 高密度 SiO₂ 等离子体（论文 Fig.9-10）
    # 双元素，单温度点，LTE条件
    # ================================================================
    params_list.append({
        '_name': '高密度SiO₂等离子体（Fig.9-10）',
        'ngases': 2,
        'izgas': {1: 14, 2: 8},
        'atomwt': {1: 28.0855, 2: 15.9994},
        'fracsp': {1: 0.333, 2: 0.667},
        'ntemp': 1,
        'tplsma': {1: 500.0},
        'ndens': 1,
        'densnn': 1.002e21,
        'ntrad': 0,
        'nptspg': 100,
        'nfrqbb': 10,
        'dtheat': 0.01,
        'iplot': {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0},
        'isw': {
            1: 0, 6: 1, 8: 0, 13: 1, 14: 0, 15: 5,
            16: 1, 17: 0, 18: 0, 19: 0, 20: 0,
            21: 1, 24: 1, 25: 1
        },
        'grupbd': [
            100.0, 126.0, 158.0, 199.0, 251.0, 315.0, 397.0, 500.0,
            629.0, 792.0, 1000.0, 1260.0, 1580.0, 1990.0, 2510.0,
            3150.0, 3970.0, 5000.0, 6290.0, 7920.0, 10000.0
        ]
    })

    # ================================================================
    # 示例 3: 太阳成分等离子体（论文 Section 9，简化为 5 种主量元素）
    # 原论文使用 10 种元素，但 IONMIX v4.8 NAMELIST 对 > 5 种元素的
    # 小丰度混合物存在 Fortran "End of file" 读取错误。
    # 此处简化为 H+He+C+N+O 太阳丰度前 5 种元素。
    # ================================================================
    params_list.append({
        '_name': '太阳成分(5元素简版)',
        'ngases': 5,
        'izgas': {1: 1, 2: 2, 3: 6, 4: 7, 5: 8},
        'atomwt': {1: 1.00794, 2: 4.002602, 3: 12.0107, 4: 14.0067, 5: 15.9994},
        'fracsp': {1: 0.94, 2: 0.06, 3: 3.4e-4, 4: 0.8e-4, 5: 5.6e-4},
        'ntemp': 20,
        'dlgtmp': 0.2,
        'tplsma': {1: 1.0},
        'ndens': 1,
        'densnn': 1.0e8,
        'ntrad': 0,
        'nptspg': 50,
        'nfrqbb': 5,
        'dtheat': 0.01,
        'iplot': {1: 0, 2: 1, 3: 0, 4: 0, 5: 1, 6: 0},
        'isw': {
            1: 0, 6: 3, 8: 0, 13: 0, 14: 0, 15: 3,
            16: 0, 17: 0, 18: 0, 19: 0, 20: 0,
            21: 1, 24: 1, 25: 1
        },
        'grupbd': [0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0]
    })

    return params_list


def main():
    print("=" * 60)
    print("IONMIX 文献示例生成器")
    print("基于 MacFarlane (1989) CPC 56, 259-278")
    print("=" * 60)
    print()

    # 输出目录: 相对于本脚本所在目录
    output_dir = os.path.join(_SCRIPT_DIR, "outputfiles", "cn4", "gen_paper")
    print(f"输出目录: {output_dir}")
    print()

    # 创建生成器
    gen = IONMIXInputGen()
    params_list = build_params_list()

    # 批量运行
    results = gen.batch_run(params_list, output_dir)

    # 汇总
    print("=" * 60)
    print("生成汇总:")
    for r in results:
        if r:
            basename = os.path.basename(os.path.dirname(r))
            cn4_name = os.path.basename(r)
            size = os.path.getsize(r) if os.path.exists(r) else 0
            print(f"  [+] {basename}/")
            print(f"      └── {cn4_name}  ({size:,} bytes)")
        else:
            print(f"  [!] 失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
