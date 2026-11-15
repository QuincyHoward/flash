"""FEOS 示例驱动脚本 —— 覆盖 vendored 包全部示例（Al + SiO2）

用法:
    python gen_examples.py            # 运行全部示例
    python gen_examples.py Al         # 只运行指定示例（名称过滤）
    python gen_examples.py --cn4      # 生成 .feos 后联动 .feos->cn4 转换
    python gen_examples.py --no-copy  # 不复制到 eos_op_data

输出: outputfiles/feos/gen_examples/<basename>-<timestamp>/
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GEN_EOS_OP = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GEN_EOS_OP not in sys.path:
    sys.path.insert(0, _GEN_EOS_OP)

from feos_core import FEOSInputGen  # noqa: E402

_EOS_OP_DATA = os.path.normpath(os.path.join(_GEN_EOS_OP, "eos_op_data"))


def build_params_list() -> list:
    """构建示例参数列表（覆盖 vendored 包全部示例: Al.par + SiO2.par）"""
    params_list = []

    # ── 示例 1: aluminum (Al) —— 对应 vendored EOS-Data/Al.par ──
    # Material-Number 3717, Rho_norm = 2.7 g/cm^3
    params_list.append({
        '_name': 'Al',
        '_elements': [(13.0, 1.0)],
        'material_number': 3717,
        'maxwell_flag': 1,
        'softsphere_flag': 1,
        'user_calculations_flag': 1,
        'rhonorm': 2.7,
        'rhoratio': {-6: 0, -5: 3, -4: 3, -3: 3, -2: 10, -1: 50,
                     0: 50, 1: 50, 2: 10, 3: 3, 4: 3, 5: 3, 6: 3},
        'tnorm': 1.0e3,
        'tratio': {-6: 1, -5: 2, -4: 10, -3: 20, -2: 20, -1: 10,
                   0: 2, 1: 1, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0},
    })

    # ── 示例 2: fused silica (SiO2) —— 对应 vendored EOS-Data/SiO2.par ──
    # Material-Number 7386, Rho_norm = 2.2 g/cm^3
    params_list.append({
        '_name': 'SiO2',
        '_elements': [(14.0, 1.0), (8.0, 2.0)],
        'material_number': 7386,
        'maxwell_flag': 1,
        'softsphere_flag': 1,
        'user_calculations_flag': 1,
        'rhonorm': 2.2,
        'rhoratio': {-6: 0, -5: 3, -4: 3, -3: 3, -2: 10, -1: 50,
                     0: 50, 1: 50, 2: 10, 3: 3, 4: 3, 5: 3, 6: 3},
        'tnorm': 1.0e3,
        'tratio': {-6: 1, -5: 2, -4: 10, -3: 20, -2: 20, -1: 10,
                   0: 2, 1: 1, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0},
    })

    return params_list


def copy_to_eos_op_data(paths: list) -> list:
    """将生成的表复制到 eos_op_data/Gen_eos_op_data/<stem>/ (注册表约定)"""
    copied = []
    base = os.path.join(_EOS_OP_DATA, "Gen_eos_op_data")
    for path in paths:
        if not path or not os.path.isfile(path):
            copied.append("")
            continue
        stem = os.path.splitext(os.path.basename(path))[0]
        dst_dir = os.path.join(base, stem)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(path))
        import shutil
        shutil.copy2(path, dst)
        print(f"  [+] 已复制: {dst}")
        copied.append(dst)
    return copied


def convert_to_cn4(paths: list) -> list:
    """对每个 .feos 调用 feos_to_cn4 转换器（7 群零填充）"""
    from feos_to_cn4 import feos_to_cn4
    cn4_paths = []
    for path in paths:
        if not path or not os.path.isfile(path):
            cn4_paths.append("")
            continue
        out = os.path.splitext(path)[0] + ".cn4"
        try:
            cn4 = feos_to_cn4(path, out)
            size = os.path.getsize(cn4)
            print(f"  [+] cn4 转换: {os.path.basename(cn4)}  ({size:,} bytes)")
            cn4_paths.append(str(cn4))
        except Exception as e:  # noqa: BLE001
            print(f"  [!] cn4 转换失败 ({os.path.basename(path)}): {e}")
            cn4_paths.append("")
    return cn4_paths


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_cn4 = '--cn4' in sys.argv
    do_copy = '--no-copy' not in sys.argv

    params_list = build_params_list()
    if args:
        params_list = [p for p in params_list if p['_name'] in args]
        if not params_list:
            print(f"未找到示例: {args}（可用: {[p['_name'] for p in build_params_list()]}）")
            sys.exit(1)

    print("=" * 60)
    print("FEOS 表生成 — vendored 全部示例 (Al / SiO2)")
    print("=" * 60)
    print(f"  示例: {[p['_name'] for p in params_list]}")
    print()

    output_dir = os.path.join(_SCRIPT_DIR, "outputfiles", "feos", "gen_examples")
    print(f"输出目录: {output_dir}")
    print()

    gen = FEOSInputGen()
    results = gen.batch_run(params_list, output_dir)

    print("=" * 60)
    print("生成汇总:")
    ok = True
    for r in results:
        if r and os.path.isfile(r) and os.path.getsize(r) > 0:
            print(f"  [+] {os.path.basename(r)}  ({os.path.getsize(r):,} bytes)")
        else:
            print(f"  [!] 失败: {r!r}")
            ok = False

    cn4_results = []
    if ok and do_cn4:
        print()
        print("转换 .feos -> .cn4 (7 群零填充，不透明度禁止消费):")
        cn4_results = convert_to_cn4(results)

    if ok and do_copy:
        print()
        print("复制到 Gen_eos_op_data (注册表约定位置):")
        copy_to_eos_op_data(results + [p for p in cn4_results if p])

    print("=" * 60)
    if ok:
        print("全部成功。" + ("注册名建议: al / sio2（EOS-only，不透明度为零占位）"
                           if do_copy else ""))
    else:
        print("存在失败项, 请检查上方日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()
