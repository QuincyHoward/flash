"""A1 —— 声明式类型表测试（**阶段 A 的零内容推断判据**）。

实测支撑：150 个无扩展名文件中
* **95 个**可由 ``material.base`` / ``DatabaseIndex.xml`` 注册表定案
* **约 50 个**可由文件名 token（``_eos_e`` / ``_ieos`` / ``_mopp`` / ``ZEFF`` …）定案
* 仅约 5 个是真硬骨头 → 交阶段 B

全树扫描结果：**1214 个文件全部有声明族，0 个 unresolved**。
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
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import config
from eosop_pro.registry import declared_types as dt
from eosop_pro.registry.annotation_store import AnnotationStore
from eosop_pro.registry.material import MaterialRegistry


def _idx():
    store = AnnotationStore().build()
    reg = MaterialRegistry(build_annotations=False)
    return reg, store


def test_all_files_have_declared_family():
    reg, store = _idx()
    dts = dt.scan_declared(registry=reg, store=store)
    expect_eq(len(dts), 1214, "文件总数")
    unresolved = [d.relpath for d in dts if d.is_unresolved]
    expect_eq(unresolved, [], "不应有无法声明类型的文件")


def test_skip_rules_cover_docs_and_metadata():
    reg, store = _idx()
    checks = {
        "Readme.txt": "skip",
        "DatabaseIndex.xml": "skip",
        "material.base": "skip",
        "ATOMIC/#LEDCOP": "skip",
        "SNOP/opbe.inhalt": "skip",
        "ColdOpacity/20170117.case.log": "skip",
    }
    for rel, fam in checks.items():
        d = dt.declare(rel, registry=reg, store=store)
        expect_eq(d.family, fam, f"{rel} 应判为 {fam}，实测 {d.family} ({d.evidence})")


def test_extension_rules():
    reg, store = _idx()
    checks = {
        "mat_Al-1.0/FEOS/Al.feos.301": "mpqeos",
        "mat_Al-1.0/FEOS/Al.feos.304": "mpqeos",
        "mat_He/Untitled.305": "mpqeos",
        "Ionmix/al-imx-002.cn4": "ionmix",
        "Ionmix/xe-100grp-lte.cnr": "ionmix",
        "ColdOpacity/Al.coldopacity": "coldopacity",
        "hyades/sesame/eos_41.hug": "hugoniot",
        "mat_Al-1.0/Al.feos": "feos_native",
    }
    for rel, fam in checks.items():
        d = dt.declare(rel, registry=reg, store=store)
        expect_eq(d.family, fam, f"{rel}: 期望 {fam}，实测 {d.family}")


def test_ext_kinds_from_extension():
    reg, store = _idx()
    expect_eq(dt.declare("mat_Al-1.0/FEOS/Al.feos.301", registry=reg).kind, "EOS_TOTAL")
    expect_eq(dt.declare("mat_Al-1.0/FEOS/Al.feos.304", registry=reg).kind, "EOS_ELECTRON")
    expect_eq(dt.declare("mat_Al-1.0/FEOS/Al.feos.305", registry=reg).kind, "EOS_ION")


def test_path_rule_hyades():
    """``Readme.txt`` 原文：含 ``hyades`` → Hyades 格式。"""
    reg, store = _idx()
    d = dt.declare("hyades/sesame/eos_41.dat", registry=reg, store=store)
    expect("hyades_eos" in d.families, f"families={d.families}")
    expect_eq(d.source, "path")
    d2 = dt.declare("hyades/Opacity/opc_1031.dat", registry=reg, store=store)
    expect_eq(d2.families[0], "hyades_opacity", "opc_* 应优先按不透明度解析")


def test_name_token_rules():
    reg, store = _idx()
    for rel, fam in (
        ("mat_Al-1.0/AL_ZEFF_multifs-1.2.dat", "multi_opacity"),
        ("mat_C-1.0/C_20GSNOP.ZEFF", "multi_opacity"),
        ("mat_Au-1.0/AU_op03p", "multi_opacity"),
    ):
        d = dt.declare(rel, registry=reg, store=store)
        expect_eq(d.family, fam, f"{rel}: 实测 {d.family}")


def test_kind_from_name_tokens():
    reg, store = _idx()
    expect_eq(dt.declare("mat_Be-1.0/BE_eos_e", registry=reg, store=store).kind,
              "EOS_ELECTRON")
    expect_eq(dt.declare("mat_Be-1.0/BE_eos_i", registry=reg, store=store).kind,
              "EOS_ION")
    expect_eq(dt.declare("mat_Au-1.0/AU_op03z", registry=reg, store=store).kind, "ZEFF")
    expect_eq(dt.declare("ATOMIC/Al.AvSqFree", registry=reg, store=store).kind, "ZEFF2")


def test_feos_extension_yields_two_candidates():
    """★ ``.feos`` 给两个候选（Readme 声明 + 回退），因为 ``AL_eos.feos`` 名实不符。"""
    reg, store = _idx()
    d = dt.declare("mat_Al-1.0/AL_eos.feos", registry=reg, store=store)
    expect_eq(d.families[:2], ["feos_native", "multi_inverted_eos"],
              f"families={d.families}")


def test_registry_gives_mid_and_material():
    reg, store = _idx()
    d = dt.declare("mat_Au-1.0/AU_eos", registry=reg, store=store)
    expect(d.mid is not None, f"应能反查到 MID，实测 {d.mid}")
    expect("material.base" in d.evidence, f"evidence={d.evidence}")


def test_source_histogram_is_diverse():
    reg, store = _idx()
    dts = dt.scan_declared(registry=reg, store=store)
    from collections import Counter
    c = Counter(d.source for d in dts)
    for key in ("extension", "path", "default", "skip_rule"):
        expect(c.get(key, 0) > 0, f"来源 {key} 应有命中，实测 {dict(c)}")


def test_default_candidates_follow_readme():
    """``Readme.txt``：其他按默认 SESAME（4×15）。"""
    reg, store = _idx()
    d = dt.declare("mat_Others/CH10Water.info", registry=reg, store=store)
    expect(d.family == "skip", "`.info` 应跳过（说明文件）")


# ══════════════════════════════════════════════════════════════
# ★ 扩展名具体性分层（EXT_SPECIFIC）
# ══════════════════════════════════════════════════════════════
def test_ext_specific_set_is_disjoint_from_generic_tags():
    """``EXT_SPECIFIC`` 里的扩展名必须都在 ``EXT_MAP`` 中，且不含通用标记。"""
    for e in dt.EXT_SPECIFIC:
        expect_in(e, dt.EXT_MAP, f"{e} 应同时出现在 EXT_MAP 中")
    # 通用标记必须**不在**具体层，否则 hyades 优先规则会失效
    for generic in (".feos", ".301", ".304", ".305"):
        expect(generic not in dt.EXT_SPECIFIC,
               f"{generic} 是通用标记，不应进 EXT_SPECIFIC")


def test_hyades_path_overrides_generic_feos_tag():
    """★ 回归：``hyades/**/*.dat.feos`` 的内容是 Hyades 布局。

    上游把 ``.feos`` 追加在原文件名后，但内容仍是标准 Hyades 5×15：
        hyades/sesame/eos_41.dat.feos → 首行 'ALUMINUM  LANL SESAME #3711 …'
        hyades/qeos/qeos_392.dat.feos → 首行 'Silicon   LLNL QEOS DATED: …'
    若让 ``.feos`` 赢，两个候选都失败 → 退化成 generic_curve，布局信息全丢。
    """
    for rel in ("hyades/sesame/eos_41.dat.feos", "hyades/qeos/qeos_392.dat.feos"):
        d = dt.declare(rel)
        expect_eq(d.source, "path", f"{rel} 应由路径规则判定")
        expect_eq(d.family, "hyades_eos", f"{rel} 第一候选应为 hyades_eos")
        expect_in("feos_native", d.families,
                  f"{rel} 的扩展名候选应保留为回退")
        expect(d.families.index("hyades_eos") < d.families.index("feos_native"),
               "hyades_eos 必须排在 feos_native 之前")


def test_ext_specific_beats_hyades_path():
    """★ 回归：hyades 优先**不能无限上纲** —— 语义唯一的扩展名仍要赢。

        hyades/sesame/eos_32.hug      → Hugoniot（不是 Hyades EOS）
        hyades/qeos/qeos_392.dat.par  → FEOS 参数（不是 Hyades EOS）
    """
    for rel, fam in (("hyades/sesame/eos_32.hug", "hugoniot"),
                     ("hyades/qeos/qeos_392.dat.par", "feos_aux")):
        d = dt.declare(rel)
        expect_eq(d.source, "extension", f"{rel} 应由扩展名规则判定")
        expect_eq(d.family, fam, f"{rel} 第一候选应为 {fam}")
        expect(all("hyades" not in f for f in d.families),
               f"{rel} 不应含 hyades 族，实测 {d.families}")


def test_hyades_extension_spelled_as_ext_still_works():
    """``Ta2O5/Ta2O5_EOS.hyades`` —— 路径本身不含 hyades，靠扩展名里的字面命中。"""
    d = dt.declare("Ta2O5/Ta2O5_EOS.hyades")
    expect_eq(d.source, "path")
    expect_eq(d.family, "hyades_eos")


def test_generic_feos_outside_hyades_keeps_extension_priority():
    """不在 hyades 下的 ``.feos`` 仍由扩展名判定。"""
    d = dt.declare("mat_Al-1.0/Al.feos")
    expect_eq(d.source, "extension")
    expect_eq(d.family, "feos_native")


def test_all_hyades_rooted_files_resolve_to_a_family():
    """``hyades/`` 下所有非跳过文件都必须有家族候选（不许落 ``unrecognized``）。"""
    reg, store = _idx()
    dts = dt.scan_declared(registry=reg, store=store)
    bad = [d.relpath for d in dts
           if d.relpath.lower().startswith("hyades/")
           and d.family is None]
    expect(not bad, f"hyades/ 下有未决文件: {bad[:8]}")


# ══════════════════════════════════════════════════════════════
# ★ identify 交叉验证抓到的 4 处分派错误（回归）
# ══════════════════════════════════════════════════════════════
def test_inv_extension_is_f1_not_feos_aux():
    """★ 回归：``.INV`` = MULTI **Inverted** EOS，**不是** FEOS 导出。

    实测 ``mat_CPC/AU.INV``：
        L0 = ' 1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02'
        → [SESAME id, 0.0, nr=123, ne=100]，6238 行 × 4 = 24952
        F1/with_e0(123,100) = 24950 (+2 尾部) ✓
    旧实现里有 ``|\\.INV$`` 的名字 token 把它抢到 ``feos_aux``。
    """
    for rel in ("mat_CPC/AU.INV", "mat_CPC/BE.INV"):
        d = dt.declare(rel)
        expect_eq(d.family, "multi_inverted_eos", f"{rel} 应为 F1")
        expect_in(".inv", dt.EXT_SPECIFIC,
                  "`.inv` 属语义唯一的扩展名，应在 EXT_SPECIFIC 里")


def test_sesame_extension_prefers_a_real_parser():
    """★ 回归：``.sesame`` 的第一候选必须是**真有解析器**的族。

    实测 6 个 ``.sesame`` 文件全是 F1 with_e0（计数精确吻合，例如
    ``SiO2/eos_22.sesame`` 130892 == 32723 行 × 4）。
    旧实现把无解析器的 ``sesame_dat`` 放第一位 → 只能退化成 generic_curve。
    """
    d = dt.declare("SiO2/eos_21.sesame")
    expect_eq(d.family, "multi_inverted_eos")
    expect_eq(d.families.index("multi_inverted_eos"), 0)
    expect_in("sesame_dat", d.families, "sesame_dat 应保留为语义标记")


def test_trailing_underscore_in_extension_is_stripped():
    """★ 回归：``PowerLawTa2O5_EOS.SESAME_`` 的尾部 ``_`` 是 Windows 复制冲突产物。

    不剥掉的话 ``.sesame_`` 不在 EXT_MAP 里，名字 token ``powerlaw``
    会把它抢到 ``generic_curve`` —— 而内容是 F1（计数 143 精确吻合）。
    """
    expect_eq(dt._ext_of("PowerLawTa2O5_EOS.SESAME_"), ".sesame")
    expect_eq(dt._ext_of("Foo.FEOS___"), ".feos")
    expect_eq(dt._ext_of("Bar.dat"), ".dat")
    d = dt.declare("Ta2O5/PowerLawTa2O5_EOS.SESAME_")
    expect_eq(d.family, "multi_inverted_eos")
    expect_eq(d.source, "extension")


def test_thermos_path_rule_includes_ideal_gas_eos():
    """★ 回归：``Thermos/`` 里也有**理想气体 EOS**，不只是不透明度。

    实测 L0 的第 2 字段正好是材料的固体密度：
        Thermos/mat_Mo/Mo_Ideal_Gas  → 10.22（Mo 实测 10.22 g/cm³）
        Thermos/mat_U/U_IdealGas_EOS → 19.1 （U  实测 19.1  g/cm³）
    计数 18 == F1/with_e0(2,2)，与 doc 里 AU_IDEAL_GAS 的布局逐一对应。
    """
    d = dt.declare("Thermos/mat_Mo/Mo_Ideal_Gas")
    expect_eq(d.source, "path")
    expect_eq(d.family, "multi_opacity", "第一候选仍应是不透明度（Thermos 多数）")
    expect_in("multi_inverted_eos", d.families,
              "理想气体 EOS 必须有 F1 作为回退候选")


def test_the_four_dispatch_fixes_end_to_end():
    """★ 端到端：4 类分派错误修复后，10 个 conflict 全部变为正确解析。"""
    from eosop_pro.registry.dispatch import parse_declared

    cases = {
        "mat_CPC/AU.INV": ("multi_inverted_eos", (123, 100)),
        "mat_CPC/BE.INV": ("multi_inverted_eos", (123, 100)),
        "Thermos/mat_Mo/Mo_Ideal_Gas": ("multi_inverted_eos", (2, 2)),
        "Thermos/mat_U/U_IdealGas_EOS": ("multi_inverted_eos", (2, 2)),
        "Thermos/mat_W/W_Ideal_Gas": ("multi_inverted_eos", (2, 2)),
        "SiO2/eos_21.sesame": ("multi_inverted_eos", (43, 1765)),
        "SiO2/eos_22.sesame": ("multi_inverted_eos", (36, 1792)),
        "Ta2O5/PowerLawTa2O5_EOS.SESAME": ("multi_inverted_eos", (3, 19)),
        "Ta2O5/PowerLawTa2O5_EOS.SESAME_": ("multi_inverted_eos", (5, 26)),
        "mat_Au/Au_2003POPHammerRosen_EOS.SESAME": ("multi_inverted_eos", (6, 31)),
    }
    for rel, (fam, dims) in cases.items():
        out = parse_declared(rel, dt.declare(rel))
        s = out.snapshot
        expect_eq(s.family, fam, f"{rel} 家族")
        expect_eq(s.status, "ok", f"{rel} 状态")
        t = out.tables[0]
        expect_eq((len(t.axes["rho"]), len(t.axes["de"])), dims, f"{rel} 维度")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
