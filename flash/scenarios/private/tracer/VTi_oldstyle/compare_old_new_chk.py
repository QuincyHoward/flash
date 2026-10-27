"""比对 VTi_oldstyle 与 VTi_old 的初始帧（chk_0000），验证两者为同一算例。

判据刻意避开"全局剖面插值"（AMR 粗细层交错时容易串层），改为直接统计
每个物种质量分数 > 0.5 的胞：其 x 范围、密度平台、压力量级。
这些量对块的排列方式不敏感，只反映真实分层。

用法:
  python compare_old_new_chk.py --depth 2 --new <chk_0000 路径>
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import h5py
import numpy as np

OLD_ROOT = Path(os.environ["FLASH_OLD_VM_WS"])  # 旧 VM 工作区（显式注入，如 <旧VM工作区>/FLASHWorkspace）
                "FLASHProjectData/data/input")
OLD_TS = {"1": "20260331_205557", "2": "20260331_215819", "3": "20260331_231147"}
SPECIES = ("cham", "samp", "shld", "targ")


def old_chk(depth: str) -> Path:
    tag = f"ReDo042sp_CH042sp{depth}um8.00e-02"
    return OLD_ROOT / tag / f"{tag}2026" / f"hdf5files_{OLD_TS[depth]}" / \
        f"src_{OLD_TS[depth]}" / "lasslab_hdf5_chk_0000"


def cells(path: Path, var: str):
    """返回 (x_center[um], dx[um], value, nb, nx) 逐胞数组，不做任何合并。"""
    with h5py.File(path, "r") as h:
        a = np.asarray(h[var][:], dtype=np.float64)
        bb = np.asarray(h["bounding box"][:], dtype=np.float64)
    if a.ndim == 4:
        a = a[:, 0, 0, :]
    nb, nx = a.shape
    dx = (bb[:, 0, 1] - bb[:, 0, 0]) / nx
    x0 = bb[:, 0, 0] + dx / 2
    x1 = bb[:, 0, 1] - dx / 2
    t = np.linspace(0, 1, nx)
    x = ((x0[:, None] * (1 - t) + x1[:, None] * t) * 1e4).ravel()
    return x, np.repeat(dx, nx) * 1e4, a.ravel(), nb, nx


def summarize(path: Path, tag: str) -> dict:
    print(f"\n===== {tag} =====")
    print(f"  {path}")
    if not path.exists():
        print("  [X] 文件不存在")
        return {}
    x, dx, dens, nb, nx = cells(path, "dens")
    print(f"  blocks={nb} nxb={nx} cells={nb * nx}")
    print(f"  x range = [{x.min():.3f}, {x.max():.3f}] um   dx = "
          f"{dx.min():.4f} .. {dx.max():.4f} um")

    info = {"nb": nb, "nx": nx, "xmin": float(x.min()), "xmax": float(x.max())}
    for sp in SPECIES:
        try:
            _, _, fr, _, _ = cells(path, sp)
        except KeyError:
            print(f"  {sp:<5} 缺失")
            continue
        m = fr > 0.5
        if not m.any():
            print(f"  {sp:<5} 无纯胞")
            continue
        print(f"  {sp:<5} n={m.sum():>4}  x=[{x[m].min():7.3f},{x[m].max():7.3f}] um"
              f"  rho={np.unique(np.round(dens[m], 3))[:4]}  frac_max={fr.max():.3f}")
        info[f"{sp}_x0"] = float(x[m].min())
        info[f"{sp}_x1"] = float(x[m].max())
        info[f"{sp}_rho"] = float(np.median(dens[m]))

    try:
        _, _, fr_sh, _, _ = cells(path, "shld")
        ms = fr_sh > 0.5
    except KeyError:
        ms = None
    for var in ("pres", "tele", "tion"):
        try:
            _, _, v, _, _ = cells(path, var)
        except KeyError:
            continue
        if ms is not None and ms.any():
            print(f"  {var:<5}(屏蔽层) median = {np.median(v[ms]):.4e}")
            info[f"{var}_shld"] = float(np.median(v[ms]))
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", default="2")
    ap.add_argument("--new", required=True)
    ap.add_argument("--old", default=None)
    args = ap.parse_args()

    a = summarize(Path(args.old) if args.old else old_chk(args.depth),
                  f"VTi_old ({args.depth} um)")
    b = summarize(Path(args.new), f"VTi_oldstyle ({args.depth} um)")

    print("\n===== 差异 =====")
    if not a or not b:
        return 1
    same_grid = (a["nb"], a["nx"]) == (b["nb"], b["nx"])
    print(f"  网格    : old=({a['nb']},{a['nx']})  new=({b['nb']},{b['nx']})  "
          f"{'一致' if same_grid else '不同'}")
    print(f"  域      : old=[{a['xmin']:.3f},{a['xmax']:.3f}]  "
          f"new=[{b['xmin']:.3f},{b['xmax']:.3f}]  um")
    for sp in SPECIES:
        if f"{sp}_x0" not in a or f"{sp}_x0" not in b:
            continue
        d0 = abs(b[f"{sp}_x0"] - a[f"{sp}_x0"])
        d1 = abs(b[f"{sp}_x1"] - a[f"{sp}_x1"])
        dr = abs(b[f"{sp}_rho"] - a[f"{sp}_rho"]) / max(a[f"{sp}_rho"], 1e-30)
        print(f"  {sp:<5} 边界偏差 = {d0:.4f} / {d1:.4f} um ; "
              f"rho={a[f'{sp}_rho']:.4g} vs {b[f'{sp}_rho']:.4g} (rel {dr:.1e})")
    for k in ("pres_shld", "tele_shld", "tion_shld"):
        if k in a and k in b:
            rel = abs(b[k] - a[k]) / max(abs(a[k]), 1e-30)
            print(f"  {k:<10} old={a[k]:.4e}  new={b[k]:.4e}  rel={rel:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
