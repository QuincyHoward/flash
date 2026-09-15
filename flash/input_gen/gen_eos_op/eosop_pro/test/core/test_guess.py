# -*- coding: utf-8 -*-
"""core.guess —— 盲读猜测层测试（用户 2026-09-15 第十一轮令新增）。

合成用例验证统计基元与分块启发；真实数据用例**惰性发现**（样品缺失
明确 skip 而非 FAIL，与 eosopdata 套件同规约）。
★ 猜测层与 field_checks 事实字典严格分离：本文件同时守护
``render_report`` 输出纯 ASCII（Windows GBK 控制台安全）且必须显式
标注 "GUESS ONLY"（猜测绝不冒充已核查事实）。
"""

import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, expect_in, main

from eosop_pro.guess import (  # noqa: E402
    analyze_file,
    factor_pairs,
    match_fingerprints,
    read_payload_values,
    render_report,
    value_fingerprint,
)

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")


def _write_fixture(name: str, text: str) -> str:
    """测试 fixture 落 ``_out/``（wb + LF：hygiene 扫描范围，禁 CRLF）。"""
    os.makedirs(_OUT, exist_ok=True)
    p = os.path.join(_OUT, name)
    with open(p, "wb") as fh:
        fh.write(text.encode("utf-8"))
    return p


# ── 统计基元 ─────────────────────────────────────────────────────────
def test_factor_pairs_most_square_first():
    """因数对按 |a-b| 升序（最"方"优先）。"""
    pairs = factor_pairs(40)
    expect_in((5, 8), pairs, "40 的因数对缺 (5,8)")
    expect_eq(pairs[0], (5, 8), "最方因数对 (5,8) 应排第一")
    expect_in((1, 40), pairs, "因数对应含 (1,40)")


def test_value_fingerprint_basics():
    """指纹：整值率 / 单调占比 / log10 跨度。"""
    fp = value_fingerprint([1, 2, 3, 4, 5])
    expect_eq(fp["int_like_frac"], 1.0, "整数序列整值率应为 1")
    expect_eq(fp["mono_frac"], 1.0, "严格递增序列单调占比应为 1")
    fp2 = value_fingerprint([1e3, 2e3, 5e3])
    expect(fp2["log10_span"] < 1.0, "同量级序列 log10 跨度应 < 1")
    fp3 = value_fingerprint([0.0, 0.0, 1.0])
    expect_in("zero_frac", fp3, "指纹应含 zero_frac 字段")
    expect_eq(fp3["zero_frac"], 0.6667, "2/3 零值 -> zero_frac=0.6667")


# ── 盲读 ─────────────────────────────────────────────────────────────
def test_read_payload_values_skip_header_and_rescue_fortran_e():
    """文本/注释头剔除 + Fortran E12.6 丢 E 自愈。"""
    p = _write_fixture("guess_fixture_basic.txt",
                       "# comment\n"
                       "header text\n"
                       "1 2 3\n"
                       "4 5 1.234567-101\n")
    vals, widths, prof = read_payload_values(p)
    expect_eq(prof.n_header, 2, "文本/注释头应被剔除")
    expect_eq(len(vals), 6, "payload 值数应为 6")
    expect_eq(widths, [3, 3], "每行 token 数应为 [3, 3]")
    expect_eq(vals[-1], 1.234567e-101, "Fortran 丢 E 数应自愈为 1.234567e-101")


def test_analyze_shape_candidates_and_axis_cols():
    """一致行宽 -> (m,n) 形状候选 + 单调轴样列识别。"""
    rows = []
    for i in range(1, 7):                      # 6 行
        rows.append(" ".join(str(i * 10 + j) for j in range(5)))
    p = _write_fixture("guess_fixture_matrix.txt",
                       "text header\n" + "\n".join(rows) + "\n")
    rep = analyze_file(p)
    expect(rep.rows_consistent, "行宽应一致")
    expect_eq(rep.width_mode, 5, "行宽众数应为 5")
    expect_in((6, 5), rep.shape_candidates, "形状候选应含行优先 (6,5)")
    expect_in((5, 6), rep.shape_candidates, "形状候选应含转置 (5,6)")
    expect_in(0, rep.axis_like_cols, "col0 严格递增且唯一 -> 轴样列")
    expect(rep.factor_pairs, "因数对不应为空")
    expect_eq(rep.total_values, 30, "总元素数应为 30")


def test_zero_runs_and_decade_jumps():
    """零长跑与正-正数量级跳变（潜在块边界）。"""
    vals = ["1", "2", "3", "1.0e5", "2.0e5", "3.0e5",
            "0", "0", "0", "0", "0"]
    p = _write_fixture("guess_fixture_runs.txt", "hdr\n" + " ".join(vals) + "\n")
    rep = analyze_file(p)
    expect(rep.zero_runs, "应检出零长跑")
    expect_eq(rep.zero_runs[0], (6, 11), "零长跑应为 [6:11)")
    expect(rep.decade_jumps, "应检出数量级跳变")
    expect_eq(rep.decade_jumps[0][0], 3, "首个跳变应在 idx 3（3 -> 1e5）")


# ── 指纹匹配（3.2 猜意义/单位的合议核心） ────────────────────────────
def test_match_fingerprints_orders_by_score():
    """量级相近的已知字段排前，且必须带 GUESS ONLY 标注。"""
    seg = value_fingerprint([2.0, 3.0, 4.0, 5.0])
    f_rho = {"field": "tbl.rho", "unit": "g/cm3", "meaning": "density",
             "fp": value_fingerprint([1.0, 2.0, 3.0, 4.0])}
    f_te = {"field": "tbl.Te", "unit": "eV", "meaning": "temperature",
            "fp": value_fingerprint([1e5, 2e5, 3e5, 4e5])}
    out = match_fingerprints([seg], [f_rho, f_te])
    expect(out, "应产出至少一个匹配")
    expect_eq(out[0]["guess_field"], "tbl.rho", "量级相近者应排前")
    expect_in("GUESS ONLY", out[0]["note"], "匹配必须带 GUESS ONLY 标注")
    expect_eq(out[0]["guess_unit"], "g/cm3", "单位应取自登记")


# ── 真实数据（惰性发现，缺失即 skip） ────────────────────────────────
def test_analyze_real_cn4_lazy():
    """真实 cn4 冒烟：payload/因数对/ASCII 报告 + GUESS ONLY 标注。"""
    from eosopdata._samples import first_cn4
    p = first_cn4()
    if p is None:
        return
    rep = analyze_file(p)
    expect(rep.n_payload > 0, "cn4 应有 payload 行")
    expect(rep.factor_pairs, "cn4 值总数应有因数对")
    txt = render_report(rep)
    expect(txt.isascii(), "报告必须纯 ASCII（Windows 控制台安全）")
    expect_in("GUESS ONLY", txt, "报告必须显式标注猜测性质")


def test_analyze_file_missing_file_notes():
    """文件缺失：零值 + note，绝不抛异常。"""
    rep = analyze_file("Z:/no/such/file.txt")
    expect_eq(rep.total_values, 0, "文件缺失应零值")
    expect(rep.notes, "文件缺失必须记 note")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
