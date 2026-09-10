"""t002 守恒体检 —— 质量 / 内能收支（发现数值失效的关键工具）

背景
----
`t002` 对比发现在 `5e14 W/cm² × 1 ns` 驱动下，SNB 腿（FLASHSNB 构建）出现
**质量与能量双重不守恒**，而这类失效在日志里**没有任何报错**
（无 negative / NaN / abort），plt 单帧剖面看起来也"正常"。
只有把**积分守恒量**随时间画出来才会暴露。

判据
----
* 总质量 `M(t) = ∫ρ dx`：域两端为 outflow，只能单调缓慢流失；**不允许下降后回升**。
* 内能 / 激光注入能量比：`E_int(t) / (I·t)` 必须 ≤ 1（实际应 ≲0.6，其余去动能/辐射）。
  电子+离子内能密度取 `3 n_e k T`（`(3/2)n_e kT` 电子 + `(3/2)n_e kT` 离子），
  `n_e ≈ 3.0e23 · ρ`（CH / He 完全电离的 Z/A·N_A 量级）。

用法:
    python scripts/analysis/check_conservation.py --tag full_1ns
    python scripts/analysis/check_conservation.py --tag full_1ns_h006 --laser 5e14 --pulse-ns 1.05
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_T002 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T002 / "common"))
sys.path.insert(0, str(_T002 / "scripts" / "analysis"))

import t002_common as C                                  # noqa: E402
from compare_models import load_series, COLORS           # noqa: E402

import numpy as np                                       # noqa: E402
import matplotlib                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402

plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "axes.linewidth": 2.0, "lines.linewidth": 2.6,
    "font.family": "DejaVu Sans",
})

NE_PER_RHO = 3.0e23        # cm^-3 / (g/cm^3)，CH/He 完全电离量级
K_B = 1.380649e-16         # erg/K


def diagnostics(model: str, tag: str, laser_w: float, pulse_s: float
                ) -> Dict[str, Any]:
    """返回单腿的守恒诊断时间序列。"""
    ser = load_series(C.leg_output_dir(model) / tag)
    if not ser:
        return {}
    t, mass, eint = [], [], []
    for fr in ser:
        x = fr["x_um"]
        d = np.asarray(fr["dens"], float)
        T = np.asarray(fr["tele"], float)
        dx = np.gradient(x) * 1e-4                  # um -> cm
        t.append(fr["t"])
        mass.append(float(np.sum(d * dx)))
        eint.append(float(np.sum(3.0 * NE_PER_RHO * d * K_B * T * dx)))
    t = np.array(t)
    injected = laser_w * np.minimum(t, pulse_s) * 1e7      # erg/cm^2
    injected[injected <= 0] = np.nan
    return {
        "t": t, "mass": np.array(mass), "eint": np.array(eint),
        "injected": injected,
        "ratio": np.array(eint) / injected,
        "mass_init": mass[0], "mass_min": float(np.min(mass)),
        "mass_final": mass[-1], "ratio_final": eint[-1] / injected[-1],
        "ratio_max": float(np.nanmax(eint / injected)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="t002 质量/能量守恒体检")
    ap.add_argument("--tag", default="full_1ns")
    ap.add_argument("--laser", type=float, default=5.0e14, help="激光强度 [W/cm^2]")
    ap.add_argument("--pulse-ns", type=float, default=1.05,
                    help="激光持续时长 [ns] (梯形波 平台+下降沿)")
    args = ap.parse_args()

    pulse_s = args.pulse_ns * 1e-9
    print("\n" + "=" * 78)
    print(f" t002 守恒体检   tag={args.tag}   激光={args.laser:.3g} W/cm² × "
          f"{args.pulse_ns:.2f} ns   {C.stamp()}")
    print("=" * 78)

    diags: Dict[str, Dict[str, Any]] = {}
    for model in ("flsh", "snb"):
        d = diagnostics(model, args.tag, args.laser, pulse_s)
        if not d:
            C.log(f"{model}: 无数据", "WARN")
            continue
        diags[model] = d
        C.log(f"{C.LEGS[model]['label']}: 质量 {d['mass_init']*1e4:.3f} → "
              f"{d['mass_final']*1e4:.3f} (最低 {d['mass_min']*1e4:.3f}) 1e-4 g/cm² | "
              f"内能/激光 末帧 {d['ratio_final']:.3f} 峰值 {d['ratio_max']:.3f}",
              "OK" if d["ratio_max"] <= 1.0 and d["mass_min"] > 0.95 * d["mass_init"]
              else "ERROR")

    if not diags:
        return 1
    outdir = C.RESULT_DIR / args.tag
    outdir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(19, 7), constrained_layout=True)
    for model, d in diags.items():
        lab = C.LEGS[model]["label"]
        axes[0].plot(d["t"] * 1e9, d["mass"] * 1e4, color=COLORS[model],
                     marker="o", ms=6, label=lab)
        axes[1].plot(d["t"] * 1e9, d["ratio"], color=COLORS[model],
                     marker="o", ms=6, label=lab)
    axes[0].axhline(diags[list(diags)[0]]["mass_init"] * 1e4, ls=":", lw=2,
                    color="gray", label="initial mass")
    axes[0].set_xlabel("t [ns]")
    axes[0].set_ylabel(r"total mass  $\int\rho\,dx$  [$10^{-4}$ g/cm$^2$]")
    axes[0].set_title("Mass conservation")
    axes[0].grid(True, alpha=0.25, lw=0.8)
    axes[0].legend(loc="best", fontsize=17)
    axes[1].axhline(1.0, ls=":", lw=2, color="gray", label="laser input = 1")
    axes[1].set_xlabel("t [ns]")
    axes[1].set_ylabel(r"$E_\mathrm{int}$ / laser input")
    axes[1].set_title("Energy budget (must be <= 1)")
    axes[1].grid(True, alpha=0.25, lw=0.8)
    axes[1].legend(loc="best", fontsize=17)
    fig.suptitle(f"Conservation check — {args.tag}", fontsize=24,
                 fontweight="bold")
    fig.savefig(str(outdir / "cmp_conservation.png"), dpi=450)
    plt.close(fig)
    C.log(f"    cmp_conservation.png ✓")

    def _safe(d: Dict[str, Any]) -> Dict[str, Any]:
        return {k: (v.tolist() if isinstance(v, np.ndarray) else v)
                for k, v in d.items()}

    (outdir / "conservation.json").write_text(
        json.dumps({m: _safe(d) for m, d in diags.items()}, indent=2),
        encoding="utf-8", newline="\n")

    print("\n  汇总:")
    print("  腿    | 质量初  | 质量末  | 质量最低 | 内能/激光 末 | 峰值")
    print("  ------+---------+---------+----------+--------------+-------")
    for m, d in diags.items():
        print(f"  {m:<5} | {d['mass_init']*1e4:7.3f} | {d['mass_final']*1e4:7.3f} | "
              f"{d['mass_min']*1e4:8.3f} | {d['ratio_final']:12.3f} | {d['ratio_max']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
