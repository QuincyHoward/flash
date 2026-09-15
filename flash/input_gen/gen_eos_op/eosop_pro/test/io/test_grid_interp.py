"""A5 —— 网格 / 插值 / 单位换算测试。

覆盖三个模块：``grid.monotonic`` / ``grid.unified_grid`` / ``grid.interpolate``。

关键断言
* 解析解 ``v = rho^a · Te^b`` 在 log-log 双线性插值下误差 < 1e-10
* 越界点**全部**为 NaN（不是 0、不是 clamp）
* ``nion_Te`` 的 x 变换与其反变换往返误差 < 1e-12
* 重复点/非单调点在 ``policy="error"`` 下必须报错
"""

import math

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
from _runner import expect, expect_almost, expect_eq, expect_in, main

from eosop_pro import config
from eosop_pro.grid import interpolate as ip
from eosop_pro.grid import monotonic as mo
from eosop_pro.grid import unified_grid as ug
from eosop_pro.grid.unified_grid import (GRID_IDS, build_all_grids, build_grid,
                                           build_grid_for_tables, data_ranges,
                                           rho_from_x, x_from_rho)


# ── monotonic ─────────────────────────────────────────────────
def test_diagnose_increasing_clean():
    d = mo.diagnose_axis([1.0, 2.0, 4.0, 8.0])
    expect(d.is_increasing and d.clean, d.describe())


def test_diagnose_log_uniform():
    d = mo.diagnose_axis([1.0, 10.0, 100.0, 1000.0])
    expect(d.is_log_uniform is True, d.describe())


def test_duplicates_detected_and_error_policy_raises():
    xs = [1.0, 2.0, 2.0, 3.0]
    d = mo.diagnose_axis(xs)
    expect(len(d.duplicates) >= 1, f"应检出重复点，实测 {d.describe()}")
    raised = False
    try:
        mo.repair_axis(xs, policy="error")
    except ValueError as exc:
        raised = True
        expect("dup_idx" in str(exc), f"错误信息应含索引，实测 {exc}")
    expect(raised, "policy=error 必须报错（默认不静默修复）")


def test_non_monotonic_detected():
    d = mo.diagnose_axis([1.0, 3.0, 2.0, 4.0])
    expect(len(d.non_monotonic) >= 1, d.describe())


def test_repair_policies_are_explicit():
    xs = [1.0, 2.0, 2.0, 3.0]
    fixed, notes = mo.repair_axis(xs, policy="keep_last")
    expect(len(fixed) < len(xs), f"keep_last 应去重，实测 {fixed}")
    expect(any("repair policy" in n for n in notes), f"必须留痕，实测 {notes}")
    avg, notes2 = mo.repair_axis(xs, policy="average")
    expect(len(avg) < len(xs), f"average 应合并，实测 {avg}")
    expect(all(avg[i] <= avg[i + 1] for i in range(len(avg) - 1)), "结果应递增")


def test_make_log_uniform_endpoints():
    g = mo.make_log_uniform(1e-6, 1e2, 9)
    expect_eq(len(g), 9)
    expect_almost(g[0], 1e-6, 1e-18)
    expect_almost(g[-1], 1e2, 1e-12)
    lg = [math.log10(v) for v in g]
    step = lg[1] - lg[0]
    expect(all(abs((lg[i] - lg[i - 1]) - step) < 1e-9 for i in range(1, len(lg))),
           "应 log10 等距")


# ── unified_grid ──────────────────────────────────────────────
def test_two_grids_share_Te_axis():
    gs = build_all_grids([], A=27.0, n_x=16, n_Te=12)
    expect_eq(tuple(gs), ("rho_Te", "nion_Te"))
    a, b = gs["rho_Te"], gs["nion_Te"]
    expect_eq(a.Te, b.Te, "两套网格必须共用同一条 Te 轴")
    expect(a.x_axis == "rho" and b.x_axis == "n_ion")


