"""非 cn4 各族的**彩图绘制**测试（全英文、字体 > 18pt、PPT 演讲级）。

被测量的绘图入口（``eosop_pro.plotting.qa_plots``）
----------------------------------------------------
==============================  =====================================
函数                            适用表
==============================  =====================================
``plot_opacity_heatmap``        2D 不透明度（``rho``/``Te`` 轴）
``plot_zeff``                   2D 平均电离度
``plot_eos_isobars``            2D EOS（``rho``/``Te`` 轴）
``plot_loglog_curve``           1D 曲线（冷不透明度等）
==============================  =====================================

硬性约束（用户既定规约，见 ``plotting/style.py`` 与 ``config.py``）
------------------------------------------------------------------
* 文本**全 ASCII** —— 由 ``all_text_ascii(fig)`` 逐 text artist 强校验；
* 字号 **> 18pt** —— ``config.PLOT_*_FONTSIZE`` 已固化；
* DPI **>= 450**；
* 线宽 >= 2.4、标记 >= 8。

样品惰性发现：找不到即早返回，不把"数据不在"当缺陷。
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
import _runner                                                    # noqa: F401
from _runner import expect, expect_eq, main                      # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

from eosopdata._samples import find_parseable, tmp_dir             # noqa: E402

from eosop_pro import config                                      # noqa: E402
from eosop_pro.plotting.labels import field_label                 # noqa: E402

#: 各族样品模式（与 test_family_extract.py 一致）。
SAMPLE_PATTERNS = {
    "mpqeos": ("*.301",),
    "hyades_eos": ("qeos_*",),
    "feos_native": ("*.feos",),
    "multi_inverted_eos": ("AL_eos",),
    "ledcop_atomic": ("Al.txt",),
    "ledcop_zeff": ("*.NoFree",),
    "multi_opacity": ("*.planck",),
    "sesame_dat": ("*.dat",),
    "coldopacity": ("*.coldopacity",),
    "generic_curve": ("ionpot*",),
    "hugoniot": ("*.hug",),
}


def _first(fam):
    """取族样品第一张表，找不到返回 ``None``。"""
    pats = SAMPLE_PATTERNS.get(fam)
    if pats is None:
        return None
    r = find_parseable(fam, pats)
    return r[1][0] if r else None


def _pick_2d(table, *cands):
    """在表里挑第一个真正是 ``(Te, rho)`` 二维的字段名。"""
    if table is None:
        return None
    for nm in cands:
        if nm not in table.fields:
            continue
        sh = table.field_shape.get(nm)
        if sh and len(sh) == 2:
            return nm
    # 退一步：任意二维字段
    for nm in table.fields:
        sh = table.field_shape.get(nm)
        if sh and len(sh) == 2:
            return nm
    return None


# ── 风格硬约束（不依赖具体族数据） ───────────────────────────────
def test_plot_style_constants_meet_ppt_requirements():
    """``config`` 里的绘图常量必须满足 PPT 演讲级要求。"""
    expect(config.PLOT_DPI >= 450, f"DPI={config.PLOT_DPI} < 450")
    for nm in ("PLOT_TITLE_FONTSIZE", "PLOT_LABEL_FONTSIZE",
               "PLOT_TICK_FONTSIZE", "PLOT_LEGEND_FONTSIZE"):
        v = getattr(config, nm, None)
        expect(v is not None and v > 18, f"{nm}={v} 未 > 18pt")
    expect(config.PLOT_LINEWIDTH >= 2.0,
           f"linewidth={config.PLOT_LINEWIDTH} < 2.0")
    expect(config.PLOT_MARKERSIZE >= 8.0,
           f"markersize={config.PLOT_MARKERSIZE} < 8.0")


def test_apply_style_forces_ascii_font_stack():
    """``apply_style`` 应设置 ASCII 字体栈（防 LaTeX 缺字导致方块）。"""
    from eosop_pro.plotting.style import apply_style
    import matplotlib
    matplotlib.use("Agg")
    plt = apply_style()
    fam = plt.rcParams.get("font.family")
    expect(fam is not None, "font.family 未设置")
    # 字体栈里不得出现非 ASCII 名称
    stack = fam if isinstance(fam, (list, tuple)) else [fam]
    for f in stack:
        expect(str(f).isascii(), f"字体名含非 ASCII: {f!r}")


# ── 二维不透明度热图 ────────────────────────────────────────────
def test_opacity_heatmap_renders_for_ledcop_atomic():
    """``ledcop_atomic`` 的 Ross/Planck 应能画热图并落盘。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap
    t = _first("ledcop_atomic")
    if t is None:
        return
    nm = _pick_2d(t, "Ross", "Rosseland", "Planck", "kappa", "kappa_g")
    if nm is None:
        return
    out = tmp_dir() / "fam_ledcop_atomic_opacity.png"
    fig = plot_opacity_heatmap(t, nm, out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    expect(out.stat().st_size > 2000, f"PNG 过小: {out.stat().st_size}")
    return fig


def test_opacity_heatmap_renders_for_multi_opacity():
    """``multi_opacity``（多群）应能画热图。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap
    t = _first("multi_opacity")
    if t is None:
        return
    nm = _pick_2d(t, "kappa_g", "kappa", "Ross", "Planck")
    if nm is None:
        return
    out = tmp_dir() / "fam_multi_opacity_heatmap.png"
    plot_opacity_heatmap(t, nm, out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return fig if False else None


def test_opacity_heatmap_renders_for_sesame_opacity_dat():
    """``sesame_dat`` 样品（真实是 hyades OPACITY 表）应能画热图。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap
    t = _first("sesame_dat")
    if t is None:
        return
    nm = _pick_2d(t, "Rosseland", "Ross", "Planck", "kappa")
    if nm is None:
        return
    out = tmp_dir() / "fam_sesame_opacity_heatmap.png"
    plot_opacity_heatmap(t, nm, out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


def _close(fig) -> None:
    """★ 用完即关 figure。

    ``run_all.py`` 在**同一进程**里顺序执行所有测试模块 —— 不关的话，
    figure 会累积到后续模块的 ``test_directory_batch_no_figure_leak``
    （期望全局 figure 数 == 0），造成跨文件假失败。
    """
    from eosop_pro.plotting.qa_plots import _plt
    _plt().close(fig)


def test_all_2d_opacity_families_produce_nonempty_png():
    """汇总：所有可画二维图的族都应产出非空 PNG，并逐一 ASCII 合规。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap, plot_zeff
    from eosop_pro.plotting.style import all_text_ascii
    made = 0
    for fam in ("ledcop_atomic", "multi_opacity", "sesame_dat"):
        t = _first(fam)
        if t is None:
            continue
        nm = _pick_2d(t, "Ross", "Rosseland", "Planck", "kappa", "kappa_g")
        if nm is None:
            continue
        out = tmp_dir() / f"fam2d_{fam}.png"
        fig = plot_opacity_heatmap(t, nm)          # 不落盘 -> 保留 fig 供检查
        ok, bad = all_text_ascii(fig)
        expect(ok, f"{fam} 图含非 ASCII 文本: {bad[:3]}")
        fig.savefig(out, dpi=config.PLOT_DPI, bbox_inches="tight")
        expect(out.stat().st_size > 2000, f"{fam} PNG 过小")
        _close(fig)
        made += 1
    # alleast one should be drawn if any data present
    if made == 0:
        return
    # zeff 单独一族
    t = _first("ledcop_zeff")
    if t is not None:
        nm = _pick_2d(t, "Z", "Zeff")
        if nm:
            _close(plot_zeff(t, nm))


# ── EOS 等密度线 ────────────────────────────────────────────────
def test_eos_isobars_render_for_mpqeos():
    """``mpqeos``（``rho``/``Te`` 基）应能画等密度线。"""
    from eosop_pro.plotting.qa_plots import plot_eos_isobars
    t = _first("mpqeos")
    if t is None:
        return
    nm = _pick_2d(t, "P", "E", "Z")
    if nm is None:
        return
    out = tmp_dir() / "fam_mpqeos_isobars.png"
    plot_eos_isobars(t, nm, out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


def test_eos_isobars_render_for_hyades_eos():
    """``hyades_eos`` 应能画等密度线。"""
    from eosop_pro.plotting.qa_plots import plot_eos_isobars
    t = _first("hyades_eos")
    if t is None:
        return
    nm = _pick_2d(t, "P", "E")
    if nm is None:
        return
    out = tmp_dir() / "fam_hyades_eos_isobars.png"
    plot_eos_isobars(t, nm, out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


def test_eos_isobars_rejects_table_without_Te_axis():
    """⚠️ 记录已知局限：``multi_inverted_eos`` 的轴是 ``(de, rho)`` 而非
    ``(rho, Te)``，``plot_eos_isobars`` 会 ``ValueError``。

    这不是缺陷 —— F1 表的温度在**场**里（``T``）而非轴上。本测试把该
    行为**显式锁定**，避免将来误判为 bug 而错误"修复"。
    """
    from eosop_pro.plotting.qa_plots import plot_eos_isobars
    t = _first("multi_inverted_eos")
    if t is None:
        return
    if "Te" in t.axes:
        return                       # 若将来归一化到 Te，则跳过
    raised = False
    try:
        plot_eos_isobars(t, "P" if "P" in t.fields else "E")
    except ValueError:
        raised = True
    expect(raised, "无 Te 轴的表应明确 ValueError，而非静默出图")


# ── 一维曲线 ────────────────────────────────────────────────────
def test_loglog_curve_renders_for_coldopacity():
    """``coldopacity``（1D）应能画 log-log 曲线。"""
    from eosop_pro.plotting.qa_plots import plot_loglog_curve
    t = _first("coldopacity")
    if t is None:
        return
    ax = t.axes.get("#Eph")
    if ax is None or not t.fields:
        return
    nm = next(iter(t.fields))
    out = tmp_dir() / "fam_coldopacity_curve.png"
    # 标签走控制字典（意义/单位/uk,uv 标记实时同步，第十二轮裁定）
    plot_loglog_curve(list(ax), list(t.fields[nm]),
                      xlabel=field_label("coldopacity", "#Eph",
                                         parser_unit=t.axis_units.get("#Eph", "")),
                      ylabel=field_label("coldopacity", nm,
                                         parser_unit=t.field_units.get(nm, "")),
                      title=f"{t.table_key}: cold opacity", out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


def test_loglog_curve_renders_for_hugoniot():
    """``hugoniot`` 的 ``P`` vs ``Rho`` 应能画 log-log 曲线。"""
    from eosop_pro.plotting.qa_plots import plot_loglog_curve
    t = _first("hugoniot")
    if t is None:
        return
    rho = t.axes.get("Rho")
    if rho is None:
        return
    nm = "P" if "P" in t.fields else (next(iter(t.fields)) if t.fields else None)
    if nm is None:
        return
    out = tmp_dir() / "fam_hugoniot_curve.png"
    # 标签走控制字典（hugoniot 单位逐文件可变：实测单位优先）
    plot_loglog_curve(list(rho), list(t.fields[nm]),
                      xlabel=field_label("hugoniot", "Rho",
                                         parser_unit=t.axis_units.get("Rho", "")),
                      ylabel=field_label("hugoniot", nm,
                                         parser_unit=t.field_units.get(nm, "")),
                      title=f"{t.table_key}: Hugoniot", out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


def test_generic_curve_multicolumn_renders():
    """``generic_curve`` 多列数据应至少能画一列。"""
    from eosop_pro.plotting.qa_plots import plot_loglog_curve
    t = _first("generic_curve")
    if t is None:
        return
    ax = t.axes.get("x")
    if ax is None or not t.fields:
        return
    nm = sorted(t.fields)[0]
    vals = list(t.fields[nm])
    if len(vals) != len(list(ax)):
        return
    out = tmp_dir() / "fam_generic_curve.png"
    # 兜底族无登记语义：field_label 回退列名本身 + uk,uv 标记（不猜）
    plot_loglog_curve(list(ax), vals,
                      xlabel=field_label("generic_curve", "x"),
                      ylabel=field_label("generic_curve", nm),
                      title=f"{t.table_key}: {nm}", out_path=out)
    expect(out.is_file(), f"{out} 未生成")
    return None


# ── 图对象结构断言 ──────────────────────────────────────────────
def test_rendered_figure_has_title_and_axes_labels():
    """出图必须带 title + x/y label（否则不满足演讲级要求）。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap
    t = _first("ledcop_atomic")
    if t is None:
        return
    nm = _pick_2d(t, "Ross", "Planck", "kappa")
    if nm is None:
        return
    fig = plot_opacity_heatmap(t, nm)
    ax = fig.axes[0]
    expect(ax.get_title(), "缺 title")
    expect(ax.get_xlabel(), "缺 xlabel")
    expect(ax.get_ylabel(), "缺 ylabel")
    _close(fig)
    return None


def test_rendered_tick_labels_meet_min_fontsize():
    """刻度/标题字号必须 > 18pt（实测量取）。"""
    from eosop_pro.plotting.qa_plots import plot_opacity_heatmap
    t = _first("ledcop_atomic")
    if t is None:
        return
    nm = _pick_2d(t, "Ross", "Planck", "kappa")
    if nm is None:
        return
    fig = plot_opacity_heatmap(t, nm)
    ax = fig.axes[0]
    sizes = [lb.get_fontsize() for lb in ax.get_xticklabels()]
    sizes += [lb.get_fontsize() for lb in ax.get_yticklabels()]
    sizes = [s for s in sizes if s]
    if sizes:
        expect(min(sizes) > 18, f"最小刻度字号 {min(sizes)} 未 > 18pt")
        expect(ax.title.get_fontsize() > 18,
               f"标题字号 {ax.title.get_fontsize()} 未 > 18pt")
    _close(fig)
    return None


def test_save_fig_rejects_non_ascii_text():
    """``save_fig`` 应拒绝含非 ASCII 的图（守护绘图规约）。"""
    from eosop_pro.plotting.qa_plots import save_fig, _plt
    from eosop_pro.plotting.style import apply_style
    apply_style()
    P = _plt()
    fig, ax = P.subplots()
    ax.set_title("Chinese title 中文")
    out = tmp_dir() / "fam_should_not_exist.png"
    raised = False
    try:
        save_fig(fig, out)
    except AssertionError:
        raised = True
    finally:
        _close(fig)
    expect(raised, "含非 ASCII 的图未被 save_fig 拒绝")
    expect(not out.exists(), f"被拒绝的图仍落盘: {out}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
