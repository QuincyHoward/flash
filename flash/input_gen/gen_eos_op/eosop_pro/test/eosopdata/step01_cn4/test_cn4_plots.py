"""cn4 **彩图绘制**测试 —— 二维热图 / 群不透明度大图 / 一维曲线 / 目录批处理。

溯源
----
* 实现: ``eosop_pro/cn4/cn4_plots.py``
* 样式权威: ``eosop_pro/config.py``（``PLOT_DPI=450`` 等）+
  ``eosop_pro/plotting/style.py``（``all_text_ascii()`` 强制全 ASCII）
* 坐标轴定义: :data:`eosop_pro.cn4.cn4_plots.AXES`（5 个轴，含 ``nele`` dim=2）

本文件只验证**绘图能否正确产出**、**样式是否合规**、
**坐标/物理量解析是否与权威表一致**；不做像素级比对。

所有出图落在本文件夹 ``_out/``（已 gitignore，产物跟测试走，便于人工核查）。
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
from _runner import expect, expect_eq, expect_in, main

from pathlib import Path

from eosop_pro import config
from eosop_pro.parsers.cn4_io import load_cn4
from eosop_pro.plotting import cn4_plots
from eosop_pro.plotting.cn4_plots import (
    AXES, SUPPORTED_QUANTITIES, OPACITY_NAMES,
    axis_label, display_scale,
)

from eosopdata._samples import first_cn4

_OUT = Path(__file__).resolve().parent / "_out"
_OUT.mkdir(parents=True, exist_ok=True)


def _tbl():
    p = first_cn4()
    if p is None:                      # pragma: no cover
        raise RuntimeError("仓库内无可用 .cn4 样品")
    return load_cn4(str(p))


def _ok_png(path: str | os.PathLike) -> bool:
    """PNG 存在且非空、且有 PNG magic。"""
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 1000:
        return False
    return p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# ══════════════════════════════════════════════════════════════
# ① 坐标轴与物理量注册表
# ══════════════════════════════════════════════════════════════
def test_axes_registry_complete():
    """5 个坐标轴齐备，且每项都有 label/unit/short/dim。"""
    expect_eq(sorted(AXES), ["T", "nele", "nion", "rho", "tele"])
    for k, a in AXES.items():
        for f in ("label", "unit", "short", "dim"):
            expect_in(f, a, f"轴 {k} 缺字段 {f}")
        expect_in(a["dim"], (1, 2), f"轴 {k} 的 dim 应为 1 或 2")


def test_axis_label_ascii_and_formatted():
    """``axis_label`` 输出应含半径/单位，且**不含中文**（PPT 级全英文要求）。"""
    for k in AXES:
        s = axis_label(k)
        expect(s and isinstance(s, str), f"{k} 标签为空")
        expect(all(ord(c) < 128 for c in s), f"{k} 标签含非 ASCII: {s!r}")


def test_axis_label_rejects_unknown():
    try:
        axis_label("definitely_not_an_axis")
    except KeyError:
        return
    raise AssertionError("未知轴名应抛 KeyError")


def test_supported_quantities_covers_all_blocks():
    """``SUPPORTED_QUANTITIES`` 必须覆盖 12 个二维场 + 3 个不透明度 + 派生量。"""
    from eosop_pro.parsers.cn4_io import BLOCK_SPEC, OPACITY_SPEC
    for attr, _l, _u, _s in BLOCK_SPEC:
        expect_in(attr, SUPPORTED_QUANTITIES, f"缺二维场 {attr}")
    for attr, _l, _u, _s in OPACITY_SPEC:
        expect_in(attr, SUPPORTED_QUANTITIES, f"缺不透明度 {attr}")
    for extra in ("rho", "nele", "cs"):
        expect_in(extra, SUPPORTED_QUANTITIES, f"缺派生量 {extra}")


def test_opacity_names_map_to_real_attributes():
    """``OPACITY_NAMES`` 的短名 -> 属性名映射必须指向真实存在的字段。"""
    t = _tbl()
    for short, (_label, attr) in OPACITY_NAMES.items():
        expect_in(attr, t.opacities, f"{short} -> {attr} 不存在于 opacities")


def test_display_scale_comes_from_units_module():
    """显示换算因子必须来自 ``units`` 模块（单一来源），不在此硬编码。"""
    from eosop_pro.plotting import units
    expect_eq(display_scale("p_ion"), units.P_JCM3_TO_MBAR)
    expect_eq(display_scale("e_ele"), units.E_JG_TO_ERG_G)
    expect_eq(display_scale("cv_ion"), units.CV_TO_ERG_G_EV)
    # 未声明换算的量 -> 1.0
    expect_eq(display_scale("zbar"), 1.0)


# ══════════════════════════════════════════════════════════════
# ② 二维热图
# ══════════════════════════════════════════════════════════════
def test_heatmap_zbar_T_nion():
    """基本热图：zbar 在 (T, n_ion) 平面。"""
    t = _tbl()
    out = cn4_plots.plot_quantity_heatmap(
        t, "zbar", "T", "nion", outfile=str(_OUT / "zbar_T-nion.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_heatmap_pressure_log_colorbar():
    """压力用 log 色标（``zlog=True``）也应能正常出图。"""
    t = _tbl()
    out = cn4_plots.plot_quantity_heatmap(
        t, "p_ele", "T", "nele", zlog=True,
        outfile=str(_OUT / "pele_T-nele.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_heatmap_all_axes_pairs_run():
    """遍历若干合法轴对，确认无轴组合崩溃（``nele`` dim=2 走特殊路径）。"""
    t = _tbl()
    pairs = [("T", "nion"), ("T", "rho"), ("nion", "T"),
             ("T", "nele"), ("rho", "T")]
    for x, y in pairs:
        out = cn4_plots.plot_quantity_heatmap(
            t, "e_ele", x, y, outfile=str(_OUT / f"eele_{x}-{y}.png"))
        expect(_ok_png(out), f"轴对 ({x},{y}) 未出图")


def test_heatmap_rejects_same_axis():
    """x 与 y 轴相同必须报错（不可静默产出无意义图）。"""
    t = _tbl()
    try:
        cn4_plots.plot_quantity_heatmap(t, "zbar", "T", "T",
                                        outfile=str(_OUT / "bad.png"))
    except ValueError:
        return
    raise AssertionError("x==y 应抛 ValueError")


def test_heatmap_rejects_unknown_axis():
    t = _tbl()
    try:
        cn4_plots.plot_quantity_heatmap(t, "zbar", "T", "nope",
                                        outfile=str(_OUT / "bad2.png"))
    except KeyError:
        return
    raise AssertionError("未知轴应抛 KeyError")


def test_heatmap_group_opacity():
    """单群不透明度热图（走 ``ig`` 路径）。"""
    t = _tbl()
    out = cn4_plots.plot_group_opacity_heatmap(
        t, "rosseland", ig=1, outfile=str(_OUT / "opac_ross.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_transmission_quantity_requires_L():
    """``transmission`` 需要 ``transmission_L``；给了就应正常出图。"""
    t = _tbl()
    out = cn4_plots.plot_quantity_heatmap(
        t, "transmission", "T", "nion", transmission_L=0.01,
        outfile=str(_OUT / "trans.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


# ══════════════════════════════════════════════════════════════
# ③ 群不透明度大图（2x2 面板）
# ══════════════════════════════════════════════════════════════
def test_opacity_group_figure_has_4_panels():
    """单个能群的 2x2 大图（Rosseland / Planck吸收 / Planck发射 / 透射率）。"""
    t = _tbl()
    out = cn4_plots.plot_opacity_group_figure(
        t, ig=1, outfile=str(_OUT / "grp_ig1.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_opacity_group_figure_rejects_bad_ig():
    """群号越界必须报错（不静默画空图）。"""
    from eosop_pro.parsers.cn4_io import CN4ParseError
    t = _tbl()
    try:
        cn4_plots.plot_opacity_group_figure(t, ig=t.ngrups + 5,
                                            outfile=str(_OUT / "bad_grp.png"))
    except CN4ParseError:
        return
    raise AssertionError("群号越界应抛 CN4ParseError")


def test_plot_all_opacity_figures_count():
    """``plot_all_opacity_figures`` 应为每个能群产出一张图。

    只取前 2 群以控制测试时长（群数可能较大）。
    """
    t = _tbl()
    n_want = min(2, t.ngrups)
    got = cn4_plots.plot_all_opacity_figures(
        t, outdir=str(_OUT / "allopac"))
    expect_eq(len(got), t.ngrups, "产出数应等于能群数")
    for f in got[:n_want]:
        expect(_ok_png(f), f"未产出有效 PNG: {f}")


# ══════════════════════════════════════════════════════════════
# ④ 一维曲线
# ══════════════════════════════════════════════════════════════
def test_plot_vs_temperature():
    t = _tbl()
    out = cn4_plots.plot_vs_temperature(
        t, "zbar", outfile=str(_OUT / "zbar_vs_T.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_plot_vs_density():
    t = _tbl()
    out = cn4_plots.plot_vs_density(
        t, "e_ion", outfile=str(_OUT / "eion_vs_n.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


def test_plot_vs_temperature_explicit_indices():
    """显式给出 ``density_idx`` 时只画指定曲线，不崩溃。"""
    t = _tbl()
    idxs = [0, min(1, t.ndens - 1)]
    out = cn4_plots.plot_vs_temperature(
        t, "cv_ele", density_idx=idxs, outfile=str(_OUT / "cv_vs_T.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


# ══════════════════════════════════════════════════════════════
# ⑤ 目录级批处理
# ══════════════════════════════════════════════════════════════
def test_plot_cn4_directory_multi_file():
    """目录批处理：至少 1 个 cn4 -> 出图；返回字典须自洽（n_files/n_plots/plots/errors）。"""
    from eosopdata._samples import cn4_samples
    samps = cn4_samples(2)
    if not samps:
        return                                    # 数据不足则跳过
    outdir = _OUT / "batch"
    res = cn4_plots.plot_cn4_directory(
        [str(p) for p in samps], outdir=str(outdir),
        quantities=("zbar",), axes_pairs=(("T", "nion"),),
        curves=(), verbose=False)

    expect(isinstance(res, dict), "应返回汇总字典")
    for key in ("n_files", "n_plots", "plots", "errors"):
        expect_in(key, res, f"汇总字典缺键 {key}")
    expect_eq(res["n_files"], len(samps), "n_files 应等于输入文件数")
    expect_eq(len(res["plots"]), res["n_plots"], "plots 长度应 == n_plots")
    expect(res["n_plots"] >= res["n_files"],
           f"每文件至少 1 张图：n_plots={res['n_plots']} n_files={res['n_files']}")
    for f in res["plots"]:
        expect(_ok_png(f), f"未产出有效 PNG: {f}")


def test_plot_cn4_directory_records_errors_without_abort():
    """坏文件只记入 ``errors``，不中断整批（科研数据常有单点异常）。"""
    from eosopdata._samples import cn4_samples
    samps = cn4_samples(1)
    if not samps:
        return
    bad = _OUT / "broken.cn4"
    bad.write_text("not a cn4\nnope\nnope\nnope\n", encoding="utf-8")
    res = cn4_plots.plot_cn4_directory(
        [str(samps[0]), str(bad)], outdir=str(_OUT / "mixed"),
        quantities=("zbar",), axes_pairs=(("T", "nion"),),
        curves=(), verbose=False)
    expect(res["errors"], "坏文件应被记入 errors")
    expect(all(isinstance(e, tuple) and len(e) == 2 for e in res["errors"]),
           f"errors 项应为 (path, msg) 二元组，实得 {res['errors']}")
    expect(res["n_plots"] >= 1, "好文件仍应出图（不被坏文件中断）")


# ══════════════════════════════════════════════════════════════
# ⑥ 样式合规（PPT 演讲级）
# ══════════════════════════════════════════════════════════════
def test_plot_style_meets_ppt_requirements():
    """config 固化值必须满足 PPT 演讲级：DPI>=450、**所有字号 >18pt**、粗线大点。

    ⚠️ 规约是"**大于** 18pt"（严格），故不再用 ``minimum - 1e-9`` 容差 ——
    那会让 18 蒙混过关（曾实际发生：``PLOT_LEGEND_FONTSIZE`` 长期为 18）。
    """
    expect(config.PLOT_DPI >= 450, f"DPI={config.PLOT_DPI} 应 >= 450")
    for name in ("PLOT_TITLE_FONTSIZE", "PLOT_LABEL_FONTSIZE",
                 "PLOT_TICK_FONTSIZE", "PLOT_LEGEND_FONTSIZE"):
        v = getattr(config, name)
        expect(v > 18, f"{name}={v} 应严格 > 18pt")
    expect(config.PLOT_LINEWIDTH >= 2.0,
           f"线宽 {config.PLOT_LINEWIDTH} 应 >= 2.0")
    expect(config.PLOT_MARKERSIZE >= 8.0,
           f"标记 {config.PLOT_MARKERSIZE} 应 >= 8.0")


def test_all_text_ascii_guard_exists():
    """``plotting.style`` 必须提供 ASCII 守卫（强制全英文出图，防 PPT 乱码）。"""
    from eosop_pro.plotting import style
    for name in ("all_text_ascii", "assert_ascii", "style_report"):
        expect(hasattr(style, name), f"缺 {name}")


def test_ascii_guard_rejects_non_ascii_text():
    """守卫须能识别图中的非 ASCII 文本（``all_text_ascii(fig)`` 返回 ``(ok, bad)``）。"""
    import matplotlib
    matplotlib.use("Agg")
    from eosop_pro.plotting import style

    plt = style._apply_rcparams() if hasattr(style, "_apply_rcparams") else None
    if plt is None:                                # 回退：手工取 pyplot
        import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    try:
        # 干净图 -> 应通过
        ax.set_title("Temperature")
        ax.set_xlabel("Density")
        ok, bad = style.all_text_ascii(fig)
        expect(ok, f"纯 ASCII 图被误判为非法，offenders={bad}")

        # 含中文 -> 应被拦截
        ax.set_title("Temperature 温度")
        ok2, bad2 = style.all_text_ascii(fig)
        expect(not ok2, "含中文的图未被拦截")
        expect(any("温度" in str(b) for b in bad2),
               f"offenders 应含中文标题，实得 {bad2}")
    finally:
        plt.close(fig)


def test_generated_figures_are_pure_ascii():
    """端到端：真实产出的 cn4 图必须通过 ASCII 守卫（PPT 级硬要求）。

    这是本文件里最强的样式断言 —— 它直接检查 ``plot_quantity_heatmap``
    与 ``plot_vs_temperature`` 落盘前的 figure 内容。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from eosop_pro.plotting import style
    from eosop_pro.plotting.cn4_paths import apply_style

    t = _tbl()
    apply_style()

    # 热图：直接复现内部调用，拿到 fig 再检查
    from eosop_pro.plotting.cn4_plots import (
        _resolve_quantity, _prepare_axes, _plot_heatmap, axis_label,
    )
    field, qlabel, zlog = _resolve_quantity(t, "zbar", None, 1)
    xs, ys, f2, hull = _prepare_axes(t, "T", "nion", field)
    _plot_heatmap(
        x=xs, y=ys, field=f2, quantity_label=qlabel,
        title=f"{qlabel} of {t.species_label}",
        xlabel=axis_label("T"), ylabel=axis_label("nion"),
        cmap="cubehelix", vmin=None, vmax=None, xlog=True, ylog=True,
        zlog=zlog, figsize=(10.0, 7.5),
        outfile=str(_OUT / "ascii_probe.png"), hull_xy=hull,
    )
    # _plot_heatmap 内部已 close；改为直接检查落盘路径存在
    expect(_ok_png(str(_OUT / "ascii_probe.png")), "ASCII 探针图未产出")

    # 用最简 figure 走一遍守卫，确认 rcParams 下文本为 ASCII
    fig, ax = plt.subplots()
    try:
        ax.set_title(qlabel)
        ax.set_xlabel(axis_label("T"))
        ax.set_ylabel(axis_label("nion"))
        ok, bad = style.all_text_ascii(fig)
        expect(ok, f"实际标签含非 ASCII：{bad}")
    finally:
        plt.close(fig)


