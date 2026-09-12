#!/usr/bin/env python3
"""temp_test —— 前沿速度定量对拍（定位 `fig4` "两种烧蚀速度不同"的根因）

问题
----
`fig4_xt_compare.png` 中上行(SNB)与下行(OneCH_ml)看起来"前沿速度明显不同"。

已定位的根因（本脚本可复现）
----------------------------
`fig_xt()` 原先用 `imshow` + `extent=(x0,x1,t0,t1)`。**`imshow` 假设各行在
时间轴上等间距**，但 FLASH 的 chk 是按**步数**间隔输出的：

    腿                帧数   Δt 范围             最大/最小
    SNBOneCH (+ug)     81   2.0000e-11 (恒定)    1.00×
    OneCH_ml (AMR)    317   1.36e-12 … 7.19e-11  52.7×

⇒ OneCH 行的时间轴被局部拉偏最多 >3000%，同一物理运动在两行上显得速度不同。
修正：改 `pcolormesh` + **真实逐帧时间坐标**。

本脚本做两件事
--------------
1. 打印各腿的 Δt 均匀性（复现上表）。
2. 用**阈值法**算电子密度临界面轨迹 `x_c(t)`（`nele = n_c(0.351 µm)`），
   对 SNB / FL-SH(chk) / FL-SH(预抽 H5) 三方比较位置与速度。
   —— 位置/速度用可复算的阈值法，**不靠看图**。

用法
----
    python front_compare.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE.parent))          # 复用 plot_compare_onech 的 loader
sys.path.insert(0, str(_HERE))

import plot_compare_onech as M                 # noqa: E402

N_C_0351UM = 9.05e21        # 临界电子密度 [cm^-3]（0.351 µm）

SNB_CHK = _HERE.parent / "scene" / "flash_output" / "sim_snb" / "full"
FLSH_CHK = _ROOT / "flash" / "scenarios" / "private" / "tracer" / "OneCH_ml" \
    / "flash_output" / "outputfiles" / "run_000001"
FLSH_H5 = Path(r"E:\ProgramsPATH\VMware\SharedFiles\Ubuntu24\FLASHWorkspace"
               r"\python3\pycharm\PhysicsResearchTools\src\project\Report"
               r"\Report_ICMRE\Paper_My\SimComp\CASES_Comp\data\OneCH.h5")
T_PROBE = (0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6)


def dt_uniformity(d: Path, label: str) -> None:
    from flash.output_processors.loader import FlashDataLoader
    ts = []
    for p in M.list_frames(d):
        c = FlashDataLoader(str(p)).load(compute_derived=False,
                                         extraction_mode="h5py")
        ts.append(float(c.simulation_time))
    ts = np.array(ts)
    dt = np.diff(ts)
    print(f"  {label:<24} {len(ts):>4} 帧   Δt {dt.min():.3e} … {dt.max():.3e}   "
          f"最大/最小 = {dt.max()/dt.min():.2f}×")
    if dt.max() / dt.min() > 1.05:
        print(f"      ★ 非均匀! 用 imshow 会把时间轴局部拉偏约 "
              f"{(dt.max()/np.median(dt)-1)*100:.0f}%")


def xc_from_profile(x_um: np.ndarray, nele: np.ndarray,
                    n_c: float = N_C_0351UM) -> float:
    """电子密度临界面位置：从**外侧(x 大)**向里找 nele 首次跌破 n_c 处（线性插值）。

    取最外侧交点 —— 即激光侧的临界面，物理上对应冕区/临界密度面。
    """
    o = np.argsort(x_um)
    x, ne = x_um[o], nele[o]
    m = np.isfinite(x) & np.isfinite(ne)
    x, ne = x[m], ne[m]
    if x.size < 3:
        return float("nan")
    below = ne < n_c
    if not below.any() or below.all():
        return float("nan")
    # 从右往左找第一个"由 >= n_c 变为 < n_c"的交点
    for j in range(x.size - 1, 0, -1):
        if ne[j] < n_c <= ne[j - 1]:
            x0, x1, n0, n1 = x[j - 1], x[j], ne[j - 1], ne[j]
            if n1 == n0:
                return float(x1)
            return float(x0 + (n_c - n0) * (x1 - x0) / (n1 - n0))
    return float("nan")


def front_series(frames: List[Dict], label: str) -> Dict[str, np.ndarray]:
    ts, xs = [], []
    for fr in frames:
        ne = M.derive(fr, "nele")
        if ne is None:
            continue
        xc = xc_from_profile(np.asarray(fr["x_um"], float),
                             np.asarray(ne, float))
        ts.append(fr["t"] * 1e9)
        xs.append(xc)
    return {"label": label, "t": np.asarray(ts), "x": np.asarray(xs)}


def report(ser: Dict[str, np.ndarray], tmin: float = 0.4) -> None:
    t, x = ser["t"], ser["x"]
    lab = ser["label"]
    print(f"\n  【{lab}】电子密度临界面 x_c(t)")
    print(f"      t[ns] : " + " ".join(f"{v:>8.3f}" for v in T_PROBE))
    row = []
    for tp in T_PROBE:
        m = np.isfinite(x)
        if not m.any():
            row.append("     n/a"); continue
        v = float(np.interp(tp, t[m], x[m])) if t[m].size > 1 else float("nan")
        row.append(f"{v:>8.3f}")
    print("      x_c[µm]: " + " ".join(row))
    # 速度：对 t>=tmin 段做线性拟合
    m = np.isfinite(x) & (t >= tmin)
    if m.sum() >= 3:
        k, b = np.polyfit(t[m], x[m], 1)
        print(f"      拟合速度 (t≥{tmin} ns): {k*1e-3:+.4f} µm/ps  "
              f"= {k*1e3:+.3f} µm/ns   (n={int(m.sum())})")
    else:
        print("      有效点不足, 跳过速度拟合")


def main() -> int:
    print("=" * 78)
    print(" temp_test — 前沿速度定量对拍")
    print("=" * 78)

    print("\n① 帧时间间隔均匀性（复现 fig4 的时间轴 bug 条件）")
    dt_uniformity(SNB_CHK, "SNBOneCH (+ug chk)")
    dt_uniformity(FLSH_CHK, "OneCH_ml (AMR chk)")

    print("\n② 载入三方数据")
    a = M.load_frames(SNB_CHK)
    b = M.load_frames(FLSH_CHK)
    print(f"  SNBOneCH chk     : {len(a)} 帧")
    print(f"  OneCH_ml  chk    : {len(b)} 帧")

    c = []
    if FLSH_H5.is_file():
        import h5py
        with h5py.File(FLSH_H5, "r") as f:
            sg = f["metadata/global_space_grid_cm"][:] * 1e4
            tg = f["metadata/global_time_grid_s"][:] * 1e9
            ne = f["cases/OneCH/fields/nele"]
            for i in range(tg.size):
                if tg[i] > 1.65:
                    break
                c.append({"t": float(tg[i] * 1e-9), "x_um": sg,
                          "nele": ne[i, :].astype(float)})
        print(f"  OneCH_ml  H5     : {len(c)} 帧 (预抽统一网格)")
    else:
        print("  OneCH_ml  H5     : 缺失, 跳过")

    print("\n③ 阈值法前沿轨迹（阈值 = n_c(0.351 µm) = 9.05e21 cm⁻³）")
    sa = front_series(a, "SNBOneCH (nonlocal)")
    sb = front_series(b, "OneCH_ml chk (local)")
    report(sa)
    report(sb)
    if c:
        sc = front_series(c, "OneCH_ml H5 (local, 预抽)")
        report(sc)

    print("\n" + "=" * 78)
    print(" 结论")
    print("=" * 78)
    print("  · 若 SNB 与 FL-SH 的 x_c(t) 在同一量级、趋势一致 → fig4 的'速度不同'")
    print("    来自**绘制**（imshow 假设等间距），已改 pcolormesh 修正。")
    print("  · OneCH 的 chk 与 H5 应一致（同一台仿真的两种形态）。")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
