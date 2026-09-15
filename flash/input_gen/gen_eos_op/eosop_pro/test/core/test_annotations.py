"""Phase 2 —— 注释 / 文字说明证据通道测试。

覆盖两类证据：
* **伴随文件**（``.info`` / ``.inhalt`` / ``.readme`` / ``README`` / ``#xxx``）
* **文件内嵌注释**（LEDCOP 的单位行、``.coldopacity`` 的两行自描述表头、幂律说明）

最重要的一条是 :func:`test_thermos_readme_declares_zeff_units` ——
它把「Z̄ 表的 T 单位」从**猜测**变成**声明**。
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
from eosop_pro.core import textio
from eosop_pro.core.annotations import canon_unit, extract_annotations
from eosop_pro.registry.annotation_store import AnnotationStore


def _ann(rel: str):
    return extract_annotations(textio.read_text(config.MATTER(rel)), source=rel)


# ── 伴随文件证据 ────────────────────────────────────────────────
def test_au_info_full_evidence():
    """``mat_Au-1.0/AU_info``（德语）—— 材料 + 群数 + 单位 + 表号→类型映射。"""
    a = _ann("mat_Au-1.0/AU_info")
    expect_eq(a.material_name, "Gold", "应抽出材料名 GOLD")
    expect_eq(a.dims.get("NT"), 20)
    expect_eq(a.dims.get("NR"), 20)
    expect_eq(a.dims.get("NP"), 1000)
    expect_eq(a.dims.get("NG"), 20, "「20 GRUPPEN ZWISCHEN 0 UND 5 KEV」")
    expect_eq(a.units.get("group_bound"), "keV", "群上限单位应规范化为 keV")
    expect_eq(
        a.table_ids,
        {"Z": 27002003, "P": 27003003, "R": 27004003, "E": 27005003},
        "MATERIALNUMMERN 段的 Z/P/R/E → 表号映射",
    )
    expect("SNOP" in a.provenance, "应由表号字母反推 SNOP 来源")


def test_opbe_inhalt_is_the_split_key():
    """``SNOP/opbe.inhalt`` 声明了 opbe 里其实有 **4 张表** —— 拆分的关键。"""
    a = _ann("SNOP/opbe.inhalt")
    expect_eq(a.dims.get("NG"), 40)
    expect_eq(a.dims.get("NT"), 20)
    expect_eq(a.dims.get("NR"), 20)
    expect_eq(a.dims.get("NP"), 6000)
    expect_eq(
        a.table_ids,
        {"NPLA": 20203000, "NROSS": 20204000, "NEPS": 20205000, "NZ": 20202000},
        "4 个表号 = opbe 的拆分键",
    )
    g = a.group_scheme
    expect(g is not None, "应抽到 GRUPPENEINTEILUNG 群方案")
    expect_eq(g.scheme_id, 15, "方案号 15")
    expect_eq(g.ng, 40, "NG=40")
    expect("1240EV" in g.range_text, f"区间文本，实测 {g.range_text!r}")
    expect_eq(len(g.bounds_eV), 41, "NG 个群应有 NG+1=41 个边界")
    expect(g.bounds_eV[0] > 0, f"首个边界应为正，实测 {g.bounds_eV[0]}")


def test_be_eos_info_decodes_e_and_i_suffix():
    """``BE_eos.info`` 解码 ``_e``/``_i`` 后缀 → IME=304 / IMI=305。"""
    a = _ann("mat_Be-1.0/BE_eos.info")
    expect_eq(a.material_name, "Beryllium", "从「(Beryllium)」抽出材料名")
    expect_eq(a.material_a, 9.012, "Atomic mass 9.012")
    expect_eq(a.dims.get("IME"), 304, "电子表 = 304")
    expect_eq(a.dims.get("IMI"), 305, "离子表 = 305")
    expect("split_EOS_table" in a.provenance, "来源 = split_EOS_table")
    expect(any("BE_eos_e and BE_eos_i" in n for n in a.notes), "应记录伴随文件清单")


def test_mix20kev_info_composition_and_groups():
    a = _ann("mat_Others/Mix20keV.info")
    expect_eq(a.material_name, "Doped Beryllium")
    expect_eq(a.dims.get("NG"), 30, "「extended to 20 keV (30 groups)」")
    expect_eq(a.units.get("group_bound"), "keV")
    expect_eq(a.table_ids.get("IP"), 20143000)
    expect_eq(a.table_ids.get("IR"), 20144000)
    expect_eq(a.table_ids.get("IEPS"), 20145000)
    expect(a.composition and "75.00 % Beryllium" in a.composition,
           f"应抽出质量组分，实测 {a.composition!r}")
    expect("SNOP" in a.provenance and "MPQeos" in a.provenance, "生成链 SNOP + MPQEOS")


# ── 文件内嵌注释证据 ────────────────────────────────────────────
def test_ledcop_inline_unit_declaration():
    """``ATOMIC/Al.txt`` 第 3 行直接声明整族单位。"""
    a = _ann("ATOMIC/Al.txt")
    expect_eq(a.units.get("T"), "keV")
    expect_eq(a.units.get("rho"), "g/cm3", "gm/cc 应规范化为 g/cm3")
    expect_eq(a.units.get("kappa"), "cm2/g", "cm**2/gm 应规范化为 cm2/g")
    expect_eq(a.dims.get("NT"), 69)
    expect_eq(a.dims.get("NR"), 50)
    expect_eq(a.dims.get("NMAT"), 1)
    expect("LEDCOP/Atomic" in a.provenance)


def test_coldopacity_two_line_self_describing_header():
    """``ColdOpacity/*.coldopacity`` 的前两行就是「列名 / 单位」。"""
    a = _ann("ColdOpacity/Al.coldopacity")
    expect_eq(a.units.get("Eph"), "eV", "光子能量单位 eV")
    expect_eq(a.units.get("miu"), "cm2/g", "质量衰减系数单位 cm2/g")


def test_czeff_readme_unit_history_takes_current_value():
    """``mat_CELIA/C.ZEFF.readme`` 是**单位变更史**，不能取第一个单位。

    原文：``Orginal C.ZEFF with Te in eV. Changed to keV.``
    → 现行单位是 **keV**（若取第一个会错成 eV）。
    """
    a = _ann("mat_CELIA/C.ZEFF.readme")
    expect_eq(a.units.get("T"), "keV", "现行单位应为 keV（取 Changed to）")
    expect(any("unit history" in n and "eV" in n and "keV" in n for n in a.notes),
           f"应记录单位变更史，实测 notes={a.notes}")


def test_ge_readme_powerlaw_units():
    a = _ann("mat_Ge/Readme.txt")
    expect_eq(a.units.get("T"), "eV")
    expect_eq(a.units.get("rho"), "g/cm3")
    expect_eq(a.units.get("kappa"), "cm2/g")


# ── ★ 解决 Z̄ 单位歧义的声明 ─────────────────────────────────────
def test_thermos_readme_declares_zeff_units():
    """★ ``Thermos/Readme.txt`` 明写 ``*_Z.dat``=eV、``*_Zeff.dat``=keV。

    这是 ``Al_Zeff.dat`` 与 ``Al_Z.dat``（表头/行数完全相同、logT 差 3.0）
    的**唯一可靠区分依据** —— 靠声明，不靠猜测。
    """
    a = _ann("Thermos/Readme.txt")
    expect_eq(a.file_unit_hints.get("_Z.dat"), "eV", "`*_Z.dat` 温度单位 eV")
    expect_eq(a.file_unit_hints.get("_Zeff.dat"), "keV", "`*_Zeff.dat` 温度单位 keV")
    expect("Thermos" in a.provenance)


def test_store_resolves_zeff_vs_z_units_by_declaration():
    """端到端：伴随索引把文件名模式提示应用到 Thermos 材料文件上。"""
    st = AnnotationStore().build()
    for el in ("Al", "Au", "Be", "C"):
        eff = st.unit_hint_for(f"Thermos/mat_{el}/{el}_Zeff.dat")
        raw = st.unit_hint_for(f"Thermos/mat_{el}/{el}_Z.dat")
        expect_eq(eff, "keV", f"{el}_Zeff.dat 应为 keV")
        expect_eq(raw, "eV", f"{el}_Z.dat 应为 eV")


def test_store_longest_pattern_wins():
    """``_Zeff.dat`` 与 ``_Z.dat`` 都能后缀匹配 ``..._Zeff.dat``？

    不会 —— ``..._Zeff.dat`` 不以 ``_Z.dat`` 结尾。但仍需保证取最长命中，
    以免将来加入更短模式时误配。
    """
    st = AnnotationStore().build()
    hints = st.merged_file_unit_hints("Thermos/mat_Al/Al_Zeff.dat")
    expect("_Zeff.dat" in hints and "_Z.dat" in hints,
           f"两个提示都在（来自同一 README），实测 {hints}")
    expect_eq(st.unit_hint_for("Thermos/mat_Al/Al_Zeff.dat"), "keV",
              "最长命中 _Zeff.dat → keV")


# ── 伴随文件索引与配对 ──────────────────────────────────────────
def test_store_pairs_stem_and_dir_level_files():
    st = AnnotationStore().build()
    srcs = {a.source for a in st.for_file("mat_Be-1.0/BE_eos_e")}
    expect("mat_Be-1.0/BE_eos.info" in srcs, f"前缀配对应命中，实测 {srcs}")
    expect("mat_Be-1.0/README" in srcs, "目录级 README 应命中")

    srcs2 = {a.source for a in st.for_file("mat_DT-1.0/DT20keV.PLANCK")}
    expect("mat_DT-1.0/DT20keV.info" in srcs2, f"前缀配对（Be20keV 式），实测 {srcs2}")

    srcs3 = {a.source for a in st.for_file("mat_CELIA/C.ZEFF")}
    expect("mat_CELIA/C.ZEFF.readme" in srcs3, f"精确 stem 配对，实测 {srcs3}")


def test_store_dir_readme_covers_subtree():
    """Thermos/Readme.txt 在父目录，数据在子目录 —— 目录级 README 应覆盖子树。"""
    st = AnnotationStore().build()
    srcs = {a.source for a in st.for_file("Thermos/mat_Al/Al_Zeff.dat")}
    expect("Thermos/Readme.txt" in srcs, f"父目录 README 应覆盖子目录，实测 {srcs}")


def test_store_table_id_kinds_from_companions():
    st = AnnotationStore().build()
    kinds = st.table_id_kinds()
    expect_eq(kinds.get(20203000), "PLANCK")
    expect_eq(kinds.get(20204000), "ROSSELAND")
    expect_eq(kinds.get(20205000), "EMISSIVITY")
    expect_eq(kinds.get(20202000), "ZEFF")
    expect_eq(kinds.get(27002003), "ZEFF", "AU_info 的 Z: 映射")
    expect_eq(kinds.get(27003003), "PLANCK")
    expect_eq(kinds.get(27004003), "ROSSELAND")
    expect_eq(kinds.get(20143000), "PLANCK", "Mix20keV 的 IP=")


def test_store_summary_is_plausible():
    st = AnnotationStore().build()
    s = st.summary()
    expect(s["companion_files"] >= 40, f"伴随文件数应 >= 40，实测 {s}")
    expect_eq(s["skipped"], 0, f"不应有读取失败的伴随文件：{st.skipped}")
    expect(s["with_units"] >= 6, f"至少 6 个伴随文件声明单位，实测 {s}")


# ── 健壮性 ─────────────────────────────────────────────────────
def test_extract_never_raises_on_garbage():
    """抽取器对任意垃圾输入都必须**降级为 notes**，绝不抛异常中断主流程。"""
    from eosop_pro.core.annotations import extract_from_text

    for junk in ("", "###", "\x00\x01\x02", "a" * 5000, "NT = ???", "Z:xxx;P:yyy"):
        ann = extract_from_text(junk, source="junk")
        expect(ann is not None, f"垃圾输入 {junk[:20]!r} 应返回 Annotation 而非异常")


def test_canon_unit_mapping():
    expect_eq(canon_unit("kev"), "keV")
    expect_eq(canon_unit("KEV"), "keV")
    expect_eq(canon_unit("ev"), "eV")
    expect_eq(canon_unit("gm/cc"), "g/cm3")
    expect_eq(canon_unit("cm**2/gm"), "cm2/g")
    expect_eq(canon_unit("weirdunit"), "weirdunit", "未知单位原样返回")
    expect_eq(canon_unit(""), "")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
