"""
layer_tracer_Ti 超算端绘图分析脚本 (独立运行, 无 flash 包依赖)
═══════════════════════════════════════════════════════════════

在超算上用 module python/3.9.6 (h5py+numpy+matplotlib) 直接读取
FLASH 1D plt HDF5, 生成 dens(x,t) 时空彩图 + 摘要 JSON。

用法 (超算端):
  module load python/3.9.6
  python layer_tracer_Ti_remote_analysis.py --outdir <outputfiles目录> \
      --save dens_timespace.png --json summary.json
"""

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def extract_1d_profile(filepath, varname="dens"):
    """从 FLASH 1D HDF5 提取变量一维剖面 (bounding box 法)。"""
    with h5py.File(str(filepath), "r") as f:
        data = f[varname][:]
        bbox = f["bounding box"][:]
    if data.ndim == 4:
        arr = data[:, 0, 0, :]
    elif data.ndim == 3:
        arr = data[:, 0, :]
    else:
        arr = data
    nblocks, nx = arr.shape
    dx = (bbox[:, 0, 1] - bbox[:, 0, 0]) / nx
    xmin_c = bbox[:, 0, 0] + dx / 2
    xmax_c = bbox[:, 0, 1] - dx / 2
    t = np.linspace(0, 1, nx)
    x = (xmin_c[:, None] * (1 - t) + xmax_c[:, None] * t).ravel()
    y = arr.ravel()
    idx = np.argsort(x, kind="mergesort")
    x_s = x[idx]
    y_s = y[idx]
    ux, inv = np.unique(x_s, return_inverse=True)
    if len(ux) < len(x_s):
        yu = np.zeros_like(ux)
        np.add.at(yu, inv, y_s)
        yu /= np.bincount(inv)
        return ux, yu
    return x_s, y_s


def read_sim_time(filepath):
    """从 real scalars 读取仿真时间 [s]。"""
    with h5py.File(str(filepath), "r") as f:
        rs = f["real scalars"][:]
        for rec in rs:
            name = rec["name"]
            name = name.decode("utf-8").strip() if isinstance(name, bytes) else str(name).strip()
            if name == "time":
                return float(rec["value"])
    return 0.0


def main():
    ap = argparse.ArgumentParser(description="layer_tracer_Ti 远端绘图分析")
    ap.add_argument("--outdir", required=True, help="plt 文件目录")
    ap.add_argument("--save", default="dens_timespace.png", help="输出 png 路径")
    ap.add_argument("--json", default="summary.json", help="输出 json 路径")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    plt_files = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*plt*"))
    plt_files = [f for f in plt_files if "forced" not in f.name]
    if not plt_files:
        print(f"[ERR] 无 plt 文件: {outdir}", flush=True)
        return 1

    records = []
    xmin = xmax = None
    for f in plt_files:
        try:
            x, d = extract_1d_profile(f, "dens")
            if x.size == 0 or d.size == 0:
                continue
            if xmin is None or x.min() < xmin:
                xmin = x.min()
            if xmax is None or x.max() > xmax:
                xmax = x.max()
            records.append((read_sim_time(f), x, d))
        except Exception as exc:  # noqa: BLE001
            print(f"  [skip] {f.name}: {exc}", flush=True)

    if not records or xmin is None:
        print("[ERR] 未能读取密度剖面", flush=True)
        return 1

    records.sort(key=lambda r: r[0])
    times = [r[0] for r in records]
    x_common = np.linspace(xmin, xmax, 4096)
    dens = np.empty((len(records), x_common.size))
    for i, (_, x_i, d_i) in enumerate(records):
        dens[i] = np.interp(x_common, x_i, d_i, left=np.nan, right=np.nan)
    dens_log = np.log10(np.maximum(dens, 1.0e-30))

    save_path = Path(args.save)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    X, T = np.meshgrid(x_common, np.asarray(times))
    pc = ax.pcolormesh(X * 1e4, T * 1e9, dens_log, shading="auto", cmap="viridis")
    cbar = fig.colorbar(pc, ax=ax)
    cbar.set_label(r"$\log_{10}(\rho)$ [g/cm$^3$]")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("t [ns]")
    ax.set_title("Density x-t map (layer_tracer_Ti)")
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=150)
    plt.close(fig)

    summary = {
        "n_plt": len(plt_files),
        "n_frames": len(records),
        "t_first": times[0],
        "t_last": times[-1],
        "xmin": float(xmin),
        "xmax": float(xmax),
        "files": [f.name for f in plt_files],
    }
    json_path = Path(args.json)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[OK] {save_path.name} ({len(records)} frames) + {json_path.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())