"""SNBOneCH_ml HPC 收集结果简单绘图分析 (全流程第 5 步)。

输入: flash_output/hpc_flash_ssh/ (SNBOneCH_ml.py --mode hpc 收集目录)
输出: flash_output/hpc_flash_ssh/analysis/
  1) profile_final.png  — 最新 forced plt 的密度 (+tele 若存在) 1D 剖面
  2) dt_evolution.png   — dt 与 sim time 演化 (解析 wsl_run_snbonech.log)

绘图规范 (PPT 级): 全英文, title>=24pt, labels>=20pt, ticks>=20pt,
legend>=18pt, DPI>=450, linewidth>=2。+ug 均匀网格: node_type==1 过滤
(通用安全), 非叶子块伪影防御 (见 FLASHDataLoader 教训)。

用法:
  python plot_snb_profile.py [--dir flash_output/hpc_flash_ssh]
"""
import argparse
import os
import re
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCEN_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))  # SNBOneCH_ml/
DEFAULT_COLLECT = os.path.join(SCEN_DIR, "flash_output", "hpc_flash_ssh")

# ── PPT 绘图规范 ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 20,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "lines.linewidth": 2.2, "figure.dpi": 100, "savefig.dpi": 450,
    "axes.grid": True, "grid.alpha": 0.3, "font.family": "DejaVu Sans",
})

NXB_UG = 128          # +ug nxb (与 SNBOneCH_ml.py 默认一致, 仅兜底用)


def _read_plt_profile(path: str):
    """读 FLASH hdf5 plt/chk → (x_um, dict[var->1D array], sim_time)。

    只取 node_type==1 叶子块; +ug 下全部为叶子。x 按 cm->um。"""
    import h5py

    with h5py.File(path, "r") as f:
        coords = np.array(f["coordinates"]).reshape(f["coordinates"].shape[0], -1)[:, 0]
        if "block size" in f:
            sizes = np.array(f["block size"]).reshape(f["block size"].shape[0], -1)[:, 0]
        else:  # 兜底: +ug 均匀 dx = 域宽/(nb*NXB)
            nb = coords.shape[0]
            sizes = np.full(nb, (coords.max() - coords.min()) / max(nb - 1, 1) * 1.0)
        # FLASH4 数据集名带空格: 'node type' / 'block size'
        node_type = (np.array(f["node type"]).reshape(-1)
                     if "node type" in f else np.ones(coords.shape[0]))
        leaf = node_type == 1
        fields = {}
        for var in ("dens", "tele", "tion", "trad"):
            if var in f:
                d = np.array(f[var]).reshape(f[var].shape[0], -1)
                fields[var] = d[leaf, :]
        # 仿真时间: 'sim info' 复合数据集不含 time (仅构建信息) → 留空,
        # 由调用方用 log 末行 t_final 兜底
        sim_time = None
    xs, data = [], []
    for b in np.where(leaf)[0]:
        nxb = fields["dens"].shape[1] if fields else NXB_UG
        dx = sizes[b] / nxb
        x_blk = coords[b] + (np.arange(nxb) + 0.5) * dx
        xs.append(x_blk)
    if not fields:
        return None
    x_all = np.concatenate(xs)
    order = np.argsort(x_all)
    out = {v: d.reshape(-1)[order] for v, d in fields.items()}
    return x_all[order] * 1e4, out, sim_time


def _find_latest_plt(collect_dir: str):
    """最新 forced plt 优先, 其次普通 plt, 最后 chk。"""
    import glob

    for pat in ("snbonechug_forced_hdf5_plt_cnt_*",
                "snbonechug_hdf5_plt_cnt_*",
                "snbonechug_hdf5_chk_*"):
        cands = sorted(glob.glob(os.path.join(collect_dir, pat)),
                       key=lambda p: int(re.search(r"_(\d+)$", p).group(1))
                       if re.search(r"_(\d+)$", p) else -1)
        if cands:
            return cands[-1]
    return None


