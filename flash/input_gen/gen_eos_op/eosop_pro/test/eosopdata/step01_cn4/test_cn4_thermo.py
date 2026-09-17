#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cn4 **热力学派生量**测试 —— 有效 γ / 声速两项分解 / 占比 / γ_sound。

溯源
----
* 实现: ``eosop_pro/plotting/cn4_thermo.py``（r16 自 test/sound_velocity
  固化，包级唯一实现；声速唯一实现 = ``cn4_paths.sound_speed``）
* 通用绘图入口: ``cn4_plots.plot_quantity_heatmap`` 的
  ``gamma_ion`` / ``gamma_ele`` / ``cs_thermal_fraction`` 通道
* CLI: ``python -m eosop_pro.plotting.cn4_thermo <sample.cn4>``

物理锚（合成理想气体表上全部**机器精度**成立，见
``eosopdata._idealgas.IdealGasStub`` 的代数自洽设计）：

=========================  =========
量                         理想气体锚
=========================  =========
γ_i / γ_e = 1 + P/(ρe)     5/3
γ_sound = c_s²ρ/P          5/3
热熵项占比 (γ-1)/γ         0.40
cs_terms 之和              = c_s²/1e7
=========================  =========

所有出图落在本文件夹 ``_out/``（已 gitignore，产物跟测试走）。
"""

import os
import sys

# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, main

from pathlib import Path

import numpy as np

from eosop_pro.parsers.cn4_io import load_cn4
from eosop_pro.plotting import cn4_thermo as TH
from eosop_pro.plotting import cn4_plots as CP
from eosop_pro.plotting.cn4_paths import sound_speed

from eosopdata._samples import first_cn4
from eosopdata._idealgas import IdealGasStub

_OUT = Path(__file__).resolve().parent / "_out"
_OUT.mkdir(parents=True, exist_ok=True)


def _tbl():
    p = first_cn4()
    if p is None:                      # pragma: no cover
        raise RuntimeError("仓库内无可用 .cn4 样品")
    return load_cn4(str(p))


def _ok_png(path) -> bool:
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 1000:
        return False
    return p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# ══════════════════════════════════════════════════════════════
# ① γ 单点恒等式（合成理想气体锚 + NaN 掩膜）
# ══════════════════════════════════════════════════════════════
def test_gamma_identity_idealgas_5_3():
    """理想气体表上 γ_i / γ_e 必须全域精确 = 5/3（单点恒等式无差分）。"""
    t = IdealGasStub()
    for name, g in (("gamma_i", TH.gamma_ion(t)),
                    ("gamma_ele", TH.gamma_ele(t))):
        g = np.asarray(g, dtype=float)
        expect(np.all(np.isfinite(g)), f"{name} 含非有限值")
        expect(np.allclose(g, 5.0 / 3.0, rtol=1e-9),
               f"{name} 偏离 5/3: [{g.min():.9f}, {g.max():.9f}]")


def test_gamma_species_nan_masking():
    """``e <= 0`` 处 γ 必须为 NaN（不静默填 0/不静默外推）。"""
    t = IdealGasStub(ndens=3, ntemp=2)
    t.e[0, :] = [0.0, -1.0]                # 第 0 行比内能置非正
    g = np.asarray(TH.gamma_ion(t), dtype=float)
    expect(np.all(np.isnan(g[0, :])), "e<=0 行的 γ 应为 NaN")
    expect(np.all(np.isfinite(g[1:, :])), "正常行不应误伤为 NaN")


def test_gamma_powerlaw_fit_constant_row():
    """常数 γ 行拟合：a≈γ、b≈0。

    注：不断言 R²——γ 行含 ~1e-16 浮点噪声使 SS_tot 非 0 但与
    残差同量级，R² 取值任意（实测可为 -0.6 等），物理上无意义。
    """
    t = IdealGasStub()
    T = np.asarray(t.temperature, dtype=float)
    g = np.asarray(TH.gamma_ion(t), dtype=float)[t.ndens // 2]
    a, b, r2 = TH.gamma_powerlaw_fit(T, g)
    expect(abs(a - 5.0 / 3.0) < 1e-6, f"常数行拟合幅 a={a:.9f} 应≈5/3")
    expect(abs(b) < 1e-9, f"常数行拟合幂 b={b:.3e} 应≈0")


# ══════════════════════════════════════════════════════════════
# ② 两项分解 / 占比 / γ_sound（与 cn4_paths 唯一声速实现互洽）
# ══════════════════════════════════════════════════════════════
def test_cs_terms_sum_matches_sound_speed():
    """两项之和必须 == (c_s)^2/1e7（两处独立差分实现的一致性守卫）。

    这是 ln10 类坐标 bug 的回归防线：若任一实现把密度差分坐标
    写成 log10(n)，两者差会立即超出机器精度。
    """
    t = IdealGasStub()
    th, iso = TH.cs_terms(t)
    cs2_jg = np.asarray(sound_speed(t), dtype=float) ** 2 * 1e-7
    expect(np.allclose(th + iso, cs2_jg, rtol=1e-12),
           f"cs_terms 与 sound_speed 不一致: "
           f"max_rel={np.max(np.abs((th + iso) - cs2_jg) / cs2_jg):.3e}")


def test_thermal_fraction_idealgas_0p4():
    """理想气体表上热熵项占比必须全域精确 = 0.40 = (γ-1)/γ。"""
    t = IdealGasStub()
    th, iso = TH.cs_terms(t)
    frac = np.asarray(TH.thermal_fraction(th, iso), dtype=float)
    expect(np.all(np.isfinite(frac)), "占比含非有限值")
    expect(np.allclose(frac, 0.4, rtol=1e-9),
           f"热熵占比偏离 0.4: [{frac.min():.9f}, {frac.max():.9f}]")


def test_thermal_fraction_range_real_sample():
    """真实样品（Z06 CH 混合，含电离效应）占比仍须 ∈ [0,1]。"""
    t = _tbl()
    th, iso = TH.cs_terms(t)
    frac = np.asarray(TH.thermal_fraction(th, iso), dtype=float)
    fin = frac[np.isfinite(frac)]
    expect(fin.size > 0, "真实样品占比无有效点")
    expect(bool(np.all((fin >= 0) & (fin <= 1))),
           f"占比越界: range=[{fin.min():.3f}, {fin.max():.3f}]")


def test_sound_gamma_eff_idealgas_5_3():
    """γ_sound = c_s²ρ/P 在理想气体表上必须全域精确 = 5/3。"""
    t = IdealGasStub()
    g = np.asarray(TH.sound_gamma_eff(t), dtype=float)
    expect(np.all(np.isfinite(g)), "γ_sound 含非有限值")
    expect(np.allclose(g, 5.0 / 3.0, rtol=1e-9),
           f"γ_sound 偏离 5/3: [{g.min():.9f}, {g.max():.9f}] "
           "(若≈2.97 为 dlnP/dlnn 坐标混用 ln10 复发)")


# ══════════════════════════════════════════════════════════════
# ③ 通用绘图引擎新通道 + 折线图 + CLI 冒烟
# ══════════════════════════════════════════════════════════════
def test_plot_quantity_heatmap_gamma_and_fraction_channels():
    """``gamma_ion``/``gamma_ele``/``cs_thermal_fraction`` 通道出图。"""
    t = _tbl()
    for q, tag in (("gamma_ion", "gi"), ("gamma_ele", "ge"),
                   ("cs_thermal_fraction", "frac")):
        f = CP.plot_quantity_heatmap(
            t, q, cmap="viridis",
            vmin=1.0 if q != "cs_thermal_fraction" else 0.0,
            vmax=2.0 if q != "cs_thermal_fraction" else 1.0,
            outfile=str(_OUT / f"thermo_{tag}_channel.png"))
        expect(_ok_png(f), f"quantity={q} 未产出有效 PNG: {f}")


def test_plot_gamma_T_fit_smoke():
    """``plot_gamma_T_fit`` 折线图（真实样品中密度行）冒烟。"""
    t = _tbl()
    T = np.asarray(t.temperature, dtype=float)
    idx = t.ndens // 2
    gi = np.asarray(TH.gamma_ion(t), dtype=float)
    ge = np.asarray(TH.gamma_ele(t), dtype=float)
    fit_i = TH.gamma_powerlaw_fit(T, gi[idx])
    fit_e = TH.gamma_powerlaw_fit(T, ge[idx])
    f = CP.plot_gamma_T_fit(
        t, gi[idx], ge[idx], fit_i, fit_e,
        outfile=str(_OUT / "thermo_gamma_T_fit.png"),
        row_note=f"n = {np.asarray(t.density, dtype=float)[idx]:.1e} cm^-3 "
                 "(mid-density row)")
    expect(_ok_png(f), f"未产出有效 PNG: {f}")


def test_cli_main_smoke():
    """CLI ``main()`` 全流程：6 图 + summary.txt 齐全且 PNG 有效。"""
    # 从 __file__ 推 gen_eos_op 根：.../gen_eos_op/eosop_pro/test/
    # eosopdata/step01_cn4/test_cn4_thermo.py -> parents[4] = gen_eos_op
    sample = (Path(__file__).resolve().parents[4] / "eos_op_data"
              / "Gen_eos_op_data" / "Z06_0.50-Z01_0.50-20260708_0850"
              / "Z06_0.50-Z01_0.50-20260708_0850.cn4")
    expect(sample.is_file(), f"CLI 冒烟样品不存在: {sample}")
    outdir = _OUT / "cli_smoke"
    rc = TH.main([str(sample), "--outdir", str(outdir)])
    expect_eq(rc, 0, "CLI 退出码应为 0")
    expected = ["gamma_ion_heatmap.png", "gamma_ele_heatmap.png",
                "cs_nt_log_heatmap.png", "cs_rho_cubehelix_linear.png",
                "cs_thermal_fraction_heatmap.png", "gamma_T_fit.png"]
    for name in expected:
        expect(_ok_png(outdir / name), f"CLI 产物缺失/无效: {name}")
    s = outdir / "summary.txt"
    expect(s.is_file() and s.stat().st_size > 100, "summary.txt 缺失或为空")
    raw = s.read_bytes()
    expect(b"\r\n" not in raw, "summary.txt 必须为 LF 换行")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
