"""Phase 1 —— L3 锚点测试。

**核心纪律**：锚点匹配结果绝不进入数值数组。
本文件最重要的一条是 :func:`test_header_numbers_must_not_leak_into_payload` ——
它直接演示了「若不先按锚点剥离表头，L2 会把 SESAME 号/日期当成数据」。
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
from eosop_pro.core import anchors as an
from eosop_pro.core import fortran_numbers as fn
from eosop_pro.core import textio


def test_header_numbers_must_not_leak_into_payload():
    """★ 核心陷阱：Hyades 注释行含 3 个数字。

    ``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483``
    若直接对整文件跑 L2，会多出 ``3711 / 22581 / 11483`` 三个伪数据。
    正确做法：先用锚点确认这是注释行 → 跳过 → 只对 payload 跑 L2/L1。
    """
    comment = "ALUMINUM    LANL SESAME #3711 DATED: 22581 11483"
    leaked = fn.extract_numbers(comment)
    expect_eq(leaked, [3711.0, 22581.0, 11483.0],
              "证明：注释行确实含 3 个会被误当数据的数字")

    # 锚点确认它是注释行
    expect(an.find(comment, "sesame_comment") is not None, "应命中 LANL SESAME 锚点")
    expect(an.find(comment, "dated") is not None, "应命中 DATED 锚点")

    # 真实文件上验证：剥离两行表头后，payload 里不再有这些数
    doc = textio.read_text(config.MATTER("hyades/sesame/eos_41.dat"))
    expect(doc.lines[0].startswith("ALUMINUM"), f"行0 应为注释，实测 {doc.lines[0]!r}")
    m = an.find(doc.lines[0], "sesame_number")
    expect(m is not None, "应能从注释行抽到 SESAME 号")
    expect_eq(m.group(1), "3711", "SESAME 号应为 3711")

    payload_vals = fn.extract_numbers("\n".join(doc.lines[2:]))
    total_vals = fn.extract_numbers("\n".join(doc.lines))

    # 精确断言：行0 含 3 个数、行1 含 5 个数 → 整读与 payload 的差应为 8
    h0 = len(fn.extract_numbers(doc.lines[0]))
    h1 = len(fn.extract_numbers(doc.lines[1]))
    expect_eq(h0, 3, "行0（注释）含 3 个数")
    expect_eq(h1, 5, "行1（id/zbar/abar/rho0/L）含 5 个数")
    expect_eq(len(total_vals) - len(payload_vals), h0 + h1,
              "整读与 payload 的差应恰为两行表头的数字数")


def test_sesame_number_two_forms():
    """``#3711`` 与 ``2700-304`` 两种写法都要能抽。"""
    m1 = an.find("ALUMINUM    LANL SESAME #3711 DATED: 22581 11483", "sesame_number")
    expect_eq(m1.group(1), "3711")
    expect_eq(m1.group(2), None, "无子表号")

    m2 = an.find("GOLD        LANL SESAME 2700-304 DATED: 81678 101582", "sesame_number")
    expect_eq(m2.group(1), "2700", "基号")
    expect_eq(m2.group(2), "304", "子表号 304 = 电子表")

    m3 = an.find("POLY        LANL SESAME #17171 DATED:  21393  21393", "sesame_number")
    expect_eq(m3.group(1), "17171", "聚乙烯 SESAME 号")


def test_ledcop_units_anchor():
    """整族单位声明（13 个 ATOMIC/*.txt 都有）。"""
    line = " Opacities in cm**2/gm, T in keV, density in gm/cc"
    m = an.find(line, "ledcop_units")
    expect(m is not None, "应命中 LEDCOP 单位声明")
    expect_eq(m.group(1), "keV", "温度单位 keV")
    expect_eq(m.group(2), "gm/cc", "密度单位 gm/cc")


def test_ledcop_dims_anchors():
    line = "Number of T =  69  Number of rho =  50  Number of materials =   1"
    expect_eq(an.find(line, "ledcop_n_t").group(1), "69")
    expect_eq(an.find(line, "ledcop_n_rho").group(1), "50")
    expect_eq(an.find(line, "ledcop_n_mat").group(1), "1")


def test_snop_table_id_mapping_anchor():
    """★ AU_info 的 ``Z:27002003; P:27003003; R:27004003`` 是**表号→类型**的权威映射。"""
    text = " **   Z:27002003; P:27003003; R:27004003  ************"
    pairs = [(m.group(1), m.group(2)) for m in an.find_all(text, "snop_table_id")]
    expect_eq(pairs, [("Z", "27002003"), ("P", "27003003"), ("R", "27004003")],
              "应抽出 3 组 表号/类型 映射")


