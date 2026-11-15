"""FEOS 用户自定义模板脚本（复制改名后使用）

用法:
    1. 复制本文件为 gen_<材料名>.py
    2. 修改 build_params_list() 中的参数
    3. python gen_<材料名>.py

注意: Material-Number 必须存在于 FEOS_Material-DB.dat
      （可用 FEOSInputGen.read_material_db() 列出全部条目）
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GEN_EOS_OP = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GEN_EOS_OP not in sys.path:
    sys.path.insert(0, _GEN_EOS_OP)

from feos_core import FEOSInputGen  # noqa: E402


def build_params_list() -> list:
    """构建参数列表 —— 在此修改为自己的算例（示例: 金 Au, Material-Number 2700）"""
    params_list = []

    # 组成 '_elements': [(Z, 每分子原子数), ...]
    #   单元材料: [(79.0, 1.0)]；混合物: [(14.0, 1.0), (8.0, 2.0)] (SiO2)
    # rhoratio/tratio: 各十进制区间的对数分布点数（x = -6..6，区间
    #   [Rho_norm*10^(x-1), Rho_norm*10^x]）；总点数 = 1 + sum(所有 ratio)
    params_list.append({
        '_name': 'Au',
        '_elements': [(79.0, 1.0)],
        'material_number': 2700,
        'maxwell_flag': 1,
        'softsphere_flag': 1,
        'user_calculations_flag': 1,
        'rhonorm': 19.3,          # 常温常压密度 (g/cm^3)
        'rhoratio': {-6: 0, -5: 3, -4: 3, -3: 3, -2: 10, -1: 50,
                     0: 50, 1: 50, 2: 10, 3: 3, 4: 3, 5: 3, 6: 3},
        'tnorm': 1.0e3,           # 温度归一化基准 (eV)
        'tratio': {-6: 1, -5: 2, -4: 10, -3: 20, -2: 20, -1: 10,
                   0: 2, 1: 1, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0},
    })

    return params_list


def main():
    print("=" * 60)
    print("FEOS 表生成 — gen_mywork (用户模板)")
    print("=" * 60)

    output_dir = os.path.join(_SCRIPT_DIR, "outputfiles", "feos", "gen_mywork")
    print(f"输出目录: {output_dir}")
    print()

    gen = FEOSInputGen()
    results = gen.batch_run(build_params_list(), output_dir)

    print("=" * 60)
    print("生成汇总:")
    ok = True
    for r in results:
        if r and os.path.isfile(r) and os.path.getsize(r) > 0:
            print(f"  [+] {os.path.basename(r)}  ({os.path.getsize(r):,} bytes)")
        else:
            print(f"  [!] 失败: {r!r}")
            ok = False
    print("=" * 60)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
