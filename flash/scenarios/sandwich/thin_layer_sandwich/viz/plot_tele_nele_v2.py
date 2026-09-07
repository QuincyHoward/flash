"""
plot_tele_nele_v2.py — Tele/Nele 双轴精修图

从 result.h5 读取 CH 中心区域数据, 绘制:
  - Tele (eV) 左轴红色
  - Nele (cm⁻³) 右轴蓝色
  - 可选手动指定 300ps 最优窗口

用法:
  python plot_tele_nele_v2.py /path/to/result.h5 [--window-start NS] [--window-end NS]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# 电子温度转换: 1 eV = K_B/e = 11604.5 K/eV
EV_PER_K = 11604.5


def plot_tele_nele_v2(
    result_h5_path: Path,
    save_path: Path,
    *,
    center_half_width_um: float = 1.0,
    tele_base_K: float = 1.2e6,
    nele_base: float = 1.4e23,
    window_start_ns: float | None = None,
    window_end_ns: float | None = None,
    xlim_ns: tuple[float, float] | None = None,
    ylim_tele_eV: tuple[float, float] | None = None,
    ylim_nele: tuple[float, float] | None = None,
) -> Path:
    """绘制 Tele(eV,左红) + Nele(cm⁻³,右蓝) 双轴精修图。

    Args:
        result_h5_path: 引擎 result.h5 路径
        save_path: PNG 保存路径
        center_half_width_um: 中心区域半宽 (um)
        tele_base_K: Tele 基线 (K), 用于归一化显示
        nele_base: Nele 基线 (cm⁻³)
        window_start_ns: 手动指定窗口起始 (ns), None=自动
        window_end_ns: 手动指定窗口结束 (ns), None=自动
        xlim_ns: 横轴显示范围 (min_ns, max_ns), None=全范围
        ylim_tele_eV: 左轴 (Tele) 显示范围 (min_eV, max_eV), None=自动
        ylim_nele: 右轴 (Nele) 显示范围 (min, max), None=自动

    Returns:
        save_path: 保存的文件路径
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import h5py

    # ── 读取 result.h5 ──
    try:
        with h5py.File(str(result_h5_path), "r") as f:
            t = np.array(f["t"][:], dtype=float)
            x = np.array(f["x"][:], dtype=float)
            tele = np.array(f["tele"][()], dtype=float)
            ye = np.array(f["ye"][()], dtype=float)
            dens = np.array(f["dens"][()], dtype=float)
    except Exception as e:
        raise FileNotFoundError(f"无法读取 result.h5: {e}") from e

    # ── 中心区域平均 ──
    center_idx = len(x) // 2
    half_cm = center_half_width_um * 1e-4
    mask = np.abs(x - x[center_idx]) <= half_cm
    tele_center = np.mean(tele[:, mask], axis=1)
    nele_center = np.mean(ye[:, mask] * dens[:, mask] * 6.02214076e23, axis=1)

    times_ns = t * 1e9

    # ── xlim 裁剪: 数据与 xlim 同步 ──
    if xlim_ns is not None:
        xmask = (times_ns >= xlim_ns[0]) & (times_ns <= xlim_ns[1])
        t = t[xmask]
        times_ns = times_ns[xmask]
        tele_center = tele_center[xmask]
        nele_center = nele_center[xmask]

    # ── Tele 转 eV ──
    tele_eV = tele_center / EV_PER_K

    # ── 确定窗口 ──
    from flash.scenarios.collision_compression.thin_layer_sandwich.analysis.core import (
        sliding_window_txn,
    )

    if window_start_ns is not None and window_end_ns is not None:
        win_start_s = window_start_ns * 1e-9
        win_end_s = window_end_ns * 1e-9
        mask_w = (t >= win_start_s) & (t <= win_end_s)
        tele_w = tele_center[mask_w]
        nele_w = nele_center[mask_w]
        tele_norm = float(np.mean(tele_w)) / tele_base_K
        nele_norm = float(np.mean(nele_w)) / nele_base
        txn_min = min(tele_norm, nele_norm)
        window_label = f"Manual 300ps txn_min={txn_min:.3f}"
        win_start_ns = window_start_ns
        win_end_ns = window_end_ns
    else:
        # 自动最优窗口
        txn_series = tele_center * nele_center
        win = sliding_window_txn(
            t, txn_series, tele_center, nele_center,
            tele_base=tele_base_K, nele_base=nele_base,
        )
        win_start_ns = win["best_start_ns"]
        win_end_ns = win["best_end_ns"]
        window_label = (
            f"Best 300ps txn_min={win['txn_effective']:.3f}, "
            # f"tele={win['tele_mean_window']/EV_PER_K:.1f}eV, "
            # f"nele={win['nele_mean_window']:.2e})"
        )

    # ── 绘图 ──
    plt.rcParams.update({
        "font.size": 20, "axes.labelsize": 22,
        "axes.titlesize": 24, "legend.fontsize": 18,
        "lines.linewidth": 2.5, "figure.dpi": 300,
    })

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # 左轴: Tele (eV, 红色)
    color_tele = "#D62728"
    tele_base_eV = tele_base_K / EV_PER_K
    ax1.set_xlabel("Time (ns)", fontsize=24)
    ax1.set_ylabel("Tele (eV)", color=color_tele, fontsize=24)
    ax1.plot(times_ns, tele_eV, color=color_tele, linewidth=2.5,
             label="Tele")
    # Tele 基线参考线
    ax1.axhline(y=tele_base_eV, color=color_tele, linestyle=":",
                alpha=0.5, linewidth=1.8,
                label=f"Tele base ({tele_base_eV:.1f} eV)")
    ax1.tick_params(axis="y", labelcolor=color_tele, labelsize=20)
    ax1.tick_params(axis="x", labelsize=20)
    ax1.grid(True, alpha=0.3)

    # 右轴: Nele (cm⁻³, 蓝色)
    ax2 = ax1.twinx()
    color_nele = "#1F77B4"
    ax2.set_ylabel("Nele (cm⁻³)", color=color_nele, fontsize=24)
    ax2.plot(times_ns, nele_center, color=color_nele, linewidth=2.5,
             linestyle="--", label="Nele")
    # Nele 基线参考线
    ax2.axhline(y=nele_base, color=color_nele, linestyle=":",
                alpha=0.5, linewidth=1.8,
                label=f"Nele base ({nele_base:.1e} cm\u207b\u00b3)")
    ax2.tick_params(axis="y", labelcolor=color_nele, labelsize=20)

    # 窗口标注
    ax1.axvspan(win_start_ns, win_end_ns, color="green", alpha=0.12)
    ax1.axvline(x=win_start_ns, color="green", linestyle="--",
                alpha=0.6, linewidth=1.5)
    ax1.axvline(x=win_end_ns, color="green", linestyle="--",
                alpha=0.6, linewidth=1.5)

    # 图例 (自动收集, 仅保留主要曲线)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    # 仅保留 Tele 和 Nele 曲线(丢弃基线参考线在图例中显示)
    legend_handles = [lines1[0], lines2[0]]
    ax1.legend(legend_handles, ["Tele", "Nele"],
               fontsize=20, loc="upper left", framealpha=0.9)

    # 窗口信息框
    ax1.text(0.98, 0.96, window_label,
             transform=ax1.transAxes, fontsize=16,
             verticalalignment="top", horizontalalignment="right",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="wheat",
                       alpha=0.8, edgecolor="gray"))

    # 横轴范围
    if xlim_ns is not None:
        ax1.set_xlim(xlim_ns[0], xlim_ns[1])

    # 纵轴范围
    if ylim_tele_eV is not None:
        ax1.set_ylim(ylim_tele_eV[0], ylim_tele_eV[1])
    if ylim_nele is not None:
        ax2.set_ylim(ylim_nele[0], ylim_nele[1])

    fig.suptitle("Electron Temperature & Density (Center)",
                 fontsize=26, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(save_path), dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"  → {save_path.resolve()}")
    print(f"  Tele base: {tele_base_K/EV_PER_K:.1f} eV")
    print(f"  Window: {win_start_ns:.2f} ~ {win_end_ns:.2f} ns")
    return save_path