def _parse_log_dt(log_path: str):
    """解析 FLASH 运行 log 表格行 → (steps, sim_times, dts)。"""
    steps, times, dts = [], [], []
    pat = re.compile(
        r"^\s*(\d+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+\(")
    if not os.path.isfile(log_path):
        return steps, times, dts
    with open(log_path, "r", errors="ignore") as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                steps.append(int(m.group(1)))
                times.append(float(m.group(2)))
                dts.append(float(m.group(3)))
    return steps, times, dts


def plot_all(collect_dir: str) -> int:
    out_dir = os.path.join(collect_dir, "analysis")
    os.makedirs(out_dir, exist_ok=True)
    rc = 0

    # 1) dt 演化
    log_path = os.path.join(collect_dir, "wsl_run_snbonech.log")
    steps, times, dts = _parse_log_dt(log_path)
    if times:
        fig, ax = plt.subplots(figsize=(10, 6.5))
        ax.semilogy(np.array(times) * 1e9, np.array(dts) * 1e12,
                    color="#1f77b4")
        ax.set_xlabel("Simulation time (ns)")
        ax.set_ylabel(r"$\Delta t$ (ps)")
        ax.set_title("SNBOneCH_ml time step evolution (NC-E 131 cores)")
        fig.tight_layout()
        p1 = os.path.join(out_dir, "dt_evolution.png")
        fig.savefig(p1)
        plt.close(fig)
        print(f"  ✓ {p1}  ({len(steps)} steps, t_final={times[-1]:.3e} s)")
    else:
        print("  (skip dt_evolution: log 表格行未找到)")
        rc = 2  # 部分成功

    # 2) 剖面
    latest = _find_latest_plt(collect_dir)
    if latest is None:
        print("  ✗ 未找到 plt/chk 文件", flush=True)
        return 1
    res = _read_plt_profile(latest)
    if res is None:
        print(f"  ✗ {os.path.basename(latest)} 无可用场变量", flush=True)
        return 1
    x_um, fields, sim_time = res
    if sim_time is None and times:
        sim_time = times[-1]          # log 末行兜底
    title_t = f"t = {sim_time*1e9:.4g} ns" if sim_time else ""
    n_panels = 2 if "tele" in fields else 1
    fig, axes = plt.subplots(1, n_panels, figsize=(7.2 * n_panels, 6.4))
    axes = np.atleast_1d(axes)
    ax = axes[0]
    ax.semilogy(x_um, np.maximum(fields["dens"], 1e-12), color="#d62728")
    ax.set_xlabel("x (μm)")
    ax.set_ylabel(r"Density (g/cm$^3$)")
    ax.set_title("Density profile" + (f"  ({title_t})" if title_t else ""))
    if "tele" in fields:
        ax = axes[1]
        # FLASH 3T 温度单位 K → keV
        ax.plot(x_um, np.asarray(fields["tele"], dtype=float) / 1.16045e7,
                color="#1f77b4")
        ax.set_xlabel("x (μm)")
        ax.set_ylabel("$T_e$ (keV)")
        ax.set_title("Electron temperature" + (f"  ({title_t})" if title_t else ""))
    fig.tight_layout()
    p2 = os.path.join(out_dir, "profile_final.png")
    fig.savefig(p2, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {p2}  (source={os.path.basename(latest)})")

    # 3) 终态数值摘要 (供汇报)
    if "dens" in fields:
        i_max = int(np.argmax(fields["dens"]))
        print(f"  [summary] dens max={fields['dens'].max():.4g} g/cc @ x={x_um[i_max]:.2f}um; "
              f"dens min={fields['dens'].min():.3g}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="SNBOneCH_ml 收集结果绘图分析")
    ap.add_argument("--dir", default=DEFAULT_COLLECT, help="收集目录")
    args = ap.parse_args()
    if not os.path.isdir(args.dir):
        print(f"✗ 收集目录不存在: {args.dir}")
        return 1
    print(f"绘图分析: {args.dir} → analysis/")
    return plot_all(args.dir)


if __name__ == "__main__":
    sys.exit(main())
