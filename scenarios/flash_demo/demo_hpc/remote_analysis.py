#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Remote FLASH Analysis Script — 在超算上运行

自包含脚本，兼容 Python 2.7+/3.x。
使用 h5py + numpy 直接读取 FLASH HDF5 checkpoint 文件，
提取密度和温度分布，生成对比图。

用法 (在超算上):
  python remote_analysis.py \\
    --dirs /path/to/power_0.5/outputfiles /path/to/power_1.0/outputfiles \\
    --powers 0.5 1.0 \\
    --output /path/to/results

输出:
  - analysis_results.json   (密度/温度摘要)
  - dens_comparison.png     (各功率密度分布对比图)
  - tele_comparison.png     (各功率电子温度对比图)
  - peak_density_vs_power.png (密度峰值随功率变化)
"""

from __future__ import print_function, division
import json
import os
import sys
import re


# ── FLASH HDF5 读取 ──────────────────────────────

def read_flash_hdf5(path):
    """读取 FLASH HDF5 checkpoint 文件。

    Args:
        path: .chk 文件路径

    Returns:
        (data_dict, bounding_box, nblocks, sim_time)
    """
    import numpy as np
    import h5py

    with h5py.File(path, "r") as f:
        # 仿真时间 (从 real scalars compound 中提取, dict-style)
        sim_time = 0.0
        if "real scalars" in f:
            rs = f["real scalars"][:]
            for rec in rs:
                name = rec["name"].decode().strip() if isinstance(rec["name"], bytes) else rec["name"].strip()
                if name == "time":
                    sim_time = float(rec["value"])
                    break

        # 数据量 (形状已知: nblocks, 1, 1, nx)
        dens = f["dens"][:]
        nblocks = dens.shape[0]

        # 打包已知变量
        known_vars = ["dens", "tele", "tion", "temp", "pres", "velx"]
        data = {}
        for v in known_vars:
            if v in f:
                data[v] = f[v][:]

        # 边界框
        bbox = f["bounding box"][:nblocks]

    return data, bbox, nblocks, float(sim_time)


def get_1d_profile(data, bbox, varname):
    """从 1D FLASH 数据中提取单元格中心坐标与值的剖面。

    使用与 `plot_dens_easy_hpc.py` 一致的单元格中心算法:
      - x_min_cell = x_min + dx/2 (首单元格中心)
      - x_max_cell = x_max - dx/2 (末单元格中心)
      - 每块 nx 个单元格中心等距分布
      - 拼合所有块, 排序, 去重

    Args:
        data: {变量名: 数组} 字典, 数组形状 (nblocks, 1, 1, nx)
        bbox: 边界框 (nblocks, 3, 2)
        varname: 变量名 (如 "dens", "tele")

    Returns:
        (x_centers, values) 或 None (变量不存在时)
    """
    import numpy as np

    var_data = data.get(varname)
    if var_data is None:
        return None

    nblocks, nz, ny, nx = var_data.shape
    x_list = []
    v_list = []
    for b in range(nblocks):
        xmin = float(bbox[b, 0, 0])
        xmax = float(bbox[b, 0, 1])
        dx = (xmax - xmin) / nx
        xs = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
        x_list.append(xs)
        v_list.append(var_data[b, 0, 0, :])

    x_all = np.concatenate(x_list)
    v_all = np.concatenate(v_list)

    # 稳定的 mergesort 确保跨平台确定性
    idx = np.argsort(x_all, kind="mergesort")
    x_sorted = x_all[idx]
    v_sorted = v_all[idx]

    # 去重: AMR 块边界处坐标重复, 取平均
    unique_x, inverse = np.unique(x_sorted, return_inverse=True)
    if len(unique_x) < len(x_sorted):
        v_unique = np.zeros_like(unique_x)
        np.add.at(v_unique, inverse, v_sorted)
        counts = np.bincount(inverse)
        v_unique /= counts
        return (unique_x.tolist(), v_unique.tolist())

    return (x_sorted.tolist(), v_sorted.tolist())


# ── 单个功率分析 ─────────────────────────────────

def analyze_power_dir(dir_path, power_factor):
    """分析单个功率变体的输出目录 (含时间演化)。

    Args:
        dir_path: 仿真输出目录
        power_factor: 功率因子

    Returns:
        分析结果字典 (含时间序列 dens_peak_over_time, tele_peak_over_time 等)
    """
    import numpy as np

    # 查找包含 chk 文件的目录
    search_dirs = [dir_path]
    for entry in os.listdir(dir_path):
        full = os.path.join(dir_path, entry)
        if os.path.isdir(full) and ("outputfiles" in entry or "chk" in entry or "plt" in entry):
            search_dirs.append(full)

    # 收集所有 checkpoint 文件
    all_chk_files = []
    for sd in search_dirs:
        files = sorted([f for f in os.listdir(sd) if "chk" in f])
        for f in files:
            all_chk_files.append(os.path.join(sd, f))
    all_chk_files = sorted(list(set(all_chk_files)))  # 去重 + 排序

    if not all_chk_files:
        return {"power_factor": power_factor, "error": "no checkpoint files found",
                "dir": dir_path}

    print("  Found " + str(len(all_chk_files)) + " checkpoint files", flush=True)

    # ── 分析最后一个 checkpoint (最终态) ──
    last_chk = all_chk_files[-1]
    try:
        data, bbox, nblocks, sim_time = read_flash_hdf5(last_chk)
    except Exception as e:
        return {"power_factor": power_factor, "error": str(e), "file": last_chk}

    result = {
        "power_factor": power_factor,
        "simulation_time": sim_time,
        "nblocks": int(nblocks),
        "checkpoint": os.path.basename(last_chk),
    }

    # 密度剖面 (最终态)
    prof = get_1d_profile(data, bbox, "dens")
    if prof:
        x, vals = prof
        result["dens_peak"] = float(np.max(vals))
        result["dens_mean"] = float(np.mean(vals))
        result["dens_x"] = x
        result["dens_y"] = vals

    # 电子温度 (最终态)
    for tv in ["tele", "tion", "temp"]:
        prof = get_1d_profile(data, bbox, tv)
        if prof:
            _, vals = prof
            result[tv + "_peak"] = float(np.max(vals))
            result[tv + "_mean"] = float(np.mean(vals))
            result[tv + "_x"] = prof[0]
            result[tv + "_y"] = prof[1]

    # ── 时间演化分析 (扫描所有 checkpoint) ──
    # 采样: 最多取 20 个均匀分布的时间点
    n_samples = min(len(all_chk_files), 20)
    step = max(1, len(all_chk_files) // n_samples)
    sampled_chks = [all_chk_files[i] for i in range(0, len(all_chk_files), step)]

    time_series = {"times": [], "dens_peaks": [], "tele_peaks": [], "dens_profiles": []}
    for chk_path in sampled_chks:
        try:
            d, bb, nb, t = read_flash_hdf5(chk_path)
            time_series["times"].append(t)
            # 密度峰值
            p = get_1d_profile(d, bb, "dens")
            if p:
                _, vals = p
                time_series["dens_peaks"].append(float(np.max(vals)))
                # 保存采样的密度剖面 (最多保存 5 个时间点用于绘图)
                if len(time_series["dens_profiles"]) < 5:
                    time_series["dens_profiles"].append({
                        "time": t, "x": p[0], "y": p[1]
                    })
            # 温度峰值
            for tv in ["tele", "tion"]:
                p = get_1d_profile(d, bb, tv)
                if p:
                    _, vals = p
                    key = tv + "_peaks"
                    if key not in time_series:
                        time_series[key] = []
                    time_series[key].append(float(np.max(vals)))
                    break
        except Exception:
            pass

    if time_series["times"]:
        result["time_series"] = time_series

    return result


# ── 主入口 ───────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Remote FLASH Analysis")
    parser.add_argument("--dirs", nargs="+", required=True,
                        help="Simulation output directories")
    parser.add_argument("--powers", nargs="+", type=float, required=True,
                        help="Power factors (matching --dirs order)")
    parser.add_argument("--output", default="analysis_results",
                        help="Output prefix (default: analysis_results)")
    args = parser.parse_args()

    if len(args.dirs) != len(args.powers):
        print("ERROR: --dirs and --powers must have same length", flush=True)
        sys.exit(1)

    print("FLASH Remote Analysis - " + str(len(args.dirs)) + " power variants", flush=True)
    print("Output prefix: " + args.output, flush=True)

    # 分析各功率
    all_results = {}
    for d, pf in zip(args.dirs, args.powers):
        print("\nAnalyzing power x" + str(pf) + ": " + d, flush=True)
        result = analyze_power_dir(d, pf)
        key = "power_" + str(pf)
        all_results[key] = result
        if "error" in result:
            print("  ERROR: " + str(result["error"]), flush=True)
        else:
            print("  dens_peak=" + str(result.get("dens_peak", "N/A")), flush=True)
            print("  tele_peak=" + str(result.get("tele_peak", "N/A")) + " K", flush=True)

    # 保存 JSON 摘要
    json_path = args.output + ".json"
    json_out = {}
    for k, v in all_results.items():
        entry = dict(v)
        # 坐标数据太长, 简单统计即足够
        for coord_key in ["dens_x", "dens_y", "tele_x", "tele_y", "tion_x", "tion_y", "temp_x", "temp_y"]:
            if coord_key in entry:
                del entry[coord_key]
        json_out[k] = entry

    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)
    print("\nJSON summary saved: " + json_path, flush=True)

    # ── 生成对比图 (需要 matplotlib, 尝试安装) ──
    HAS_MPL = False
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # ── PPT-friendly plot style (fonts >= 18, English only) ──
        try:
            from output_processors.plotter.plot_style import apply_plot_style
            apply_plot_style()
        except ImportError:
            pass
        import numpy as np
        HAS_MPL = True
    except ImportError:
        # 尝试通过 pip 安装 matplotlib (超算环境可用)
        print("\nmatplotlib not found, attempting pip install...", flush=True)
        try:
            import subprocess
            result = subprocess.call(
                [sys.executable, "-m", "pip", "install", "matplotlib",
                 "--quiet", "--user"],
                timeout=120,
            )
            if result == 0:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                import numpy as np
                HAS_MPL = True
                print("  matplotlib installed successfully via pip", flush=True)
            else:
                print("  pip install failed (code=" + str(result) + ")", flush=True)
        except Exception as e:
            print("  pip install exception: " + str(e), flush=True)

    if HAS_MPL:
        print("\nGenerating plots...", flush=True)

        # 图 1: 密度分布对比 (最终态)
        fig, ax = plt.subplots(figsize=(10, 6))
        for key in sorted(all_results.keys()):
            result = all_results[key]
            if "dens_x" in result and "dens_y" in result:
                ax.plot(result["dens_x"], result["dens_y"],
                        label="Power x" + str(result["power_factor"]))
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("Density (g/cm$^3$)")
        ax.set_title("Density Distribution (Power Factor Comparison)")
        ax.legend()
        fig.savefig(args.output + "_dens_comparison.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("  Plot: " + args.output + "_dens_comparison.png", flush=True)

        # 图 2: 电子温度对比 (最终态)
        fig, ax = plt.subplots(figsize=(10, 6))
        for key in sorted(all_results.keys()):
            result = all_results[key]
            if "tele_x" in result and "tele_y" in result:
                ax.plot(result["tele_x"], result["tele_y"],
                        label="Power x" + str(result["power_factor"]))
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("Electron Temperature (K)")
        ax.set_title("Electron Temperature (Power Factor Comparison)")
        ax.legend()
        fig.savefig(args.output + "_tele_comparison.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("  Plot: " + args.output + "_tele_comparison.png", flush=True)

        # 图 3: 密度峰值 vs 功率因子
        fig, ax = plt.subplots(figsize=(8, 5))
        powers = []
        peaks = []
        for key in sorted(all_results.keys()):
            result = all_results[key]
            if "dens_peak" in result:
                powers.append(result["power_factor"])
                peaks.append(result["dens_peak"])
        if powers:
            ax.plot(powers, peaks, "o-", linewidth=2, markersize=8)
            ax.set_xlabel("Power Factor")
            ax.set_ylabel("Peak Density (g/cm$^3$)")
            ax.set_title("Peak Density vs Power Factor")
            ax.grid(True, alpha=0.3)
            fig.savefig(args.output + "_peak_density_vs_power.png", dpi=200, bbox_inches="tight")
            plt.close(fig)
            print("  Plot: " + args.output + "_peak_density_vs_power.png", flush=True)

        # 图 4: 密度峰值随时间演化 (时间序列)
        has_time_series = any("time_series" in r for r in all_results.values())
        if has_time_series:
            fig, ax = plt.subplots(figsize=(10, 6))
            for key in sorted(all_results.keys()):
                result = all_results[key]
                ts = result.get("time_series", {})
                times = ts.get("times", [])
                dpeaks = ts.get("dens_peaks", [])
                if times and dpeaks:
                    ax.plot(times, dpeaks, "o-", linewidth=1.5, markersize=4,
                            label="Power x" + str(result.get("power_factor", "")))
            if ax.lines:
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Peak Density (g/cm$^3$)")
                ax.set_title("Density Peak Evolution Over Time")
                ax.legend()
                fig.savefig(args.output + "_dens_peak_vs_time.png", dpi=200, bbox_inches="tight")
                plt.close(fig)
                print("  Plot: " + args.output + "_dens_peak_vs_time.png", flush=True)
            else:
                plt.close(fig)

            # 图 5: 各功率密度剖面时间演化 (多子图)
            n_powers = len([k for k in all_results if "time_series" in all_results[k]])
            if n_powers > 0:
                fig, axes = plt.subplots(1, n_powers, figsize=(6 * n_powers, 5),
                                         squeeze=False)
                for idx, key in enumerate(sorted(all_results.keys())):
                    result = all_results[key]
                    ts = result.get("time_series", {})
                    profiles = ts.get("dens_profiles", [])
                    if not profiles:
                        continue
                    ax_i = axes[0][idx]
                    for prof in profiles:
                        ax_i.plot(prof["x"], prof["y"],
                                  label="t=" + "{:.2e}".format(prof["time"]) + "s")
                    ax_i.set_xlabel("x (cm)")
                    ax_i.set_ylabel("Density (g/cm$^3$)")
                    ax_i.set_title("Power x" + str(result.get("power_factor", "")))
                    ax_i.legend()
                fig.tight_layout()
                fig.savefig(args.output + "_dens_evolution.png", dpi=200, bbox_inches="tight")
                plt.close(fig)
                print("  Plot: " + args.output + "_dens_evolution.png", flush=True)

        print("All plots generated.", flush=True)

    # 保存完整数据 (含坐标和时间序列)
    full_json_path = args.output + "_full.json"
    with open(full_json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print("Full data: " + full_json_path, flush=True)


if __name__ == "__main__":
    main()
