"""A2 —— F6d IONMIX（``*.cn4`` / ``*.cnr``）解析器测试。

两种互斥的 CONRAD 家族格式（均出自 ``src/Ionmix/abjt_03.f`` ``SUBROUTINE OWTF``）:

* ``.cn4`` —— ``isw(21) != 0`` 分支（line 4662–4743），18 块，含完整 EOS；
  头部第 4 行为 ``982 format (i12)``，``ngrups`` **独占一行**。
* ``.cnr`` —— ``isw(8) = 1/12/13`` 分支（line 4598–4621），注释原文
  "original (i.e., late 1986) CONRAD-acceptable format"，7 块，**无** EOS 场；
  头部第 4 行为 ``981 format (4e12.6,i12)``，4 个网格参数与 ``ngrups`` **同行**。

⚠️ 旧版本测试断言"列语义待定"与 ``raw_values`` —— 那是**简化占位版**的行为。
完整解码版已逐块给出名称与单位，故该断言同步升级为
"18 块完整解码 + 计数守恒 + 单位来源已标注"。
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
from eosop_pro.cn4.cnr_io import expected_number_count
from eosop_pro.parsers import ionmix


def test_composition_and_dims_extracted():
    t = ionmix.parse(config.MATTER("Ionmix/al-imx-002.cn4"), "Ionmix/al-imx-002.cn4")
    note = " ".join(t.notes)
    expect("Z=[13]" in note, f"应抽出 Z=[13]（铝），实测 {t.notes}")
    expect("ntemp=21" in note and "ndens=21" in note,
           f"应抽出 (21,21)，实测 {t.notes}")


def test_polystyrene_composition_has_two_elements():
    t = ionmix.parse(config.MATTER("Ionmix/polystyrene-imx-002.cn4"),
                     "Ionmix/polystyrene-imx-002.cn4")
    note = " ".join(t.notes)
    expect("Z=[1, 6]" in note or "Z=[6, 1]" in note,
           f"聚苯乙烯应为 H+C 双组分，实测 {note[:200]}")


def test_cn4_full_block_decode():
    """完整解码版: 18 块全部落位，计数守恒，单位来源可追溯。"""
    t = ionmix.parse(config.MATTER("Ionmix/al-imx-002.cn4"), "Ionmix/al-imx-002.cn4")
    expect_eq(t.kind, "cn4_eos", "cn4 应为 cn4_eos 总表")
    # 12 个二维 EOS 场 + 3 个三维不透明度场
    for name in ("zbar", "dzdt", "p_ion", "p_ele", "dpion_dt", "dpele_dt",
                 "e_ion", "e_ele", "cv_ion", "cv_ele", "deion_dn", "deele_dn"):
        expect(name in t.fields, f"应解出 2D 场 {name}，实测 {sorted(t.fields)}")
    for name in ("kappa_rosseland", "kappa_planck_abs", "kappa_planck_ems"):
        expect(name in t.fields, f"应解出 3D 不透明度 {name}")
    expect(t.n_numbers_seen == t.n_numbers_expected,
           f"计数必须守恒: {t.n_numbers_seen} vs {t.n_numbers_expected}")
    expect("abjt_03.f" in (t.unit_source or ""),
           f"单位来源须指向源码，实测 {t.unit_source!r}")


def test_cn4_unknown_units_declared():
    """``deion_dn`` / ``deele_dn`` 源码自注 ``(not sure)`` -> 单位标 unknown。"""
    from eosop_pro.cn4.units import UNCERTAIN_UNITS
    expect("deion_dn" in UNCERTAIN_UNITS, "deion_dn 单位应标 unknown")
    expect("deele_dn" in UNCERTAIN_UNITS, "deele_dn 单位应标 unknown")
    t = ionmix.parse(config.MATTER("Ionmix/al-imx-002.cn4"), "Ionmix/al-imx-002.cn4")
    note = " ".join(t.notes)
    expect("not sure" in note, f"应在 notes 中声明该不确定，实测 {t.notes}")


def test_all_ionmix_files_parse():
    import os
    root = config.MATTER_DIR / "Ionmix"
    files = sorted(f for f in os.listdir(root)
                   if f.lower().endswith((".cn4", ".cnr")))
    expect(len(files) >= 15, f"Ionmix 下应有 >=15 个文件，实测 {len(files)}")
    for f in files:
        t = ionmix.parse(root / f, f"Ionmix/{f}")
        expect(t is not None, f"{f} 应可解析")
        if f.lower().endswith(".cn4"):
            expect_eq(t.kind, "cn4_eos", f"{f} 应为 cn4_eos")
        else:
            expect_eq(t.kind, "cnr_legacy", f"{f} 应为 cnr_legacy")


def test_cnr_legacy_variant_parsed():
    """``.cnr`` 为 late-1986 CONRAD 格式（981 头部），须能解出组分与计数。"""
    t = ionmix.parse(config.MATTER("Ionmix/al-imx-001.cnr"), "Ionmix/al-imx-001.cnr")
    expect_eq(t.kind, "cnr_legacy", ".cnr 应为 cnr_legacy")
    note = " ".join(t.notes)
    expect("Z=[13]" in note, f"al-imx-001.cnr 应为铝 Z=13，实测 {note[:200]}")
    expect("cnr" in (t.layout_rule or "").lower(), "layout_rule 须标明 cnr 来源")
    # .cnr 不含 EOS 的 12 个二维场 —— 必须显式声明这一局限
    expect("不含" in note and "EOS" in note,
           f".cnr 须声明缺失 EOS 场，实测 {t.notes}")


def test_cnr_ntrad_solved_or_unknown():
    """.cnr 的 ntrad 须由计数守恒反解；不可整除时标 unknown（不猜）。"""
    from eosop_pro.cn4 import parse_cnr
    t = parse_cnr(config.MATTER("Ionmix/al-imx-001.cnr"))
    expect(t.ntrad == 16, f"al-imx-001.cnr 的 ntrad 应为 16，实测 {t.ntrad}")
    t2 = parse_cnr(config.MATTER("Ionmix/xe-005grp-lte.cnr"))
    expect(t2.ntrad is None,
           f"xe-005grp-lte.cnr 余数不可整除 -> ntrad 应为 None，实测 {t2.ntrad}")
    expect("op2tr" in t2.unknown_blocks,
           f"无法切分的块须标 unknown，实测 {t2.unknown_blocks}")

    # 计数守恒（可解时）
    n = expected_number_count(t.ntemp, t.ndens, t.ngrups, t.ntrad)
    expect_eq(n, len(t.raw_tail_values), "cnr 计数须守恒")


def test_cnr_does_not_look_like_cn4():
    """``.cnr`` 的 4e12.6+i12 头部**不得**被 cn4 的 i12 解析器接受。"""
    from eosop_pro.cn4.cn4_io import parse_header, CN4ParseError
    from eosop_pro.core.textio import read_text
    doc = read_text(config.MATTER("Ionmix/al-imx-001.cnr"))
    try:
        parse_header(doc.lines)
        raised = False
    except CN4ParseError:
        raised = True
    expect(raised, ".cnr 头部应被 cn4 解析器拒绝（格式互斥）")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
