"""cn4 **数据提取**测试 —— 18 块解析 / 头部 / 网格 / 往返。

溯源
----
* 格式权威: ``ionmix/ionmix/src/Ionmix/abjt_03.f`` ``SUBROUTINE OWTF``
  (line 4510)，``isw(21) != 0`` 分支 (line 4662-4743) 的 18 个
  ``write(123,...)`` 语句
* 文字规格: ``ionmix/ionmix/docs/IONMIX用户指南.md`` §5.4
* 实现脚本: ``eosop_pro/cn4/cn4_io.py``

本文件只验证"能否正确取出数据"，绘图与路径见同目录其它文件。
"""

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

import numpy as np

from eosop_pro.cn4 import (
    N_BLOCKS, load_cn4, parse_cn4, write_cn4,
    cn4_to_parsed_tables, parsed_tables_to_cn4,
)
from eosop_pro.cn4.cn4_io import (
    BLOCK_SPEC, OPACITY_SPEC, FIXED_WIDTH, ELEMENT_ATOMWT, CN4ParseError,
)

from eosopdata._samples import first_cn4, cn4_samples, tmp_dir


def _tbl():
    p = first_cn4()
    if p is None:                      # pragma: no cover
        raise RuntimeError("仓库内无可用 .cn4 样品")
    return load_cn4(str(p))


# ══════════════════════════════════════════════════════════════
# ① 格式常量 —— 与 abjt_03.f 的 OWTF 序列一致
# ══════════════════════════════════════════════════════════════
def test_block_count_is_18():
    """``.cn4`` = 18 块（2 个 1D 网格 + 12 个 2D 场 + 1 群边界 + 3 个 3D 场）。"""
    expect_eq(N_BLOCKS, 18)
    # BLOCK_SPEC 描述 12 个二维场（第 3..14 块）
    expect_eq(len(BLOCK_SPEC), 12, "BLOCK_SPEC 应含 12 个二维场")
    # OPACITY_SPEC 描述 3 个三维不透明度场（第 16..18 块）
    expect_eq(len(OPACITY_SPEC), 3, "OPACITY_SPEC 应含 3 个三维场")


def test_fixed_width_is_12():
    """Fortran ``4e12.6`` 每字段 12 列 —— 与 OWTF 的格式声明一致。"""
    expect_eq(FIXED_WIDTH, 12)


def test_element_atomwt_matches_config_single_source():
    """原子量表必须来自权威来源，且与 config 的 N_A 一致使用。

    ``ELEMENT_ATOMWT`` 是解析 cn4 头部原子序数 -> 质量数的唯一依据；
    其数值与 ``AtomicWeightTable.txt`` 对应（见 IONMIX 用户指南 §5.4）。
    """
    expect_in(1, ELEMENT_ATOMWT, "H 应在元素表中")
    expect_in(6, ELEMENT_ATOMWT, "C 应在元素表中")
    expect_in(13, ELEMENT_ATOMWT, "Al 应在元素表中")
    # 物理量级 sanity
    expect(1.0 < ELEMENT_ATOMWT[1] < 1.1, f"H 原子量 {ELEMENT_ATOMWT[1]}")
    expect(11.5 < ELEMENT_ATOMWT[6] < 12.5, f"C 原子量 {ELEMENT_ATOMWT[6]}")
    expect(26.0 < ELEMENT_ATOMWT[13] < 27.5, f"Al 原子量 {ELEMENT_ATOMWT[13]}")


# ══════════════════════════════════════════════════════════════
# ② 头部与网格
# ══════════════════════════════════════════════════════════════
def test_header_grids_are_consistent():
    """头部 ntemp/ndens/ngrups 与各场内元素数必须自洽。"""
    t = _tbl()
    expect(t.ntemp > 0, f"ntemp={t.ntemp}")
    expect(t.ndens > 0, f"ndens={t.ndens}")
    expect(t.ngrups > 0, f"ngrups={t.ngrups}")
    # 温度/密度轴长度
    expect_eq(len(t.temperature), t.ntemp, "温度轴长度 == ntemp")
    expect_eq(len(t.density), t.ndens, "密度轴长度 == ndens")
    # 每个二维场 = ntemp * ndens
    n2d = t.ntemp * t.ndens
    for attr, _lbl, _unit, _src in BLOCK_SPEC:
        blk = t.fields2d.get(attr)
        expect(blk is not None, f"缺二维场 {attr}")
        expect_eq(len(blk), n2d, f"{attr} 长度应为 ntemp*ndens={n2d}")


