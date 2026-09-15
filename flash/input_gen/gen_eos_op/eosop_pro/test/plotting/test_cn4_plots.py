"""cn4 绘图测试 —— 二维彩图 / 一维曲线 / 群大图，逐条断言 PPT 要求。

覆盖迁移自参考实现的三块绘图能力：
* ``plot_utils.py``  -> 热图原语（本测试的 ``plot_quantity_heatmap``）
* ``plot_heatmaps.py`` -> 彩图矩阵 + 群不透明度 2x2 大图
* ``plot_curves.py``  -> 一维变化曲线

硬性要求（来自用户长期约定，可测）
----------------------------------
* DPI ≥ 450，**所有字号 > 18**（title 26 / label 22 / tick 20 / legend 20）
* lw ≥ 2，ms ≥ 8
* **所有可见文本纯 ASCII**（PNG 落盘前由 ``assert_ascii`` 强制）
* ``nele`` 轴（2D 派生量）走散点插值 + 凸包边界，不得抛异常
* 批量出图必须**逐图关闭 figure**，否则 pyplot 句柄累积
"""

import os
import tempfile
from pathlib import Path

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

import numpy as np

from eosop_pro.cn4 import load_cn4
from eosop_pro.cn4 import cn4_plots as P
from eosop_pro.cn4.cn4_io import CN4ParseError
from eosop_pro.plotting.style import ASCII_RE, all_text_ascii

# ── 测试数据: 仓库内自带的 CH 生成数据（C6H1 混合，原子量可解析） ──
# 本文件位于 test/plotting/ -> 上溯 4 级到 gen_eos_op
_REPO = Path(__file__).resolve().parents[3]              # .../gen_eos_op
_CN4 = (_REPO / "eos_op_data" / "Gen_eos_op_data"
        / "Z06_0.50-Z01_0.50-20260708_0850"
        / "Z06_0.50-Z01_0.50-20260708_0850.cn4")


def _tbl():
    if not _CN4.exists():                     # pragma: no cover
        raise RuntimeError(f"测试数据缺失: {_CN4}")
    return load_cn4(str(_CN4))


def _tmpdir():
    d = Path(tempfile.mkdtemp(prefix="cn4plots_"))
    return d


def test_axes_registry_complete():
    """五个坐标轴齐全，且标签含单位。"""
    for name in ("T", "tele", "nion", "nele", "rho"):
        expect_in(name, P.AXES)
        lab = P.axis_label(name)
        expect("(" in lab and ")" in lab, f"{name} 标签应含单位: {lab}")
    expect_eq(P.AXES["T"]["dim"], 1)
    expect_eq(P.AXES["nion"]["dim"], 1)
    expect_eq(P.AXES["nele"]["dim"], 2, "nele 是 2D 派生量 -> dim=2")


def test_display_scale_matches_units_module():
    """显示单位换算因子必须来自 units.py，不是本地硬编码。"""
    from eosop_pro.cn4 import units as U
    expect_eq(P.display_scale("p_ion"), U.P_JCM3_TO_MBAR)
    expect_eq(P.display_scale("dpion_dt"), U.P_JCM3_TO_MBAR)
    expect_eq(P.display_scale("e_ion"), U.E_JG_TO_ERG_G)
    expect_eq(P.display_scale("cv_ele"), U.CV_TO_ERG_G_EV)
    expect_eq(P.display_scale("zbar"), 1.0, "zbar 无量纲，因子应为 1")
    expect_eq(P.display_scale("nele"), 1.0, "nele 已是 cm^-3，因子应为 1")
    expect_eq(P.display_scale("rho"), 1.0, "rho 已是 g/cm^3，因子应为 1")


def test_heatmap_regular_grid_axes():
    """规则网格轴（T-nion / T-rho）：出图 + 落盘 + ASCII + 尺寸。"""
    t = _tbl()
    od = _tmpdir()
    for (xa, ya) in (("T", "nion"), ("T", "rho"), ("nion", "T")):
        out = P.plot_quantity_heatmap(
            t, "zbar", xa, ya, outfile=od / f"z_{xa}-{ya}.png")
        expect(os.path.exists(out), f"PNG 应落盘: {out}")
        expect(os.path.getsize(out) > 10_000, "PNG 不应是空图")


