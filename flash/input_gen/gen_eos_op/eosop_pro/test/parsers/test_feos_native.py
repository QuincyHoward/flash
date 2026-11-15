"""A2 —— F4b FEOS 原生表（``*.feos``）解析器测试（布局已定案版）。

★ 权威依据：FE-01_TABTOOLS.C::write_FEOS_format（196-355 行）。
三方实测一致：gen_eos_op/feos 产物（Al/SiO2/Au）+ matter++ ``.feos``
（Al/B/Cr 等）+ C 源码。此前"数据块列序未定"（R3）**已废除**。

关键事实：声明 NR/NT = 真实点数 + 1（前导 ``Qstart=0.0`` 哨兵计入声明值，
``makeRTPointArray array[0]=Qstart``）；16 块 T-major + Qtot + Q（k 最内层交错）。
"""

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
from _runner import expect, expect_eq, main

from eosop_pro import config
from eosop_pro.parsers import feos_native as f4b

_FEOS_BLOCKS = f4b.FEOS_BLOCKS


def _p(rel):
    return f4b.parse(config.MATTER(rel), rel)


def test_header_decoded_and_cross_validated_al():
    """Al.feos: 声明 192x69（含前导哨兵）→ 真实网格 191x68。"""
    t = _p("mat_Al-1.0/Al.feos")
    expect_eq(t.nr, 191, "rho 真实网格 191（声明 192，前导哨兵已修剪）")
    expect_eq(t.nt, 68, "T 真实网格 68（声明 69，前导哨兵已修剪）")
    expect_eq(t.table_id, 3717, "SESAME 号")
    expect(any("一致" in n and "301" in n for n in t.notes),
           f"应记录与兄弟文件的交叉校验，实测 {[n for n in t.notes if '301' in n]}")
    # 头部声明值仍须如实解码（notes 记录行 0 字段）
    expect(any("nrho_decl=192" in n for n in t.notes),
           f"行 0 字段 notes 应含声明的 nrho_decl=192")
    # 哨兵修剪必须在 notes 中留痕
    expect(any("哨兵已修剪" in n and "68x191" in n for n in t.notes),
           f"应记录哨兵修剪，实测 {[n for n in t.notes if '哨兵' in n]}")


def test_header_decoded_and_cross_validated_b():
    """B.feos: 声明 123x101（含前导哨兵）→ 真实网格 122x100。"""
    t = _p("mat_B/B.feos")
    expect_eq((t.nr, t.nt), (122, 100),
              "B.feos 真实网格 (122,100)；声明 (123,101)，前导哨兵已修剪")
    expect_eq(t.table_id, 104005)


def test_header_fields_decoded():
    """行 0 十字段 + 行 1 十参数按源码语义解码。"""
    t = _p("mat_Al-1.0/Al.feos")
    expect(any("file_version=12.06" in n for n in t.notes),
           f"FileVersion=12.06 应入 notes，实测 {t.notes[:2]}")
    expect(any("rho_ref=2.7" in n for n in t.notes),
           f"RhoRef=2.7 应入 notes")
    expect_eq(len(f4b.HEADER_FIELDS), 10, "行 0 固定 10 字段")
    expect_eq(len(f4b.LINE1_FIELDS), 10, "行 1 固定 10 参数")


def test_blocks_fully_decoded():
    """16 块 + Qtot + Q 全解码；计数公式闭合（R3 废除）。"""
    t = _p("mat_Al-1.0/Al.feos")
    for blk in _FEOS_BLOCKS:
        expect(blk in t.fields, f"块 {blk} 应已解码，实测 {list(t.fields)}")
    expect("Qtot" in t.fields and "Q0" in t.fields,
           f"Qtot/Q0 应已解码，实测 {list(t.fields)}")
    shape = t.field_shape["P"]
    expect_eq(shape, (68, 191), f"块形状应为 (NT_real, NR_real)=(68,191)，实测 {shape}")
    expect_eq(t.n_numbers_expected, t.n_numbers_seen,
              "计数公式应闭合（20+3ne+NR+NT+(17+ne)*NR*NT）")
    # 单位：原生 cgs + eV，不换算
    expect_eq(t.field_units["Pi"], "dyn/cm2")
    expect_eq(t.field_units["Ei"], "erg/g")
    expect_eq(t.field_units["Si"], "erg/g/eV")
    expect_eq(t.field_units["Qtot"], "-")
    expect(any("R3 已废除" in n for n in t.notes), "notes 应声明 R3 已废除")


def test_grids_located_and_positive():
    t = _p("mat_Al-1.0/Al.feos")
    expect("rho" in t.axes and "Te" in t.axes, f"axes={list(t.axes)}")
    expect_eq(len(t.axes["rho"]), t.nr)
    expect_eq(len(t.axes["Te"]), t.nt)
    expect(all(v > 0 for v in t.axes["rho"]), "rho 轴应严格正（哨兵已修剪）")
    expect(all(v > 0 for v in t.axes["Te"]), "Te 轴应严格正（哨兵已修剪）")


def test_sibling_lookup_works():
    p = config.MATTER("mat_Al-1.0/Al.feos")
    sib = f4b.find_sibling_301(p, "mat_Al-1.0/Al.feos")
    expect(sib is not None, "应找到 FEOS/Al.feos.301")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
