"""VTi_old vs VTi_oldstyle **时间序列**对照（逐 plt 帧）。

只比"对块排列不敏感"的量：
  * 仿真时刻 t
  * 各物种质量分数 > 0.5 的胞的 x 区间（层边界）
  * 屏蔽层/V 层密度、Ti 层质心
这些量直接反映分层演化，避免 AMR 粗细层交错导致的剖面插值串层。

用法:
  python compare_old_new_series.py --depth 2
产物:
  plots/series_vti{depth}_old_vs_oldstyle.png
  plots/series_vti{depth}_old_vs_oldstyle.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import os
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OLD_ROOT = Path(os.environ["FLASH_OLD_VM_WS"])  # 旧 VM 工作区（显式注入，如 <旧VM工作区>/FLASHWorkspace）
                "FLASHProjectData/data/input")
OLD_TS = {"1": "20260331_205557", "2": "20260331_215819", "3": "20260331_231147"}
SPECIES = ("cham", "samp", "shld", "targ")


def old_dir(depth: str) -> Path:
    tag = f"ReDo042sp_CH042sp{depth}um8.00e-02"
    return OLD_ROOT / tag / f"{tag}2026" / f"hdf5files_{OLD_TS[depth]}" / \
        f"src_{OLD_TS[depth]}"


def frame_idx(p: Path) -> int:
    m = re.search(r"plt_cnt_(\d+)$", p.name)
    return int(m.group(1)) if m else -1


def sim_time(path: Path) -> float:
    with h5py.File(path, "r") as h:
        rs = h["real scalars"][:]
    for rec in rs:
        n = rec["name"]
        n = n.decode().strip() if isinstance(n, bytes) else str(n).strip()
        if n == "time":
            return float(rec["value"])
    return float("nan")


def probe(path: Path) -> dict:
    """一帧的关键标量。"""
    out: dict[str, float] = {"t": sim_time(path)}
    with h5py.File(path, "r") as h:
        bb = np.asarray(h["bounding box"][:], dtype=np.float64)
        a = np.asarray(h["dens"][:], dtype=np.float64)
        if a.ndim == 4:
            a = a[:, 0, 0, :]
        nb, nx = a.shape
        dx = (bb[:, 0, 1] - bb[:, 0, 0]) / nx
        x0 = bb[:, 0, 0] + dx / 2
        x1 = bb[:, 0, 1] - dx / 2
        tt = np.linspace(0, 1, nx)
        x = ((x0[:, None] * (1 - tt) + x1[:, None] * tt) * 1e4).ravel()
        dens = a.ravel()
        for sp in SPECIES:
            if sp not in h:
                continue
            v = np.asarray(h[sp][:], dtype=np.float64)
            if v.ndim == 4:
                v = v[:, 0, 0, :]
            v = v.ravel()
            m = v > 0.5
            if not m.any():
                continue
            out[f"{sp}_x0"] = float(x[m].min())
            out[f"{sp}_x1"] = float(x[m].max())
            out[f"{sp}_rho"] = float(np.median(dens[m]))
            out[f"{sp}_n"] = float(m.sum())
        # Ti 层质心（ρ·X 加权，比值量，块排列无关）
        if "targ" in h:
            v = np.asarray(h["targ"][:], dtype=np.float64)
            if v.ndim == 4:
                v = v[:, 0, 0, :]
            w = v.ravel() * dens
            if w.sum() > 0:
                out["targ_xc"] = float((x * w).sum() / w.sum())
        # 屏蔽层压强（判"过压"是否复现）
        if "pres" in h and "shld" in h:
            v = np.asarray(h["shld"][:], dtype=np.float64)
            if v.ndim == 4:
                v = v[:, 0, 0, :]
            ms = v.ravel() > 0.5
            pr = np.asarray(h["pres"][:], dtype=np.float64)
            if pr.ndim == 4:
                pr = pr[:, 0, 0, :]
            if ms.any():
                out["pres_shld"] = float(np.median(pr.ravel()[ms]))
    return out


def series(root: Path) -> tuple[np.ndarray, list[dict]]:
    frames = sorted(root.glob("lasslab_hdf5_plt_cnt_*"), key=frame_idx)
    rows = []
    for f in frames:
        try:
            rows.append(probe(f))
        except Exception as exc:                       # noqa: BLE001
            print(f"  [!] {f.name}: {type(exc).__name__} {exc}")
    rows = [r for r in rows if np.isfinite(r.get("t", np.nan))]
    return np.array([r["t"] for r in rows]), rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", default="2")
    ap.add_argument("--new", default=None)
    args = ap.parse_args()

    old = old_dir(args.depth)
    new = Path(args.new) if args.new else (HERE / "flash_output" / f"VTi{args.depth}old")
    print(f"[i] old: {old}  ({len(list(old.glob('*plt_cnt*')))} plt)")
    print(f"[i] new: {new}  ({len(list(new.glob('*plt_cnt*')))} plt)")
    if not new.exists():
        print("[X] 新算例输出目录不存在")
        return 2

    t_o, r_o = series(old)
    t_n, r_n = series(new)
    print(f"[i] 读入 old={len(r_o)} 帧, new={len(r_n)} 帧")
    if not r_o or not r_n:
        return 1

    # 帧数与时刻一致性
    print(f"\n=== 帧序列 ===")
    print(f"  old: {len(r_o)} 帧, t=[{t_o[0]:.4e}, {t_o[-1]:.4e}] s")
    print(f"  new: {len(r_n)} 帧, t=[{t_n[0]:.4e}, {t_n[-1]:.4e}] s")
    print(f"  帧数差 = {len(r_n) - len(r_o)}, 末时刻差 = {(t_n[-1]-t_o[-1]):.3e} s")

    # 帧时刻偏移（判断 dt 序列是否同一）
    ncmp = min(len(r_o), len(r_n))
    dt_off = t_n[:ncmp] - t_o[:ncmp]
    print(f"  同索引帧时刻差: max|Δ| = {np.abs(dt_off).max():.3e} s "
          f"({np.abs(dt_off).max() / max(t_o[-1], 1e-30) * 100:.2f}%)")

    print(f"\n=== 分层演化对照（按物理时刻插值对齐）===")
    keys = [k for k in ("targ_xc", "targ_x0", "targ_x1", "shld_x0", "shld_x1",
                        "samp_x0", "samp_x1", "pres_shld")
            if any(k in r for r in r_o) and any(k in r for r in r_n)]
    print(f"  {'量':<10}{'t=0':>12}{'old(t_hi)':>13}{'new(t_hi)':>13}"
          f"{'max|Δ|':>12}{'max rel':>10}")
    summary: dict[str, tuple[float, float]] = {}
    for k in keys:
        # ⚠ 两个 run 的帧数通常不同（L500 跑 2.5 ns，旧算例只有 1.6 ns），
        #   所以"有效性掩码"必须各自算，不能先 & 起来（会广播失败）。
        a_raw = np.array([r.get(k, np.nan) for r in r_o], dtype=float)
        b_raw = np.array([r.get(k, np.nan) for r in r_n], dtype=float)
        oka = np.isfinite(a_raw)
        okb = np.isfinite(b_raw)
        if oka.sum() < 5 or okb.sum() < 5:
            print(f"  {k:<10} 有效帧不足 (old {oka.sum()}, new {okb.sum()}), 跳过")
            continue
        # 只在两者都有数据的时间交集内插值
        lo = max(t_o[oka][0], t_n[okb][0])
        hi = min(t_o[oka][-1], t_n[okb][-1])
        if hi <= lo:
            print(f"  {k:<10} 无公共时段, 跳过")
            continue
        g = np.linspace(lo, hi, 120)
        a = np.interp(g, t_o[oka], a_raw[oka])
        b = np.interp(g, t_n[okb], b_raw[okb])
        d = np.abs(b - a)
        scale = max(abs(np.nanmax(a)), abs(np.nanmin(a)), 1e-30)
        rel = d / np.maximum(np.abs(a), 1e-30)
        big = np.abs(a) > 0.05 * scale          # 相对误差只在量级足够大处统计
        rel_typ = float(np.median(rel[big])) if big.any() else float("nan")
        print(f"  {k:<10}{a_raw[oka][0]:>12.4g}{a[-1]:>13.4g}{b[-1]:>13.4g}"
              f"{d.max():>12.3e}{rel_typ:>10.1e}")
        summary[k] = (float(d.max()), rel_typ)

    # 图：Ti 层质心 + 各层边界（缺失帧留 nan，不连线）
    def col(rows, k):
        return np.array([r.get(k, np.nan) for r in rows], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    ax = axes[0]
    for k, lab in (("targ_xc", "Ti centroid"), ("targ_x0", "Ti left"),
                   ("targ_x1", "Ti right")):
        ax.plot(t_o * 1e9, col(r_o, k), "-", lw=2, label=f"old {lab}")
        ax.plot(t_n * 1e9, col(r_n, k), "--", lw=2, label=f"new {lab}")
    ax.set_xlabel("time [ns]")
    ax.set_ylabel("x [$\\mu$m]")
    ax.set_title("Ti tracer layer (VTi_old vs VTi2old)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)

    ax = axes[1]
    for k, lab in (("shld_x0", "V shld left"), ("shld_x1", "V shld right"),
                   ("samp_x1", "CH front")):
        ax.plot(t_o * 1e9, col(r_o, k), "-", lw=2, label=f"old {lab}")
        ax.plot(t_n * 1e9, col(r_n, k), "--", lw=2, label=f"new {lab}")
    ax.set_xlabel("time [ns]")
    ax.set_ylabel("x [$\\mu$m]")
    ax.set_title("V shield / CH front")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)

    outdir = HERE / "plots"
    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"series_vti{args.depth}_old_vs_oldstyle.png"
    fig.savefig(png, dpi=150)
    print(f"\n[OK] {png}")

    csv_p = outdir / f"series_vti{args.depth}_old_vs_oldstyle.csv"
    allk = sorted({k for r in r_o + r_n for k in r})
    with open(csv_p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "frame"] + allk)
        for tag, rows in (("old", r_o), ("new", r_n)):
            for i, r in enumerate(rows):
                w.writerow([tag, i] + [r.get(k, "") for k in allk])
    print(f"[OK] {csv_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