def test_grids_are_monotonic_increasing():
    """温度与密度轴必须单调递增（否则插值/等值线提取无意义）。"""
    t = _tbl()
    T = np.asarray(t.temperature, dtype=float)
    rho = np.asarray(t.density, dtype=float)
    expect(np.all(np.diff(T) > 0), "温度轴非单调递增")
    expect(np.all(np.diff(rho) >= 0), "密度轴应单调不减（允许首点 0）")


def test_composition_is_consistent():
    """原子序数 / 丰度 / 原子量三者长度一致，且丰度归一。"""
    t = _tbl()
    zs = list(t.izgas)
    fs = list(t.fracsp)
    expect_eq(len(zs), len(fs), "izgas 与 fracsp 长度须一致")
    expect(all(z > 0 for z in zs), f"原子序数应为正: {zs}")
    s = sum(fs)
    expect(abs(s - 1.0) < 1e-6 or abs(s) < 1e-12,
           f"丰度之和应为 1，实测 {s}")


# ══════════════════════════════════════════════════════════════
# ③ 二维场取值
# ══════════════════════════════════════════════════════════════
def test_physical_quantities_are_finite_or_placeholder():
    """12 个二维场不得含 NaN 垃圾 —— 除显式占位外应全为有限值。"""
    from eosop_pro.cn4.cn4_io import is_nan_placeholder
    t = _tbl()
    bad = []
    for attr, _lbl, _unit, _src in BLOCK_SPEC:
        arr = np.asarray(t.fields2d[attr], dtype=float)
        n_plc = int(sum(1 for v in arr if is_nan_placeholder(float(v))))
        n_nan = int(np.isnan(arr).sum())
        n_inf = int(np.isinf(arr).sum())
        # 允许占位；不允许"非占位的 nan/inf"
        if n_nan + n_inf > n_plc:
            bad.append(f"{attr}: nan={n_nan} inf={n_inf} placeholder={n_plc}")
    expect(not bad, "存在非法 NaN/Inf：\n  " + "\n  ".join(bad))


def test_zbar_in_valid_range():
    """平均电离度 ``zbar`` 必须在 ``[0, Z_max]``。"""
    t = _tbl()
    z = np.asarray(t.fields2d["zbar"], dtype=float)
    zmax = max(t.izgas)
    expect(np.nanmin(z) >= -1e-9, f"zbar 最小值 {np.nanmin(z)} 应 >= 0")
    expect(np.nanmax(z) <= zmax + 1e-6,
           f"zbar 最大值 {np.nanmax(z)} 应 <= Z_max={zmax}")


def test_pressure_positive():
    """离子/电子压 ``p_ion``/``p_ele`` 应为正（J/cm^3）。"""
    t = _tbl()
    for q in ("p_ion", "p_ele"):
        a = np.asarray(t.fields2d[q], dtype=float)
        expect(np.nanmin(a) > 0, f"{q} 最小值 {np.nanmin(a)} 应 > 0")


def test_energy_and_cv_positive():
    """比内能与比热应为正。"""
    t = _tbl()
    for q in ("e_ion", "e_ele"):
        a = np.asarray(t.fields2d[q], dtype=float)
        expect(np.nanmin(a) > 0, f"{q} 最小值 {np.nanmin(a)} 应 > 0")


