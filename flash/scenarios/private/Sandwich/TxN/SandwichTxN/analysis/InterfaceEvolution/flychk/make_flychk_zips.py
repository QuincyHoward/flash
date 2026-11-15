#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_flychk_zips — Si 区平均量 → 两类 NIST FLYCHK history 输入 zip.

数据源: data/si_history.csv (extract_interfaces.py 产物, 299 帧非均匀采样)
  Si 区域定义: dens·targ 半高段内 targ≥0.5 格元算术平均 (report §7)

两类输出 (FLYCHK history 格式契约 flychk-history-v1, 元素 Si, Z=14):
  1.1  columns = time, size, te, ti, tr, ne    (ne = Si 区平均 nele, cm⁻³)
  1.3  columns = time, size, te, ti, tr, rho   (rho = dens·targ 平均, g/cm³)

时间: [0, 1.6] ns 均匀 175 点 — FLYCHK 要求 t > 0, 故取
      t_i = 1.6 ns × i/175 (i = 1..175), 末点恰为 1.6 ns, 首点 9.14 ps;
      各列由 299 帧序列线性插值 (NaN 跳过)。

输出 (flychk/out/, 两类 zip 归拢同一目录):
  history_si1.1ne_Si_Z14_in_.zip / history_si1.3rho_Si_Z14_in_.zip
  + 同名 .txt 数据表 + *_preview.png 预诊断图 + manifest.json (合并清单)
写出后自动回读自检 (zip_integrity)。

用法: python make_flychk_zips.py
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # flychk/
ROOT = HERE.parent                              # InterfaceEvolution/
DATA = ROOT / "data"
FIGS = ROOT / "figures"
OUT = HERE / "out"
REPO = ROOT
for _ in range(12):
    if (REPO / "pyproject.toml").is_file():
        break
    REPO = REPO.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
from flash.input_gen.gen_flychk_his.extract import RegionSeries
from flash.input_gen.gen_flychk_his.regions import RegionSpec
from flash.input_gen.gen_flychk_his.writer import FlychkHistoryWriter

ELEMENT = "Si"
N_PTS = 175
T0_NS, T1_NS = 0.0, 1.6

# 重采样所需源列 → 单位换算
SRC_COLS = ("time_ns", "size_um", "tele_eV_mean", "tion_eV_mean",
            "trad_eV_mean", "nele_mean", "dens_targ_mean",
            "si_areal_mass_gcm2", "si_areal_mass_all_gcm2")

TE_FLOOR_EV = 0.01          # 保留冷态 (默认 1.0 会把 t<0.1 ns 的冷 Si 钳到 1 eV)


