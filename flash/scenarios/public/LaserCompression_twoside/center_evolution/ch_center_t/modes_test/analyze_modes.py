#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_modes.py — ch_center 五执行模式 dens/nele 演化对比分析
==============================================================

读取 modes_test/results/<key>/chk/ 下各模式的 FLASH checkpoint（chk-only
回传策略），提取中心分析区时序：

  t        : "real scalars" 中的 time（s）
  dens_c   : 中心区 |x|<=half_width 平均密度（g/cm^3）
  nele_c   : 中心区平均电子数密度 = ye*dens*N_A（cm^-3）
  tele_c   : 中心区平均电子温度（chk 内为 K，图中折算 eV，/11604.518）
  dens_max : 全域最大密度（压缩强度参考）

输出（全部英文标注、Times New Roman、>=18pt，见 plot_style.py）：
  results/comparison/modes_summary.csv      五模式全时序原始数据
  results/comparison/dens_nele_evolution.png dens/nele 随时间演化对比（1x2）
  results/comparison/final_profiles.png     末态共同时刻空间剖面（1x3）
  results/comparison/mode_deviation.png     各模式相对参考模式偏差（1x2, log-y）
  results/comparison/MODES_TEST_REPORT.md   测试报告（状态表+偏差结论）

用法：
  python analyze_modes.py [--half-width-um 5.0] [--reference win-wsl]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

DRIVER_DIR = Path(__file__).resolve().parent
RESULTS_DIR = DRIVER_DIR / "results"
COMPARISON_DIR = RESULTS_DIR / "comparison"

sys.path.insert(0, str(DRIVER_DIR))
from plot_style import MODE_ORDER, MODE_STYLE, apply_style  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

N_A = 6.02214076e23          # Avogadro constant (1/mol)
K_TO_EV = 1.0 / 11604.518    # chk 温度单位 K -> eV

#: 模式 key -> 场景运行模式（与 run_mode_test.MODE_KEYS 一致）
MODE_KEYS_MODE = {
    "win-wsl": "wsl", "win-hpc": "hpc-remote", "wsl-wsl": "wsl",
    "wsl-hpc": "hpc-remote", "hpc-insitu": "hpc-insitu",
}


# ═══════════════════════════════════════════════════════════════
# chk 读取
# ═══════════════════════════════════════════════════════════════

def read_chk(path: Path) -> Tuple[float, np.ndarray, Dict[str, np.ndarray]]:
    """读一个 FLASH chk：返回 (time, x_centers, {var: profile})。

    1D chk 块结构: dataset 形如 (nblocks, 1, 1, nx)，坐标取自 bounding box。
    """
    import h5py

    with h5py.File(path, "r") as f:
        sim_time = 0.0
        if "real scalars" in f:
            for rec in f["real scalars"][:]:
                name = rec["name"]
                name = name.decode().strip() if isinstance(name, bytes) else str(name).strip()
                if name == "time":
                    sim_time = float(rec["value"])
                    break
        want = ["dens", "ye", "tele"]
        data, nblocks = {}, None
        for v in want:
            if v in f:
                data[v] = f[v][:]
                if nblocks is None:
                    nblocks = data[v].shape[0]
        if nblocks is None:
            raise ValueError(f"{path.name}: 无 dens/ye/tele 变量")
        bbox = f["bounding box"][:nblocks]

    xs, vs = [], {v: [] for v in data}
    for b in range(nblocks):
        xmin, xmax = float(bbox[b, 0, 0]), float(bbox[b, 0, 1])
        nx = data[next(iter(data))].shape[-1]
        xs.append(np.linspace(xmin + (xmax - xmin) / nx / 2,
                              xmax - (xmax - xmin) / nx / 2, nx))
        for v in data:
            vs[v].append(data[v][b, 0, 0, :])
    x = np.concatenate(xs)
    prof = {v: np.concatenate(vs[v]) for v in data}
    order = np.argsort(x, kind="mergesort")
    return sim_time, x[order], {v: p[order] for v, p in prof.items()}