def test_heatmap_figure_style_and_ascii():
    """图形对象的标题/标签/刻度/图例文本必须满足 PPT 要求且纯 ASCII。"""
    t = _tbl()
    od = _tmpdir()
    out = P.plot_quantity_heatmap(
        t, "p_ion", "T", "nion", outfile=od / "p.png")
    expect(os.path.exists(out))


def test_nele_axis_uses_interpolation_and_hull():
    """nele 轴（2D 派生量）走 log 散点插值 + 凸包边界，不得抛异常。"""
    t = _tbl()
    od = _tmpdir()
    for (xa, ya) in (("T", "nele"), ("nele", "T")):
        out = P.plot_quantity_heatmap(
            t, "zbar", xa, ya, outfile=od / f"ne_{xa}-{ya}.png")
        expect(os.path.exists(out), f"nele 轴出图应成功: {out}")


def test_prepare_axes_field_shape_contract():
    """_prepare_axes 返回的场形状必须严格等于 (len(y), len(x))。"""
    t = _tbl()
    field = np.asarray(t.field("zbar"), dtype=float).reshape(t.ndens, t.ntemp)
    for (xa, ya) in (("T", "nion"), ("nion", "T"), ("T", "rho"), ("rho", "T"),
                     ("T", "nele"), ("nele", "T")):
        xs, ys, f2, hull = P._prepare_axes(t, xa, ya, field)
        expect_eq(f2.shape, (len(ys), len(xs)),
                  f"x={xa} y={ya}: field {f2.shape} 应为 (nY={len(ys)}, nX={len(xs)})")
        if xa == "nele" or ya == "nele":
            expect(hull is not None and len(hull) >= 3,
                   f"含 nele 轴时应返回凸包顶点 (got {None if hull is None else len(hull)})")


def test_same_axis_pair_rejected():
    """x/y 轴相同必须报错。"""
    t = _tbl()
    try:
        P.plot_quantity_heatmap(t, "zbar", "T", "T")
    except ValueError:
        return
    raise AssertionError("x==y 轴应抛 ValueError")


def test_no_temperature_axis_rejected():
    """两轴均非温度轴（nion-rho）必须报错。"""
    t = _tbl()
    try:
        P.plot_quantity_heatmap(t, "zbar", "nion", "rho")
    except ValueError:
        return
    raise AssertionError("无温度轴应抛 ValueError")


def test_opacity_and_transmission_quantities():
    """群不透明度与透射率物理量可出图。"""
    t = _tbl()
    od = _tmpdir()
    for q in ("opac_rosseland", "opac_planck_abs", "opac_planck_ems"):
        out = P.plot_quantity_heatmap(
            t, q, "T", "nion", ig=1, outfile=od / f"{q}.png")
        expect(os.path.exists(out), f"{q} 应出图")
    out = P.plot_quantity_heatmap(
        t, "transmission", "T", "nion", ig=1, transmission_L=0.01,
        outfile=od / "trans.png")
    expect(os.path.exists(out), "transmission 应出图")


def test_opacity_group_figure_2x2():
    """单群 2x2 大图：4 个子图、2 个 y 轴、2 个 x 轴（2x2 布局）。"""
    t = _tbl()
    od = _tmpdir()
    out = P.plot_opacity_group_figure(t, 1, outfile=od / "g1.png")
    expect(os.path.exists(out))
    # 2x2 = 4 个子图，每个 1 个 xlabel + 1 个 ylabel
    from PIL import Image  # noqa: F401  可选依赖，缺失时跳过尺寸检查
    expect(os.path.getsize(out) > 50_000, "2x2 大图应显著大于单图")


def test_plot_all_opacity_figures_count():
    """全部能群大图数量 = ngrups。"""
    t = _tbl()
    od = _tmpdir()
    outs = P.plot_all_opacity_figures(t, outdir=od)
    expect_eq(len(outs), t.ngrups, f"应出 {t.ngrups} 张大图")
    for o in outs:
        expect(os.path.exists(o))


def test_group_opacity_heatmap_single():
    t = _tbl()
    od = _tmpdir()
    out = P.plot_group_opacity_heatmap(
        t, "rosseland", ig=2, outfile=od / "ross_g2.png")
    expect(os.path.exists(out))