def load_si_history():
    with open(DATA / "si_history.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for k in SRC_COLS:
        out[k] = np.array([float(r[k]) if r.get(k, "") not in ("", "nan")
                           else np.nan for r in rows])
    return out


def resample(t, y, tq):
    """NaN 跳过的线性插值重采样."""
    y = np.asarray(y, dtype=float)
    m = np.isfinite(y)
    if m.sum() < 2:
        raise ValueError("有效点不足, 无法重采样")
    return np.interp(tq, t[m], y[m])


def plot_custom_preview(table, out_png, title, areal=None):
    """自定义预诊断图 (4 面板).

    温度面板: Si 区 te≈ti 几乎重合, 实线互相覆盖 → 三线全部非实线,
    不同 dash 模式交错可见 (TE 长虚线 / TI 密点线置顶 / TR 点划线)。
    第 4 面板 (areal 给出时): Si 面质量 ∫dens·targ dx [g/cm²] —
    size 范围内 vs 全域 targ≥0.5, 水平参考线为初始值 (质量守恒核查)。
    """
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
        "font.size": 18, "axes.labelsize": 19, "axes.titlesize": 19,
        "xtick.labelsize": 17, "ytick.labelsize": 17, "legend.fontsize": 15,
        "lines.linewidth": 2.4, "figure.dpi": 150,
    })

    t_ns = table.column("time") * 1e9                 # time_unit = s
    panels = []
    # (标签, ylabel, [(图例, 数组, 颜色, 线型, zorder), ...], ylog)
    panels.append(("Temperature", "Temperature  (eV)", [
        ("TR", table.column("tr"), "#1E8449", "-.", 2),
        ("TE", table.column("te"), "#C0392B", (0, (6, 1.5)), 3),
        ("TI", table.column("ti"), "#1F4E79", (0, (1, 1)), 4),  # 密点线置顶
    ], False))
    if "ne" in table.columns:
        panels.append(("Density", r"Electron density  $n_e$  (cm$^{-3}$)", [
            ("$n_e$", table.column("ne"), "#C0392B", "-", 3),
        ], True))
    elif "rho" in table.columns:
        panels.append(("Density", r"Mass density  $\rho_{\rm Si}$  (g cm$^{-3}$)", [
            (r"$\rho_{\rm Si}$", table.column("rho"), "#C0392B", "-", 3),
        ], False))
    panels.append(("Plasma size", "Path length  (cm)", [
        ("size", table.column("size"), "#B9770E", "-", 3),
    ], True))
    if areal is not None:
        panels.append(("Si mass budget", r"Areal mass  $\int\rho_{\rm Si}\,dx$  (g cm$^{-2}$)", [
            ("all targ$\\geq$0.5", areal["all_domain"], "#7F8C8D", (0, (6, 1.5)), 2),
            ("in size range", areal["in_range"], "#C0392B", (0, (1, 1)), 3),
        ], False))

    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(6.6 * n, 6.0))
    for ax, (pname, ylabel, series, ylog) in zip(np.atleast_1d(axes), panels):
        for lbl, arr, color, ls, z in series:
            ax.plot(t_ns, arr, ls=ls, color=color, label=lbl, zorder=z,
                    lw=2.8 if ls == (0, (1, 1)) else 2.4)
        if ylog:
            ax.set_yscale("log")
        if pname == "Si mass budget" and areal is not None:
            ax.axhline(areal["initial_in"], color="k", ls=":", lw=1.5,
                       label=f"initial = {areal['initial_in']:.3e}")
        ax.set_xlabel("Time  (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(pname)
        ax.grid(alpha=0.3)
        ax.legend(framealpha=0.9, fontsize=14)
    fig.suptitle(title, fontsize=21)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main():
    data = load_si_history()
    t_ns = data["time_ns"]
    print(f"[flychk] source frames={t_ns.size}  "
          f"t=[{t_ns.min():.4f},{t_ns.max():.4f}] ns")

    # ── 均匀 175 点 (FLYCHK 需 t>0: i=1..175, 首点 9.14 ps, 末点 1.6 ns) ──
    tq_ns = T1_NS * np.arange(1, N_PTS + 1) / N_PTS
    tq_s = tq_ns * 1e-9
    cols = {k: resample(t_ns, data[k], tq_ns) for k in SRC_COLS if k != "time_ns"}
    dt_ps = np.diff(tq_ns).mean() * 1e3
    print(f"[flychk] resample: {N_PTS} pts, Δt = {dt_ps:.2f} ps, "
          f"t=[{tq_ns[0]:.4f},{tq_ns[-1]:.4f}] ns")

    spec = RegionSpec(name="placeholder", kind="whole")
    OUT.mkdir(parents=True, exist_ok=True)

    reports, manifest_regions = {}, {}
    jobs = [
        ("si1.1ne", ["time", "size", "te", "ti", "tr", "ne"],
         {"ne": cols["nele_mean"]},
         "1.1: density basis = ne (Si-region mean electron number density)"),
        ("si1.3rho", ["time", "size", "te", "ti", "tr", "rho"],
         {"rho": cols["dens_targ_mean"]},
         "1.3: density basis = rho = dens*targ (Si component mass density)"),
    ]
    for label, columns, dens_values, desc in jobs:
        values = {
            "time": tq_s,
            "te": cols["tele_eV_mean"],
            "ti": cols["tion_eV_mean"],
            "tr": cols["trad_eV_mean"],
            "size": cols["size_um"] * 1e-4,             # µm → cm
            **dens_values,
        }
        rs = RegionSeries(RegionSpec(name=label, kind="whole"),
                          times=tq_s, values=values,
                          notes=dict(agg="arithmetic-mean (targ>=0.5 in "
                                          "dens*targ half-max region)"))
        cfg = FlychkHisConfig(
            element=ELEMENT, columns=columns, time_unit="s",
            n_time_max=0, drop_nonpositive_time=True,
            te_floor=TE_FLOOR_EV, write_preview=False,   # 预览改由自定义函数绘制
        )
        writer = FlychkHistoryWriter(cfg)
        report = writer.write([rs], str(OUT), write_manifest=False,
                              self_check=True,
                              source_meta={"desc": desc})
        print(f"[flychk] {label}: {report.summary()}")
        if not report.ok:
            for r in report.results:
                print("  report:", r.report.summary() if r.report else r.error)
            raise SystemExit(f"[flychk] {label} 生成失败")
        reports[label] = report

        res = report.results[0]

        # 自定义预诊断图 (4 面板, TE/TI 非实线交错) → out/ + figures/
        prev_out = OUT / (Path(res.zip_path).stem.rstrip("_") + "_preview.png")
        areal = dict(
            in_range=cols["si_areal_mass_gcm2"],
            all_domain=cols["si_areal_mass_all_gcm2"],
            initial_in=float(data["si_areal_mass_gcm2"][0]),
            initial_all=float(data["si_areal_mass_all_gcm2"][0]),
        )
        plot_custom_preview(
            res.table, prev_out,
            f"FLYCHK history input preview - Si (Z=14), region '{label}', "
            f"{res.table.n_steps} time steps", areal=areal)
        fig_copy = FIGS / f"flychk_{label}_preview.png"
        FIGS.mkdir(exist_ok=True)
        shutil.copy(prev_out, fig_copy)

        manifest_regions[label] = dict(
            desc=desc,
            columns=columns,
            zip=str(res.zip_path),
            table=str(res.table_path) if res.table_path else None,
            preview=str(prev_out),
            integrity=res.integrity,
            n_time=int(res.table.n_steps),
        )

    # ── 合并 manifest (两类 zip 归拢同一目录, 全程可追溯) ──
    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scenario": "sandwich_txn (run 000002)",
        "source": {
            "csv": str(DATA / "si_history.csv"),
            "frames": int(t_ns.size),
            "region_def": "cells with targ>=0.5 inside dens*targ half-max span; "
                          "arithmetic mean per frame",
        },
        "resample": {
            "n_points": N_PTS,
            "t_range_ns": [T0_NS, T1_NS],
            "grid": "uniform, t_i = 1.6ns * i/175 (i=1..175); t>0 per FLYCHK contract",
            "dt_ps": float(dt_ps),
            "interp": "linear (nan-skipped) from 299-frame series",
        },
        "units": {"te/ti/tr": "eV", "size": "cm", "ne": "cm^-3",
                  "rho": "g/cm^3", "time": "s"},
        "te_floor_ev": TE_FLOOR_EV,
        "format_contract": "flychk-history-v1",
        "writer": "flash.input_gen.gen_flychk_his.FlychkHistoryWriter "
                  "(self-contained, self_check=True)",
        "regions": manifest_regions,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[flychk] OK  zips -> {OUT}")
    for label, rep in reports.items():
        for r in rep.results:
            integ = (r.integrity or {}).get("ok") if r.integrity else None
            print(f"  {label}: zip={Path(r.zip_path).name}  "
                  f"integrity_ok={integ}  n_time={r.table.n_steps}")


if __name__ == "__main__":
    main()
