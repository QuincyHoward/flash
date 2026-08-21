# -*- coding: utf-8 -*-
"""
不透明度 / 发射 / 透射率彩图一键生成脚本 (通用, 不依赖特定材料)
================================================================

对任意 IONMIX .cn4 文件, 为其每个能群绘制一张大图 (2x2 子图):
    (a) Rosseland opacity
    (b) Planck absorption opacity
    (c) Planck emission opacity
    (d) Transmission  exp(-kappa_abs * rho * L)

约定:
    x = T (eV), y = nion (cm^-3), 对数坐标;
    不透明度 colorbar 标注单位 cm^2/g; 透射率无量纲。
    标题与标签均从数据自动派生 (data.species_label), 不硬编码材料。

用法:
    python run_opacity_plots.py <file.cn4> [-o 输出目录] [-L 特征长度cm]

若未指定 cn4, 自动在 eos_op_data/Gen_eos_op_data 下搜索首个 .cn4。
"""

import argparse
import os
import sys
import glob

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from cn4_parser import load_cn4, guess_atomwt             # noqa: E402
from plot_heatmaps import plot_all_opacity_figures        # noqa: E402


def _find_default_cn4() -> str:
    """在 eos_op_data/Gen_eos_op_data 下搜索首个 .cn4 (按文件名排序)"""
    base = os.path.normpath(os.path.join(
        _SCRIPT_DIR, "..", "..", "..",
        "eos_op_data", "Gen_eos_op_data"))
    if os.path.isdir(base):
        cn4s = sorted(glob.glob(os.path.join(base, "**", "*.cn4"),
                                recursive=True))
        if cn4s:
            return cn4s[0]
    return None


def main():
    p = argparse.ArgumentParser(
        description="Plot group opacity figures for any IONMIX .cn4")
    p.add_argument("cn4", nargs="?", default=None,
                   help=".cn4 file path (default: auto-search "
                        "eos_op_data/Gen_eos_op_data)")
    p.add_argument("-o", "--outdir", default=os.path.join(_SCRIPT_DIR,
                                                          "plots", "opacity"),
                   help="output directory")
    p.add_argument("-L", "--length", type=float, default= 0.01,
                   help="transmission reference length L (cm), default 0.01")
    args = p.parse_args()

    cn4 = args.cn4 or _find_default_cn4()
    if not cn4 or not os.path.exists(cn4):
        print("[!] 未找到 .cn4 文件, 请显式指定: "
              "python run_opacity_plots.py <file.cn4>")
        sys.exit(1)

    print(f"[i] 读取 cn4: {cn4}")
    data = load_cn4(cn4)
    print(f"[i] 材料成分: {data.species_label}")
    print(f"[i] 原子量   : {data.atomwt}")
    print(f"[i] 网格     : ntemp={data.ntemp}, ndens={data.ndens}, "
          f"ngrups={data.ngrups}")
    print(f"[i] 温度范围 : {data.temperature[0]:.3e} ~ "
          f"{data.temperature[-1]:.3e} eV")
    print(f"[i] 密度范围 : {data.density[0]:.3e} ~ "
          f"{data.density[-1]:.3e} cm^-3")
    print(f"[i] 能群边界 (eV): {data.group_bounds}")
    print(f"[i] 输出目录 : {args.outdir}")
    print(f"[i] 透射率特征长度 L = {args.length} cm")
    print()

    outs = plot_all_opacity_figures(data, outdir=args.outdir,
                                    transmission_L=args.length)
    print()
    print(f"完成, 共 {len(outs)} 张大图:")
    for o in outs:
        print(f"  [+] {o}")


if __name__ == "__main__":
    main()