if __name__ == "__main__":
    # 确保 flash 包可导入
    import sys as _sys
    from pathlib import Path as _Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


    parser = argparse.ArgumentParser(
        description="Tele/Nele 精修图 — 从 result.h5 绘制 (双击自动查找)")
    parser.add_argument("result_h5", type=str, nargs="?",
                        default=None,
                        help="result.h5 文件路径 (默认自动查找)")
    parser.add_argument("--save", type=str, default="tele_nele_v2.png",
                        help="保存路径 (默认 tele_nele_v2.png)")
    parser.add_argument("--window-start", type=float, default=None,
                        help="手动指定窗口起始 (ns)")
    parser.add_argument("--window-end", type=float, default=None,
                        help="手动指定窗口结束 (ns)")
    parser.add_argument("--xlim", type=float, nargs=2, default=None,
                        metavar=("XMIN", "XMAX"),
                        help="横轴时间范围, 如 --xlim 0 1.2")
    parser.add_argument("--tele-base", type=float, default=110*EV_PER_K,
                        help="Tele 基线 (K), 默认 1.2e6")
    parser.add_argument("--nele-base", type=float, default=1.4e23,
                        help="Nele 基线 (cm⁻³), 默认 1.4e23")
    parser.add_argument("--ylim-tele", type=float, nargs=2, default=None,
                        metavar=("TMIN", "TMAX"),
                        help="Tele 左轴范围 (eV), 如 --ylim-tele 0 3000")
    parser.add_argument("--ylim-nele", type=float, nargs=2, default=None,
                        metavar=("NMIN", "NMAX"),
                        help="Nele 右轴范围 (cm⁻³), 如 --ylim-nele 0 1e23")
    args = parser.parse_args()

    # 自动查找 result.h5
    if args.result_h5 is None or not _Path(args.result_h5).exists():
        # 在 flash test 目录下查找最新 result.h5
        test_scenarios = _flash_root / "test" / "scenarios"
        h5_files = sorted(test_scenarios.rglob("result.h5"))
        # 也在 chsich 运行目录下查找
        chsich_runs = test_scenarios / "chsich" / "run_tools"
        if chsich_runs.exists():
            h5_files.extend(sorted(chsich_runs.rglob("result.h5")))
        h5_files = sorted(set(h5_files), key=lambda p: p.stat().st_mtime)
        if h5_files:
            args.result_h5 = str(h5_files[-1])
            print(f"自动查找 result.h5: {args.result_h5}")
        else:
            print("Error: 未找到 result.h5，请指定路径")
            _sys.exit(1)

    if not _Path(args.result_h5).exists():
        print(f"Error: {args.result_h5} 不存在")
        _sys.exit(1)

    plot_tele_nele_v2(
        _Path(args.result_h5),
        _Path(args.save),
        window_start_ns=args.window_start,
        window_end_ns=args.window_end,
        xlim_ns=tuple(args.xlim) if args.xlim else None,
        ylim_tele_eV=tuple(args.ylim_tele) if args.ylim_tele else None,
        ylim_nele=tuple(args.ylim_nele) if args.ylim_nele else None,
        tele_base_K=args.tele_base,
        nele_base=args.nele_base,
    )
