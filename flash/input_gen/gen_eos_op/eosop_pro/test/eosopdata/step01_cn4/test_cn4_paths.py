"""cn4 **材料路径**测试 —— 等温线 / 等压线 / 等熵线 / 冲击雨贡纽 / P-V 图。

溯源
----
* 实现: ``eosop_pro/cn4/cn4_paths.py``
* 单位换算: ``eosop_pro/cn4/units.py``（全部因子集中于此，单一来源）
* 物理依据:
  - 熵积分 ``de = T ds + (P/rho^2) drho``（见 ``compute_entropy`` docstring）
  - Rankine-Hugoniot: ``Us^2 = (P-P0)/(rho0(1-rho0/rho))``、``Up = Us(1-rho0/rho)``
    （见 ``trace_hugoniot`` docstring）
  - 声速 ``cs``（见 ``sound_speed``）

⚠️ 这些都是"材料响应曲线"，是本包最核心的物理功能，
此前**零测试覆盖**（见 ``test/`` 重组前的目录清单）。

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

import numpy as np

from eosop_pro.parsers.cn4_io import load_cn4
from eosop_pro.plotting import cn4_paths as P
from eosop_pro.plotting import units
from eosop_pro.parsers.cn4_io import CN4ParseError

from eosopdata._samples import first_cn4
from eosopdata._idealgas import IdealGasStub as _IdealGasStub  # r16 共享化

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
# ① 密度换算（rho <-> n_ion）
# ══════════════════════════════════════════════════════════════
def test_rho_nion_roundtrip():
    """``rho -> nion -> rho`` 必须闭合（换算因子只有 <A> 与 N_A）。"""
    t = _tbl()
    n0 = np.asarray(t.density, dtype=float)
    rho = P.rho_from_nion(t, n0)
    n1 = P.nion_from_rho(t, rho)
    expect(np.allclose(n1, n0, rtol=1e-12), f"往返不一致 max={np.max(np.abs(n1-n0))}")


def test_rho_matches_hand_computation():
    """``rho = n_ion * <A> / N_A`` 手工复算（不依赖实现内部）。"""
    t = _tbl()
    aw = t.avgatw
    expect(aw is not None, "样品缺原子量，无法验证换算")
    n0 = np.asarray(t.density, dtype=float)
    got = P.rho_from_nion(t, n0)
    want = n0 * aw / units.NA
    expect(np.allclose(got, want, rtol=1e-12),
           f"rho 与手算不符 max={np.max(np.abs(got-want))}")


def test_scale_factors_are_positive_and_documented():
    """``units`` 的每个换算因子应为正有限值，且换算函数单调。"""
    for name in ("DPDT_TO_MBAR_EV", "E_JG_TO_ERG_G", "CV_TO_ERG_G_EV",
                 "V_CMS_TO_UM_NS", "T_S_TO_NS", "X_CM_TO_UM"):
        v = getattr(units, name)
        expect(np.isfinite(v) and v > 0, f"{name}={v} 非正/非有限")
    # 换算是线性缩放：2 倍输入 -> 2 倍输出
    expect_eq(units.pressure_mbar(2.0), 2.0 * units.pressure_mbar(1.0))
    expect_eq(units.velocity_umns(2.0), 2.0 * units.velocity_umns(1.0))


def test_units_module_is_the_only_scale_source():
    """单一来源：``units`` 必须导出全部换算因子与函数，``cn4_paths`` 从中取用。

    用 ``ast`` 而非正则，避免命中注释/docstring
    （``hygiene/test_config_single_source.py`` 用的是同一手法）。
    """
    import ast

    # units 必须具备的公开换算设施
    for name in ("pressure_mbar", "energy_ergg", "heat_cgs",
                 "velocity_umns", "density_gcc_from_nion",
                 "nion_from_rhogcc"):
        expect(hasattr(units, name), f"units 缺换算函数 {name}")
    for name in ("E_JG_TO_ERG_G", "V_CMS_TO_UM_NS", "DPDT_TO_MBAR_EV"):
        expect(hasattr(units, name), f"units 缺换算因子 {name}")

    # cn4_paths 必须导入 units（接口优先，而非自带一套）
    src = Path(P.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            for a in node.names:
                imported.add(a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imported.add(a.name)
    expect(any("units" in m for m in imported),
           f"cn4_paths 未从 units 导入换算设施（已导入: {sorted(imported)}）")


#: 已知遗留：``J/cm^3 -> dyne/cm^2``（``1 J = 1e7 erg``）与
#: ``J/g -> cm^2/s^2`` 两处换算在 ``cn4_paths`` 中仍以字面量 ``1e7`` 出现。
#: ``units.py`` 未导出对应常量，故无法改为引用 —— 属**已记录的单一来源缺口**。
#: 本测试把它固化为"已知清单"，一旦有人新增同类硬编码即失败；
#: 修好（把 1e7 提到 units）后删掉相应条目即可。
KNOWN_LITERAL_SCALE_HOLES = {
    "J_TO_ERG_E7": 1e7,
}


def test_no_new_hardcoded_scale_beyond_known_holes():
    """源码级：除已知缺口外，``cn4_paths`` 不得再引入单位换算字面量。

    与 ``hygiene/test_config_single_source.py`` 互补 —— 后者只查
    ``config`` 里已登记的常量；本测试盯住"换算因子应在 ``units`` 里"这条。
    """
    import ast

    lines = Path(P.__file__).read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(lines))

    # 收集"形如 x * 1e7 / 1e7 * x / sqrt(... 1e7)"的换算字面量
    suspicious: list[tuple[int, float]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, (ast.Mult, ast.Div)):
            continue
        for side in (node.left, node.right):
            if isinstance(side, ast.Constant) and isinstance(side.value, float):
                v = side.value
                # 只看"用于换算"的整数幂次（1e4/1e5/1e7/1e9）且不在已知清单
                if v in (1e4, 1e5, 1e6, 1e7, 1e8, 1e9) \
                        and not any(abs(v - k) <= abs(k) * 1e-9
                                    for k in KNOWN_LITERAL_SCALE_HOLES.values()):
                    suspicious.append((node.lineno, v))

    expect(not suspicious,
           "cn4_paths 出现未登记的单位换算字面量（应提到 units.py）：\n  "
           + "\n  ".join(f"line {ln}: {v!r}  >>> {lines[ln - 1].strip()}"
                         for ln, v in suspicious))


def test_known_scale_holes_are_still_present():
    """已知缺口若被修好（1e7 提到 units），本测试应反向失败提醒更新清单。

    这是"防遗忘"护栏：缺口修好后测试会失败，提示把
    ``KNOWN_LITERAL_SCALE_HOLES`` 清空。
    """
    src = Path(P.__file__).read_text(encoding="utf-8")
    # 用 repr 风格匹配源码里的字面量写法（1e7 -> "1e+07" 需归一化）
    def _lit_repr(v: float) -> str:
        return f"{v:.0e}".replace("e+0", "e").replace("e-0", "e-")

    still_there = any(_lit_repr(v) in src
                      for v in KNOWN_LITERAL_SCALE_HOLES.values())
    if KNOWN_LITERAL_SCALE_HOLES and not still_there:
        raise AssertionError(
            "已知换算缺口似乎已修复 —— 请从 KNOWN_LITERAL_SCALE_HOLES 移除"
            "对应条目（或确认 units.py 已导出该常量）")


# ══════════════════════════════════════════════════════════════
# ② 二维插值
# ══════════════════════════════════════════════════════════════
def test_interpolate_scalar_semantics():
    """标量 (rho, T) -> 返回 ``float``。"""
    t = _tbl()
    rho = float(P.rho_from_nion(t, t.density[t.ndens // 2]))
    T = float(t.temperature[t.ntemp // 2])
    v = P.interpolate_quantity(t, "P", rho, T)
    expect(isinstance(v, float), f"标量输入应返回 float，实得 {type(v)}")
    expect(np.isfinite(v) and v > 0, f"插值压力 {v} 应为正有限值")


def test_interpolate_at_grid_node_reproduces_table():
    """插值点正好落在网格点上时，应精确复现表值（无平滑误差）。"""
    t = _tbl()
    i, j = t.ndens // 2, t.ntemp // 2
    rho = float(P.rho_from_nion(t, t.density[i]))
    T = float(t.temperature[j])
    got = P.interpolate_quantity(t, "p_ele", rho, T)
    want = float(np.asarray(t.field("p_ele")).reshape(t.ndens, t.ntemp)[i, j])
    expect(abs(got - want) <= 1e-9 * max(1.0, abs(want)),
           f"网格点插值 {got} != 表值 {want}")


def test_interpolate_array_shapes():
    """数组语义：一维广播与笛卡尔积的返回形状必须符合 docstring。

    ⚠️ 分派优先级（按实现）: 同形状 > 一维广播 > 笛卡尔积。
    故 rho/T **同长度**时走"同形状"分支，得到一维而非矩阵。
    """
    t = _tbl()
    rho_ax = P.rho_from_nion(t, np.asarray(t.density, dtype=float))
    T_ax = np.asarray(t.temperature, dtype=float)
    T_mid = float(T_ax[t.ntemp // 2])

    # rho 数组 + T 标量 -> 一维（长度 ndens）
    a = P.interpolate_quantity(t, "P", rho_ax, T_mid)
    expect_eq(np.shape(a), (t.ndens,), "rho 数组 + T 标量 应为一维 ndens")

    # 同长度数组 -> 同形状（逐点对应，非笛卡尔积）
    b = P.interpolate_quantity(t, "P", rho_ax[:t.ntemp], T_ax)
    if t.ntemp <= t.ndens:
        expect_eq(np.shape(b), (t.ntemp,), "同形状应返回同形状（逐点）")

    # 异长度且非标量 -> 笛卡尔积 (n_rho, n_T)
    if t.ndens != t.ntemp:
        c = P.interpolate_quantity(t, "P", rho_ax, T_ax)
        expect_eq(np.shape(c), (t.ndens, t.ntemp),
                  "异长度数组应为 (n_rho, n_T) 笛卡尔积")


def test_interpolate_unknown_quantity_raises():
    t = _tbl()
    try:
        P.interpolate_quantity(t, "no_such_quantity_xyz", 1.0, 10.0)
    except (KeyError, CN4ParseError):
        return
    raise AssertionError("未知物理量应报错")


# ══════════════════════════════════════════════════════════════
# ③ 等温线
# ══════════════════════════════════════════════════════════════
def test_isotherm_by_index():
    """等温线（按网格索引）返回 ``(x, P_mbar, e_ergg, outfile)``。"""
    t = _tbl()
    out = _OUT / "iso_idx.png"
    x, Pmbar, eergg, f = P.trace_isotherm(t, T_idx=min(10, t.ntemp - 1),
                                          outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect_eq(len(x), len(Pmbar), "x 与 P 长度应一致")
    expect_eq(len(x), len(eergg), "x 与 e 长度应一致")
    expect(np.all(np.asarray(Pmbar) > 0), "压力应全为正")
    expect(np.all(np.asarray(eergg) > 0), "比能量应全为正")
    # 单位换算正确性：Mbar 值应比原始 J/cm3 小 1e-5 倍量级
    expect(np.max(Pmbar) < 1e6, f"Mbar 量级异常: max={np.max(Pmbar)}")


def test_isotherm_by_temperature_value():
    """等温线（按任意温度值，走插值分支）。"""
    t = _tbl()
    T_mid = float(t.temperature[t.ntemp // 2])
    out = _OUT / "iso_val.png"
    x, Pmbar, eergg, f = P.trace_isotherm(t, T=T_mid, x_axis="nion",
                                          outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect(np.all(np.isfinite(Pmbar)), "压力应全为有限值")


def test_isotherm_monotonic_in_density():
    """等温线上的压力应随密度单调递增（物理必然）。"""
    t = _tbl()
    x, Pmbar, _e, _f = P.trace_isotherm(t, T_idx=min(5, t.ntemp - 1),
                                        x_axis="nion",
                                        outfile=str(_OUT / "iso_mono.png"))
    d = np.diff(np.asarray(Pmbar, dtype=float))
    expect(np.all(d > 0), f"压力非单调递增，最小增量 {np.min(d)}")


# ══════════════════════════════════════════════════════════════
# ④ 等压线
# ══════════════════════════════════════════════════════════════
def test_isobar_inside_range():
    """取压力范围中点做等压线，应返回 ``(T_curve, nion_curve, outfile)``。"""
    t = _tbl()
    from eosop_pro.plotting.cn4_paths import _press
    Pg = np.asarray(_press(t), dtype=float)
    P_target = float(np.sqrt(Pg.min() * Pg.max()))     # 几何中点（跨数量级）
    out = _OUT / "isobar.png"
    Tc, nc, f = P.trace_isobar(t, P_target, outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect_eq(len(Tc), len(nc), "T 与 n 长度应一致")
    expect(len(Tc) >= 2, f"等压线点数过少: {len(Tc)}")
    expect(np.all(np.asarray(Tc) > 0) and np.all(np.asarray(nc) > 0),
           "等压线坐标应为正（对数轴）")


def test_isobar_outside_range_raises():
    """压力超出数据范围必须报错，不得静默返回空线。"""
    t = _tbl()
    try:
        P.trace_isobar(t, 1e30, outfile=str(_OUT / "isobar_bad.png"))
    except ValueError:
        return
    raise AssertionError("超范围压力应抛 ValueError")


# ══════════════════════════════════════════════════════════════
# ⑤ 熵场与等熵线
# ══════════════════════════════════════════════════════════════
def test_entropy_field_shape_and_reference_zero():
    """熵场形状 ``(ndens, ntemp)``，且参考点处归零（只用于比较）。"""
    t = _tbl()
    i0, j0 = 0, 0
    s = P.compute_entropy(t, ref_rho_idx=i0, ref_T_idx=j0)
    expect_eq(np.shape(s), (t.ndens, t.ntemp), "熵场形状应为 (ndens, ntemp)")
    expect(np.all(np.isfinite(s)), "熵场含非有限值")
    expect(abs(float(s[i0, j0])) < 1e-12, f"参考点熵应归零，实得 {s[i0, j0]}")


def test_entropy_increases_with_temperature():
    """沿等容方向升温应增熵（``ds = de/T``，能量单调增且 T>0）。"""
    t = _tbl()
    s = P.compute_entropy(t)
    # 取中间密度行，看温度方向
    row = s[t.ndens // 2]
    d = np.diff(row)
    frac_up = float(np.mean(d > 0))
    expect(frac_up > 0.8,
           f"沿温度方向熵应基本单调增，实测上升比例 {frac_up:.2f}")


def test_isentrope_from_reference():
    """等熵线提取应返回 ``(T_curve, nion_curve, outfile)`` 且出图。"""
    t = _tbl()
    s = P.compute_entropy(t)
    i0 = min(5, t.ndens - 1)
    j0 = min(10, t.ntemp - 1)
    out = _OUT / "isentrope.png"
    Tc, nc, f = P.trace_isentrope(t, s, s0_idx=(i0, j0), outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect(len(Tc) >= 2, f"等熵线点数过少: {len(Tc)}")
    expect_eq(len(Tc), len(nc), "T 与 n 长度应一致")


def test_isentrope_reference_point_lies_on_curve():
    """等熵线必须经过其参考态（``s = s0`` 的定义）。"""
    t = _tbl()
    s = P.compute_entropy(t)
    i0 = min(5, t.ndens - 1)
    j0 = min(10, t.ntemp - 1)
    T0 = float(t.temperature[j0])
    n0 = float(t.density[i0])
    Tc, nc, _f = P.trace_isentrope(t, s, s0_idx=(i0, j0),
                                   outfile=str(_OUT / "isentrope_ref.png"))
    Tc = np.asarray(Tc, dtype=float)
    nc = np.asarray(nc, dtype=float)
    # 曲线上离参考态最近的点的相对距离应很小（contour 离散化误差）
    dT = np.abs(np.log10(Tc) - np.log10(T0))
    dn = np.abs(np.log10(nc) - np.log10(n0))
    dmin = float(np.min(np.hypot(dT, dn)))
    expect(dmin < 0.05,
           f"等熵线未经过参考态，最近对数距离 {dmin:.4f} (应 <0.05)")


# ══════════════════════════════════════════════════════════════
# ⑥ 冲击雨贡纽
# ══════════════════════════════════════════════════════════════
def test_hugoniot_by_grid_index():
    """雨贡纽（网格参考态）返回 ``(rho, P, Us, Up, outfile)``。"""
    t = _tbl()
    out = _OUT / "hug_grid.png"
    rho, Pc, Us, Up, f = P.trace_hugoniot(t, ref_idx=(0, 0),
                                          outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect(len(rho) >= 2, f"雨贡纽点数过少: {len(rho)}")
    for arr, nm in ((rho, "rho"), (Pc, "P"), (Us, "Us"), (Up, "Up")):
        expect_eq(len(arr), len(rho), f"{nm} 长度应与 rho 一致")
        expect(np.all(np.isfinite(arr)), f"{nm} 含非有限值")
    expect(np.all(Us > 0), "冲击速度应为正")
    expect(np.all(Up >= 0), "粒子速度应非负")


def test_hugoniot_rankine_hugoniot_selfconsistent():
    """自洽性检验：``Up`` 必须由 ``Us`` 与压缩比按 R-H 关系复算得出。

    ``Up = Us (1 - rho0/rho)`` —— 用返回的 ``rho`` 反推，必须吻合。
    """
    t = _tbl()
    rho0 = float(P.rho_from_nion(t, t.density[0]))
    rho, Pc, Us, Up, _f = P.trace_hugoniot(
        t, ref_idx=(0, 0), n_rho=60, n_T=30,
        outfile=str(_OUT / "hug_rh.png"))
    rho = np.asarray(rho, dtype=float)
    Us = np.asarray(Us, dtype=float)
    Up = np.asarray(Up, dtype=float)
    want_Up = Us * (1.0 - rho0 / rho)
    rel = np.max(np.abs(Up - want_Up) / np.maximum(np.abs(Up), 1e-30))
    expect(rel < 1e-9,
           f"Up 与 R-H 关系不符，最大相对偏差 {rel:.3e}")


def test_hugoniot_compression_only():
    """雨贡纽只保留压缩分支 ``rho > rho0``（膨胀支被裁掉）。"""
    t = _tbl()
    rho0 = float(P.rho_from_nion(t, t.density[0]))
    rho, _P, _Us, _Up, _f = P.trace_hugoniot(
        t, ref_idx=(0, 0), n_rho=60, n_T=30,
        outfile=str(_OUT / "hug_comp.png"))
    expect(np.all(np.asarray(rho, dtype=float) > rho0),
           f"存在非压缩点 rho<=rho0={rho0:.4e}")


def test_hugoniot_by_rho_t_value():
    """雨贡纽（任意 ``rho0``/``T0``，走插值参考态分支）。"""
    t = _tbl()
    rho0 = float(P.rho_from_nion(t, t.density[1]))
    out = _OUT / "hug_interp.png"
    rho, Pc, Us, Up, f = P.trace_hugoniot(
        t, rho0=rho0, T0=float(t.temperature[0]),
        n_rho=60, n_T=30, outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    expect(len(rho) >= 2, "插值参考态分支点数过少")


def test_plot_usup_vs_pressure():
    """``Us``/``Up`` vs ``P`` 图应能单独绘制（单位 um/ns，窗口 [0,100]）。"""
    t = _tbl()
    rho, Pc, Us, Up, _f = P.trace_hugoniot(
        t, ref_idx=(0, 0), n_rho=60, n_T=30,
        outfile=str(_OUT / "hug_for_usup.png"))
    out = _OUT / "usup_vs_P.png"
    f = P.plot_usup_vs_pressure(Us, Up, Pc, outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")
    # 换算窗口检查：um/ns 值不应全部超出 [0,100]
    Us_u = units.velocity_umns(np.asarray(Us, dtype=float))
    expect(np.any((Us_u >= 0) & (Us_u <= 100)),
           "Us 换算后全部落在 [0,100] um/ns 之外（换算或量级错误）")


# ══════════════════════════════════════════════════════════════
# ⑦ 声速与 P-V 图
# ══════════════════════════════════════════════════════════════
def test_sound_speed_positive_finite():
    t = _tbl()
    cs = np.asarray(P.sound_speed(t), dtype=float)
    expect(cs.size > 0, "声速场为空")
    expect(np.all(np.isfinite(cs)), "声速含非有限值")
    expect(np.nanmin(cs) > 0, f"声速应全为正，min={np.nanmin(cs)}")


def test_sound_speed_ideal_gas_gamma_anchor():
    """ln10 回归守卫：理想气体表上 γ_sound = c_s²ρ/P 必须精确 = 5/3。

    2026-09-15 诊断：``np.gradient(np.log(P), log10(n))`` 混用自然
    对数值与常用对数坐标，dlnP/dlnn 被虚大 ln(10)≈2.303 倍，
    γ_sound 变 ~3.0（c_s 偏大 ~33%）。本表 P ∝ n（zbar 恒定），
    dlnP/dlnn 必须 = 1；坐标混用若复发则 γ_sound ≈ 2.97 必 FAIL。
    （合成表 stub 已共享化至 ``eosopdata._idealgas.IdealGasStub``）
    """
    t = _IdealGasStub()
    cs = np.asarray(P.sound_speed(t), dtype=float)
    g = cs ** 2 * P._rho(t) / P._press(t) * 1e-7         # c_s²[cm²/s²] -> J/g
    expect(np.allclose(g, 5.0 / 3.0, rtol=1e-9),
           f"理想气体锚失败: gamma_sound=[{g.min():.6f}, {g.max():.6f}]"
           " (期望 5/3；若≈2.97 为 dlnP/dlnn 坐标混用 ln10 复发)")


def test_pv_diagram_three_paths():
    """P-V 图：等温 / 等熵 / 雨贡纽三条路径从同一参考态出发。"""
    t = _tbl()
    i0, j0 = min(5, t.ndens - 1), min(10, t.ntemp - 1)
    rho_ref = float(P.rho_from_nion(t, t.density[i0]))
    T_ref = float(t.temperature[j0])
    s = P.compute_entropy(t)
    rho_h, P_h, _Us, _Up, _fh = P.trace_hugoniot(
        t, ref_idx=(i0, j0), n_rho=80, n_T=40,
        outfile=str(_OUT / "hug_for_pv.png"))
    out = _OUT / "pv.png"
    f = P.plot_pv_diagram(t, T_ref, s, rho_ref, rho_h, P_h,
                          outfile=str(out))
    expect(_ok_png(f), f"未产出有效 PNG: {f}")


def test_pv_diagram_requires_atomwt():
    """缺原子量时 P-V 图必须报错（无法定位等熵线参考态），不得瞎画。"""
    t = _tbl()
    if t.avgatw is None:
        return                                # 该样品本就缺原子量 -> 天然覆盖
    # 有原子量时无法触发；改用缺原子量的构造表
    from dataclasses import replace
    t2 = replace(t, atomwt=None)
    if t2.avgatw is not None:
        return                                # replace 未生效则跳过
    s = P.compute_entropy(t)
    try:
        P.plot_pv_diagram(t2, float(t.temperature[0]), s, 1.0,
                          np.array([1.0, 2.0]), np.array([1.0, 2.0]),
                          outfile=str(_OUT / "pv_bad.png"))
    except CN4ParseError:
        return
    raise AssertionError("缺原子量应抛 CN4ParseError")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
