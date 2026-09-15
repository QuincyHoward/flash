# -*- coding: utf-8 -*-
"""eosop 控制字典（``field_checks``）的**结构与状态守护**测试。

标记规约（用户 2026-09-15 第二次裁定：**标记只有 uk/uv 两个**）
----
* ``uk`` —— 无来源确认（没有可指认的文献/文档/文件内声明）；
* ``uv`` —— 未人工核查；
* 有来源且已人工核查 -> **标记整体省略**（:func:`tags_label` 返回 ""，
  当前只有 cn4 全 18 块）；
* 用户将挨个人工核查，手动把 ``checked`` 翻为 True 后标记即消失；
* 未来未知格式经 :func:`register_family` 注册进字典，即可被
  gridmap 绘图/报告链路自动采用（不得绕过字典）。

来源规约（用户 2026-09-15 补充裁定：**source 必须下探到一级出处**）
----
* ``kind`` 取受控词表 KIND_*（in-file declaration / primary document /
  source code / parser-measured / code-derived / none）；
* ``source`` 为长文本溯源详述，只引用一级出处（文件内声明 / ``doc/``
  权威手册 + 抽取文本路径 / 源码行号 / 派生公式）；
* ⚠️ ``docs/20`` 手册是中间产物，任何 ``source`` 都**不得**引用它
  （本文件守护，见 ``test_every_entry_has_meaning_unit_and_source``）；
* ``doc`` 是由 ``kind`` 派生的只读属性（单一事实来源），白名单比对
  直接用 ``fc.doc``；
* 字典 Markdown 全文（``docs/eosop变量控制字典.md``）与字典**逐字
  同步**（本文件守护；字典改动后重跑
  ``python -m eosop_pro.registry.field_checks`` 再生成）。
"""

import os
import sys

# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner                                                    # noqa: F401
from _runner import expect, expect_eq, expect_in, main            # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

from eosopdata.step02_families._family_plot_common import (  # noqa: E402
    FAMILY_PATTERNS)

from eosop_pro.registry.field_checks import (                     # noqa: E402
    DOC_DOCUMENTED, DOC_UNKNOWN,
    DICT_DOC_RELPATH, FIELD_CHECKS, KIND_CODE, KIND_DERIVED, KIND_DOC,
    KIND_IN_FILE, KIND_MEASURED, KIND_NONE,
    checked_families, dump_markdown, family_check_stats, field_check,
    register_family, tags_label)

_KNOWN_KINDS = frozenset({KIND_IN_FILE, KIND_DOC, KIND_CODE,
                          KIND_MEASURED, KIND_DERIVED, KIND_NONE})


def test_ionmix_cn4_all_18_entries_fully_verified():
    """cn4 的 18 块：有源 + 已人工核查 -> **标记整体省略**（tags==""）。"""
    st = family_check_stats("ionmix")
    expect_eq(st["total"], 18, f"ionmix 应登记 18 块，实得 {st['total']}")
    expect_eq(st["checked"], 18, f"checked 应为 18，实得 {st['checked']}")
    expect_eq(st["unchecked"], 0, "ionmix 不应有 unchecked 条目")
    for fld in ("T", "nion", "zbar", "dzdt", "p_ion", "p_ele", "dpion_dt",
                "dpele_dt", "e_ion", "e_ele", "cv_ion", "cv_ele",
                "deion_dn", "deele_dn", "engrup",
                "opac_rosseland", "opac_planck_abs", "opac_planck_ems"):
        fc = field_check("ionmix", fld)
        expect(fc.checked, f"ionmix.{fld} 应 checked=True")
        expect_eq(fc.doc, DOC_DOCUMENTED, f"ionmix.{fld} 应有来源确认")
        expect_eq(tags_label(fc), "",
                  f"ionmix.{fld} 标记应整体省略（有源+已核查），实得 "
                  f"{tags_label(fc)!r}")
        expect(fc.meaning and fc.unit, f"ionmix.{fld} 缺 meaning/unit")
        expect("abjt_03.f" in fc.source or "guide" in fc.source,
               f"ionmix.{fld} 缺溯源（abjt_03.f / guide）: {fc.source}")


def test_every_step02_family_registered():
    """SAMPLE_PATTERNS 里的 11 个族都必须在字典里登记（防腐烂）。"""
    for fam in FAMILY_PATTERNS:
        expect_in(fam, FIELD_CHECKS, f"族 {fam} 未登记进 FIELD_CHECKS")


