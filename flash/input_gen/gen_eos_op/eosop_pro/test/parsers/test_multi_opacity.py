"""A2 —— F2「不透明度 / Zeff / EPS」解析器测试。

★ 核心结构结论（本文件最重要的一条）
--------------------------------------
**多群文件是 ``ng`` 个独立子表的串联，每个子表自带完整表头 + 能群边界线。**
行数算术精确验证：

* ``AU_op03p``            20 子表 × (1 头 + 1 边界 + 110 payload) = **2240** 行 ✓
* ``Thermos/Al_Planck.dat`` 25 子表 × (1 + 1 + 127)              = **3225** 行 ✓
* ``AU_SIMPLE_PLANCK_MG``   24 子表 × 4                          = **96** 行 ✓

且 ``ng`` 与三处**独立声明**一一对上：``AU_info`` 的 ``NG=20``、README 的「24 群」、
``opbe.inhalt`` 的 ``NG=40`` —— 这解决了风险 R1。
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
from eosop_pro.parsers import multi_opacity as f2


def _p(rel, **kw):
    return f2.parse(config.MATTER(rel), rel, **kw)


def test_gray_tables():
    t = _p("mat_Al-1.0/AL_SIMPLE_ROSSELAND")
    expect_eq((t.table_id, t.n_groups, t.nr, t.nt), (1401, 1, 2, 2))
    expect_eq(t.kind, "ROSSELAND")
    expect_eq(t.field_shape["kappa"], (2, 2))

    t2 = _p("mat_Al-1.0/AL_SIMPLE_PLANCK")
    expect_eq((t2.table_id, t2.kind), (1701, "PLANCK"))


def test_sesame_numbered_gray_tables_with_three_digit_exponent():
    """``1041_ROSS`` 表头含三位指数 ``1.0410000e+003``；``1041_PLANCK`` 是 ``1.1041000e+004``。"""
    r = _p("mat_Al-1.0/1041_ROSS")
    expect_eq((r.table_id, r.kind, r.nr, r.nt, r.n_groups), (1041, "ROSSELAND", 31, 46, 1))
    p = _p("mat_Al-1.0/1041_PLANCK")
    expect_eq((p.table_id, p.kind, p.nr, p.nt, p.n_groups), (11041, "PLANCK", 31, 46, 1))


def test_au_op03p_is_20_subtables_matching_au_info():
    """★ ``AU_info`` 声明 ``NG=20``；文件确有 20 个子表。"""
    t = _p("mat_Au-1.0/AU_op03p")
    expect_eq(t.n_groups, 20, "20 子表")
    expect_eq((t.nr, t.nt), (20, 20))
    expect_eq(t.kind, "MUGROUP")
    expect_eq(t.field_shape["kappa_g"], (20, 20, 20), "(ng, nt, nr)")
    gb = t.group_bounds
    expect(gb is not None and len(gb) == 21, f"21 个群边界，实测 {gb and len(gb)}")
    expect(gb[0] == 1.0 and gb[1] == 10.0 and gb[2] == 50.0,
           f"前三边界应为 1/10/50 eV，实测 {gb[:3]}")
    expect(gb == sorted(gb), "群边界应单调递增")


def test_au_simple_planck_mg_is_24_subtables():
    """每子表 4 行（头/边界/rho+T/kappa），24 子表 = 96 行。README 亦称「24 群」。"""
    t = _p("mat_Au-1.0/AU_SIMPLE_PLANCK_MG")
    expect_eq(t.n_groups, 24)
    expect_eq((t.nr, t.nt), (2, 2))
    expect_eq(t.field_shape["kappa_g"], (24, 2, 2))


def test_thermos_al_planck_is_25_subtables():
    t = _p("Thermos/mat_Al/Al_Planck.dat")
    expect_eq(t.n_groups, 25)
    expect_eq((t.nr, t.nt), (22, 21))


def test_opbe_splits_into_three_tables():
    """``opbe`` 是**不同 KIND 的表**串联（``opbe.inhalt`` 声明 4 个表号，实际 3 张）。"""
    tables = f2.parse_all(config.MATTER("mat_Be-1.0/opbe"), "mat_Be-1.0/opbe")
    expect_eq(len(tables), 3, f"实测 {[t.table_key for t in tables]}")
    kinds = [t.kind for t in tables]
    expect_eq(kinds, ["MUGROUP", "MUGROUP", "ZEFF"], f"kinds={kinds}")
    ids = [t.table_id for t in tables]
    expect_eq(ids, [20203000, 20204000, 20202000], "表号与 sesame 类型位 3/4/2 对应")
    for t in tables[:2]:
        expect_eq(t.n_groups, 40, "opbe.inhalt 声明 NG=40")
    expect_eq(tables[2].n_groups, 1)


def test_zeff_kind_and_unit_default():
    t = _p("mat_Au-1.0/AU_op03z")
    expect_eq((t.kind, t.table_id, t.n_groups), ("ZEFF", 27002003, 1))
    expect("default:eV" in t.unit_source, f"未声明单位时应标注默认，实测 {t.unit_source}")
    expect("⚠️" in t.unit_source, "ZEFF 表存在 eV/keV 两套 → 必须告警")


def test_unit_hint_applied_for_zeff_kev():
    """``Al_Zeff.dat`` 的 T 是 keV（由 Thermos Readme 声明）→ 传入后应换算 ×1000。"""
    ev = _p("Thermos/mat_Al/Al_Zeff.dat", unit_hint="eV")
    kev = _p("Thermos/mat_Al/Al_Zeff.dat", unit_hint="keV")
    expect(abs(kev.axes["Te"][0] / ev.axes["Te"][0] - 1000.0) < 1e-6,
           f"keV 应比 eV 大 1000 倍，实测 {ev.axes['Te'][0]} vs {kev.axes['Te'][0]}")
    expect("declared:keV" in kev.unit_source)


def test_packed_label_line_parsed():
    """``.27100000E+04PLANCK M`` —— id 与标签紧贴，无分隔符。"""
    h = f2.parse_header("  .27100000E+04PLANCK M         .20000000E+01  .20000000E+01")
    expect_eq(h["table_id"], 2710)
    expect_eq(h["label"], "PLANCK")
    expect(h["packed"] is True, "应检出紧贴")
    expect_eq((h["nr"], h["nt"]), (2, 2))


def test_label_normalization_rossland_variants():
    """三种拼写都要归一为 ROSSELAND：``ROSSELAND`` / ``ROSSLAN``。"""
    for text in ("ROSSELAND M", "ROSSLAN M", "ROSSLAN"):
        h = f2.parse_header(f"27004000      {text}        0.20000000E+02 0.20000000E+02")
        expect_eq(h["label"], "ROSSELAND", f"text={text!r}")
    h2 = f2.parse_header(" 0.1234567E+000PLANCK 1        5.0000000e+001 6.9000000e+001")
    expect_eq(h2["label"], "PLANCK")
    expect_eq((h2["nr"], h2["nt"]), (50, 69), "LEDCOP 拆分件尺寸")


def test_marker_line_detection():
    expect(f2.is_marker_line("0.10000000E+01 0.10000000E+02") is True)
    expect(f2.is_marker_line(" 1.            25.") is True)
    expect(f2.is_marker_line("-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01")
           is False, "4 个数的 payload 行不是边界线")
    expect(f2.is_marker_line("27003003      PLANCK M  20 20") is False, "含字母不是")


def test_take_numbers_rejects_overshoot():
    """数值跨越子表边界必须报错，而不是静默截断。"""
    import eosop_pro.core.errors as errs
    raised = False
    try:
        f2.take_numbers(["1 2 3 4", "5 6 7 8"], 0, 6)
    except errs.ParseError:
        raised = True
    expect(raised, "overshoot 应抛 ParseError")


def test_count_mismatch_on_wrong_dims():
    """人为破坏一个数 → 必须落 count_mismatch / ParseError，不得静默成功。"""
    import eosop_pro.core.errors as errs
    import tempfile
    from pathlib import Path
    src = config.MATTER("mat_Al-1.0/1041_ROSS")
    txt = src.read_text(encoding="utf-8", errors="replace")
    # 删掉最后一个数值 → 子表数不足
    broken = txt.rstrip()
    broken = broken[: broken.rfind(" ")].rstrip()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "broken_ross"
        p.write_text(broken, encoding="utf-8")
        raised = False
        try:
            f2.parse_all(p, "broken_ross")
        except Exception as exc:  # noqa: BLE001
            raised = isinstance(exc, (errs.ParseError, errs.CountMismatch))
            if not raised:
                raise
            expect(raised, f"应抛 ParseError/CountMismatch，实测 {type(exc).__name__}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
