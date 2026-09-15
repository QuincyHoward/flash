"""A2 —— F4a MPQeos（``.301/.304/.305``）解析器测试。

★ 两个实测陷阱
1. **表头不可定宽切分**：ID 列宽 16/17 不定，16 与 15 都会切出污染字段
   （``'2.70000000e+00 1'``）→ 表头走 L2 正则。
2. **字段宽逐文件不同**：``Al.feos.301`` payload 行 60 字符（W=15），
   ``mat_He/Untitled.304`` 是 64 字符（W=16）→ 逐文件推断 ``W = len(line)/4``。

基准：``Al.feos.301`` 头 ``37170301 2.7 192 69`` → 192+69+3·192·69 = **40005**。
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
from eosop_pro.parsers import mpqeos as f4
from eosop_pro.core import fixedwidth as fw
from eosop_pro.core import fortran_numbers as fn


def _p(rel):
    return f4.parse(config.MATTER(rel), rel)


def test_al_feos_301_baseline():
    t = _p("mat_Al-1.0/FEOS/Al.feos.301")
    expect_eq(t.table_id, 37170301)
    expect_eq((t.nr, t.nt), (192, 69))
    # payload = nr + nt + 3*nr*nt = 40005；加 4 个表头数 → 全文件 40009
    expect_eq(t.n_numbers_expected, 4 + 192 + 69 + 3 * 192 * 69)
    expect_eq(t.n_numbers_expected, 40009)
    expect_eq(t.n_numbers_seen, 40009, "全文件数值个数（含 4 个表头）")
    expect_eq(t.kind, "EOS_TOTAL")
    expect_eq(t.field_shape["P"], (69, 192))


def test_ext_kind_mapping():
    expect_eq(_p("mat_Al-1.0/FEOS/Al.feos.301").kind, "EOS_TOTAL")
    expect_eq(_p("mat_Al-1.0/FEOS/Al.feos.304").kind, "EOS_ELECTRON")
    expect_eq(_p("mat_Al-1.0/FEOS/Al.feos.305").kind, "EOS_ION")


def test_unit_conversion_is_exact_factor():
    """直接验证换算因子：Mbar = GPa × 1e-2、Mbar·cm³/g = MJ/kg × 1e-2。

    不依赖量级经验判断，而是从原始 payload 重算后逐点比对。
    """
    from eosop_pro.core import textio
    from eosop_pro.core import fixedwidth as fw

    t = _p("mat_Al-1.0/FEOS/Al.feos.301")
    doc = textio.read_text(config.MATTER("mat_Al-1.0/FEOS/Al.feos.301"))
    payload_lines = [ln for ln in doc.lines[1:] if ln.strip()]
    w = fw.infer_payload_width(payload_lines, 4)
    raw: list[float] = []
    for ln in payload_lines:
        raw.extend(fw.slice_values(ln, width=w))
    nr, nt = t.nr, t.nt
    n2 = nr * nt
    raw_P = raw[nr + nt:nr + nt + n2]
    raw_E = raw[nr + nt + n2:nr + nt + 2 * n2]

    expect_eq(t.field_units["P"], "Mbar")
    expect_eq(t.field_units["E"], "Mbar*cm3/g")
    for k in (0, n2 // 3, n2 - 1):
        expect(abs(t.fields["P"][k] - raw_P[k] * 1e-2) < 1e-12 * max(1.0, abs(raw_P[k])),
               f"P[{k}]: {t.fields['P'][k]} != {raw_P[k]}*1e-2")
        expect(abs(t.fields["E"][k] - raw_E[k] * 1e-2) < 1e-12 * max(1.0, abs(raw_E[k])),
               f"E[{k}]: {t.fields['E'][k]} != {raw_E[k]}*1e-2")


def test_temperature_kelvin_to_ev():
    t = _p("mat_Al-1.0/FEOS/Al.feos.301")
    T = t.axes["Te"]
    expect(min(T) >= 0, f"min={min(T)}")
    expect(max(T) > 1e3, f"Kelvin 应换算到 eV，实测 max={max(T):.4g}")


def test_header_slicing_by_fixed_width_is_provably_wrong():
    """反证：定宽 16 切分把字段切坏 → 证明必须用 L2 正则。"""
    from eosop_pro.core import textio
    doc = textio.read_text(config.MATTER("mat_Al-1.0/FEOS/Al.feos.301"))
    bad = fw.slice_fields(doc.lines[0], width=fw.WIDTH_MPQEOS, count=4)
    expect_eq(bad, ["37170301", "2.70000000e+00 1", ".92000000e+02 6.", "90000000e+01"])
    failed = False
    try:
        fn.parse_fortran_float(bad[1])
    except ValueError:
        failed = True
    expect(failed, "被污染的字段应无法解析为 float")


def test_payload_width_inferred_per_file():
    """同族字段宽不同：Al=15、He=16。"""
    from eosop_pro.core import textio
    d1 = textio.read_text(config.MATTER("mat_Al-1.0/FEOS/Al.feos.301"))
    p1 = [ln for ln in d1.lines[1:] if ln.strip()]
    expect_eq(fw.infer_payload_width(p1, 4), 15)
    d2 = textio.read_text(config.MATTER("mat_He/Untitled.304"))
    p2 = [ln for ln in d2.lines[1:] if ln.strip()]
    expect_eq(fw.infer_payload_width(p2, 4), 16)


def test_he_untitled_304_has_nonfinite_source_defect():
    """★ ``mat_He/Untitled.304`` 的 payload 含 MSVC 的 ``-1.#INF`` —— **源数据缺陷**。

    必须：① 不因此中断解析；② 显式计数并告警。
    """
    t = _p("mat_He/Untitled.304")
    expect_eq((t.nr, t.nt), (123, 101))
    expect(any("非有限值" in n for n in t.notes), f"应告警，实测 {t.notes}")
    infs = fn.count_nonfinite(t.fields["P"] + t.fields["E"] + t.fields["Z"])
    expect(infs > 0, f"应确实存在 inf/nan，实测 {infs}")


def test_z_field_present_and_anomaly_flagged():
    """MPQeos 的 payload 第 5 段应是 Z(ρ,T)（``(n_ele,Te)`` 网格的候选来源）。

    ⚠️ 实测该段含**负值且量级异常**，与「电离度」语义不符 →
    解析器必须**显式告警**，不得悄悄当成电离度使用。
    """
    t = _p("mat_Al-1.0/FEOS/Al.feos.304")
    expect("Z" in t.fields, f"fields={list(t.fields)}")
    expect_eq(t.field_shape["Z"], (69, 192))
    expect_eq(t.field_units["Z"], "1")
    finite = [v for v in t.fields["Z"] if v == v and abs(v) != float("inf")]
    has_neg = any(v < 0 for v in finite)
    if has_neg:
        expect(any("待核" in n for n in t.notes),
               f"含负值就必须告警，实测 notes={t.notes}")


def test_b_301_baseline():
    t = _p("mat_B/B.301")
    expect_eq((t.nr, t.nt), (123, 101))


if __name__ == "__main__":
    raise SystemExit(main(globals()))
