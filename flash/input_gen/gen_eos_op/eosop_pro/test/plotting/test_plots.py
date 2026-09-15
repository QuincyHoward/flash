"""出图测试 —— 逐条断言 PPT / 演讲级要求。

必须满足（可测）
----------------
* ``figure.dpi`` / ``savefig.dpi`` ≥ **450**
* title ≥ **24** pt，轴标签 ≥ **20** pt，刻度 ≥ **20** pt，图例 ≥ **18** pt
* ``lines.linewidth`` ≥ 2，``lines.markersize`` ≥ 8
* **所有可见文本纯 ASCII**（正则 ``^[\\x00-\\x7F]*$``）—— 中文会在 PPT 里乱码
* 真实数据出图不抛异常，且 PNG 落盘
"""

import tempfile
from pathlib import Path

import sys
import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import config
from eosop_pro.parsers import hyades_eos as f3
from eosop_pro.parsers import multi_opacity as f2
from eosop_pro.plotting import qa_plots
from eosop_pro.plotting.style import (ASCII_RE, all_text_ascii, apply_style,
                                        style_report)


def test_rcparams_meet_ppt_requirements():
    apply_style()
    s = style_report()
    expect(s["figure.dpi"] >= config.PLOT_DPI >= 450, f"dpi={s['figure.dpi']}")
    expect(s["axes.titlesize"] >= 24, f"title={s['axes.titlesize']}")
    expect(s["axes.labelsize"] >= 20, f"label={s['axes.labelsize']}")
    expect(s["xtick.labelsize"] >= 20, f"tick={s['xtick.labelsize']}")
    expect(s["legend.fontsize"] > 18, f"legend={s['legend.fontsize']} 应 > 18")
    expect(s["lines.linewidth"] >= 2, f"lw={s['lines.linewidth']}")
    expect(s["lines.markersize"] >= 8, f"ms={s['lines.markersize']}")


def test_ascii_regex_semantics():
    expect(ASCII_RE.match("Te_eV / rho") is not None)
    expect(ASCII_RE.match("rho [g/cm^3]") is not None)
    expect(ASCII_RE.match("温度") is None, "非 ASCII 必须被检出")
    expect(ASCII_RE.match("T_e (eV)") is not None)


def test_eos_isobars_figure_ascii_and_dpi():
    t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    fig = qa_plots.plot_eos_isobars(t, "P")
    expect(fig.dpi >= 450, f"fig.dpi={fig.dpi}")
    ok, bad = all_text_ascii(fig)
    expect(ok, f"图中不应有非 ASCII 文本，实测 {bad[:4]}")
    ax = fig.get_axes()[0]
    expect(ax.get_title() != "", "应有标题")
    expect(ax.get_xlabel() != "" and ax.get_ylabel() != "", "应有轴标签")
    expect(ax.get_legend() is not None, "应有图例")
    del fig


def test_opacity_heatmap_figure():
    t = f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "x")
    fig = qa_plots.plot_opacity_heatmap(t, "kappa")
    ok, bad = all_text_ascii(fig)
    expect(ok, f"非 ASCII 文本 {bad[:4]}")
    expect(len(fig.axes) >= 2, "热图应带 colorbar")
    del fig


def test_zeff_figure():
    t = f2.parse(config.MATTER("mat_Au-1.0/AU_op03z"), "x")
    fig = qa_plots.plot_zeff(t, "Z")
    ok, _bad = all_text_ascii(fig)
    expect(ok)
    del fig


def test_loglog_curve_and_save(tmp=None):
    with tempfile.TemporaryDirectory() as td:
        t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
        p = Path(td) / "figs" / "isobars.png"
        fig = qa_plots.plot_eos_isobars(t, "P", out_path=p)
        expect(p.exists(), f"应写出 PNG: {p}")
        expect(p.stat().st_size > 5000, f"PNG 大小应 >5KB，实测 {p.stat().st_size}")
        del fig


def test_font_family_is_ascii_safe():
    apply_style()
    s = style_report()
    fam = str(s["font.family"])
    expect("DejaVu" in fam or "ASCII" in fam or "Sans" in fam,
           f"应使用 ASCII 安全字体，实测 {fam}")


# ══════════════════════════════════════════════════════════════
# ★ figure 生命周期与 log 边界（批量出图的两个实测问题）
# ══════════════════════════════════════════════════════════════
def test_saved_figures_are_closed_not_leaked():
    """★ 回归：``plot-all`` 出 60 组图时报
    ``RuntimeWarning: More than 20 figures have been opened``。

    修法：**传了 out_path**（调用方不再需要 figure）时关闭。
    """
    import matplotlib.pyplot as plt

    plt.close("all")
    t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    with tempfile.TemporaryDirectory() as td:
        for i in range(30):
            qa_plots.plot_eos_isobars(t, "P", out_path=Path(td) / f"p{i}.png")
        expect_eq(len(plt.get_fignums()), 0,
                  "落盘后应关闭 figure，否则 pyplot 会累积 30 个")
    plt.close("all")


def test_figures_kept_when_no_out_path():
    """不传 out_path 时**不关闭** —— 测试需要拿回 figure 继续检查。"""
    import matplotlib.pyplot as plt

    plt.close("all")
    t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    for _ in range(3):
        fig = qa_plots.plot_eos_isobars(t, "P")
        expect(fig is not None)
    expect_eq(len(plt.get_fignums()), 3, "未落盘时应保留 figure 供调用方使用")
    plt.close("all")


def test_isobars_tolerates_rho_containing_zero():
    """★ 回归：F1 的 ``rho[0] == 0.0`` 会让 ``log10`` 触发
    ``divide by zero encountered in log10`` RuntimeWarning。

    修法：只在**正 rho** 上挑等密度线。
    """
    import warnings

    import matplotlib.pyplot as plt
    import numpy as np

    plt.close("all")
    t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    # 人工把第一个 rho 改成 0，模拟 F1 的真实情形
    t.axes["rho"] = [0.0] + list(t.axes["rho"][1:])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        fig = qa_plots.plot_eos_isobars(t, "P")
    ax = fig.get_axes()[0]
    expect(ax.get_legend() is not None, "仍应画出等密度线")
    for line in ax.get_lines():
        lbl = line.get_label()
        expect(not lbl.startswith("rho = 0 "),
               f"不应挑到 rho==0 的列，实测 label={lbl!r}")
    plt.close("all")


def test_isobars_rejects_all_nonpositive_rho():
    """全非正 rho → 明确抛错，不画出空图。"""
    import matplotlib.pyplot as plt

    plt.close("all")
    t = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    t.axes["rho"] = [0.0] * len(t.axes["rho"])
    try:
        qa_plots.plot_eos_isobars(t, "P")
    except ValueError as exc:
        expect_in("no positive rho", str(exc))
    else:
        raise AssertionError("全非正 rho 应抛 ValueError")
    plt.close("all")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