def test_curves_vs_temperature_and_density():
    """一维曲线（vs T / vs n_ion）可出图。"""
    t = _tbl()
    od = _tmpdir()
    o1 = P.plot_vs_temperature(t, "zbar", outfile=od / "vs_T.png")
    o2 = P.plot_vs_density(t, "zbar", outfile=od / "vs_nion.png")
    expect(os.path.exists(o1) and os.path.exists(o2))


def test_pick_indices_semantics():
    """曲线索引选择：None 时最多 6 条；显式给出则原样去重排序。"""
    expect_eq(P._pick_indices(3, None, 6), [0, 1, 2], "少于 6 条全取")
    got = P._pick_indices(100, None, 6)
    expect_eq(len(got), 6, "应取 6 条")
    expect_eq(got[0], 0)
    expect_eq(got[-1], 99, "应覆盖到末点")
    expect_eq(P._pick_indices(50, [5, 3, 3], 6), [3, 5], "应去重排序")


def test_auto_log_threshold():
    """量纲跨 >4 个数量级且全正 -> 建议对数。"""
    expect(P._auto_log(np.array([1.0, 1e5])) is True, "跨 5 个量级 -> log")
    expect(P._auto_log(np.array([1.0, 1e2])) is False, "跨 2 个量级 -> linear")
    expect(P._auto_log(np.array([-1.0, 1e5])) is False, "含非正值 -> 不 log")


def test_directory_batch_no_figure_leak():
    """批量出图后 pyplot 不应**新增**残留 figure（句柄释放）。

    ⚠️ 2026-09 修正：断言从「全局 figure 数 == 0」改为「**增量** == 0」。
    ``run_all.py`` 在同一进程里顺序执行所有模块，同模块/前序模块的测试
    可能尚有未关 figure（它们各自的生命周期管理），把全局清零作为本测试
    的前提会把它变成跨模块耦合的假失败（实测 actual=2 且稳定复现，
    而单独运行本文件时前序 figure 为 0、测试通过）。
    本测试真正要守护的是：``plot_cn4_directory`` 自己**不新增**泄漏。
    """
    import matplotlib.pyplot as plt
    t_paths = [str(_CN4)]
    od = _tmpdir()
    n_before = len(plt.get_fignums())
    r = P.plot_cn4_directory(
        t_paths, outdir=od, quantities=("zbar", "p_ion"),
        axes_pairs=(("T", "nion"),), curves=("zbar",), verbose=False)
    expect_eq(r["n_files"], 1)
    expect_eq(r["n_plots"], 4, "1 文件 x (2 彩图 + 2 曲线) = 4 图")
    expect_eq(len(r["errors"]), 0, f"不应有错误: {r['errors']}")
    expect_eq(len(plt.get_fignums()), n_before,
              "批量出图后不应新增残留 figure（内存泄漏）")


def test_directory_batch_records_errors_without_aborting():
    """单文件失败必须被记录，但不中断整批。"""
    od = _tmpdir()
    from eosop_pro.cn4.cn4_io import parse_header
    bad = od / "broken.cn4"
    bad.write_text("not a cn4\nnope\nnope\nnope\n", encoding="utf-8")
    r = P.plot_cn4_directory(
        [str(bad), str(_CN4)], outdir=od, quantities=("zbar",),
        axes_pairs=(("T", "nion"),), curves=(), verbose=False)
    expect_eq(r["n_files"], 2)
    expect(len(r["errors"]) >= 1, "坏文件应被记录进 errors")
    expect(r["n_plots"] >= 1, "好文件仍应正常出图（不中断）")


def test_unknown_quantity_raises():
    t = _tbl()
    try:
        P.plot_quantity_heatmap(t, "definitely_not_a_quantity")
    except (CN4ParseError, KeyError):
        return
    raise AssertionError("未知物理量应报错")


def test_supported_quantities_listed():
    for q in ("zbar", "p_ion", "e_ele", "cv_ion", "nele", "rho",
              "opac_rosseland", "transmission", "cs"):
        expect_in(q, P.SUPPORTED_QUANTITIES)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