def test_snop_groups_german_anchor():
    line = " *** 20 GRUPPEN ZWISCHEN 0 UND 5 KEV      ************"
    m = an.find(line, "snop_groups_de")
    expect(m is not None, "应命中德语群数声明")
    expect_eq(m.group(1), "20", "NG")
    expect_eq(m.group(2), "0", "下限")
    expect_eq(m.group(3), "5", "上限")
    expect_eq(m.group(4), "KEV", "单位")


def test_snop_group_scheme_anchor():
    line = "GRUPPENEINTEILUNG 15: NG=40 (0-1240EV) (BE SCHWANDA)"
    m = an.find(line, "snop_group_scheme")
    expect(m is not None, "应命中群划分方案")
    expect_eq(m.group(1), "15", "方案号")
    expect_eq(m.group(2), "40", "NG=40")
    expect("1240EV" in m.group(3), f"区间文本，实测 {m.group(3)!r}")


def test_info_n_groups_declared_in_keV():
    """Mix20keV/Be20keV/DT20keV.info 的模板句（注意原文跨行）。"""
    text = (
        "Standard settings, except that group ranges have been extended to 20 keV (30\n"
        "groups)\n"
    )
    m = an.find(text, "info_n_groups_keV")
    expect(m is not None, "应能跨行命中（\\s 匹配换行）")
    expect_eq(m.group(1), "20", "上限 20 keV")
    expect_eq(m.group(2), "30", "30 群")


def test_info_composition_anchor():
    text = "Mass composition: 75.00 % Beryllium, 15.00 % Bromide, 10.00 % Sodium"
    m = an.find(text, "info_mass_comp")
    expect(m is not None)
    expect("75.00 % Beryllium" in m.group(1), f"实测 {m.group(1)!r}")


def test_info_ime_imi_anchor():
    """BE_eos.info 解码 ``_e`` / ``_i`` 后缀 → IME=304 / IMI=305。"""
    text = (
        "   IEOS table for electrons            (IME=304)\n"
        "   IEOS table for ions                 (IMI=305)\n"
    )
    expect_eq(an.find(text, "info_ime").group(1), "304")
    expect_eq(an.find(text, "info_imi").group(1), "305")


def test_powerlaw_units_anchor_from_ge_readme():
    """mat_Ge/Readme.txt 显式给出单位 —— 单位『声明』而非『猜测』。"""
    text = (
        "REM equation k=e^a*T^b*rho^c\n"
        "REM where e=2.71828, T in eV, rho in g/cc, k in cm2/g\n"
    )
    expect(an.find(text, "powerlaw_eq") is not None, "应命中幂律方程")
    m = an.find(text, "powerlaw_units")
    expect(m is not None, "应命中单位声明")
    expect_eq(m.group(1), "eV")
    expect_eq(m.group(2), "g/cc")
    expect_eq(m.group(3), "cm2/g")


def test_material_block_anchor():
    m = an.find("MATERIAL MID9", "material_block")
    expect(m is not None)
    expect_eq(m.group(1), "MID9")


def test_real_au_info_anchors_together():
    """在真实 AU_info 上一次性验证 4 个锚点协同工作。"""
    doc = textio.read_text(config.MATTER("mat_Au-1.0/AU_info"))
    text = "\n".join(doc.lines)

    expect(an.find(text, "snop_input_hdr") is not None, "应有 EINGANGSPARAMETER")
    expect(an.find(text, "snop_matnummern") is not None, "应有 MATERIALNUMMERN")

    g = an.find(text, "snop_groups_de")
    expect(g is not None, "应抽到群数声明")
    expect_eq(g.group(1), "20", "NG=20")
    expect(g.group(4).upper() == "KEV", f"单位应含 KEV，实测 {g.group(4)!r}")

    ids = {m.group(1): m.group(2) for m in an.find_all(text, "snop_table_id")}
    expect_eq(ids.get("Z"), "27002003", "Zeff 表号")
    expect_eq(ids.get("P"), "27003003", "Planck 表号")
    expect_eq(ids.get("R"), "27004003", "Rosseland 表号")
    expect_eq(ids.get("E"), "27005003", "发射率表号")


def test_real_eos_comment_anchor():
    doc = textio.read_text(config.MATTER("hyades/sesame/eos_41.dat"))
    expect(an.find(doc.lines[0], "sesame_comment") is not None)
    q = textio.read_text(config.MATTER("hyades/qeos/qeos_52.dat"))
    expect(an.find(q.lines[0], "qeos_comment") is not None,
           f"qeos 注释行应命中 QEOS 锚点，实测 {q.lines[0]!r}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
