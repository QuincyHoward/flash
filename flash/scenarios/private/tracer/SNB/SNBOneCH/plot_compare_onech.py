#!/usr/bin/env python3
"""SNBOneCH vs OneCH_ml —— nele / tele / pele 对比作图
═══════════════════════════════════════════════════════════════════════════════

两个场景的关系
--------------
| | OneCH_ml | SNBOneCH |
|---|---|---|
| 电子热传导 | Spitzer + flux limiter（**local**） | **SNB 多群非局域** |
| 几何/密度/材料/激光/辐射 | 完全相同 | 完全相同 |
| 物种 | 8 标记 | 2 标记（cham/targ） |
| 数据源 | `plt`（float32） | `chk`（float64） |

物理量口径（两腿**同式**，且**统一走项目 `flash.output_processors`**）
------------------------------------------------------------------------------
* 加载：`FlashDataLoader(...).load(compute_derived=False,
  extraction_mode="h5py")` —— 走 `extract_var`，**只取叶子块**。
  ★ AMR 场景（OneCH_ml）**必须**如此：默认 `load()` 不过滤 `node type`，
  会把父块陈旧粗网格值混入并搞错坐标。
* 派生量：`DataCalculator(...).compute("nele")` / `compute("nion")` ——
  按项目 `DATA_CONFIG` 的**权威公式**（`nele = ye*dens*NA`），**不自行实现**。
* 仅单位换算在本地做：`tele/ tion/ trad` K → eV；`pele/ pres` dyne/cm² → Mbar。

★ 注意 `nele` 与 `dens` 的形态差异很大是**物理**：`ye` 是**电离态相关**的电子
  丰度（mol e⁻/g），室温冷靶 `zbar = ye/sumy ≈ 0.001` → `nele` 仅 ~1e14；
  加热到 `zbar ≈ 3.5` 才到 1e23。**不是提取错误**（详见场景 `README.md` §7）。

产出
----
    fig1_profiles_nele.png   电子数密度剖面（多时刻 × 双模型）
    fig2_profiles_tele.png   电子温度剖面
    fig3_profiles_pele.png   电子压力剖面
    fig4_xt_compare.png      x-t 时空图 2×3（上行 SNB, 下行 OneCH_ml）
    fig5_front_zoom.png      靶前区放大（x ∈ [-10, 20] µm）
    metrics_compare.csv      末帧定量对照

用法
----
    python plot_compare_onech.py --snb-scene <SNBOneCH/scene> --out <images>
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.colors import LogNorm, Normalize      # noqa: E402
from matplotlib.ticker import MaxNLocator             # noqa: E402

_HERE = Path(__file__).resolve().parent

# ── Bootstrap: 把 flash 包根加进 sys.path（OneCH_ml 的 plt 需 FlashDataLoader）
_ROOT = _HERE
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _find_snb_core() -> Path:
    for anc in [_HERE] + list(_HERE.parents):
        for cand in (anc / "SNB", anc.parent / "SNB", anc / "SNB" / "SNB"):
            if (cand / "scripts").is_dir() and (cand / "source").is_dir():
                return cand
    raise SystemExit("[X] 未找到 SNB 核心模块")


SNB = _find_snb_core()
sys.path.insert(0, str(SNB / "scripts" / "analysis"))
import compare_4way as C4                              # noqa: E402

# ★★ 数据提取统一走项目自带的 `flash.output_processors`（用户要求 2026-09-12）：
#    · FlashDataLoader + extraction_mode="h5py" → **只取叶子块**
#      （AMR 场景必需；默认 load() 会把父块陈旧数据混入并搞错坐标）
#    · DataCalculator → 派生量按 `DATA_CONFIG` 的**权威公式**计算，不自实现
#      （`nele = ye*dens*NA`、`nion = sumy*dens*NA`；NA 取项目常数）
from flash.output_processors.loader import FlashDataLoader            # noqa: E402
from flash.output_processors.hdf5processor import DataCalculator      # noqa: E402
try:
    from flash.output_processors.hdf5processor import NA as NA_PROJ
except ImportError:                                     # pragma: no cover
    NA_PROJ = 6.02214076e23
_loader = FlashDataLoader
_dc = DataCalculator

# 单位换算（物理常数；`tele` 在 FLASH/项目中均以 K 存储）
K_PER_EV = C4.K_PER_EV              # 1 eV = 11604.519 K
ERG_CM3_TO_MBAR = C4.ERG_CM3_TO_MBAR   # 1 dyne/cm^2 = 1 erg/cm^3 = 1e-12 Mbar
NA = NA_PROJ

# 需要保留的原始变量（其余派生量交给 DataCalculator）
RAW_WANT = ("dens", "tele", "tion", "trad", "pele", "pres", "ye", "sumy", "depo")

plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
    "xtick.labelsize": 18, "ytick.labelsize": 18, "legend.fontsize": 17,
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.6, "font.family": "DejaVu Sans",
})

# 模型样式
STYLE = {
    "SNBOneCH (nonlocal)": {"c": "#C1440E", "ls": "-"},
    "OneCH_ml (local)": {"c": "#1B5E9C", "ls": "--"},
}
TITLE = {
    "nele": ("Electron number density", r"cm$^{-3}$", True),
    "tele": ("Electron temperature", "eV", False),
    "pele": ("Electron pressure", "Mbar", False),
}


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


# ══════════════════════════════════════════════════════════════
# 读取 —— 统一经 `flash.output_processors`（两腿同一条链）
# ══════════════════════════════════════════════════════════════
def list_frames(d: Path) -> List[Path]:
    """列出目录内的输出帧（**chk 优先**，其次 plt；排除 forced）。"""
    fs = [p for p in d.glob("*hdf5_chk_*") if "forced" not in p.name]
    if not fs:
        fs = [p for p in d.glob("*plt_cnt*") if "forced" not in p.name]
    if not fs:
        fs = [p for p in d.glob("*plt*") if "forced" not in p.name]

    def key(p: Path) -> int:
        try:
            return int(p.name.rsplit("_", 1)[-1])
        except ValueError:
            return 10 ** 9
    return sorted(fs, key=key)


def load_frames(d: Path) -> List[Dict[str, Any]]:
    """用 `FlashDataLoader` 读帧，并用 `DataCalculator` 算派生量。

    统一口径（两腿完全一致）：

    * 提取模式 **`h5py`** → 走 `extract_var`，**只取 `node_type==1` 的叶子块**。
      AMR 场景**必须**这样 —— 默认的 `load()` 不过滤父块，会把陈旧粗网格值
      混进来并把坐标搞错。
    * 派生量走项目 `DATA_CONFIG` 的**权威公式**：`nele = ye*dens*NA`、
      `nion = sumy*dens*NA` —— **不自行实现**，以保证与项目其它脚本一致。
      ★ 注意 `ye` 是**电离态相关**的电子丰度（mol e⁻/g），室温冷物质下很小，
      故 `nele` 在冷区远低于"完全电离"估计值；这是**物理**，不是提取错误。
    """
    out: List[Dict[str, Any]] = []
    for p in list_frames(d):
        try:
            c = _loader(str(p)).load(compute_derived=False,
                                     extraction_mode="h5py")
        except Exception as exc:                       # noqa: BLE001
            log(f"跳过 {p.name}: {exc}", "WARN")
            continue
        x = np.asarray(c.x).ravel()
        if x.size == 0:
            continue
        o = np.argsort(x)
        rec: Dict[str, Any] = {"t": float(c.simulation_time),
                               "x_um": x[o] * 1e4}
        raw: Dict[str, np.ndarray] = {}
        for k in RAW_WANT:
            v = c.data.get(k)
            if v is not None:
                raw[k] = np.asarray(v).ravel()[o]
        rec.update(raw)
        if raw:
            try:
                calc = _dc(raw)
                for name in ("nele", "nion"):
                    rec[name] = np.asarray(calc.compute(name), float)
            except Exception as exc:                   # noqa: BLE001
                log(f"{p.name}: 派生量计算失败 ({exc})", "WARN")
        out.append(rec)
    out.sort(key=lambda r: r["t"])
    return out


def derive(fr: Dict[str, Any], var: str) -> Optional[np.ndarray]:
    """取物理量。

    `nele` / `nion` **已在 `load_frames()` 中由项目的 `DataCalculator`
    按 `DATA_CONFIG` 公式算好**，此处只做取值；本函数不再自行实现任何公式。
    其余量仅做单位换算（K → eV、dyne/cm² → Mbar）。
    """
    v = fr.get(var)
    if v is None:
        return None
    v = np.asarray(v, float)
    if var in ("nele", "nion"):
        return v
    if var in ("tele", "tion", "trad"):
        return v / K_PER_EV                       # K → eV
    if var in ("pele", "pres"):
        return v * ERG_CM3_TO_MBAR                # dyne/cm^2 → Mbar
    return v


# ══════════════════════════════════════════════════════════════
def fig_profiles(data: Dict[str, List[Dict[str, Any]]], var: str,
                 out_dir: Path, fname: str, n_times: int,
                 zoom: Optional[Tuple[float, float]] = None) -> Optional[Path]:
    title, unit, use_log = TITLE[var]
    legs = [k for k in data if data[k]]
    if not legs:
        log(f"{var}: 无数据", "WARN"); return None
    t_hi = min(max(f["t"] for f in data[k]) for k in legs)
    t_lo = max(min(f["t"] for f in data[k]) for k in legs)
    ts = np.linspace(t_lo, t_hi, n_times) if t_hi > t_lo else np.array([t_hi])

    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(13.5, 8.6))
    ymin, ymax = np.inf, -np.inf
    for k in legs:
        st = STYLE[k]
        used = set()
        for t in ts:
            i = int(np.argmin([abs(f["t"] - t) for f in data[k]]))
            if i in used:
                continue
            used.add(i)
            fr = data[k][i]
            v = derive(fr, var)
            if v is None:
                continue
            x = np.asarray(fr["x_um"], float)
            m = np.isfinite(v)
            if zoom is not None:
                m &= (x >= zoom[0]) & (x <= zoom[1])
            if not np.any(m):
                continue
            fin = v[m]
            ymin, ymax = min(ymin, float(fin.min())), max(ymax, float(fin.max()))
            frac = 0.06 + 0.88 * (t - t_lo) / ((t_hi - t_lo) or 1.0)
            ax.plot(x[m], v[m], color=cmap(frac), ls=st["ls"], lw=2.8)
    if not np.isfinite(ymin):
        log(f"{var}: 无有效数据", "WARN"); plt.close(fig); return None
    if use_log and ymin > 0:
        ax.set_yscale("log")
    ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=22)
    ax.set_ylabel(f"{title}  [{unit}]", fontsize=22)
    ax.set_title(f"{title} — SNB (solid) vs OneCH_ml (dashed)",
                 fontsize=21, pad=10)
    ax.grid(alpha=0.25, lw=1.0, which="both")
    ax.tick_params(labelsize=18, width=2.0)
    for s in ax.spines.values():
        s.set_linewidth(2.0)
    if zoom is not None:
        ax.set_xlim(*zoom)
    # 双图例: 颜色=时刻, 线型=模型
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=STYLE[k]["c"], ls=STYLE[k]["ls"], lw=3.2, label=k)
         for k in legs]
    ax.legend(handles=h, fontsize=17, loc="upper right", framealpha=0.92)
    return C4.save_fig(fig, out_dir / fname)


def fig_xt(data: Dict[str, List[Dict[str, Any]]], out_dir: Path) -> Optional[Path]:
    """x-t 对比: 上行 SNB / 下行 OneCH_ml，**每列共享色标**（否则无法横向比较）。"""
    legs = [k for k in data if data[k]]
    if len(legs) < 2:
        log("x-t: 需两腿数据, 跳过", "WARN"); return None
    # 明确上行 = SNB
    order = sorted(legs, key=lambda k: 0 if "SNB" in k else 1)
    varlist = ("nele", "tele", "pele")

    # ① 先建好所有网格
    grids: Dict[Tuple[str, str], Any] = {}
    for k in order:
        for var in varlist:
            xs, ts, rows = [], [], []
            for fr in data[k]:
                v = derive(fr, var)
                if v is None:
                    continue
                xs.append(np.asarray(fr["x_um"], float)); rows.append(v)
                ts.append(fr["t"])
            if not rows:
                continue
            x0 = max(a.min() for a in xs); x1 = min(a.max() for a in xs)
            xg = np.linspace(x0, x1, 900)
            Z = np.vstack([np.interp(xg, x, v, left=np.nan, right=np.nan)
                           for x, v in zip(xs, rows)])
            grids[(k, var)] = (np.asarray(ts), xg, Z)

    # ② **每列共享色标**（跨两腿取极值）
    norms: Dict[str, Any] = {}
    for var in varlist:
        zs = [grids[(k, var)][2] for k in order if (k, var) in grids]
        if not zs:
            continue
        allv = np.concatenate([z.ravel() for z in zs])
        allv = allv[np.isfinite(allv)]
        if allv.size == 0:
            continue
        if TITLE[var][2]:                      # 对数
            pos = allv[allv > 0]
            fl = float(pos.min()) * 0.5 if pos.size else 1e-30
            norms[var] = (LogNorm(vmin=fl * 1.0000001, vmax=float(allv.max())), fl)
        else:
            norms[var] = (Normalize(vmin=float(allv.min()), vmax=float(allv.max())), None)

    fig, axes = plt.subplots(2, 3, figsize=(21.0, 11.4))
    fig.subplots_adjust(left=0.070, right=0.945, top=0.880, bottom=0.070,
                        hspace=0.30, wspace=0.32)
    for r, k in enumerate(order):
        for c, var in enumerate(varlist):
            ax = axes[r][c]
            title, unit, _ = TITLE[var]
            if (k, var) not in grids:
                ax.text(.5, .5, "no data", ha="center", va="center",
                        transform=ax.transAxes, fontsize=20, color="0.45")
                continue
            ts, xg, Z = grids[(k, var)]
            norm, fl = norms[var]
            if fl is not None:
                Z = np.where(np.isfinite(Z) & (Z > 0), Z, fl)
            # ★★ 必须用 pcolormesh + **真实逐帧时间坐标**，**不能用 imshow**：
            #    imshow 假设各帧在 extent 内**等间距**；而 FLASH 的 chk 是按
            #    *步数* 间隔输出的 —— OneCH_ml 实测 Δt = 1.36e-12 … 7.19e-11
            #    （**52.7×** 不均匀），用 imshow 会把时间轴局部拉偏 >3000%，
            #    从而让**同一物理运动在两腿上显得"前沿速度不同"**。
            #    （SNBOneCH 的 Δt 恒定 2e-11，两腿不均匀性差异是造成假象的原因。）
            X, T = np.meshgrid(xg, ts * 1e9)
            im = ax.pcolormesh(X, T, Z, shading="auto",
                               cmap="inferno" if var == "tele" else "viridis",
                               norm=norm, rasterized=True)
            ax.set_title(title, fontsize=19, pad=6)
            ax.set_xlim(-60, 60)
            ax.tick_params(labelsize=16, width=1.8)
            for s in ax.spines.values():
                s.set_linewidth(1.8)
            if c == 0:
                ax.set_ylabel("Time  [ns]", fontsize=19)
            if r == 1:
                ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=19)
            cb = fig.colorbar(im, ax=ax, pad=0.03, fraction=0.046)
            cb.set_label(f"{unit}", fontsize=16)
            cb.ax.tick_params(labelsize=14, width=1.6)
            cb.outline.set_linewidth(1.6)
        # 行标签 (避免长标题互相挤压)
        yc = axes[r][0].get_position().y0 + \
            axes[r][0].get_position().height / 2.0
        fig.text(0.014, yc, k, rotation=90, va="center", ha="center",
                 fontsize=19, color="0.15")
    # 时间窗从数据动态取 (秒 → ns), 避免写死后与实际不符
    t_end = max(float(grids[(k, v)][0].max()) for k in order
                for v in varlist if (k, v) in grids) * 1e9
    fig.suptitle(f"x-t comparison — shared color scale per column  "
                 f"(radiation ON, 0 → {t_end:.2f} ns)",
                 fontsize=24, y=0.945)
    return C4.save_fig(fig, out_dir / "fig4_xt_compare.png")


def write_metrics(data: Dict[str, List[Dict[str, Any]]], out_dir: Path) -> None:
    rows = []
    for k, frs in data.items():
        if not frs:
            continue
        fr = frs[-1]
        rec = {"model": k, "t_ns": fr["t"] * 1e9}
        for var in ("nele", "tele", "pele"):
            v = derive(fr, var)
            rec[f"{var}_max"] = float(np.nanmax(v)) if v is not None else float("nan")
        rows.append(rec)
    if not rows:
        return
    p = out_dir / "metrics_compare.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"定量表 → {p.name}", "OK")


# ══════════════════════════════════════════════════════════════
def _resolve_onech_dir(root: Path) -> Path:
    """定位 OneCH_ml 的 plt 目录。

    `OneCH_ml` 经 runner 收集后输出落在
    `flash_output/outputfiles/run_<NNNNNN>/`（带 run_id 子目录），
    故这里自动挑**最新且含 plt 的 run_* 子目录**；找不到则退回 root 本身。
    """
    if not root.is_dir():
        return root
    def _has_plt(p: Path) -> bool:
        return bool(list(p.glob("*plt_cnt*")) or list(p.glob("*plt*")))
    if _has_plt(root):
        return root
    runs = sorted((p for p in root.iterdir()
                   if p.is_dir() and p.name.startswith("run_")), reverse=True)
    for r in runs:
        if _has_plt(r):
            return r
    return root


def main() -> int:
    ap = argparse.ArgumentParser(description="SNBOneCH vs OneCH_ml (nele/tele/pele)")
    ap.add_argument("--snb-scene", required=True, help="SNBOneCH/scene")
    ap.add_argument("--snb-tag", default="full")
    ap.add_argument("--onech-dir", default=None,
                    help="OneCH_ml 输出目录 (默认 tracer/OneCH_ml/flash_output/outputfiles)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--n-times", type=int, default=6)
    args = ap.parse_args()

    scene = Path(args.snb_scene).resolve()
    out = Path(args.out).resolve() if args.out else _HERE / "images"
    # 默认 OneCH_ml 输出: <scene>/../../OneCH_ml/flash_output/outputfiles
    #   scene = tracer/SNB/SNBOneCH/scene → parents[2] = tracer
    onech = Path(args.onech_dir).resolve() if args.onech_dir else \
        scene.parents[2] / "OneCH_ml" / "flash_output" / "outputfiles"
    onech = _resolve_onech_dir(onech)
    out.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 78)
    print(" SNBOneCH vs OneCH_ml —— nele / tele / pele 对比")
    print(f" SNB  : {scene}/flash_output/sim_snb/{args.snb_tag}")
    print(f" OneCH: {onech}")
    print(f" 输出 : {out}")
    print("=" * 78)

    data: Dict[str, List[Dict[str, Any]]] = {}
    d_snb = scene / "flash_output" / "sim_snb" / args.snb_tag
    data["SNBOneCH (nonlocal)"] = load_frames(d_snb) if d_snb.is_dir() else []
    log(f"SNBOneCH (nonlocal): {len(data['SNBOneCH (nonlocal)'])} 帧"
        f"  (经 flash.output_processors)")
    data["OneCH_ml (local)"] = load_frames(onech) if onech.is_dir() else []
    log(f"OneCH_ml (local)   : {len(data['OneCH_ml (local)'])} 帧"
        f"  (经 flash.output_processors)")

    if not any(data.values()):
        log("无任何数据 —— 检查路径", "ERROR")
        return 1

    fig_profiles(data, "nele", out, "fig1_profiles_nele.png", args.n_times)
    fig_profiles(data, "tele", out, "fig2_profiles_tele.png", args.n_times)
    fig_profiles(data, "pele", out, "fig3_profiles_pele.png", args.n_times)
    fig_profiles(data, "tele", out, "fig5_front_zoom.png", args.n_times,
                 zoom=(-10.0, 20.0))
    fig_xt(data, out)
    write_metrics(data, out)

    print("\n" + "=" * 78)
    print(f" 完成 — {out}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
