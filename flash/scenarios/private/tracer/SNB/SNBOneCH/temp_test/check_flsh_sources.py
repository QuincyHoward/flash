#!/usr/bin/env python3
"""temp_test —— FL-SH(OneCH_ml) 两种数据形态逐时刻对拍

背景
----
`fig4_xt_compare.png` 里 FL-SH 腿看起来"烧蚀速度"与预期不符。用户要求先排除
**数据/提取**问题，再谈绘制。

因此这里对同一台仿真（OneCH_ml, run_000001, 383 文件 md5 已证同源）的**两种形态**逐时刻对拍：

  A. **原始 chk**  —— 经 `flash.output_processors` 提取（`extraction_mode="h5py"`，
     只取叶子块），再用项目 `DataCalculator` 算 `nele`。即本项目当前使用的方式。
  B. **预抽统一网格 H5** —— 论文管线产物 `CASES_Comp/data/OneCH.h5`
     （`cases/OneCH/fields/*`，space 30000 点 / time 500 点）。即对方彩图的数据源。

对拍量：`dens` / `tele` / `nele`，在若干**固定时刻**与**固定位置**上比对。

判据
----
若各时刻两者一致 → 数据与提取无问题，`fig4` 的差异只能来自**绘制/坐标轴/插值**；
若某些时刻大幅不一致 → 定位到具体是 A 还是 B 有问题（并给出首次分歧的时刻）。

用法
----
    python check_flsh_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np

_HERE = Path(__file__).resolve().parent
_SNBONECH = _HERE.parent
_ROOT = _SNBONECH
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.output_processors.loader import FlashDataLoader          # noqa: E402
from flash.output_processors.hdf5processor import DataCalculator    # noqa: E402

# ── 路径 ──────────────────────────────────────────────────────
CHK_DIR = _ROOT / "flash" / "scenarios" / "private" / "tracer" / "OneCH_ml" \
    / "flash_output" / "outputfiles" / "run_000001"
H5_PATH = Path(r"E:\ProgramsPATH\VMware\SharedFiles\Ubuntu24\FLASHWorkspace"
               r"\python3\pycharm\PhysicsResearchTools\src\project\Report"
               r"\Report_ICMRE\Paper_My\SimComp\CASES_Comp\data\OneCH.h5")

T_PROBE = (0.0, 0.2, 0.4, 0.8, 1.2, 1.6)          # ns
X_PROBE = (-200.0, -100.0, -50.0, -20.0, 0.0, 10.0, 30.0, 50.0)   # µm
K_PER_EV = 1.1604519e4


def list_chk(d: Path) -> List[Tuple[float, Path]]:
    """（t 从文件名推不出 → 调用方按索引排序）返回按编号排序的 chk 列表。"""
    fs = [p for p in d.glob("*hdf5_chk_*") if "forced" not in p.name]
    fs.sort(key=lambda p: int(p.name.rsplit("_", 1)[-1]))
    return fs


def load_chk_frame(p: Path) -> dict:
    c = FlashDataLoader(str(p)).load(compute_derived=False,
                                     extraction_mode="h5py")
    x = np.asarray(c.x).ravel()
    o = np.argsort(x)
    raw = {}
    for k in ("dens", "tele", "ye", "sumy"):
        v = c.data.get(k)
        if v is not None:
            raw[k] = np.asarray(v).ravel()[o]
    rec = {"t": float(c.simulation_time), "x_um": x[o] * 1e4}
    rec.update(raw)
    if raw:
        calc = DataCalculator(raw)
        rec["nele"] = np.asarray(calc.compute("nele"), float)
    return rec


def main() -> int:
    print("=" * 78)
    print(" temp_test — FL-SH(OneCH_ml) 两种数据形态逐时刻对拍")
    print("=" * 78)
    print(f" A 原始 chk : {CHK_DIR}")
    print(f"     存在={CHK_DIR.is_dir()}")
    print(f" B 预抽 H5  : {H5_PATH}")
    print(f"     存在={H5_PATH.is_file()}")
    if not (CHK_DIR.is_dir() and H5_PATH.is_file()):
        print("[X] 路径缺失, 无法对拍")
        return 1

    # ── A: 原始 chk ─────────────────────────────────────────
    chks = list_chk(CHK_DIR)
    print(f"\n[A] chk 帧数 = {len(chks)}")
    frames = []
    for p in chks:
        try:
            frames.append(load_chk_frame(p))
        except Exception as exc:                       # noqa: BLE001
            print(f"    跳过 {p.name}: {exc}")
    frames.sort(key=lambda r: r["t"])
    print(f"    载入 {len(frames)} 帧;  t = {frames[0]['t']*1e9:.4f} … "
          f"{frames[-1]['t']*1e9:.4f} ns")
    tA = np.array([f["t"] for f in frames]) * 1e9

    # ── B: 预抽 H5 ──────────────────────────────────────────
    import h5py
    with h5py.File(H5_PATH, "r") as f:
        sgB = f["metadata/global_space_grid_cm"][:] * 1e4     # µm
        tgB = f["metadata/global_time_grid_s"][:] * 1e9       # ns
        g = f["cases/OneCH/fields"]
        B = {k: f[f"cases/OneCH/fields/{k}"][:].astype(float)
             for k in ("dens", "tele", "nele")}
    print(f"\n[B] H5 网格: x {sgB.min():.0f}…{sgB.max():.0f} µm ({sgB.size} 点), "
          f"t {tgB.min():.3f}…{tgB.max():.3f} ns ({tgB.size} 点)")

    # ── 逐时刻对拍 ──────────────────────────────────────────
    print("\n" + "=" * 78)
    print(" 逐时刻对拍: 在固定 x 上比 A(chk) 与 B(H5)")
    print("=" * 78)
    worst = {}
    for tp in T_PROBE:
        iA = int(np.argmin(np.abs(tA - tp)))
        iB = int(np.argmin(np.abs(tgB - tp)))
        fA = frames[iA]
        print(f"\n── t ≈ {tp:.2f} ns   A: t={tA[iA]:.4f} ns  "
              f"B: t={tgB[iB]:.4f} ns ──")
        for var in ("dens", "tele", "nele"):
            vA = fA.get(var)
            if vA is None:
                print(f"  {var}: A 缺")
                continue
            if var == "tele":
                vA = vA / K_PER_EV
            rB = B[var][iB, :]
            if var == "tele":
                rB = rB / K_PER_EV
            a_pts = np.interp(X_PROBE, fA["x_um"], vA)
            b_pts = np.interp(X_PROBE, sgB, rB)
            ok = a_pts > 0
            rel = np.where(ok, np.abs(a_pts - b_pts) / np.maximum(a_pts, 1e-30),
                           np.nan)
            print(f"  {var:<5} A/B 相对差: "
                  f"中位 {np.nanmedian(rel)*100:7.2f}%   "
                  f"最大 {np.nanmax(rel)*100:7.2f}%")
            worst[var] = max(worst.get(var, 0.0),
                             float(np.nanmax(rel)) if rel.size else 0.0)
            for i, xp in enumerate(X_PROBE):
                print(f"      x={xp:>7.1f} µm   A={a_pts[i]:>10.3e}   "
                      f"B={b_pts[i]:>10.3e}   Δ={rel[i]*100:6.2f}%")

    print("\n" + "=" * 78)
    print(" 汇总: 各量在所有时刻/位置上的最大相对差")
    for k, v in worst.items():
        flag = "✓ 一致" if v < 0.05 else ("△ 有差异" if v < 0.5 else "✗ 显著不一致")
        print(f"   {k:<5} {v*100:8.2f}%   {flag}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