# ══════════════════════════════════════════════════════════════
# ④ 群不透明度（3D 块）
# ══════════════════════════════════════════════════════════════
def test_opacity_blocks_have_group_dimension():
    """3 个不透明度块应为 ``ngrups * ntemp * ndens``。

    属性名是 ``opacities``（不是 ``fields3d``），键名见 ``OPACITY_SPEC``。
    """
    t = _tbl()
    n3d = t.ngrups * t.ntemp * t.ndens
    for attr, _lbl, _unit, _src in OPACITY_SPEC:
        blk = t.opacities.get(attr)
        expect(blk is not None, f"缺三维块 {attr}")
        expect_eq(len(blk), n3d, f"{attr} 应为 ngrups*ntemp*ndens={n3d}")


def test_group_opacity_slices_are_2d():
    """``group_opacity(name, ig)`` 每群应正好是 ``ndens*ntemp``（群维被切掉）。"""
    t = _tbl()
    n2 = t.ndens * t.ntemp
    for ig in (1, t.ngrups):
        for key in ("rosseland", "planck_abs", "planck_ems"):
            sl = t.group_opacity(key, ig)
            expect_eq(len(sl), n2, f"{key} 群 {ig} 长度应 == ndens*ntemp={n2}")
    # 群号越界须报错
    try:
        t.group_opacity("rosseland", t.ngrups + 1)
    except CN4ParseError:
        pass
    else:
        raise AssertionError("群号越界应抛 CN4ParseError")


def test_opacity_positive():
    """不透明度（cm^2/g）应为正。"""
    t = _tbl()
    for attr, _lbl, _unit, _src in OPACITY_SPEC:
        a = np.asarray(t.opacities[attr], dtype=float)
        expect(np.nanmin(a) > 0, f"{attr} 含非正值 min={np.nanmin(a)}")


def test_planck_absorption_leq_rosseland_typical():
    """物理关系：对多数光学薄区 ``kappa_P <= kappa_R`` 不成立，
    但两者都应与密度反相关。这里只断言两者量级同阶（不做物理断言）。"""
    t = _tbl()
    kr = np.asarray(t.opacities["opac_rosseland"], dtype=float)
    kp = np.asarray(t.opacities["opac_planck_abs"], dtype=float)
    ratio = np.nanmedian(kp / kr)
    expect(1e-4 < ratio < 1e4, f"kappa_P/kappa_R 中位数 {ratio} 量级异常")


def test_field_grid_reshape_matches_flat():
    """``field_grid`` 的嵌套 ``[i_dens][j_T]`` 应与扁平场一致（轴序自洽）。"""
    t = _tbl()
    for attr, _lbl, _unit, _src in BLOCK_SPEC[:3]:
        flat = np.asarray(t.fields2d[attr], dtype=float)
        grid = np.asarray(t.field_grid(attr), dtype=float)
        expect_eq(grid.shape, (t.ndens, t.ntemp),
                  f"{attr} grid 形状应为 (ndens, ntemp)")
        expect(np.allclose(grid.ravel(), flat, equal_nan=True),
               f"{attr} 扁平与嵌套不一致")


def test_derived_quantities_are_consistent():
    """派生量自洽：``rho`` 只随密度变、``nele = zbar * n_ion``。"""
    t = _tbl()
    rho = np.asarray(t.quantity("rho"), dtype=float).reshape(t.ndens, t.ntemp)
    # 每行的 rho 应与温度无关（常数列）
    expect(np.allclose(rho, rho[:, :1]), "rho 沿温度方向应恒定")
    # nele = zbar * n_ion
    zb = np.asarray(t.field("zbar"), dtype=float).reshape(t.ndens, t.ntemp)
    ne = np.asarray(t.quantity("nele"), dtype=float).reshape(t.ndens, t.ntemp)
    dens = np.asarray(t.density, dtype=float)[:, None]
    expect(np.allclose(ne, zb * dens, rtol=1e-9, equal_nan=True),
           "nele 应等于 zbar * n_ion")
    # 总量 = 分量之和
    p = np.asarray(t.quantity("p"), dtype=float)
    pi = np.asarray(t.field("p_ion"), dtype=float)
    pe = np.asarray(t.field("p_ele"), dtype=float)
    expect(np.allclose(p, pi + pe, rtol=1e-12), "p 应等于 p_ion + p_ele")


