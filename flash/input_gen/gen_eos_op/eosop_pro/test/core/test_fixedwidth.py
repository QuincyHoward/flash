"""Phase 1 —— L1 定宽切分测试（与 L2 正则必须给出**一致**结果）。"""

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
from eosop_pro.core import fixedwidth as fw
from eosop_pro.core import fortran_numbers as fn
from eosop_pro.core import textio


def test_mpqeos_header_is_parsed_by_L2_not_fixed_width():
    """实测发现：``.301/.304/.305`` 的**表头行不可定宽切分**。

    其 ID 字段宽为 16 或 17 列（不定），故 16 或 15 的固定切分都会切错。
    但表头全是空格分隔的正数、不存在紧邻负数问题 —— 交给 L2 正则即可。
    """
    doc = textio.read_text(config.MATTER("mat_Al-1.0/FEOS/Al.feos.301"))
    vals = fn.extract_numbers(doc.lines[0])
    expect_eq(len(vals), 4, "表头应恰有 4 个数")
    expect_eq(int(vals[0]), 37170301, "表号")
    expect(abs(vals[1] - 2.7) < 1e-9, f"density={vals[1]}")
    expect_eq(int(vals[2]), 192, "NR")
    expect_eq(int(vals[3]), 69, "NT")
    # 反证：定宽 16 会切错 —— 第二个字段被污染成不可解析的串
    bad = fw.slice_fields(doc.lines[0], width=fw.WIDTH_MPQEOS, count=4)
    expect_eq(
        bad,
        ["37170301", "2.70000000e+00 1", ".92000000e+02 6.", "90000000e+01"],
        "定宽 16 切分的确会污染字段（这就是它不可用的证据）",
    )
    parse_failed = False
    try:
        fn.parse_fortran_float(bad[1])
    except ValueError:
        parse_failed = True
    expect(parse_failed, "被污染的字段应无法解析为 float —— 证明定宽 16 不可用")


def test_infer_payload_width_al_is_15():
    """Al.feos.301 payload 行 60 字符 → W = 60/4 = 15。"""
    doc = textio.read_text(config.MATTER("mat_Al-1.0/FEOS/Al.feos.301"))
    payload = [ln for ln in doc.lines[1:] if ln.strip()]
    w = fw.infer_payload_width(payload, fw.FIELDS_MULTI)
    expect_eq(w, 15, "Al.feos.301 字段宽应为 15")
    expect_eq(fw.fields_per_line(len(payload[0]), w), 4)
    vals = fw.values_from_lines(payload, width=w)
    expect(len(vals) > 39000, f"payload 数值个数应接近 40005，实测 {len(vals)}")


def test_infer_payload_width_he_is_16():
    """对照：mat_He/Untitled.304 payload 行 64 字符 → W = 64/4 = 16。

    → 同一家族内字段宽**并不统一**，必须逐文件推断。
    """
    doc = textio.read_text(config.MATTER("mat_He/Untitled.304"))
    payload = [ln for ln in doc.lines[1:] if ln.strip()]
    w = fw.infer_payload_width(payload, fw.FIELDS_MULTI)
    expect_eq(w, 16, "mat_He/Untitled.304 字段宽应为 16")
    expect_eq(fw.fields_per_line(len(payload[0]), w), 4)


def test_multi_line1_4x15():
    """实测 mat_Al-1.0/AL_eos 表头（15 字符宽，因负号吃空格而字段不齐）。"""
    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    vals = fw.slice_values(doc.lines[0], width=fw.WIDTH_MULTI, count=4)
    expect_eq(len(vals), 4)
    expect_eq(int(vals[0]), 37181000)
    expect(abs(vals[1] - 2.7) < 1e-9)
    expect_eq(int(vals[2]), 66)
    expect_eq(int(vals[3]), 74)


def test_L1_and_L2_agree_on_packed_negatives():
    """紧邻负数：L1（定宽）必须与 L2（正则）给出同一组数。"""
    line = "-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01"
    l1 = fw.slice_values(line, width=fw.WIDTH_MULTI, count=4)
    l2 = fn.extract_numbers(line)
    expect_eq(len(l1), 4, "L1 应得 4 个数")
    expect_eq(len(l2), 4, "L2 应得 4 个数")
    for a, b in zip(l1, l2):
        expect(abs(a - b) < 1e-12, f"L1={a} L2={b} 不一致")


def test_L1_and_L2_agree_on_whole_AL_eos_payload():
    """整文件级一致性：AL_eos payload 两种路径都应得 9974 个数。"""
    doc = textio.read_text(config.MATTER("mat_Al-1.0/AL_eos"))
    body = doc.lines[1:]
    via_l1 = fw.values_from_lines(body, width=fw.WIDTH_MULTI)
    via_l2 = fn.extract_numbers("\n".join(body))
    expect_eq(len(via_l1), 9974, "L1 计数")
    expect_eq(len(via_l2), 9974, "L2 计数")
    mismatch = [i for i, (a, b) in enumerate(zip(via_l1, via_l2)) if abs(a - b) > 1e-9]
    expect_eq(mismatch[:5], [], "L1 与 L2 数值逐点一致（前 5 个不一致的索引）")


def test_fields_per_line():
    expect_eq(fw.fields_per_line(60, 15), 4)
    expect_eq(fw.fields_per_line(64, 16), 4)
    expect_eq(fw.fields_per_line(75, 15), 5, "Hyades 每行 5 字段")
    expect_eq(fw.fields_per_line(59, 15), 3, "含 1 字符尾部空白时只算 3 个满字段")


def test_slice_fields_skips_empty_tail():
    """尾部不足一个字段时不应产生空字段。"""
    fields = fw.slice_fields("  " + "1.0".ljust(15), width=15, count=None)
    expect_eq(len(fields), 1, "只有 1 个有效字段")


def test_hyades_5x15():
    """实测 eos_41.dat 的 payload 行宽 75 = 5×15。"""
    doc = textio.read_text(config.MATTER("hyades/sesame/eos_41.dat"))
    widths = sorted({len(ln) for ln in doc.lines[:40]})
    expect(75 in widths, f"应出现 75 字符行，实测 widths={widths}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