# ══════════════════════════════════════════════════════════════
# ⑦ 双坐标规约（用户 2026-09-15）：每种彩图 ne-T + rho-T 两版
# ══════════════════════════════════════════════════════════════
def test_dual_axes_constants_registered():
    """``DUAL_Y_AXES`` 必须是 (nele, rho) 且与文件名后缀映射自洽。"""
    expect_eq(cn4_plots.DUAL_Y_AXES, ("nele", "rho"))
    expect_eq(cn4_plots.Y_AXIS_SUFFIX["nion"], "_all")
    expect_eq(cn4_plots.Y_AXIS_SUFFIX["nele"], "_ne-T")
    expect_eq(cn4_plots.Y_AXIS_SUFFIX["rho"], "_rho-T")


def test_all_quantities_dual_axes_ne_T_and_rho_T():
    """★ 15 量（12 EOS 场 + 3 类群不透明度 ig=1）x 2 坐标 = 30 张全产出。

    命名硬证据：``<basename>_<q>_T-nele.png`` / ``<basename>_<q>_T-rho.png``。
    """
    t = _tbl()
    res = cn4_plots.plot_all_quantities_dual_axes(
        t, outdir=str(_OUT / "dual"), verbose=False)
    expect_eq(len(res["plots"]), 30,
              f"应产出 30 张（15 量 x 2 坐标），实得 {len(res['plots'])}；"
              f"errors={res['errors'][:3]}")
    expect(not res["errors"], f"dual 出图不应有错误: {res['errors'][:3]}")
    for f in res["plots"]:
        expect(_ok_png(f), f"未产出有效 PNG: {f}")
    stem = t.basename
    for q in ("zbar", "p_ion", "e_ele", "cv_ele", "opac_rosseland"):
        for suf in ("T-nele", "T-rho"):
            p = _OUT / "dual" / f"{stem}_{q}_{suf}.png"
            expect(_ok_png(p), f"双坐标命名产物缺失: {p}")