def test_nion_conversion_is_one_to_one():
    A = 26.982
    for rho in (1e-6, 1.0, 2.7, 1e3):
        x = x_from_rho("nion_Te", rho, A)
        back = rho_from_x("nion_Te", x, A)
        expect(abs(back - rho) / rho < 1e-12,
               f"往返误差过大：rho={rho} -> x={x} -> {back}")
    # 量级合理性：固体 Al 的离子数密度 ~6e22 /cm3
    n = x_from_rho("nion_Te", 2.7, A)
    expect(5e22 < n < 7e22, f"Al 离子数密度应在 6e22 量级，实测 {n:.3g}")


def test_rho_grid_identity_transform():
    expect_eq(x_from_rho("rho_Te", 4.2, None), 4.2)
    expect_eq(rho_from_x("rho_Te", 4.2, None), 4.2)


def test_nele_grid_not_implemented_raises():
    """``(n_ele, Te)`` 本轮**不实现** —— 接口明确报错而不是返回错值。"""
    raised = False
    try:
        x_from_rho("nele_Te", 1.0, 27.0)
    except KeyError:
        raised = True
    expect(raised, "nele_Te 应明确报错（后补项）")


def test_grid_attrs_and_ranges():
    g = build_grid("rho_Te", rho_range=(1e-6, 1e2), Te_range=(0.1, 1e5),
                   n_x=32, n_Te=24)
    expect_eq(g.n_x, 32)
    expect_eq(g.n_Te, 24)
    for k in ("x_axis", "x_min", "x_max", "n_x", "Te_min_eV", "Te_max_eV",
              "n_Te", "spacing", "nan_semantics"):
        expect(k in g.attrs, f"attrs 缺 {k}")
    expect_eq(g.attrs["nan_semantics"], "out_of_range")


def test_data_ranges_intersection():
    class T:
        def __init__(self, rho, Te):
            self.axes = {"rho": rho, "Te": Te}
    r = data_ranges([T([1.0, 10.0], [1.0, 100.0]), T([2.0, 5.0], [10.0, 50.0])])
    expect_eq(r["rho"], (1.0, 10.0))
    expect_eq(r["Te"], (1.0, 100.0))


# ── interpolate ───────────────────────────────────────────────
def test_analytic_loglog_exactness():
    """解析解 ``v = rho^a · Te^b`` 在 log-log 双线性下应**精确**复现。"""
    a, b = 0.8, -0.5
    rho = [10.0 ** (-6 + 0.5 * i) for i in range(17)]      # log10 等距
    Te = [10.0 ** (-1 + 0.3 * j) for j in range(21)]
    import numpy as np
    R, T = np.meshgrid(rho, Te)
    V = (R ** a) * (T ** b)
    rho_q = [10.0 ** (-5 + 0.25 * i) for i in range(9)]
    Te_q = [10.0 ** (0 + 0.2 * j) for j in range(11)]
    res = ip.resample_2d(rho, Te, V, rho_q, Te_q, logs=("x", "y"),
                         log_value=True)
    Rq, Tq = np.meshgrid(rho_q, Te_q)
    exact = (Rq ** a) * (Tq ** b)
    err = np.nanmax(np.abs(res.values - exact) / np.abs(exact))
    expect(err < 1e-10, f"log-log 双线性误差应 <1e-10，实测 {err:.3e}")
    expect_eq(res.out_of_range, 0, "目标点在范围内 → 不应有越界")


def test_out_of_range_is_nan_not_zero():
    import numpy as np
    rho = [1.0, 10.0]
    Te = [1.0, 10.0]
    V = np.array([[1.0, 2.0], [3.0, 4.0]])
    res = ip.resample_2d(rho, Te, V, [0.1, 1.0, 100.0], [1.0, 10.0],
                         logs=(), log_value=False)
    v = res.values
    expect(np.isnan(v[0, 0]), "左侧越界应为 NaN")
    expect(np.isnan(v[1, 2]), "右侧越界应为 NaN")
    expect(not np.isnan(v[0, 1]), "边界内不应为 NaN")
    expect(res.out_of_range >= 2, f"越界计数，实测 {res.out_of_range}")
    expect(res.coverage < 1.0)


