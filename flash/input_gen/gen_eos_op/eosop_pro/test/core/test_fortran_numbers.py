"""Phase 1 —— Fortran 数值解析内核测试。

关键反例（本项目最经典的陷阱）：负号吃掉前导空格后字段紧邻，``str.split()`` 会漏计。
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
import _runner  # noqa: F401  —— 顺带把项目根加入 sys.path
from _runner import expect, expect_eq, main

from eosop_pro import config
from eosop_pro.core import fortran_numbers as fn


def test_packed_negatives_are_four_numbers():
    """实测于 mat_Au-1.0/AU_op03z：4 个数挤在 60 字符内，无任何分隔符。"""
    line = "-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01"
    expect_eq(len(line.split()), 1, "前提：split() 只得 1 个 token")
    vals = fn.extract_numbers(line)
    expect_eq(len(vals), 4, "紧邻负数必须被解析为 4 个数")


def test_packed_negatives_values():
    vals = fn.extract_numbers("-0.60000000E+01-0.55789474E+01")
    expect_eq(len(vals), 2)
    expect(abs(vals[0] - (-6.0)) < 1e-12, f"first={vals[0]}")
    expect(abs(vals[1] - (-5.5789474)) < 1e-9, f"second={vals[1]}")


def test_ramis_no_leading_zero():
    """实测于 mat_Al-1.0/AL_eos。"""
    vals = fn.extract_numbers("  .27000000E+01  .66000000E+02  .74000000E+02")
    expect_eq(len(vals), 3)
    expect(abs(vals[0] - 2.7) < 1e-12, f"{vals[0]}")
    expect(abs(vals[1] - 66.0) < 1e-12, f"{vals[1]}")
    expect(abs(vals[2] - 74.0) < 1e-12, f"{vals[2]}")


def test_three_digit_exponent_lowercase_e():
    """实测于 mat_Al-1.0/1041_PLANCK 行1：1.1041000e+004。"""
    vals = fn.extract_numbers(" 1.1041000e+004 0.70000000E+01 3.1000000E+001 4.6000000E+001")
    expect_eq(len(vals), 4)
    expect(abs(vals[0] - 11041.0) < 1e-9, f"{vals[0]}")
    expect(abs(vals[2] - 31.0) < 1e-9, f"{vals[2]}")
    expect(abs(vals[3] - 46.0) < 1e-9, f"{vals[3]}")


def test_d_exponent():
    expect(abs(fn.parse_fortran_float("1.0D+03") - 1000.0) < 1e-12)
    expect(abs(fn.parse_fortran_float("1.5d-2") - 0.015) < 1e-12)


def test_empty_decimal_and_bare_fraction():
    vals = fn.extract_numbers(" 1.            25.")
    expect_eq(len(vals), 2)
    expect(abs(vals[0] - 1.0) < 1e-12)
    expect(abs(vals[1] - 25.0) < 1e-12)
    vals2 = fn.extract_numbers("  .0             .10000000E+01")
    expect_eq(len(vals2), 2)
    expect(abs(vals2[0]) < 1e-12)
    expect(abs(vals2[1] - 1.0) < 1e-12)


def test_sign_only_tokens_are_not_numbers():
    expect_eq(fn.extract_numbers("  -   +   .  "), [], "纯符号不成数")


def test_payload_line_has_no_letters_and_full_coverage():
    """payload 行判据：不含（非数值）字母 + 数值覆盖率 1.0。"""
    payload = "-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01"
    expect_eq(fn.numeric_coverage(payload), 1.0, "纯数值行覆盖率应为 1.0")
    expect_eq(fn.letter_ratio(payload), 0.0, "纯数值行不应含字母")
    expect(fn.has_letters(payload) is False, "纯数值行不应被判为含字母")
    expect(fn.is_payload_line(payload) is True, "应判为 payload 行")


def test_exponent_E_is_not_a_letter():
    """回归防护（真实踩过的坑）：payload 行含指数 ``E``，naive「含字母」会全员误判。

    ``-0.60000000E+01`` 里的 ``E`` 属于数值 token，必须先剔除再判字母，
    否则**每一行 payload 都会被误判成表头**。
    """
    payload = "-0.60000000E+01-0.55789474E+01"
    raw_letters = [ch for ch in payload if ch.isalpha()]
    expect_eq(raw_letters, ["E", "E"], "前提：原始行确实含 E")
    expect(
        fn.has_letters(payload) is False,
        "剔除数值 token 后不应残留字母 —— 这是分界判据成立的前提",
    )


def test_real_file_header_line_0_is_pure_numeric():
    """AL_eos 第 0 行（``37181000 2.7 66 74``）本就是纯数字，不含字母。

    → 所以**分界不能只看字母**：F1 家族的分界靠「表头行号规则」，
    字母判据只在「头部是自由文本」（F3/F5）时才作为主判据。
    """
    from eosop_pro.core import textio

    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    expect(
        fn.has_letters(doc.lines[0]) is False,
        f"AL_eos 第 0 行应为纯数字，实测 {doc.lines[0]!r}",
    )


def test_header_line_coverage_is_not_zero_but_letters_give_it_away():
    """实测陷阱：注释行里**也含数字**，故覆盖率不能单独当分界判据。

    ``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483`` 会被 L2 正则匹到
    ``3711 / 22581 / 11483``，覆盖率约 0.359（而非 0）。
    区分它的是**字母**：letter_ratio 约 0.64。
    """
    header = "ALUMINUM    LANL SESAME #3711 DATED: 22581 11483"
    cov = fn.numeric_coverage(header)
    expect(0.0 < cov < 0.5, f"注释行覆盖率应明显低于 1.0，实测 {cov}")
    lr = fn.letter_ratio(header)
    expect(lr > 0.5, f"注释行字母占比应 > 0.5，实测 {lr}")
    expect(fn.has_letters(header) is True, "注释行应被判为含字母")
    expect(fn.is_payload_line(header) is False, "注释行不应判为 payload 行")


def test_real_file_boundary_detected_by_letters():
    """真实文件：AL_eos 第 0 行含字母 → 头部；第 1 行起全部为 payload 行。"""
    from eosop_pro.core import textio

    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    expect(fn.has_letters(doc.lines[0]) is False,
           "AL_eos 表头行是纯数字，本就不含字母 —— 分界靠行号规则而非字母")
    body = doc.lines[1:]
    bad = [i for i, ln in enumerate(body) if fn.has_letters(ln)]
    expect_eq(bad, [], "AL_eos 的 payload 区不应出现任何含字母的行")


def test_real_file_AL_eos_payload_count():
    """实测基准：AL_eos 全文件 9978 个数，其中表头 4 个 → payload 9974。

    9974 == 2*nr + ne + 2*nr*ne == 2*66 + 74 + 2*66*74
    """
    from eosop_pro.core import textio

    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    total = fn.count_numbers("\n".join(doc.lines))
    expect_eq(total, 9978, "AL_eos 全文件数值个数")
    payload = fn.extract_numbers("\n".join(doc.lines[1:]))
    expect_eq(len(payload), 9974, "剥离表头后的 payload 数值个数")
    expect_eq(2 * 66 + 74 + 2 * 66 * 74, 9974, "表头公式自校验")


def test_real_file_header_numbers_only_four():
    """表头行恰含 4 个数（id / rho0 / nr / ne）—— 证明分区纪律的必要性。"""
    from eosop_pro.core import textio

    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    hdr = fn.extract_numbers(doc.lines[0])
    expect_eq(len(hdr), 4, "AL_eos 表头应恰含 4 个数")
    expect_eq(int(hdr[0]), 37181000, "表号")
    expect(abs(hdr[1] - 2.7) < 1e-9, "rho0")
    expect_eq(int(hdr[2]), 66, "nr")
    expect_eq(int(hdr[3]), 74, "ne")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