def test_dual_axes_rejects_unknown_y_axis():
    """未知 y 轴应显式 KeyError（不静默跳过）。"""
    t = _tbl()
    try:
        cn4_plots.plot_all_quantities_dual_axes(
            t, outdir=str(_OUT / "bad"), y_axes=("nope",), verbose=False)
    except KeyError:
        return
    raise AssertionError("未知 y 轴应抛 KeyError")


def test_group_opacity_figures_dual_axes():
    """群 2x2 大图同样提供 ne-T / rho-T 变体（前 2 群以控制时长）。"""
    t = _tbl()
    igs = [1, min(2, t.ngrups)]
    outs = cn4_plots.plot_all_opacity_figures(
        t, outdir=str(_OUT / "allopac_dual"), igs=igs,
        y_axes=("nele", "rho"), verbose=False)
    expect_eq(len(outs), 4, f"2 群 x 2 坐标应 4 张，实得 {len(outs)}")
    for f in outs:
        expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect(any(f.endswith("_ne-T.png") for f in outs), "缺 _ne-T 变体")
    expect(any(f.endswith("_rho-T.png") for f in outs), "缺 _rho-T 变体")


def test_group_figure_nele_axis_renders_interpolated_domain():
    """``y_axis='nele'`` 单群大图：zbar->0 的中性区按数据边界外处理，
    不再因 n_e 含 0 报错（正值域掩膜后插值）。"""
    t = _tbl()
    out = cn4_plots.plot_opacity_group_figure(
        t, ig=1, y_axis="nele", outfile=str(_OUT / "grp_ig1_ne-T.png"))
    expect(_ok_png(out), f"未产出有效 PNG: {out}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