def test_clamp_extrapolation_option():
    import numpy as np
    rho = [1.0, 10.0]
    Te = [1.0, 10.0]
    V = np.array([[1.0, 2.0], [3.0, 4.0]])
    res = ip.resample_2d(rho, Te, V, [0.1, 100.0], [1.0], logs=(),
                         extrapolation="clamp")
    expect(not np.isnan(res.values).any(), "clamp 不应产生 NaN")
    expect_almost(res.values[0, 0], 1.0, 1e-12, "左侧 clamp 到边界值")
    expect_almost(res.values[0, 1], 2.0, 1e-12, "右侧 clamp 到边界值")


def test_resample_1d_log_space():
    xs = [1.0, 10.0, 100.0]
    vs = [1.0, 10.0, 100.0]         # v = x  -> log v = log x
    res = ip.resample_1d(xs, vs, [math.sqrt(10.0)], log_x=True, log_value=True)
    expect_almost(res.values[0], math.sqrt(10.0), 1e-9)


# ══════════════════════════════════════════════════════════════
# ★ 退化轴范围：宁可缺轨，不造假网格
# ══════════════════════════════════════════════════════════════
def test_can_build_rejects_degenerate_and_nonpositive():
    """``can_build`` 的判据：正、有限、**严格递增**。"""
    expect(not ug.can_build((1.0, 1.0)), "单点范围必须被拒绝")
    expect(not ug.can_build((10.0, 1.0)), "递减范围必须被拒绝")
    expect(not ug.can_build((0.0, 10.0)), "非正下界必须被拒绝")
    expect(not ug.can_build((-5.0, 10.0)), "负下界必须被拒绝")
    expect(not ug.can_build((float("inf"), float("inf"))), "非有限必须被拒绝")
    expect(not ug.can_build((float("nan"), 1.0)), "NaN 必须被拒绝")
    expect(ug.can_build((1e-6, 1e2)), "正常范围应通过")


def test_degenerate_table_yields_no_grid_instead_of_raising():
    """★ 回归：``Mo_Ideal_Gas`` 的 rho 网格是 ``[0.0, 1.0]``，
    过滤非正值后范围退化成 ``(1.0, 1.0)``。

    旧实现直接在 ``build_grid`` 里抛 ``ValueError: invalid rho range`` ——
    这会让**整批** ``convert-all`` 中断（实测 700/1214 处崩溃）。
    新实现返回空 dict，让 h5 少一条 unified 轨。
    """
    from eosop_pro.registry import declared_types as dt_mod
    from eosop_pro.registry.dispatch import parse_declared

    rel = "Thermos/mat_Mo/Mo_Ideal_Gas"
    out = parse_declared(rel, dt_mod.declare(rel))
    expect(out.ok, f"该文件应能解析（F1 理想气体），实测 {out.snapshot.status}")
    grids = ug.build_all_grids(out.tables)
    expect_eq(grids, {}, f"退化范围应返回空 grid dict，实测 {list(grids)}")

    g = ug.build_grid_for_tables(out.tables, gid="rho_Te")
    expect(g is None, "build_grid_for_tables 对退化范围应返回 None")


def test_build_grid_still_raises_on_direct_bad_input():
    """★ 直接调用 ``build_grid`` 仍应抛错 —— 严格性只在"显式给坏参数"时保留。"""
    try:
        ug.build_grid("rho_Te", rho_range=(1.0, 1.0), Te_range=(1.0, 10.0))
    except ValueError as exc:
        expect_in("invalid rho range", str(exc))
    else:
        raise AssertionError("build_grid 对坏范围应抛 ValueError")


def test_healthy_table_still_gets_both_grids():
    """★ 回归保护：修好退化处理之后，正常表的两套网格不能少。"""
    from eosop_pro.registry import declared_types as dt_mod
    from eosop_pro.registry.dispatch import parse_declared

    out = parse_declared("mat_Al-1.0/AL_eos", dt_mod.declare("mat_Al-1.0/AL_eos"))
    grids = ug.build_all_grids(out.tables, A=26.982)
    expect_eq(sorted(grids), ["nion_Te", "rho_Te"])
    for gid in ("rho_Te", "nion_Te"):
        expect_eq(len(grids[gid].x), config.N_X_UNIFIED)
        expect_eq(len(grids[gid].Te), config.N_TE_UNIFIED)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
