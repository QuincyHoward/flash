"""三系列对比图包（从 three_series_scalars.csv 出图，剖面另读 HDF5）。

为什么单独一个绘图脚本
----------------------
`compare_three_series.py` 负责**慢的**部分（逐帧读 9 个 run ≈ 1500 帧 → CSV）；
本脚本只读那个 CSV 出图，秒级可迭代。剖面只在少数时刻读 HDF5。

三条口径（与 compare_three_series 一致，勿改）
1. 物种场是质量分数，质心用 ρX 加权；
2. 三个系列 plt 间隔 500/2000/500 步且 dt 随演化变化 ⇒ 速度不能直接帧差：
   先插到均匀时间网格，再用 Savitzky–Golay 求导（窗口按帧数自适应）；
3. plt 含父块（node type 1/2/3）⇒ 剖面"粗块先画、细块覆盖"。

产物（均在 plots/）
    pk_ti_centroid.png  pk_ti_velocity.png  pk_ti_width.png  pk_ti_frac.png
    pk_shock_front.png  pk_thermo.png       pk_profiles_1um.png
    pk_profiles_2um.png pk_summary_bars.png
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

import compare_three_series as C

OUT = C.OUT
WALL = {"base": (-250.0, 75.0), "L1500": (-1500.0, 75.0), "L500": (-500.0, 150.0)}
ORDER = ("base", "L1500", "L500")
DEPTHS = (1, 2, 3)


def load_csv():
    """{(series, depth): {col: array}}"""
    rows = list(csv.DictReader(open(OUT / "three_series_scalars.csv", encoding="utf-8")))
    data = {}
    for r in rows:
        key = (r["series"], int(r["depth_um"]))
        data.setdefault(key, {}).setdefault("_n", 0)
        for k, v in r.items():
            if k in ("series", "depth_um", "frame"):
                continue
            data[key].setdefault(k, []).append(float(v) if v not in ("", "nan") else np.nan)
    return {k: {kk: np.asarray(vv, dtype=float) for kk, vv in d.items() if kk != "_n"}
            for k, d in data.items()}


def wall_time(d: dict, series: str, margin: float = 25.0) -> float:
    """Ti 层接近左墙（余量 < margin µm）的时刻；不触及则返回末时刻。"""
    x0 = d.get("targ_x0")
    if x0 is None:
        return float(d["t"][-1])
    lim = WALL[series][0] + margin
    idx = np.where(np.nan_to_num(x0, nan=1e9) < lim)[0]
    return float(d["t"][idx[0]]) if len(idx) else float(d["t"][-1])


def smoothed_velocity(t, xc, npts=240, avg=13):
    """均匀网格上的梯度 + 滑动平均（等效 ~80 ps 分辨率的平滑速度，µm/s）。

    ★ 两点必须做对，否则出假信号（本项目实测踩过）：
    1. `savgol_filter` 的 `delta` 默认 1（按采样序号求导），必须传真实步长；
    2. 先切成"撞墙前"再求导/平滑，否则 SG 窗口跨越撞墙点会把边界回弹抹进上游。
    这里直接用 `np.gradient(y, g)` + 滑动平均，避免 delta 陷阱。
    """
    ok = np.isfinite(xc)
    if ok.sum() < 7:
        return np.array([]), np.array([])
    g = np.linspace(t[ok][0], t[ok][-1], npts)
    y = np.interp(g, t[ok], xc[ok])
    v = np.gradient(y, g)
    if avg > 1:
        ker = np.ones(avg) / avg
        v = np.convolve(v, ker, mode="same")
        # 两端被卷积衰减，补回边界值
        v[:avg // 2] = v[avg // 2]
        v[-(avg // 2):] = v[-(avg // 2) - 1]
    # ★ 帧间空洞处断线：应只抓"突发的孤立大间隔"（L1500 末段 137 ps vs 常规 7 ps），
    #   不能用全局中位数当基准 —— base 的 dt 本就单调增长（0.1→400 ps）且帧距随之增大，
    #   用中位数会把整段误判成空洞（实测误杀 64% 的点）。
    dt = np.diff(t[ok])
    if len(dt) > 8:
        ref = np.array([np.median(dt[max(0, i - 5):i + 1]) for i in range(len(dt))])
        bad = dt > 5.0 * ref
        # 用"所在区间"判定（阶跃），不能用线性插值 —— 否则空洞边缘仍会留下半段假斜率。
        idx = np.clip(np.searchsorted(t[ok], g, side="right") - 1, 0, len(bad) - 1)
        v = np.where(bad[idx], np.nan, v)
    return g, v


def panel3(ylab, title, fname, fn, ylog=False, note_wall=True):
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8), layout="constrained")
    for ax, dep in zip(axes, DEPTHS):
        for s in ORDER:
            d = DATA.get((s, dep))
            if d is None:
                continue
            t = d["t"]
            tw = wall_time(d, s)
            m = t <= tw * 1.0001
            y = fn(d)
            ax.plot(t[m] * 1e9, y[m], C.SERIES[s]["ls"], color=C.SERIES[s]["color"],
                    lw=2.2, label=C.SERIES[s]["label"])
            if note_wall and tw < t[-1] * 0.995:
                ax.axvline(tw * 1e9, color=C.SERIES[s]["color"], ls=":", lw=1.2, alpha=0.8)
        if ylog:
            ax.set_yscale("log")
        ax.set_xlabel("time [ns]")
        ax.set_ylabel(ylab)
        ax.set_title(f"{title} — {dep} $\\mu$m")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8, loc="best")
    if note_wall:
        fig.supxlabel("dotted vertical lines = Ti layer reaching within 25 $\\mu$m of the left wall "
                      "(beyond that the curve is boundary-limited)", fontsize=9)
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)
    print("[OK]", OUT / fname)


def fig_velocity():
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8), layout="constrained")
    for ax, dep in zip(axes, DEPTHS):
        for s in ORDER:
            d = DATA.get((s, dep))
            if d is None or "targ_xc" not in d:
                continue
            tw = wall_time(d, s, margin=40.0)
            # ★ 先把"撞墙之后"的帧切掉再平滑：SG 窗口会跨越撞墙点，
            #   否则边界造成的质心回弹会污染撞墙前 ~60 ps 的速度。
            m = d["t"] <= tw
            g, v = smoothed_velocity(d["t"][m], d["targ_xc"][m])
            if len(g) == 0:
                continue
            ax.plot(g * 1e9, v * 1e-11, C.SERIES[s]["ls"],
                    color=C.SERIES[s]["color"], lw=2.2, label=C.SERIES[s]["label"])
            if tw < d["t"][-1] * 0.995:
                ax.axvline(tw * 1e9, color=C.SERIES[s]["color"], ls=":", lw=1.2, alpha=0.8)
        ax.set_xlabel("time [ns]")
        ax.set_ylabel("$v_{Ti}$ [$10^5$ m/s]")
        ax.set_title(f"Ti layer velocity — {dep} $\\mu$m")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(OUT / "pk_ti_velocity.png", dpi=150)
    plt.close(fig)
    print("[OK]", OUT / "pk_ti_velocity.png")


def fig_shock():
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8), layout="constrained")
    for ax, dep in zip(axes, DEPTHS):
        for s in ORDER:
            d = DATA.get((s, dep))
            if d is None:
                continue
            t = d["t"]
            ax.plot(t * 1e9, d["x_dens_max"], C.SERIES[s]["ls"],
                    color=C.SERIES[s]["color"], lw=2.2, label=f"{C.SERIES[s]['label']} shock")
            if "samp_x1" in d:
                ax.plot(t * 1e9, d["samp_x1"], C.SERIES[s]["ls"],
                        color=C.SERIES[s]["color"], lw=1.3, alpha=0.55)
        ax.axhline(WALL["base"][1], color="0.35", ls=":", lw=1.2)
        ax.axhline(WALL["L500"][1], color="0.6", ls=":", lw=1.2)
        ax.set_xlabel("time [ns]")
        ax.set_ylabel("x [$\\mu$m]")
        ax.set_title(f"shock (bold) & CH front (thin) — {dep} $\\mu$m")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.supxlabel("dotted horizontals = right walls of base/L1500 (+75) and L500 (+150) $\\mu$m",
                  fontsize=9)
    fig.savefig(OUT / "pk_shock_front.png", dpi=150)
    plt.close(fig)
    print("[OK]", OUT / "pk_shock_front.png")


def fig_thermo():
    fig, axes = plt.subplots(2, 3, figsize=(16.5, 8.4), layout="constrained")
    for j, dep in enumerate(DEPTHS):
        for i, (k, lab) in enumerate((("dens_max", "$\\rho_{max}$ [g/cm$^3$]"),
                                      ("tele_max", "$T_{e,max}$ [eV]"))):
            ax = axes[i, j]
            for s in ORDER:
                d = DATA.get((s, dep))
                if d is None or k not in d:
                    continue
                ax.plot(d["t"] * 1e9, d[k], C.SERIES[s]["ls"],
                        color=C.SERIES[s]["color"], lw=2.2, label=C.SERIES[s]["label"])
            ax.set_xlabel("time [ns]")
            ax.set_ylabel(lab)
            ax.set_title(f"{'peak density' if i == 0 else 'peak Te'} — {dep} $\\mu$m")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
    fig.savefig(OUT / "pk_thermo.png", dpi=150)
    plt.close(fig)
    print("[OK]", OUT / "pk_thermo.png")


def _profile_cache(depth):
    cache = {}
    for k in ORDER:
        d = C.run_dir(k, depth)
        if d is None:
            continue
        fs = sorted(__import__("glob").glob(str(Path(d) / "lasslab_hdf5_plt_cnt_*")),
                    key=lambda p: int(__import__("re").search(r"plt_cnt_(\d+)", p).group(1)))
        ts = []
        import h5py
        for f in fs:
            with h5py.File(f, "r") as h:
                ts.append(C.sim_time(h))
        cache[k] = (fs, np.array(ts))
    return cache


def fig_profiles(depth, times, xlim, fname):
    import h5py
    cache = _profile_cache(depth)
    fig, axes = plt.subplots(2, len(times), figsize=(5.4 * len(times), 8.4),
                             layout="constrained", squeeze=False)
    for j, tq in enumerate(times):
        for i, var in enumerate(("dens", "tele")):
            ax = axes[i, j]
            for k in ORDER:
                if k not in cache:
                    continue
                fs, ts = cache[k]
                idx = int(np.argmin(np.abs(ts - tq)))
                with h5py.File(fs[idx], "r") as h:
                    xc, y = C.profile(h, var)
                if var == "tele":
                    y = y / 11604.518
                ax.plot(xc, y, C.SERIES[k]["ls"], color=C.SERIES[k]["color"], lw=1.7,
                        label=f"{C.SERIES[k]['label']} t={ts[idx]*1e9:.2f}ns")
            if var == "dens":
                ax.set_yscale("log")
                ax.set_ylim(1e-8, 1e2)
                ax.set_ylabel("$\\rho$ [g/cm$^3$]")
            else:
                ax.set_ylabel("$T_e$ [eV]")
                ax.set_ylim(0, None)
            ax.set_xlim(*xlim)
            ax.set_xlabel("x [$\\mu$m]")
            ax.set_title(f"{'density' if var=='dens' else 'Te'} @ {tq*1e9:.2f} ns — {depth} $\\mu$m")
            ax.grid(alpha=0.3, which="both")
            ax.legend(fontsize=7)
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)
    print("[OK]", OUT / fname)


def fig_bars():
    """t=1.3 ns 的 5 个量，按深度分组、按系列着色。"""
    TQ = 1.30e-9
    metrics = (("targ_xc", "Ti centroid x [$\\mu$m]"),
               ("_v", "|$v_{Ti}$| [$10^5$ m/s]"),
               ("x_dens_max", "shock x [$\\mu$m]"),
               ("dens_max", "$\\rho_{max}$ [g/cm$^3$]"),
               ("tele_max", "$T_{e,max}$ [eV]"))
    fig, axes = plt.subplots(1, len(metrics), figsize=(20.5, 4.6), layout="constrained")
    for ax, (k, lab) in zip(axes, metrics):
        vals = {s: [] for s in ORDER}
        limited = {s: [] for s in ORDER}
        for dep in DEPTHS:
            for s in ORDER:
                d = DATA.get((s, dep))
                if d is None:
                    vals[s].append(np.nan)
                    limited[s].append(False)
                    continue
                limited[s].append(TQ > wall_time(d, s, margin=40.0))
                if k == "_v":
                    tw = wall_time(d, s, margin=40.0)
                    m = d["t"] <= tw
                    g, v = smoothed_velocity(d["t"][m], d["targ_xc"][m])
                    ok = np.isfinite(v)
                    vals[s].append(abs(float(np.interp(TQ, g[ok], v[ok]))) * 1e-11 if ok.any() else np.nan)
                else:
                    a = d[k]
                    ok = np.isfinite(a)
                    vals[s].append(float(np.interp(TQ, d["t"][ok], a[ok])) if ok.any() else np.nan)
        x = np.arange(len(DEPTHS))
        w = 0.26
        for i, s in enumerate(ORDER):
            bars = ax.bar(x + (i - 1) * w, vals[s], w, color=C.SERIES[s]["color"],
                          alpha=0.85, label=C.SERIES[s]["label"])
            # 撞墙后的读数不可信 → 打斜线标记
            for bar, lim in zip(bars, limited[s]):
                if lim:
                    bar.set_hatch("///")
                    bar.set_alpha(0.45)
        ax.set_xticks(x, [f"{d} $\\mu$m" for d in DEPTHS])
        ax.set_ylabel(lab)
        ax.set_title(lab.split(" [")[0] + f"  @ {TQ*1e9:.1f} ns")
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=6.5, loc="lower left", framealpha=0.9)
        ax.margins(y=0.18)
    fig.supxlabel("hatched bars = the Ti layer had already reached the left wall by 1.3 ns "
                  "(boundary-limited, not physical)", fontsize=9)
    fig.savefig(OUT / "pk_summary_bars.png", dpi=150)
    plt.close(fig)
    print("[OK]", OUT / "pk_summary_bars.png")



def fig_wide(depth=1, tq=1.30e-9):
    """全域密度/Te：直观显示三个系列计算域不同，base 在 -250 处被截断。"""
    import h5py
    cache = _profile_cache(depth)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), layout="constrained")
    for ax, var in zip(axes, ("dens", "tele")):
        for k in ORDER:
            if k not in cache:
                continue
            fs, ts = cache[k]
            idx = int(np.argmin(np.abs(ts - tq)))
            with h5py.File(fs[idx], "r") as h:
                xc, y = C.profile(h, var, nbin=8000)
            if var == "tele":
                y = y / 11604.518
            ax.plot(xc, y, C.SERIES[k]["ls"], color=C.SERIES[k]["color"], lw=1.6,
                    label=f"{C.SERIES[k]['label']} t={ts[idx]*1e9:.2f}ns")
        for k in ORDER:
            ax.axvline(WALL[k][0], color=C.SERIES[k]["color"], ls=":", lw=1.0, alpha=0.7)
        ax.set_xlim(-560, 170)
        if var == "dens":
            ax.set_yscale("log")
            ax.set_ylim(1e-8, 1e2)
            ax.set_ylabel("$\\rho$ [g/cm$^3$]")
        else:
            ax.set_ylabel("$T_e$ [eV]")
            ax.set_ylim(0, None)
        ax.set_xlabel("x [$\\mu$m]")
        ax.set_title(f"{'density' if var=='dens' else 'Te'} across the whole domain "
                     f"@ {tq*1e9:.1f} ns — {depth} $\\mu$m")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=7)
    fig.supxlabel("dotted verticals = left walls: base -250, L500 -500, L1500 -1500 $\\mu$m",
                  fontsize=9)
    fig.savefig(OUT / f"pk_profiles_wide_{depth}um.png", dpi=150)
    plt.close(fig)
    print("[OK]", OUT / f"pk_profiles_wide_{depth}um.png")


DATA = load_csv()

if __name__ == "__main__":
    panel3("Ti centroid x [$\\mu$m]", "Ti tracer centroid", "pk_ti_centroid.png",
           lambda d: d["targ_xc"])
    fig_velocity()
    panel3("Ti layer width [$\\mu$m]", "Ti layer thickness", "pk_ti_width.png",
           lambda d: d["targ_x1"] - d["targ_x0"], ylog=True)
    panel3("max Ti mass fraction", "Ti mixing (peak mass fraction)", "pk_ti_frac.png",
           lambda d: d["targ_frac_max"], ylog=False)
    fig_shock()
    fig_thermo()
    fig_profiles(1, (1.0e-9, 1.3e-9), (-80, 80), "pk_profiles_1um.png")
    fig_profiles(2, (1.0e-9, 1.3e-9), (-80, 80), "pk_profiles_2um.png")
    fig_bars()
    fig_wide(1)
    fig_wide(2)