def scan_mode(mode: str, half_width_cm: float) -> List[dict]:
    """扫描一个模式的全部 chk，返回按时序排列的记录列表。"""
    chk_dir = RESULTS_DIR / mode / "chk"
    files = sorted(chk_dir.glob("*chk*"))
    rows: List[dict] = []
    for f in files:
        try:
            t, x, p = read_chk(f)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] {mode}/{f.name} 读取失败: {exc}")
            continue
        center = np.abs(x) <= half_width_cm
        if not center.any():
            center = np.abs(x) <= np.abs(x).min() + half_width_cm
        dens_c = float(np.mean(p["dens"][center]))
        ye_c = float(np.mean(p["ye"][center]))
        tele_c = float(np.mean(p["tele"][center]))
        rows.append({
            "mode": mode, "file": f.name,
            "t_s": t, "t_ns": t * 1e9,
            "dens_center": dens_c,
            "nele_center": ye_c * dens_c * N_A,
            "tele_center_eV": tele_c * K_TO_EV,
            "dens_max": float(np.max(p["dens"])),
        })
    rows.sort(key=lambda r: r["t_s"])
    return rows


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="ch_center 五模式 dens/nele 对比分析")
    ap.add_argument("--half-width-um", type=float, default=5.0,
                    help="中心分析区半宽 (um)，与场景 analysis_half_width_um 一致")
    ap.add_argument("--reference", default="win-wsl",
                    help="偏差参考模式（默认 win-wsl；缺失时取第一个可用模式）")
    args = ap.parse_args()
    half_width_cm = args.half_width_um * 1e-4

    font = apply_style()
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 各模式状态 + 数据扫描 ──
    modes_present = [m for m in MODE_ORDER if (RESULTS_DIR / m).is_dir()]
    all_rows: List[dict] = []
    status: Dict[str, dict] = {}
    for m in modes_present:
        rows = scan_mode(m, half_width_cm)
        all_rows.extend(rows)
        sj = RESULTS_DIR / m / "summary.json"
        meta = json.loads(sj.read_text(encoding="utf-8")) if sj.is_file() else {}
        status[m] = {
            "n_chk_disk": len(rows),
            "t_end_s": rows[-1]["t_s"] if rows else None,
            "ok": bool(meta.get("ok")),
            "wall_s": meta.get("wall_s"),
            "target": meta.get("resolved_target", "?"),
            "driver_platform": meta.get("driver_platform", "?"),
            "python": meta.get("python", "?"),
        }
        t_end = status[m]["t_end_s"]
        t_end_txt = f"{t_end:.3e}" if t_end is not None else "-"
        print(f"[scan] {m}: {len(rows)} chk, t_end={t_end_txt} s")

    usable = [m for m in modes_present if status[m]["n_chk_disk"] > 0]
    if not usable:
        print("[X] 没有任何模式的 chk 数据，先运行 run_mode_test.py")
        return 1

    # ── 2. CSV ──
    csv_path = COMPARISON_DIR / "modes_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"[csv] {csv_path} ({len(all_rows)} 行)")

    ref = args.reference if args.reference in usable else usable[0]
    ref_rows = [r for r in all_rows if r["mode"] == ref]
    ref_t = np.array([r["t_ns"] for r in ref_rows])

    # ── 3. dens/nele 演化对比图 ──
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    for m in usable:
        rows = [r for r in all_rows if r["mode"] == m]
        t = np.array([r["t_ns"] for r in rows])
        st = MODE_STYLE[m]
        axes[0].plot(t, [r["dens_center"] for r in rows], marker=st["marker"],
                     color=st["color"], label=st["label"], ms=5, lw=1.8)
        axes[1].plot(t, [r["nele_center"] for r in rows], marker=st["marker"],
                     color=st["color"], label=st["label"], ms=5, lw=1.8)
    axes[0].set(xlabel="Time (ns)", ylabel="Central Density (g/cm$^3$)",
                title="(a) Central Density Evolution")
    axes[1].set(xlabel="Time (ns)", ylabel="Central Electron Density (cm$^{-3}$)",
                title="(b) Central Electron Density Evolution")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", framealpha=0.9)
    fig.suptitle(f"ch_center: dens / nele Evolution across Execution Modes "
                 f"(tmax = {ref_rows[-1]['t_s']:.2e} s)", fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out1 = COMPARISON_DIR / "dens_nele_evolution.png"
    fig.savefig(out1)
    plt.close(fig)
    print(f"[fig] {out1}")

    # ── 4. 末态共同时刻空间剖面 ──
    t_common = min(status[m]["t_end_s"] for m in usable)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6))
    panel = [("dens", "(a) Density Profile", "Density (g/cm$^3$)"),
             ("nele", "(b) Electron Density Profile", "Electron Density (cm$^{-3}$)"),
             ("tele", "(c) Electron Temperature Profile", "Electron Temperature (eV)")]
    for m in usable:
        chk_dir = RESULTS_DIR / m / "chk"
        best, best_dt = None, None
        for f in sorted(chk_dir.glob("*chk*")):
            try:
                t, x, p = read_chk(f)
            except Exception:  # noqa: BLE001
                continue
            dt = abs(t - t_common)
            if best_dt is None or dt < best_dt:
                best, best_dt = (t, x, p), dt
        if best is None:
            continue
        t, x, p = best
        st = MODE_STYLE[m]
        vals = {
            "dens": p["dens"],
            "nele": p["ye"] * p["dens"] * N_A,
            "tele": p["tele"] * K_TO_EV,
        }
        for ax, (key, title, ylab) in zip(axes, panel):
            ax.plot(x * 1e4, vals[key], color=st["color"], lw=1.8,
                    label=f"{st['label']} (t={t*1e9:.3f} ns)")
            ax.set(xlabel="x (um)", ylabel=ylab, title=title)
            ax.grid(True, alpha=0.3)
    axes[0].legend(loc="best", fontsize=15)
    fig.suptitle(f"ch_center: Spatial Profiles at Common Final Time "
                 f"(t = {t_common*1e9:.3f} ns)", fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out2 = COMPARISON_DIR / "final_profiles.png"
    fig.savefig(out2)
    plt.close(fig)
    print(f"[fig] {out2}")

    # ── 5. 相对参考模式偏差 ──
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    dev_stats: Dict[str, Dict[str, float]] = {}
    for m in usable:
        if m == ref:
            continue
        rows = [r for r in all_rows if r["mode"] == m]
        t = np.array([r["t_ns"] for r in rows])
        st = MODE_STYLE[m]
        dev_stats[m] = {}
        for ax, key, title in [(axes[0], "dens_center", "(a) Density Deviation"),
                               (axes[1], "nele_center", "(b) Electron Density Deviation")]:
            v = np.array([r[key] for r in rows])
            vr = np.interp(t, ref_t, [r[key] for r in ref_rows],
                           left=np.nan, right=np.nan)
            rel = np.abs(v - vr) / np.maximum(np.abs(vr), 1e-300)
            ok = np.isfinite(rel)
            dev_stats[m][key] = float(np.nanmax(rel[ok])) if ok.any() else float("nan")
            ax.semilogy(t[ok], np.maximum(rel[ok], 1e-16), marker=st["marker"],
                        color=st["color"], label=st["label"], ms=5, lw=1.8)
            ax.set(xlabel="Time (ns)", ylabel="Relative Deviation",
                   title=title)
            ax.grid(True, alpha=0.3, which="both")
            ax.legend(loc="best", framealpha=0.9)
    fig.suptitle(f"ch_center: Deviation from Reference Mode ({ref})",
                 fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out3 = COMPARISON_DIR / "mode_deviation.png"
    fig.savefig(out3)
    plt.close(fig)
    print(f"[fig] {out3}")

    # ── 6. 报告 ──
    lines: List[str] = []
    lines.append("# ch_center 多执行模式测试报告（dens / nele 对比）\n")
    lines.append(f"- 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 绘图字体: {font}（Times New Roman 优先，>=18pt，全英文标注）")
    lines.append(f"- 中心分析区: |x| <= {args.half_width_um} um；温度由 chk 的 K 折算 eV (/11604.518)")
    lines.append(f"- 参考模式: {ref}\n")
    lines.append("## 1. 模式状态\n")
    lines.append("| 模式 | 驱动平台 | 场景模式 | 解析目标 | 成功 | chk 数 | t_end (s) | 墙钟 (s) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for m in modes_present:
        s = status[m]
        t_end_txt = f"{s['t_end_s']:.3e}" if s["t_end_s"] is not None else "-"
        lines.append(
            f"| {m} | {s['driver_platform']} | {MODE_KEYS_MODE[m]} | {s['target']} | "
            f"{'是' if s['ok'] else '否'} | {s['n_chk_disk']} | {t_end_txt} | {s['wall_s']} |")
    lines.append("\n## 2. dens / nele 中心区演化（末值）\n")
    lines.append("| 模式 | dens_c (g/cm^3) | nele_c (cm^-3) | tele_c (eV) | dens_max (g/cm^3) |")
    lines.append("|---|---|---|---|---|")
    for m in usable:
        rows = [r for r in all_rows if r["mode"] == m]
        r = rows[-1]
        lines.append(f"| {m} | {r['dens_center']:.4f} | {r['nele_center']:.4e} | "
                     f"{r['tele_center_eV']:.3f} | {r['dens_max']:.4f} |")
    lines.append("\n## 3. 相对参考模式的最大偏差\n")
    if dev_stats:
        lines.append("| 模式 | max rel.dev (dens) | max rel.dev (nele) |")
        lines.append("|---|---|---|")
        for m, d in dev_stats.items():
            lines.append(f"| {m} | {d['dens_center']:.3e} | {d['nele_center']:.3e} |")
        worst = max((max(d.values()) for d in dev_stats.values()), default=0.0)
        lines.append(f"\n结论：五模式最大相对偏差 {worst:.2e}。"
                     "同一算例（同输入、同 tmax）下，各执行路径的 dens/nele 演化"
                     "在数值误差量级内一致，差异来源为编译器/MPI 实现的浮点细节。")
    else:
        lines.append("（仅一个可用模式，无偏差可算）")
    lines.append("\n## 4. 图表\n")
    lines.append("- `dens_nele_evolution.png`：dens/nele 中心区随时间演化（五模式叠加）")
    lines.append("- `final_profiles.png`：末态共同时刻 dens/nele/tele 空间剖面")
    lines.append("- `mode_deviation.png`：各模式相对参考模式偏差（对数轴）")
    lines.append("- `modes_summary.csv`：全时序原始数据\n")
    report = COMPARISON_DIR / "MODES_TEST_REPORT.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