# 有源条目白名单（kind != "none" 即视为有源 -> doc）。
# None = 该族全部条目有源；frozenset = 仅列出的条目（其余无源 -> uk）。
_SOURCE_WHITELIST: dict[str, "frozenset[str] | None"] = {
    "ionmix": None,          # 全 18 块：abjt_03.f 行号 + IONMIX 指南（source code）
    "multi_inverted_eos": frozenset({"rho", "de", "P", "E", "e0_cold",
                                     "de_energy", "T"}),
    #   MULTI SESAME docx「参数单位制」节逐字单位（primary document）
    "multi_opacity": frozenset({"rho", "Te", "kappa"}),
    #   同 docx logloglog 节；Z 段（NZ kind）语义待核 -> uk
    "hyades_eos": frozenset({"rho", "Te", "P", "E", "kappa"}),
    "hyades_opacity": frozenset({"rho", "Te", "P", "E", "kappa"}),
    "sesame_dat": frozenset({"rho", "Te", "P", "E", "kappa"}),
    #   Hyades doc 逐字单位；raw_tail 无源 -> uk
    "mpqeos": frozenset({"rho", "Te", "P", "E"}),
    #   MPQeos/SESAME 节单位+换算式；Z 段自述负值待核（R3）-> uk
    "ledcop_atomic": frozenset({"rho", "Te", "Ross", "Planck"}),
    #   文件头第 3 行 'Opacities in cm**2/gm, T in keV, density in gm/cc'
    "ledcop_zeff": frozenset({"rho", "Te", "NoFree", "AvSqFree"}),
    #   docx Zeff 节（log 坐标 + keV）；NoFree/AvSqFree = LANL TOPS FAQ
    #   Q1/Q7 逐字定义（2026-09-15 联网核查）
    "snop_input": frozenset({"T1", "T2", "X1", "X2", "FG"}),
    #   SNOP.MANUAL 逐字（X1/X2 = photon energy bounds）
    "coldopacity": frozenset({"Eph", "miu", "*"}),
    #   逐文件两行头 '#<name>' + '#<unit>'
    "hugoniot": None,        # 逐文件 '# name [unit]' 注释头逐列声明
    "derived_axes": frozenset({"n_e"}),
    #   代码内派生公式 n_e = rho*N_A*Zbar/A（code-derived）
}


def test_source_confirmation_matches_whitelist():
    """来源确认状态必须与白名单**精确一致**（多翻/漏翻都 FAIL）。"""
    for fam, entries in FIELD_CHECKS.items():
        wl = _SOURCE_WHITELIST.get(fam, frozenset())
        for fld, fc in entries.items():
            should = (wl is None) or (fld in wl)
            expect_eq(fc.doc,
                      DOC_DOCUMENTED if should else DOC_UNKNOWN,
                      f"{fam}.{fld} 来源确认状态与白名单不符（doc={fc.doc}）")


def test_second_tier_all_uv_except_cn4():
    """人工核查：除 cn4 外**所有族所有条目** checked=False（显示 uv）。"""
    for fam, entries in FIELD_CHECKS.items():
        if fam == "ionmix":
            continue
        for fld, fc in entries.items():
            expect(not fc.checked,
                   f"{fam}.{fld} 不应标记 checked（只有 cn4 完成人工核查）")
            expect_eq(tags_label(fc), "uv" if fc.doc == DOC_DOCUMENTED
                      else "uk, uv",
                      f"{fam}.{fld} 标记折叠不符（doc={fc.doc}）")


def test_tags_label_folding_rules():
    """``tags_label`` 折叠规则逐例锁定（标记只有 uk/uv 两个）。"""
    # 有源 + 已核查 -> 省略
    expect_eq(tags_label(field_check("ionmix", "zbar")), "")
    # 有源（文件内声明）+ 未核查 -> 只显示 uv
    expect_eq(tags_label(field_check("ledcop_atomic", "Te")), "uv")
    expect_eq(tags_label(field_check("coldopacity", "miu")), "uv")
    expect_eq(tags_label(field_check("hugoniot", "P")), "uv")
    # 有源（一级说明文档）+ 未核查 -> 只显示 uv
    expect_eq(tags_label(field_check("multi_inverted_eos", "P")), "uv")
    expect_eq(tags_label(field_check("hyades_eos", "P")), "uv")
    expect_eq(tags_label(field_check("mpqeos", "P")), "uv")
    expect_eq(tags_label(field_check("snop_input", "X1")), "uv")
    expect_eq(tags_label(field_check("ledcop_zeff", "NoFree")), "uv")
    expect_eq(tags_label(field_check("ledcop_zeff", "AvSqFree")), "uv")
    # 有源（代码派生公式）+ 未核查 -> 只显示 uv
    expect_eq(tags_label(field_check("derived_axes", "n_e")), "uv")
    # 无源 + 未核查 -> uk, uv
    expect_eq(tags_label(field_check("mpqeos", "Z")), "uk, uv")
    expect_eq(tags_label(field_check("feos_native", "raw_values")), "uk, uv")