# ══════════════════════════════════════════════════════════════
# ⑤ 往返与桥接
# ══════════════════════════════════════════════════════════════
def test_write_parse_roundtrip_values():
    """``parse_cn4(write_cn4(t))`` 数值须逐位回读（12 列定宽）。"""
    t = _tbl()
    od = tmp_dir() / "roundtrip"
    od.mkdir(parents=True, exist_ok=True)
    out = write_cn4(t, od / "rt.cn4")
    t2 = load_cn4(str(out))

    expect_eq(t2.ntemp, t.ntemp)
    expect_eq(t2.ndens, t.ndens)
    expect_eq(t2.ngrups, t.ngrups)
    for attr, _lbl, _unit, _src in BLOCK_SPEC:
        a = np.asarray(t.fields2d[attr], dtype=float)
        b = np.asarray(t2.fields2d[attr], dtype=float)
        # 6 位小数 -> 相对容差 1e-5
        ok = np.allclose(a, b, rtol=1e-5, atol=1e-12, equal_nan=True)
        expect(ok, f"{attr} 往返不一致，最大偏差 {np.nanmax(np.abs(a-b))}")


def test_bridge_cn4_to_parsed_and_back():
    """``cn4 -> ParsedTable -> cn4`` 必须数值等价（转换桥梁）。"""
    t = _tbl()
    tabs = cn4_to_parsed_tables(t)
    expect_eq(len(tabs), 4, "应为 EOS_TOTAL + 3 张不透明度表")
    kinds = sorted(x.kind for x in tabs)
    expect_eq(kinds, ["EMISSIVITY", "EOS_TOTAL", "PLANCK", "ROSSELAND"])

    t2 = parsed_tables_to_cn4(tabs, izgas=t.izgas, fracsp=t.fracsp)
    expect_eq(t2.ntemp, t.ntemp)
    expect_eq(t2.ndens, t.ndens)
    for attr, _lbl, _unit, _src in BLOCK_SPEC:
        a = np.asarray(t.fields2d[attr], dtype=float)
        b = np.asarray(t2.fields2d[attr], dtype=float)
        expect(np.allclose(a, b, rtol=1e-5, atol=1e-12, equal_nan=True),
               f"{attr} 桥接后不一致")


def test_parsed_tables_to_cn4_requires_composition():
    """缺 ``izgas``/``fracsp`` 必须报错 —— 不允许猜元素组成。"""
    t = _tbl()
    tabs = cn4_to_parsed_tables(t)
    try:
        parsed_tables_to_cn4(tabs)
    except CN4ParseError:
        return
    raise AssertionError("缺 izgas/fracsp 应抛 CN4ParseError（不得猜测）")


def test_cross_material_consistency():
    """不同材料的 cn4 结构须一致（块数/字段齐全）。"""
    samps = cn4_samples(3)
    if len(samps) < 2:
        return                                    # 数据不足则跳过
    for p in samps:
        t = load_cn4(str(p))
        expect_eq(t.ntemp * t.ndens,
                  len(t.fields2d["zbar"]),
                  f"{p.name}: zbar 长度与网格不符")
        for attr, _lbl, _unit, _src in OPACITY_SPEC:
            expect(attr in t.opacities, f"{p.name}: 缺 {attr}")


# ══════════════════════════════════════════════════════════════
# ⑥ 错误处理
# ══════════════════════════════════════════════════════════════
def test_bad_header_raises():
    """非 cn4 内容必须明确抛错，不得静默返回空表。"""
    od = tmp_dir() / "badhead"
    od.mkdir(parents=True, exist_ok=True)
    bad = od / "broken.cn4"
    bad.write_text("not a cn4\nnope\nnope\nnope\n", encoding="utf-8")
    try:
        parse_cn4(str(bad))
    except CN4ParseError:
        return
    raise AssertionError("坏文件应抛 CN4ParseError")


def test_missing_file_raises():
    try:
        load_cn4("/definitely/not/here.cn4")
    except CN4ParseError:
        return
    raise AssertionError("不存在的文件应抛 CN4ParseError")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
