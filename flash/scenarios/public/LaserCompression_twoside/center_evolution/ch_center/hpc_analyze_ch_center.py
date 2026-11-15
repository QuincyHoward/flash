#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hpc_analyze_ch_center.py — 超算分析脚本（ch_center LaserSlab 专用）
====================================================================

自包含脚本（h5py + numpy + matplotlib），在超算上直接运行，
读取 FLASH checkpoint/plotfile，提取中心区域 1D 剖面并绘图。

用法 (在超算上, 由 laserslab1d_local_custom.py 自动调用):
  python hpc_analyze_ch_center.py \\
    --input-dir <outputfiles 目录> \\
    --output-dir <PNG 输出目录> \\
    --center-half-width <中心半宽, cm> \\
    --L0 <域半宽, cm>

输出:
  dens_hpc.png / tele_hpc.png / trad_hpc.png
"""

from __future__ import print_function, division

import argparse
import glob
import os


def read_flash_hdf5(path):
    """读取 FLASH HDF5 checkpoint/plotfile 文件。"""
    import numpy as np
    import h5py

    with h5py.File(path, "r") as f:
        # 仿真时间 (从 real scalars compound 中提取)
        sim_time = 0.0
        if "real scalars" in f:
            rs = f["real scalars"][:]
            for rec in rs:
                name = rec["name"].decode().strip() if isinstance(rec["name"], bytes) else rec["name"].strip()
                if name == "time":
                    sim_time = float(rec["value"])
                    break

        # 已知变量 (1D: nblocks, 1, 1, nx)
        known_vars = ["dens", "tele", "tion", "trad", "pres", "velx", "ye", "sumy"]
        data = {}
        nblocks = None
        for v in known_vars:
            if v in f:
                data[v] = f[v][:]
                if nblocks is None:
                    nblocks = data[v].shape[0]
        if nblocks is None:
            nblocks = 0

        # 边界框
        bbox = f["bounding box"][:nblocks] if nblocks else None

    return data, bbox, nblocks, float(sim_time)


def get_1d_profile(data, bbox, varname):
    """从 1D FLASH 数据中提取单元格中心坐标与值的剖面。

    算法: x_min_cell = x_min + dx/2; 每块 nx 个中心等距; 拼合→排序→去重取平均。
    """
    import numpy as np

    var_data = data.get(varname)
    if var_data is None or bbox is None:
        return None

    nblocks, nz, ny, nx = var_data.shape
    x_list, v_list = [], []
    for b in range(nblocks):
        xmin = float(bbox[b, 0, 0])
        xmax = float(bbox[b, 0, 1])
        dx = (xmax - xmin) / nx
        xs = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
        x_list.append(xs)
        v_list.append(var_data[b, 0, 0, :])

    x_all = np.concatenate(x_list)
    v_all = np.concatenate(v_list)

    idx = np.argsort(x_all, kind="mergesort")
    x_sorted = x_all[idx]
    v_sorted = v_all[idx]

    unique_x, inverse = np.unique(x_sorted, return_inverse=True)
    if len(unique_x) < len(x_sorted):
        v_unique = np.zeros_like(unique_x)
        np.add.at(v_unique, inverse, v_sorted)
        counts = np.bincount(inverse)
        v_unique /= counts
        return (unique_x.tolist(), v_unique.tolist())

    return (x_sorted.tolist(), v_sorted.tolist())


def main():
    parser = argparse.ArgumentParser(description="ch_center LaserSlab 超算分析")
    parser.add_argument("--input-dir", required=True, help="FLASH 输出目录 (含 chk/plt)")
    parser.add_argument("--output-dir", required=True, help="PNG 输出目录")
    parser.add_argument("--center-half-width", type=float, default=5e-4,
                        help="中心分析区域半宽 (cm), 默认 5e-4")
    parser.add_argument("--L0", type=float, default=1e-2,
                        help="仿真域半宽 (cm), 默认 1e-2")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 找输入文件: 优先 chk, 其次 plt
    files = (
        sorted(glob.glob(os.path.join(args.input_dir, "*chk*")))
        or sorted(glob.glob(os.path.join(args.input_dir, "*plt_cnt*")))
        or sorted(glob.glob(os.path.join(args.input_dir, "*plt*")))
    )
    if not files:
        print("[hpc_analyze] 未找到 chk/plt 文件:", args.input_dir)
        return 1

    target = files[-1]
    print("[hpc_analyze] 分析文件:", target)
    data, bbox, nblocks, sim_time = read_flash_hdf5(target)
    print("[hpc_analyze] nblocks=%d sim_time=%.6e" % (nblocks, sim_time))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    center_hw = args.center_half_width
    ok_count = 0
    for varname, fname, ylabel in [
        ("dens", "dens_hpc.png", "Density (g/cm^3)"),
        ("tele", "tele_hpc.png", "Electron Temp (eV)"),
        ("trad", "trad_hpc.png", "Radiation Temp (eV)"),
    ]:
        prof = get_1d_profile(data, bbox, varname)
        if prof is None:
            print("[hpc_analyze] 变量缺失:", varname)
            continue
        x, v = prof
        # 截取中心区域
        pts = [(xi, vi) for xi, vi in zip(x, v) if abs(xi) <= center_hw]
        if not pts:
            pts = list(zip(x, v))
        xs = [p[0] * 1e4 for p in pts]   # cm → um
        vs = [p[1] for p in pts]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(xs, vs, lw=2)
        ax.set_xlabel("x (um)")
        ax.set_ylabel(ylabel)
        ax.set_title("ch_center %s profile (t=%.3e s)" % (varname, sim_time))
        ax.grid(True, alpha=0.3)
        fig.savefig(os.path.join(args.output_dir, fname), dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("[hpc_analyze] 已生成:", fname)
        ok_count += 1

    print("[hpc_analyze] 完成, 共生成 %d 张 PNG" % ok_count)
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