def test_accessor_fallback_for_dynamic_columns():
    """未登记列名走 ``"*"`` 兜底：coldopacity 兜底列有源（uv）；
    generic_curve / 未注册族无源（uk, uv）—— 查询永不崩溃。"""
    fc = field_check("coldopacity", "some_new_column")
    expect(not fc.checked, "动态列不应被当作已核查")
    expect_eq(tags_label(fc), "uv",
              "coldopacity 兜底列由逐文件两行头声明 -> uv")
    expect_eq(fc.unit, "unknown", "动态列单位应为 unknown（不猜）")
    fc2 = field_check("generic_curve", "col3")
    expect_eq(tags_label(fc2), "uk, uv", "generic_curve 动态列应 uk, uv")
    fc3 = field_check("family_not_registered_at_all", "x")
    expect(not fc3.checked, "未注册族查询应返回 unchecked 兜底")
    expect_eq(tags_label(fc3), "uk, uv", "未注册族兜底应 uk, uv")
    expect_eq(fc3.unit, "unknown", "未注册族兜底单位应为 unknown")


def test_register_family_for_future_unknown_formats():
    """未来未知格式经 register_family 注册后立即生效（且防误覆盖）。"""
    fake = {"x": field_check("generic_curve", "anything"),
            "*": field_check("generic_curve", "anything")}
    try:
        register_family("__test_future_family__", fake)
        expect_in("__test_future_family__", FIELD_CHECKS)
        fc = field_check("__test_future_family__", "x")
        expect_eq(tags_label(fc), "uk, uv", "新注册族未核查 -> uk, uv")
        try:
            register_family("__test_future_family__", fake)
            raise AssertionError("重复注册（无 overwrite）应拒绝")
        except ValueError:
            pass
    finally:
        FIELD_CHECKS.pop("__test_future_family__", None)   # 同进程守护
    expect("__test_future_family__" not in FIELD_CHECKS, "测试后应清理")


def test_every_entry_has_meaning_unit_and_source():
    """三条描述字段（meaning/unit/source）逐条非空 —— 保证报告可读。

    来源规约守护（用户 2026-09-15 补充裁定）：
    * ``kind`` 必须取受控词表 KIND_* 之一；
    * ``source`` 只引用一级出处 —— **不得**出现中间产物 ``docs/20``
      （含 ``_P20``）字样；
    * 无来源确认（uk）条目的 ``source`` 仍须如实写明检索结果与不采信
      理由 —— 是诚实陈述不是权威来源，显示层折叠为 uk。
    """
    for fam, entries in FIELD_CHECKS.items():
        for fld, fc in entries.items():
            expect(fc.meaning, f"{fam}.{fld} 缺 meaning")
            expect(fc.unit, f"{fam}.{fld} 缺 unit")
            expect(fc.source, f"{fam}.{fld} 缺 source 依据出处")
            expect_in(fc.kind, _KNOWN_KINDS,
                      f"{fam}.{fld} kind 越出受控词表: {fc.kind!r}")
            expect("docs/20" not in fc.source,
                   f"{fam}.{fld} source 引用了中间产物 docs/20 —— "
                   f"必须下探一级出处: {fc.source[:80]}")
            expect("_P20" not in fc.source,
                   f"{fam}.{fld} source 残留 _P20 标识: {fc.source[:80]}")


def test_unknown_units_stay_unknown():
    """手册 §11 的 unknown 处**必须保持 unknown**，不许代为断言。"""
    expect_eq(field_check("hyades_eos", "raw_tail").unit, "unknown")
    expect_eq(field_check("feos_native", "raw_values").unit, "unknown")
    expect_eq(field_check("generic_curve", "anything").unit, "unknown")


def test_control_dictionary_doc_in_sync():
    """``docs/eosop变量控制字典.md`` 必须与字典**逐字同步**。

    人工核查翻 ``checked`` 后，重跑
    ``python -m eosop_pro.registry.field_checks`` 再生成。
    """
    # 与生成器同源的确定性锚点：field_checks.py 上溯 3 层 = 仓库根
    # （.../eosop_pro/eosop_pro/registry/field_checks.py -> .../eosop_pro/）
    import eosop_pro.registry.field_checks as _fcm
    _repo_root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(_fcm.__file__))))
    doc = os.path.join(_repo_root, DICT_DOC_RELPATH.replace("/", os.sep))
    expect(os.path.isfile(doc), f"字典文档缺失: {doc}")
    with open(doc, encoding="utf-8", newline="") as f:
        on_disk = f.read()
    expect_eq(on_disk, dump_markdown(),
              "字典文档与 field_checks 不同步 —— 重跑 "
              "python -m eosop_pro.registry.field_checks 再生成")


def test_checked_families_is_only_ionmix():
    expect_eq(checked_families(), ("ionmix",),
              f"checked 族应只有 ionmix，实得 {checked_families()}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
