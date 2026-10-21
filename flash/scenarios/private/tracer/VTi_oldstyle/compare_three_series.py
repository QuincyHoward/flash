"""三个系列的同设置对比：base(-250/+75) vs L1500(-1500/+75) vs L500(-500/+150)。

三个系列都是同一实验设置（V 屏蔽 + CH + 2 µm 处 0.1 µm Ti 示踪 + He，激光 8.00e-02 档），
差别只在**计算域/分辨率/终止时刻**：

| 系列 | 目录 | xmin | xmax | W | lrefine_max | dx_min | plt 间隔 | tmax |
|---|---|---|---|---|---|---|---|---|
| base  | ReDo042sp_CH042sp{d}um8.00e-02   | -250  | +75  | 325  | 8  | 0.019836 | 500  | 1.6 ns |
| L1500 | ReDo042sp_CH042sp{d}umL8.00e-02  | -1500 | +75  | 1575 | 10 | 0.024034 | 2000 | 1.6 ns |
| L500  | 本地 VTi{d}L500（本轮新算）      | -500  | +150 | 650  | 8  | 0.019836 | 500  | 2.5 ns |

★ 读数据时必须遵守的三条（本项目已踩过的坑）
1. 物种场是**质量分数**（四者之和 = 1）。质心必须 ρX 加权；`∫X dx` 不守恒，不能当质量。
2. 三个系列的 **plt 帧间隔不同**（500 / 2000 / 500 步），且 dt 随演化变化
   ⇒ 速度只能用相邻帧自适应中心差分 `v_i=(x_{i+1}-x_{i-1})/(t_{i+1}-t_{i-1})`，
   固定时间窗一定会在帧间空洞里出 NaN。
3. plt 里**同时含父块与叶块**（node type 1/2/3 混杂）⇒ 拼剖面必须
   "粗块先画、细块覆盖"（按 dx 从大到小绘制），否则粗细层交错会串层。

用法:
    python compare_three_series.py              # 全量（约 5–10 分钟）
    python compare_three_series.py --depth 2    # 只做 2 µm
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OLD_ROOT = Path("E:/ProgramsPATH/VMware/SharedFiles/Ubuntu24/FLASHWorkspace/"
                "FLASHProjectData/data/input")
OUT = HERE / "plots"
DEPTHS = (1, 2, 3)

SERIES = {
    "base":  dict(label="base  (-250/+75 µm)",  color="#1f4e79", ls="-",
                  glob="ReDo042sp_CH042sp{d}um8.00e-02"),
    "L1500": dict(label="L1500 (-1500/+75 µm)", color="#548235", ls="-",
                  glob="ReDo042sp_CH042sp{d}umL8.00e-02"),
    "L500":  dict(label="L500  (-500/+150 µm)", color="#c00000", ls="--",
                  glob=None),
}
SPECIES = ("cham", "samp", "shld", "targ")


# ── 定位与读取 ────────────────────────────────────────────

def old_src(tag: str) -> Path | None:
    ds = sorted(glob.glob(str(OLD_ROOT / tag / f"{tag}2026" / "hdf5files_*")))
    if not ds:
        return None
    subs = [d for d in os.listdir(ds[-1]) if d.startswith("src_")]
    return Path(ds[-1]) / subs[0] if subs else None


def run_dir(key: str, depth: int) -> Path | None:
    if key == "L500":
        d = HERE / "flash_output" / f"VTi{depth}L500"
        return d if d.exists() else None
    return old_src(SERIES[key]["glob"].format(d=depth))


def sim_time(h) -> float:
    for rec in h["real scalars"][:]:
        n = rec["name"]
        n = n.decode().strip() if isinstance(n, bytes) else str(n).strip()
        if n == "time":
            return float(rec["value"])
    return float("nan")


def cells(h, var: str):
    """返回 (x_center[um], dx[um], value) 逐胞；plt 含父块，调用方须按 dx 排序绘制。"""
    a = np.asarray(h[var][:], dtype=np.float64)
    bb = np.asarray(h["bounding box"][:], dtype=np.float64)
    if a.ndim == 4:
        a = a[:, 0, 0, :]
    nb, nx = a.shape
    dx = (bb[:, 0, 1] - bb[:, 0, 0]) / nx
    x0 = bb[:, 0, 0] + dx / 2
    x1 = bb[:, 0, 1] - dx / 2
    tt = np.linspace(0, 1, nx)
    x = ((x0[:, None] * (1 - tt) + x1[:, None] * tt) * 1e4).ravel()
    return x, np.repeat(dx * 1e4, nx), a.ravel()


def profile(h, var: str, nbin: int = 4000):
    """把（含父块的）AMR 数据画到统一网格：粗块先画、细块覆盖 ⇒ 取到最细信息。

    返回 (bin_center[um], value)。仅在需要看剖面时调用（比逐帧标量贵）。
    """
    a = np.asarray(h[var][:], dtype=np.float64)
    bb = np.asarray(h["bounding box"][:], dtype=np.float64)
    if a.ndim == 4:
        a = a[:, 0, 0, :]
    nb, nx = a.shape
    xmin, xmax = float(bb[:, 0, 0].min()), float(bb[:, 0, 1].max())
    edges = np.linspace(xmin, xmax, nbin + 1)
    val = np.full(nbin, np.nan)
    dxb = (bb[:, 0, 1] - bb[:, 0, 0]) / nx
    for b in np.argsort(-dxb):                      # 粗 → 细
        e = np.linspace(bb[b, 0, 0], bb[b, 0, 1], nx + 1)
        i0 = np.clip(np.searchsorted(edges, e[:-1], "right") - 1, 0, nbin - 1)
        i1 = np.clip(np.searchsorted(edges, e[1:], "left"), 0, nbin)
        for j in range(nx):
            if i1[j] > i0[j]:
                val[i0[j]:i1[j]] = a[b, j]
    ctr = 0.5 * (edges[:-1] + edges[1:]) * 1e4
    return ctr, val


def probe(path: Path) -> dict:
    """一帧的标量诊断量。"""
    with h5py.File(path, "r") as h:
        out = {"t": sim_time(h)}
        x, dx, dens = cells(h, "dens")
        out["dens_max"] = float(dens.max())
        out["x_dens_max"] = float(x[int(np.argmax(dens))])
        if "tele" in h:
            out["tele_max"] = float(cells(h, "tele")[2].max()) / 11604.518
        if "pres" in h:
            out["pres_max"] = float(cells(h, "pres")[2].max())
        for sp in SPECIES:
            if sp not in h:
                continue
            _, _, fr = cells(h, sp)
            out[f"{sp}_frac_max"] = float(fr.max())
            m = fr > 0.5
            if m.any():
                out[f"{sp}_x0"] = float(x[m].min())
                out[f"{sp}_x1"] = float(x[m].max())
        # Ti 质心（ρX 加权：物种场是质量分数）
        if "targ" in h:
            _, _, fr = cells(h, "targ")
            w = fr * dens
            if w.sum() > 0:
                out["targ_xc"] = float((x * w).sum() / w.sum())
    return out


def load_series(key: str, depth: int) -> tuple[np.ndarray, list[dict]]:
    d = run_dir(key, depth)
    if d is None:
        print(f"  [!] {key} {depth}um: 找不到输出目录")
        return np.array([]), []
    fs = sorted(glob.glob(str(d / "lasslab_hdf5_plt_cnt_*")),
                key=lambda p: int(re.search(r"plt_cnt_(\d+)", p).group(1)))
    rows = [probe(Path(f)) for f in fs]
    rows = [r for r in rows if np.isfinite(r.get("t", np.nan))]
    print(f"  [i] {key:<5} {depth}um: {len(rows)} 帧, "
          f"t=[{rows[0]['t']*1e9:.3f}, {rows[-1]['t']*1e9:.3f}] ns" if rows else "")
    return np.array([r["t"] for r in rows]), rows


def velocity(t: np.ndarray, xc: np.ndarray) -> np.ndarray:
    """相邻帧自适应中心差分 [µm/s]（帧间隔 500/2000 步且 dt 随演化变化）。"""
    v = np.full_like(xc, np.nan)
    if len(t) < 2:
        return v
    v[1:-1] = (xc[2:] - xc[:-2]) / (t[2:] - t[:-2])
    v[0] = (xc[1] - xc[0]) / (t[1] - t[0])
    v[-1] = (xc[-1] - xc[-2]) / (t[-1] - t[-2])
    return v


def col(rows, k, n=None):
    a = np.array([r.get(k, np.nan) for r in rows], dtype=float)
    return a if n is None else np.pad(a, (0, max(0, n - len(a))), constant_values=np.nan)


# ── 出图 ─────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=None)
    args = ap.parse_args()
    depths = (args.depth,) if args.depth else DEPTHS
    OUT.mkdir(parents=True, exist_ok=True)

    data: dict[tuple[str, int], tuple[np.ndarray, list[dict]]] = {}
    for d in depths:
        print(f"=== 读 {d} µm ===")
        for k in SERIES:
            data[(k, d)] = load_series(k, d)

    # ── CSV ──
    csv_p = OUT / "three_series_scalars.csv"
    keys_all = sorted({k for _, rows in data.values() for r in rows for k in r})
    with open(csv_p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["series", "depth_um", "frame"] + keys_all)
        for (k, d), (_, rows) in data.items():
            for i, r in enumerate(rows):
                w.writerow([k, d, i] + [r.get(x, "") for x in keys_all])
    print(f"[OK] {csv_p}")

    def plot(key, ylab, title, fname, depths_=None, transform=None):
        ds = depths_ or depths
        fig, axes = plt.subplots(1, len(ds), figsize=(5.6 * len(ds), 4.8),
                                 layout="constrained", squeeze=False)
        for ax, d in zip(axes[0], ds):
            for k, meta in SERIES.items():
                t, rows = data.get((k, d), (np.array([]), []))
                if len(t) == 0:
                    continue
                y = col(rows, key)
                if transform:
                    y = transform(y)
                ax.plot(t * 1e9, y, meta["ls"], color=meta["color"], lw=2.2,
                        label=meta["label"])
            ax.set_xlabel("time [ns]")
            ax.set_ylabel(ylab)
            ax.set_title(f"{title} — {d} $\\mu$m")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
        fig.savefig(OUT / fname, dpi=150)
        plt.close(fig)
        print(f"[OK] {OUT / fname}")

    plot("targ_xc", "Ti centroid x [$\\mu$m]", "Ti tracer centroid",
         "cmp_ti_centroid.png")
    plot("targ_x1", "Ti right edge [$\\mu$m]", "Ti layer right edge",
         "cmp_ti_right_edge.png")
    plot("x_dens_max", "x of $\\rho_{max}$ [$\\mu$m]", "Density-peak (shock) position",
         "cmp_shock_position.png")
    plot("samp_x1", "CH front [$\\mu$m]", "CH front",
         "cmp_ch_front.png")
    plot("dens_max", "$\\rho_{max}$ [g/cm$^3$]", "Peak density",
         "cmp_dens_max.png")
    plot("tele_max", "$T_{e,max}$ [eV]", "Peak electron temperature",
         "cmp_tele_max.png")
    plot("targ_frac_max", "max Ti mass fraction", "Ti mixing (peak mass fraction)",
         "cmp_ti_frac_max.png")

    # Ti 层宽度
    def width(rows):
        return col(rows, "targ_x1") - col(rows, "targ_x0")

    ds = depths
    fig, axes = plt.subplots(1, len(ds), figsize=(5.6 * len(ds), 4.8),
                             layout="constrained", squeeze=False)
    for ax, d in zip(axes[0], ds):
        for k, meta in SERIES.items():
            t, rows = data.get((k, d), (np.array([]), []))
            if len(t) == 0:
                continue
            ax.semilogy(t * 1e9, width(rows), meta["ls"], color=meta["color"],
                        lw=2.2, label=meta["label"])
        ax.set_xlabel("time [ns]")
        ax.set_ylabel("Ti layer width (x1 − x0) [$\\mu$m]")
        ax.set_title(f"Ti layer thickness — {d} $\\mu$m")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8)
    fig.savefig(OUT / "cmp_ti_width.png", dpi=150)
    plt.close(fig)
    print(f"[OK] {OUT / 'cmp_ti_width.png'}")

    # Ti 层速度
    fig, axes = plt.subplots(1, len(ds), figsize=(5.6 * len(ds), 4.8),
                             layout="constrained", squeeze=False)
    for ax, d in zip(axes[0], ds):
        for k, meta in SERIES.items():
            t, rows = data.get((k, d), (np.array([]), []))
            if len(t) < 3:
                continue
            xc = col(rows, "targ_xc")
            v = velocity(t, xc) * 1e-11          # µm/s -> 1e5 m/s
            ax.plot(t * 1e9, v, meta["ls"], color=meta["color"], lw=2.2,
                    label=meta["label"])
        ax.set_xlabel("time [ns]")
        ax.set_ylabel("$v_{Ti}$ [$10^5$ m/s]")
        ax.set_title(f"Ti layer velocity — {d} $\\mu$m")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(OUT / "cmp_ti_velocity.png", dpi=150)
    plt.close(fig)
    print(f"[OK] {OUT / 'cmp_ti_velocity.png'}")

    # 剖面（2 µm，三个代表时刻）
    if 2 in depths:
        want = (0.5e-9, 1.0e-9, 1.35e-9)
        # 先把每个系列的 (帧路径, 时刻) 缓存一次，避免每个时刻都重扫全目录
        cache: dict[str, tuple[list[str], np.ndarray]] = {}
        for k in SERIES:
            d = run_dir(k, 2)
            if d is None:
                continue
            fs = sorted(glob.glob(str(d / "lasslab_hdf5_plt_cnt_*")),
                        key=lambda p: int(re.search(r"plt_cnt_(\d+)", p).group(1)))
            ts = []
            for f in fs:
                with h5py.File(f, "r") as h:
                    ts.append(sim_time(h))
            cache[k] = (fs, np.array(ts))

        fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout="constrained")
        for j, tq in enumerate(want):
            for i, var in enumerate(("dens", "tele")):
                ax = axes[i, j]
                for k, meta in SERIES.items():
                    if k not in cache:
                        continue
                    fs, ts = cache[k]
                    idx = int(np.argmin(np.abs(ts - tq)))
                    with h5py.File(fs[idx], "r") as h:
                        xc, y = profile(h, var)
                    if var == "tele":
                        y = y / 11604.518
                    ax.plot(xc, y, meta["ls"], color=meta["color"], lw=1.8,
                            label=f"{meta['label']}  t={ts[idx]*1e9:.2f} ns")
                ax.set_xlim(-40, 60)
                if var == "dens":
                    ax.semilogy()
                    ax.set_ylim(1e-7, 1e2)
                    ax.set_ylabel("$\\rho$ [g/cm$^3$]")
                else:
                    ax.set_ylabel("$T_e$ [eV]")
                    ax.set_ylim(0, None)
                ax.set_xlabel("x [$\\mu$m]")
                ax.set_title(f"{'density' if var=='dens' else 'Te'} @ {tq*1e9:.2f} ns")
                ax.grid(alpha=0.3, which="both")
                ax.legend(fontsize=7)
        fig.savefig(OUT / "cmp_profiles_2um.png", dpi=150)
        plt.close(fig)
        print(f"[OK] {OUT / 'cmp_profiles_2um.png'}")

    # 汇总表：t = 1.30 ns（三系列都还在跑的公共时刻）
    tq = 1.30e-9
    rows_out = []
    print(f"\n=== t = {tq*1e9:.2f} ns 汇总（按物理时刻插值）===")
    print(f"{'series':<7}{'depth':>6}{'Ti_xc':>9}{'Ti_x0':>9}{'Ti_x1':>9}"
          f"{'v_Ti':>9}{'shock_x':>9}{'dens_max':>9}{'Te_max':>9}")
    for d in depths:
        for k in SERIES:
            t, rows_ = data.get((k, d), (np.array([]), []))
            if len(t) < 3:
                continue
            def it(name):
                a = col(rows_, name)
                ok = np.isfinite(a)
                return float(np.interp(tq, t[ok], a[ok])) if ok.any() else float("nan")
            xc = col(rows_, "targ_xc")
            v = velocity(t, xc) * 1e-11
            okv = np.isfinite(v)
            vq = float(np.interp(tq, t[okv], v[okv])) if okv.any() else float("nan")
            rec = [k, d, it("targ_xc"), it("targ_x0"), it("targ_x1"), vq,
                   it("x_dens_max"), it("dens_max"), it("tele_max")]
            print(f"{rec[0]:<7}{rec[1]:>6}{rec[2]:>9.1f}{rec[3]:>9.1f}{rec[4]:>9.1f}"
                  f"{rec[5]:>9.2f}{rec[6]:>9.1f}{rec[7]:>9.3f}{rec[8]:>9.1f}")
            rows_out.append(rec)
    sum_p = OUT / "three_series_at_1p3ns.csv"
    with open(sum_p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["series", "depth_um", "Ti_xc_um", "Ti_x0_um", "Ti_x1_um",
                    "v_Ti_1e5ms", "shock_x_um", "dens_max", "Te_max_eV"])
        w.writerows(rows_out)
    print(f"[OK] {sum_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
