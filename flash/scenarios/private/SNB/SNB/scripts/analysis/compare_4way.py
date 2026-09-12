#!/usr/bin/env python3
"""2×2 对比绘图与定量分析 —— 辐射开关矩阵 (SNB/SNB 核心模块自带)
═══════════════════════════════════════════════════════════════════════════════

**自包含**：内置 chk 读取（不依赖外部 plot_common），单位换算与判据统一。

产出（分门别类）
----------------
    <out>/pcolor/    xt4_<var>_<tag>.png     2×2 四联时空彩图（每物理量一张）
    <out>/profiles/  prof4_<var>_<tag>.png   2×2 四联 10 时刻剖面
    <out>/ablation/  ablation_4way_<tag>.csv 烧蚀面/面密度时间序列
    <out>/compare/   summary_4way_<tag>.md   四腿定量汇总

数据源 **chk**（71 键 / float64；plt 受 plot_var 12 项上限）。

用法
----
    python scripts/analysis/compare_4way.py \
        --scene <场景目录> --out <输出目录> --tag full
    # 数据目录形如 <场景目录>/flash_output/sim_{snb,flsh}/{radon,radoff}
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.colors import LogNorm, Normalize     # noqa: E402
from matplotlib.ticker import MaxNLocator            # noqa: E402

# ── 单位换算 (chk 原生 CGS) ───────────────────────────────────
K_PER_EV = 1.1604519e4          # K → eV
ERG_CM3_TO_MBAR = 1.0e-12       # erg/cm^3 → Mbar
NA_APPROX = 6.02e23             # 与源码一致的电子数密度系数
NC_0351 = 9.05e21               # 0.351 µm 临界电子数密度 [cm^-3]

# ── 物种 A/Z (nele 离线推导用) ────────────────────────────────
SPECIES_A_Z: Dict[str, Tuple[float, float]] = {
    "cham": (4.002602, 2.0), "tar1": (6.5, 3.5),
    "tar2": (6.5, 3.5), "tar3": (6.5, 3.5),
}
SUB = {"cham": "targ", "targ": "cham"}   # 兜底物种

# ── 物理量定义: var → (标题, 单位, 色图, 是否对数) ─────────────
QUANTITIES: Dict[str, Dict[str, Any]] = {
    "tele": {"title": "Electron temperature", "unit": "eV", "cmap": "inferno", "log": False},
    "tion": {"title": "Ion temperature", "unit": "eV", "cmap": "inferno", "log": False},
    "trad": {"title": "Radiation temperature", "unit": "eV", "cmap": "magma", "log": False},
    "dens": {"title": "Mass density", "unit": "g/cm$^3$", "cmap": "viridis", "log": False},
    "pele": {"title": "Electron pressure", "unit": "Mbar", "cmap": "cividis", "log": False},
    "pres": {"title": "Total pressure", "unit": "Mbar", "cmap": "cividis", "log": False},
    "nele": {"title": "Electron number density", "unit": "cm$^{-3}$", "cmap": "turbo", "log": True},
}

plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
    "xtick.labelsize": 18, "ytick.labelsize": 18, "legend.fontsize": 18,
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.4, "font.family": "DejaVu Sans",
})


def _rel(p: Path, base: Path) -> str:
    """安全相对路径: --out 在 scene 之外时 relative_to 会抛 ValueError。"""
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return p.as_posix()


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def save_fig(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=450, bbox_inches="tight")
    plt.close(fig)
    log(f"写出 {path.name}  ({path.stat().st_size/1024:.0f} KB)", "OK")
    return path


# ══════════════════════════════════════════════════════════════
# chk 读取 (h5py, 叶子块直读)
# ══════════════════════════════════════════════════════════════
def list_chk(d: Path) -> List[Path]:
    fs = [p for p in d.glob("*hdf5_chk_*") if "forced" not in p.name]
    def num(p: Path) -> int:
        try:
            return int(p.name.rsplit("_", 1)[-1])
        except ValueError:
            return 10 ** 9
    return sorted(fs, key=num)


def _decode(v) -> str:
    return v.decode() if isinstance(v, bytes) else str(v)


def read_time(f) -> float:
    """读帧时间 [s]。★ `real scalars` 是**复合 Dataset**(非 Group),
    需用 dtype.names + 数组索引取字段; 兼容多种布局并带属性兜底。"""
    if "real scalars" in f:
        try:
            arr = f["real scalars"][()]
            dn = getattr(arr.dtype, "names", None)
            if dn:
                if len(dn) >= 2:                      # (name, value) 复合型
                    nm, vl = arr[dn[0]], arr[dn[1]]
                    for k in range(len(nm)):
                        s_ = nm[k]
                        s_ = s_.decode() if isinstance(s_, bytes) else str(s_)
                        if s_.strip().lower() in ("time", "sim time", "simulation time"):
                            return float(vl[k])
                elif len(dn) == 1 and arr.size == 1:
                    return float(arr[dn[0]])
            elif getattr(arr, "size", 0) == 1:
                return float(arr.ravel()[0])          # 纯标量数据集
        except Exception:                             # noqa: BLE001
            pass
    for k in ("time", "sim time", "simulation time", "SimulationTime"):
        try:
            if k in f.attrs:
                return float(f.attrs[k])
        except Exception:                             # noqa: BLE001
            pass
    return 0.0


def load_chk(path: Path, want: Optional[List[str]] = None) -> Dict[str, Any]:
    """读一帧 chk。**+ug 均匀网格所有块都是叶子块, 无需过滤**。

    coordinates 是**块中心**; 重建节点坐标用 bounding box 线性插值,
    拼接时每块取左闭右开避免界面重复。
    """
    with h5py.File(path, "r") as f:
        # ★ 不要用 "unknown names" 做存在性判断: 该数据集的元素是
        #   **repr 形式的定宽字符串** (如 "[b'absr']"), 解码后带引号/前缀,
        #   与变量名不相等 → 会误判为"变量不存在"而读到空数组。
        #   直接用 `key in f` (顶层数据集) 判断最稳。
        coord = f["coordinates"][:]                       # (nb, 3) 块中心
        nb = coord.shape[0]
        order = np.argsort(coord[:, 0])
        t = read_time(f)
        # 取变量
        keys = want or ["dens"]
        raw: Dict[str, np.ndarray] = {}
        for k in keys:
            if k == "nele":
                continue
            if k in f:                                   # 顶层数据集存在即读
                raw[k] = f[k][:]
        # 物种质量分数 (nele 推导需要)
        for sp in SPECIES_A_Z:
            if sp in f and sp not in raw:
                raw[sp] = f[sp][:]
        bbox = f["bounding box"][:] if "bounding box" in f else None
    # 组装: 每块 (1,1,nxb) → flatten, 用左闭右开拼接
    out_x: List[np.ndarray] = []
    out_v: Dict[str, List[np.ndarray]] = {k: [] for k in raw}
    for i in order:
        arr0 = raw.get("dens")
        if arr0 is None:
            break
        n = arr0.shape[-1]
        if bbox is not None:
            x0, x1 = float(bbox[i, 0, 0]), float(bbox[i, 0, 1])
        else:
            dx = 1.0
            x0 = float(coord[i, 0]) - dx * n / 2
            x1 = x0 + dx * n
        nodes = np.linspace(x0, x1, n + 1)
        out_x.append(0.5 * (nodes[:-1] + nodes[1:]))      # 格心
        for k, v in raw.items():
            out_v[k].append(np.asarray(v[i]).ravel()[:n])
    x = np.concatenate(out_x) * 1e4                        # cm → µm
    data = {k: np.concatenate(v) for k, v in out_v.items() if v}
    return {"t": t, "x_um": x, **data}


def load_series(d: Path, want: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """★ want 缺省 = **全部 QUANTITIES** —— 原实现缺省只读 dens,
    导致 tele/tion/trad/pele/pres 全部"无数据"。"""
    if want is None:
        want = list(QUANTITIES)
    fr = []
    for p in list_chk(d):
        try:
            fr.append(load_chk(p, want))
        except Exception as exc:                          # noqa: BLE001
            log(f"跳过 {p.name}: {exc}", "WARN")
    fr.sort(key=lambda r: r["t"])
    return fr


def electron_density(fr: Dict[str, Any]) -> Optional[np.ndarray]:
    """nele = Ye · 6.02e23 · ρ, Ye = Σ X_s·Z_s/A_s (离线推导, 两腿口径一致)。"""
    rho = fr.get("dens")
    if rho is None:
        return None
    ye = np.zeros_like(rho)
    tot = np.zeros_like(rho)
    for sp, (a, z) in SPECIES_A_Z.items():
        if sp in fr:
            f = np.asarray(fr[sp], dtype=float)
            ye += f * z / a
            tot += f
    if not np.any(tot > 0):
        # 退化: 用兜底物种
        a, z = SPECIES_A_Z["tar1"]
        return z / a * NA_APPROX * rho
    ye = np.where(tot > 0, ye, 0.0)
    return ye * NA_APPROX * rho


def convert(fr: Dict[str, Any], var: str) -> Optional[np.ndarray]:
    if var == "nele":
        return electron_density(fr)
    v = fr.get(var)
    if v is None:
        return None
    v = np.asarray(v, dtype=float)
    if var in ("tele", "tion", "trad"):
        return v / K_PER_EV
    if var in ("pele", "pres"):
        return v * ERG_CM3_TO_MBAR
    return v


# ══════════════════════════════════════════════════════════════
# 四腿定义: (显示名, leg)  —— 数据目录 = <scene>/flash_output/sim_<leg>/<tag>
# ★ 显示名必须与 GRID_ORDER 中的字面量**严格一致**(含大小写) ——
#   `fig_*4` 用 `name in grids` / `panels.get(name)` 查表, 一旦不一致
#   该面板会静默退化为 "no data" (曾因 "snb radON" vs "SNB radON" 踩坑)。
# ══════════════════════════════════════════════════════════════
LEGS_BY_TAG = {
    "radon": ("FL-SH radON", "SNB radON"),
    "radoff": ("FL-SH radOFF", "SNB radOFF"),
}
GRID_ORDER = [["FL-SH radON", "FL-SH radOFF"], ["SNB radON", "SNB radOFF"]]

# 一致性自检: 两个表必须覆盖完全相同的显示名集合
assert {n for pair in LEGS_BY_TAG.values() for n in pair} == \
       {n for row in GRID_ORDER for n in row}, \
    "LEGS_BY_TAG 与 GRID_ORDER 的显示名不一致 → 面板会退化为 'no data'"


def resolve(scene: Path, leg: str, tag: str, prefix: str = "") -> Path:
    """数据目录 = <scene>/flash_output/sim_<leg>/<prefix><tag>。

    ★ `prefix` 用于区分**同一场景的不同批次**（如短时验证 `smoke_`），
      与产出文件名的 `--tag` 解耦 —— 否则短测数据会覆盖正式数据。
    """
    return scene / "flash_output" / f"sim_{leg}" / f"{prefix}{tag}"


def load_all(scene: Path, tag: str, prefix: str = "") -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for rad, (n_sh, n_snb) in LEGS_BY_TAG.items():
        for leg, name in (("flsh", n_sh), ("snb", n_snb)):
            d = resolve(scene, leg, rad, prefix)
            fr = load_series(d)
            out[name] = fr
            log(f"{name:<14} {d.relative_to(scene)}: {len(fr)} chk 帧",
                "OK" if fr else "WARN")
    return out


# ══════════════════════════════════════════════════════════════
def build_xt_arrays(fr_list: List[Dict[str, Any]], var: str):
    xs, ts, rows = [], [], []
    for fr in fr_list:
        v = convert(fr, var)
        if v is None:
            continue
        xs.append(np.asarray(fr["x_um"], float)); rows.append(np.asarray(v, float))
        ts.append(fr["t"])
    if not rows:
        return None
    x0 = max(a.min() for a in xs); x1 = min(a.max() for a in xs)
    ng = 900
    xg = np.linspace(x0, x1, ng)
    Z = np.vstack([np.interp(xg, x, v, left=np.nan, right=np.nan)
                   for x, v in zip(xs, rows)])
    return np.asarray(ts) * 1e9, xg, Z


def fig_pcolor4(series, var, out_dir: Path, tag: str) -> Optional[Path]:
    grids = {n: build_xt_arrays(series[n], var) for n in series if series[n]}
    grids = {k: v for k, v in grids.items() if v is not None}
    if not grids:
        log(f"{var}: 无数据, 跳过", "WARN"); return None
    q = QUANTITIES[var]
    allv = np.concatenate([g[2].ravel() for g in grids.values()])
    allv = allv[np.isfinite(allv)]
    use_log = bool(q["log"])
    floor = None
    if use_log:
        pos = allv[allv > 0]
        floor = float(pos.min()) * 0.5 if pos.size else 1e-30
        norm = LogNorm(vmin=max(float(np.maximum(allv, floor).min()), floor * 1.0000001),
                       vmax=float(np.maximum(allv, floor).max()))
        cbl = f"{q['title']}  [{q['unit']}]  (log)"
    else:
        vmin, vmax = float(allv.min()), float(allv.max())
        vmax = vmax if vmax > vmin else vmin + abs(vmin) * 1e-3 + 1e-30
        norm = Normalize(vmin=vmin, vmax=vmax)
        cbl = f"{q['title']}  [{q['unit']}]"

    fig, axes = plt.subplots(2, 2, figsize=(17.5, 12.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.075, right=0.885, top=0.888, bottom=0.072,
                        hspace=0.14, wspace=0.10)
    im = None
    for r, row in enumerate(GRID_ORDER):
        for c, name in enumerate(row):
            ax = axes[r][c]
            if name not in grids:
                ax.text(.5, .5, "no data", ha="center", va="center",
                        transform=ax.transAxes, fontsize=20, color="0.45"); continue
            t_ns, xg, Z = grids[name]
            if floor is not None:
                Z = np.where(np.isfinite(Z) & (Z > 0), Z, floor)
            # ★★ 用 pcolormesh + **真实逐帧时间坐标**，**不要用 imshow**：
            #    FLASH 的 chk 由 `checkpointFileIntervalStep` 触发 → Δt 随 dt
            #    变化、**高度不均匀**（实测 AMR 腿 1.36e-12…7.19e-11，52.7×；
            #    `+ug` 腿恒定）。imshow 假设各行等间距铺在 extent 内 → 时间轴
            #    被局部拉偏可达数千个百分点，使"同一物理运动在不同腿显得
            #    前沿速度不同"（纯假象）。pcolormesh 用显式坐标即无此问题。
            X, T = np.meshgrid(xg, t_ns)
            im = ax.pcolormesh(X, T, Z, shading="auto",
                               cmap=q["cmap"], norm=norm, rasterized=True)
            ax.set_title(name, fontsize=22, pad=7)
            ax.tick_params(labelsize=18, width=2.0)
            for s in ax.spines.values():
                s.set_linewidth(2.0)
            if c == 0:
                ax.set_ylabel("Time  [ns]", fontsize=21)
            if r == 1:
                ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)
    fig.suptitle(f"{q['title']} — radiation-ON/OFF 2×2 matrix  (x-t, source: chk)",
                 fontsize=24, y=0.952)
    if im is not None:
        cax = fig.add_axes([0.900, 0.072, 0.022, 0.816])
        cb = fig.colorbar(im, cax=cax); cb.set_label(cbl, fontsize=21)
        cb.ax.tick_params(labelsize=18, width=2.0); cb.outline.set_linewidth(2.0)
        if use_log:
            cb.ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
            cb.ax.yaxis.set_minor_locator(
                plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * .1)))
            cb.ax.yaxis.set_minor_formatter(plt.NullFormatter())
        else:
            cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    return save_fig(fig, out_dir / f"xt4_{var}_{tag}.png")


def pick_even(fr: List[Dict[str, Any]], n: int, twin: Tuple[float, float]):
    if not fr:
        return []
    lo, hi = twin
    ts = np.linspace(lo, hi, n)
    ts_all = np.array([f["t"] for f in fr])
    out, used = [], set()
    for t in ts:
        i = int(np.argmin(np.abs(ts_all - t)))
        if i in used:
            continue
        used.add(i); out.append(fr[i])
    return out


def fig_profiles4(series, var, out_dir: Path, tag: str, n_times: int,
                  twin: Tuple[float, float]) -> Optional[Path]:
    q = QUANTITIES[var]
    panels: Dict[str, List[Tuple[float, np.ndarray, np.ndarray]]] = {}
    ymin, ymax = np.inf, -np.inf
    for name, fr in series.items():
        if not fr:
            continue
        lst = []
        for f in pick_even(fr, n_times, twin):
            v = convert(f, var)
            if v is None:
                continue
            v = np.asarray(v, float); x = np.asarray(f["x_um"], float)
            fin = v[np.isfinite(v)]
            if fin.size:
                ymin, ymax = min(ymin, float(fin.min())), max(ymax, float(fin.max()))
            lst.append((f["t"], x, v))
        panels[name] = lst
    if not np.isfinite(ymin):
        log(f"{var}: 无有效数据, 跳过", "WARN"); return None
    use_log = bool(q["log"]) and ymin > 0
    ylim = ((max(ymin, ymax * 1e-9), ymax) if use_log
            else (ymin - .04 * (ymax - ymin + 1e-30), ymax + .04 * (ymax - ymin + 1e-30)))

    cmap = plt.get_cmap("viridis")
    tall = [t for lst in panels.values() for t, _, _ in lst]
    t_lo, t_hi = (min(tall), max(tall)) if tall else (0., 1.)
    tr = (t_hi - t_lo) or 1.

    fig, axes = plt.subplots(2, 2, figsize=(17.5, 12.8), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.072, right=0.878, top=0.884, bottom=0.072,
                        hspace=0.13, wspace=0.10)
    for r, row in enumerate(GRID_ORDER):
        for c, name in enumerate(row):
            ax = axes[r][c]
            lst = panels.get(name) or []
            if not lst:
                ax.text(.5, .5, "no data", ha="center", va="center",
                        transform=ax.transAxes, fontsize=20, color="0.45"); continue
            ls = "--" if "radOFF" in name else "-"
            for t, x, v in lst:
                vv = np.where(v > 0, v, np.nan) if use_log else v
                ax.plot(x, vv, color=cmap(0.06 + 0.90 * (t - t_lo) / tr),
                        lw=2.6, ls=ls, solid_capstyle="round")
            ax.set_title(name, fontsize=22, pad=7)
            ax.tick_params(labelsize=18, width=2.0)
            for s in ax.spines.values():
                s.set_linewidth(2.0)
            ax.grid(alpha=0.25, lw=0.9, which="both")
            if use_log:
                ax.set_yscale("log")
                ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
                ax.yaxis.set_minor_locator(
                    plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * .1)))
                ax.yaxis.set_minor_formatter(plt.NullFormatter())
            ax.set_ylim(ylim)
            if c == 0:
                ax.set_ylabel(f"{q['title']}  [{q['unit']}]", fontsize=21)
            if r == 1:
                ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)
    fig.suptitle(f"{q['title']} — 4 legs, {n_times} times   "
                 f"(solid = radON, dashed = radOFF; source: chk)", fontsize=24, y=0.950)
    cax = fig.add_axes([0.892, 0.072, 0.020, 0.812])
    sm = plt.cm.ScalarMappable(norm=Normalize(t_lo * 1e9, t_hi * 1e9), cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax); cb.set_label("Simulation time  [ns]", fontsize=21)
    cb.ax.tick_params(labelsize=18, width=2.0); cb.outline.set_linewidth(2.0)
    cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    return save_fig(fig, out_dir / f"prof4_{var}_{tag}.png")


# ══════════════════════════════════════════════════════════════
def frame_metrics(fr: Dict[str, Any], rho_solid: float = 1.04) -> Optional[Dict[str, float]]:
    rho = fr.get("dens")
    if rho is None:
        return None
    x = np.asarray(fr["x_um"], float); rho = np.asarray(rho, float)
    sel = x <= 0.0
    if not np.any(sel):
        return None
    xs, rs = x[sel], rho[sel]
    if xs.size < 5:
        return None
    drho = np.abs(np.gradient(rs, xs))
    band = (rs > 0.02 * rho_solid) & (rs < 0.98 * rho_solid)
    x_a = float(xs[np.where(band)[0][int(np.argmax(drho[band]))]]) if np.any(band) else np.nan
    target = 0.5 * rho_solid
    above = np.where(rs >= target)[0]
    x_solid = np.nan
    if above.size:
        i1 = above[-1]
        if i1 + 1 < rs.size and rs[i1 + 1] < target and rs[i1 + 1] != rs[i1]:
            x_solid = float(xs[i1] + (target - rs[i1]) * (xs[i1 + 1] - xs[i1]) / (rs[i1 + 1] - rs[i1]))
        else:
            x_solid = float(xs[i1])
    dense = rs >= target
    M_dense = float(np.trapezoid(rs[dense], xs[dense]) * 1e-4) if np.count_nonzero(dense) >= 2 else np.nan
    ne = convert(fr, "nele"); x_c = np.nan
    if ne is not None:
        ne = np.asarray(ne, float)
        lo = x_a if np.isfinite(x_a) else 0.0
        idx = np.where((x >= lo) & (x <= lo + 80.0) & (ne >= NC_0351))[0]
        if idx.size:
            i1 = idx[-1]
            x_c = float(x[i1]) if not (i1 + 1 < ne.size and ne[i1 + 1] < NC_0351
                                       and ne[i1 + 1] != ne[i1]) else \
                float(x[i1] + (NC_0351 - ne[i1]) * (x[i1 + 1] - x[i1]) / (ne[i1 + 1] - ne[i1]))
    return {"t_ns": fr["t"] * 1e9, "x_a_um": x_a, "x_solid_um": x_solid,
            "x_c_um": x_c, "M_dense_gcm2": M_dense,
            "Mt": float(np.trapezoid(rho, x) * 1e-4),
            "rho_max": float(np.nanmax(rs)),
            "te_max": float(np.nanmax(convert(fr, "tele"))) if "tele" in fr else np.nan,
            "ti_max": float(np.nanmax(convert(fr, "tion"))) if "tion" in fr else np.nan,
            "tr_max": float(np.nanmax(convert(fr, "trad"))) if "trad" in fr else np.nan}


def rate_abl(rows: List[Dict[str, float]]) -> Tuple[float, float]:
    if len(rows) < 4:
        return float("nan"), float("nan")
    t = np.array([r["t_ns"] for r in rows]) * 1e-9
    M = np.array([r["M_dense_gcm2"] for r in rows])
    ok = np.isfinite(M) & np.isfinite(t)
    if ok.sum() < 4:
        return float("nan"), float("nan")
    t, M = t[ok], M[ok]
    # ★ 加固: polyfit 对 NaN/常数序列会抛 "SVD did not converge";
    #   先剔除 NaN 后再要求 ≥3 个点且 M 有变化, 否则返回 NaN 而不是崩溃。
    good = np.isfinite(t) & np.isfinite(M)
    t, M = t[good], M[good]
    if t.size < 3 or not np.ptp(M) > 0:
        return (float(M[0]) if M.size else float("nan")), float("nan")
    i0 = max(0, len(t) - max(3, len(t) * 30 // 100))
    if len(t) - i0 < 3:
        i0 = max(0, len(t) - 3)
    try:
        k = float(np.polyfit(t[i0:], M[i0:], 1)[0])
    except np.linalg.LinAlgError:
        return float(M[0]), float("nan")
    return float(M[0]), -k


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="2×2 辐射开关对比 (图 + 定量)")
    ap.add_argument("--scene", required=True, help="场景目录")
    ap.add_argument("--out", default=None, help="输出目录 (默认 <scene>/images)")
    ap.add_argument("--tag", default="full", help="输出命名标记")
    ap.add_argument("--data-prefix", default="",
                    help="数据目录前缀 (如 smoke_); 与 --tag 解耦, "
                         "用于读取同场景的另一批次数据")
    ap.add_argument("--n-times", type=int, default=10)
    ap.add_argument("--vars", nargs="*", default=None)
    args = ap.parse_args()

    scene = Path(args.scene).resolve()
    out = Path(args.out).resolve() if args.out else scene / "images"
    variables = list(QUANTITIES) if not args.vars else list(args.vars)

    print("\n" + "=" * 78)
    print(" 2×2 辐射开关对比 (SNB/SNB 核心模块)")
    print(f" 场景: {scene}")
    print(f" 输出: {out}")
    if args.data_prefix:
        print(f" 数据前缀: '{args.data_prefix}'")
    print("=" * 78)

    series = load_all(scene, args.tag, args.data_prefix)
    have = [n for n, f in series.items() if f]
    if not have:
        log(f"无 chk 数据 (检查 flash_output/sim_*/{{radon,radoff}}, "
            f"前缀='{args.data_prefix}')", "ERROR")
        return 1
    starts = [f[0]["t"] for f in series.values() if f]
    ends = [f[-1]["t"] for f in series.values() if f]
    twin = (max(starts), min(ends)) if ends and min(ends) > max(starts) else \
           (min(starts), max(ends))
    log(f"共同时间窗: {twin[0]*1e9:.4f} .. {twin[1]*1e9:.4f} ns "
        f"(已就绪 {len(have)}/4 腿)", "INFO")

    pdir, rdir = out / "pcolor", out / "profiles"
    adir, cdir = out / "ablation", out / "compare"
    for v in variables:
        fig_pcolor4(series, v, pdir, args.tag)
        fig_profiles4(series, v, rdir, args.tag, args.n_times, twin)

    # 定量
    metrics = {n: sorted([m for m in (frame_metrics(f) for f in series[n]) if m],
                         key=lambda r: r["t_ns"]) for n in series}
    hdr = (f"{'腿':<16}{'帧':>4}{'t末[ns]':>9}{'x_a[µm]':>9}{'M0[1e-3]':>10}"
           f"{'M末[1e-3]':>11}{'Ṁ[g/cm²/s]':>13}{'ρmax':>8}{'Te_max':>9}{'Tr_max':>10}")
    print("\n" + hdr); print("-" * len(hdr))
    summary: Dict[str, Dict[str, float]] = {}
    for n in series:
        rows = metrics[n]
        if not rows:
            print(f"{n:<16}  (无数据)"); continue
        M0, rate = rate_abl(rows); L = rows[-1]
        summary[n] = {"M0": M0, "rate": rate, **L}
        print(f"{n:<16}{len(rows):>4}{L['t_ns']:>9.3f}{L['x_a_um']:>9.2f}"
              f"{M0*1e3:>10.4f}{L['M_dense_gcm2']*1e3:>11.4f}{rate:>13.4e}"
              f"{L['rho_max']:>8.3f}{L['te_max']:>9.1f}{L['tr_max']:>10.3f}")

    print("\n  ── 辐射开关效应 (同模型内) ─────────────────────────")
    for model, a, b in (("FL-SH", "FL-SH radON", "FL-SH radOFF"),
                        ("SNB", "SNB radON", "SNB radOFF")):
        x, y = summary.get(a), summary.get(b)
        if not x or not y:
            continue
        if np.isfinite(x["rate"]) and x["rate"]:
            print(f"    {model}: 关辐射使 Ṁ 变为 **{y['rate']/x['rate']:.3f}×** "
                  f"({x['rate']:.4e} → {y['rate']:.4e})")
        print(f"          x_a {x['x_a_um']:.2f} vs {y['x_a_um']:.2f} µm; "
              f"Trad_max {x['tr_max']:.3f} vs {y['tr_max']:.3f} eV")
    print("\n  ── 模型效应 (同辐射状态) ──────────────────────────")
    for st, a, b in (("辐射开", "FL-SH radON", "SNB radON"),
                     ("辐射关", "FL-SH radOFF", "SNB radOFF")):
        x, y = summary.get(a), summary.get(b)
        if x and y and np.isfinite(x["rate"]) and x["rate"]:
            print(f"    {st}: SNB/FL-SH = **{y['rate']/x['rate']:.3f}×**  "
                  f"(x_a {y['x_a_um']:.2f} vs {x['x_a_um']:.2f} µm)")

    # 落盘
    adir.mkdir(parents=True, exist_ok=True)
    csv_out = adir / f"ablation_4way_{args.tag}.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["leg", "t_ns", "x_a_um", "x_solid_um", "x_c_um",
                    "M_dense_gcm2", "Mt", "rho_max", "te_max", "ti_max", "tr_max"])
        for n in series:
            for r in metrics[n]:
                w.writerow([n] + [r[k] for k in ("t_ns", "x_a_um", "x_solid_um",
                            "x_c_um", "M_dense_gcm2", "Mt", "rho_max",
                            "te_max", "ti_max", "tr_max")])
    log(f"时间序列表 → {_rel(csv_out, scene)}", "OK")

    cdir.mkdir(parents=True, exist_ok=True)
    md = cdir / f"summary_4way_{args.tag}.md"
    with md.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# 2×2 辐射开关矩阵 — 定量汇总\n\n")
        fh.write(f"共同时间窗 {twin[0]*1e9:.4f}–{twin[1]*1e9:.4f} ns\n\n")
        fh.write("| 腿 | 帧 | t末[ns] | x_a[µm] | M0[1e-3] | M末[1e-3] | Ṁ[g/cm²/s] | "
                 "ρmax | Te_max[eV] | Trad_max[eV] |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for n in series:
            s_ = summary.get(n)
            if not s_:
                fh.write(f"| {n} | — | — | — | — | — | — | — | — | — |\n"); continue
            fh.write(f"| {n} | {len(metrics[n])} | {s_['t_ns']:.3f} | {s_['x_a_um']:.2f} | "
                     f"{s_['M0']*1e3:.4f} | {s_['M_dense_gcm2']*1e3:.4f} | {s_['rate']:.4e} | "
                     f"{s_['rho_max']:.3f} | {s_['te_max']:.1f} | {s_['tr_max']:.3f} |\n")
    log(f"汇总表 → {_rel(md, scene)}", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
