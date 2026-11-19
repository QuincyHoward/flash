# -*- coding: utf-8 -*-
"""plot_fe_frames — flychk_fe_groups 新链路（19 群台阶 fe(E)，max-tele 探针）逐帧图。

输入:  out/fe_group_data.npz（由 make_fe_group_zips.py 落盘，无需重读 chk）
输出:  plots/fe_frames/fe_stairs_t{idx:03d}_chk{tag}.png  × 175

每帧内容:
  黑实线   = 19 群台阶 fe(E_g) = (n0+n1_g)/sqrt(E_g)  （含 fe zip 写入的量）
  红虚线   = 121 点细网格参考 fe(E) = f0+f1（同一帧，平滑渲染）
  蓝点线   = 麦氏核心 fe0 = n0/sqrt(E)（不含 fe 版的基线）
  注释框   = t / Te / ne / n1_tot·ne⁻¹ / 探针位置；冷启动前向填充帧有标注

对照（旧链路）: plots/fe_fits/fe_fit_t*.png —— tar2(Ti-track) 探针 + 121 点
渲染，探针格点与本图不同（manifest caveat #1），两组图不可逐帧数值比对形状
以外的量。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
sys.path.insert(0, str(ROOT))

import matplotlib                      # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402
from matplotlib.lines import Line2D    # noqa: E402

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"],
    "font.size": 18, "axes.labelsize": 18, "axes.titlesize": 18,
    "legend.fontsize": 13.5, "xtick.labelsize": 15, "ytick.labelsize": 15,
    "axes.linewidth": 1.3, "figure.dpi": 110,
})

NPZ = HERE / "out" / "fe_group_data.npz"
OUT = HERE / "plots" / "fe_frames"


def _stairs_edges(E_eV: np.ndarray) -> np.ndarray:
    """19 个群中心值 → 20 条 stairs 边界（几何均值，端点 10^(1/6) 外推）。"""
    mid = np.sqrt(E_eV[:-1] * E_eV[1:])
    return np.concatenate([[E_eV[0] / 10 ** (1 / 6)], mid,
                           [E_eV[-1] * 10 ** (1 / 6)]])


def main() -> int:
    with np.load(NPZ) as z:
        d = {k: z[k] for k in z.files}
    E = d["E_eV"]                          # (19,) 群上边界 [eV]
    Ef = _stairs_edges(E)
    E_fine = np.geomspace(0.1, 1e5, 121)   # fe_fine 的能量轴（与生成端同源）
    t, chk = d["t_ns"], d["chk"]
    Te, ne, n1t = d["Te_eV"], d["ne"], d["n1_tot"]
    x_um = d.get("x_um")
    filled = set(int(i) for i in d["filled_idx"])
    first_valid = (max(filled) + 1) if filled else None

    OUT.mkdir(parents=True, exist_ok=True)
    for k in range(len(t)):
        fe = np.maximum(d["fe_stairs"][k], 1e-300)
        fe0 = np.maximum(d["fe0_stairs"][k], 1e-300)
        ff = np.maximum(d["fe_fine"][k], 1e-300)
        peak = max(fe.max(), ff.max())
        floor = peak * 1e-6

        fig, ax = plt.subplots(figsize=(9.5, 7.0))
        ax.stairs(fe, Ef, baseline=None, color="k", lw=2.4,
                  label=r"fe$(E_g)$ 19-group stairs (with-fe zip)")
        ax.loglog(E_fine, ff, "r--", lw=1.6,
                  label=r"fine-grid fe(E) = $f_0+f_1$ (reference)")
        ax.stairs(fe0, Ef, baseline=None, color="#1f77b4", lw=1.6, ls=":",
                  label=r"Maxwellian core $f_0$ (without-fe baseline)")
        for g in range(1, 19):
            ax.axvline(E[g - 1], color="0.6", lw=0.5, alpha=0.35, zorder=0)

        ax.set_xlim(Ef[0], Ef[-1])
        ax.set_ylim(floor, peak * 30)
        ax.set_xlabel("E [eV]  (SNB 19 group boundaries)")
        ax.set_ylabel(r"fe(E) [cm$^{-3}$ eV$^{-3/2}$]")
        tag = str(chk[k]).split("_chk_")[-1]
        ax.set_title(f"#{k:03d}  t = {t[k]:.3f} ns  (chk {tag})", pad=10)
        note = ""
        if k in filled and first_valid is not None:
            note = ("\ncold-start row, forward-filled from frame "
                    f"#{first_valid:03d}")
        ratio = n1t[k] / max(ne[k], 1e-300)
        box = (rf"$T_e$ = {Te[k]:.3g} eV,  $n_e$ = {ne[k]:.3g} cm$^{{-3}}$"
               "\n" rf"$n_{{1,tot}}/n_e$ = {ratio:.3g}"
               + (rf",  probe x = {x_um[k]:.2f} $\mu$m" if x_um is not None else "")
               + note)
        ax.text(0.03, 0.03, box, transform=ax.transAxes, fontsize=15,
                ha="left", va="bottom", color="#7b1fa2",
                bbox=dict(fc="white", ec="#7b1fa2", alpha=0.85, pad=5))
        handles = [Line2D([], [], c="k", lw=2.4),
                   Line2D([], [], c="r", ls="--", lw=1.6),
                   Line2D([], [], c="#1f77b4", ls=":", lw=1.6)]
        ax.legend(handles, [h.get_label() for h in handles],
                  loc="upper right", framealpha=0.9)
        fig.tight_layout()
        out = OUT / f"fe_stairs_t{k:03d}_chk{tag}.png"
        fig.savefig(out)
        plt.close(fig)
        if (k + 1) % 25 == 0 or k + 1 == len(t):
            print(f"    {k + 1}/175 -> {out.parent}")

    print(f"[feframes] done: {len(t)} PNGs in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
