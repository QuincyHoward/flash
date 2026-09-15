"""B2 —— 「声明类型 vs 内容反演」比对测试。

★ 核心用例：``mat_Al-1.0/AL_eos.feos`` 与 ``AL_eos`` **字节相同**（名为 FEOS、实为 SESAME）。
声明规则按 ``Readme.txt`` 给出 ``feos_native`` 优先，**内容反演给出 ``multi_inverted_eos``**
→ 必须判为 ``order_mismatch``（声明优先级被内容证据推翻）。

⚠️ 反演「无结论」**不计为冲突**：多群子表串联等结构本就超出扁平模板的表达力。
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
from eosop_pro.registry import declared_types as dt
from eosop_pro.registry.identify import identify, sweep


def test_al_eos_feos_is_order_mismatch():
    """★ 名实不符的经典案例：靠**内容**抓出来。"""
    c = identify("mat_Al-1.0/AL_eos.feos")
    expect_eq(c.declared_first, "feos_native", "声明规则给出的第一候选")
    expect("multi_inverted_eos" in c.declared_families, "候选回退列表应含 F1")
    expect_eq(c.inferred_family, "multi_inverted_eos", "内容反演结果")
    expect_eq(c.agreement, "order_mismatch")
    expect_eq(c.inferred_dims, (66, 74), "反演维数应与 AL_eos 一致")
    expect(any("推翻" in n for n in c.notes), f"应说明原因，实测 {c.notes}")


def test_true_files_agree():
    for rel in ("mat_Al-1.0/AL_eos", "hyades/sesame/eos_41.dat",
                "mat_Be-1.0/BE_eos", "mat_Al-1.0/FEOS/Al.feos.301"):
        c = identify(rel)
        expect_eq(c.agreement, "agree", f"{rel}: {c.describe()}")


def test_inconclusive_inference_is_not_a_conflict():
    """多群子表串联（``AU_op03p``）超出扁平模板表达能力 → declared_only，不是冲突。"""
    c = identify("mat_Au-1.0/AU_op03p")
    expect_eq(c.agreement, "declared_only", f"{c.describe()}")
    expect(c.inferred_family is None, "无结论时不应给出 inferred_family")
    expect(any("不计为冲突" in n for n in c.notes), f"notes={c.notes}")


def test_skipped_files_excluded_from_sweep():
    """跳过文件（非数值）不应进入比对清单。"""
    comps = sweep(relpaths=["Readme.txt", "material.base", "mat_Al-1.0/AL_eos"])
    rels = {c.relpath for c in comps}
    expect("Readme.txt" not in rels, "说明文件应被排除")
    expect("material.base" not in rels, "注册表应被排除")
    expect("mat_Al-1.0/AL_eos" in rels, "真实数据文件应保留")


def test_sweep_and_report():
    import tempfile
    from pathlib import Path
    from eosop_pro.registry.identify import write_report
    reg, store = dt.default_registry()
    rels = [d.relpath for d in dt.scan_declared(registry=reg, store=store)
            if not d.is_skipped][:25]
    comps = sweep(registry=reg, store=store, relpaths=rels)
    expect(len(comps) == len(rels), f"应逐文件产出比对，实测 {len(comps)}")
    with tempfile.TemporaryDirectory() as td:
        csv_p, md_p = write_report(comps, td)
        expect(Path(csv_p).exists(), "应写出 CSV")
        text = Path(md_p).read_text(encoding="utf-8")
        for token in ("声明类型 vs 内容反演", "比对结果分布", "反演状态分布"):
            expect(token in text, f"报告应含 {token!r}")


def test_no_silent_conflict_swallowing():
    """任何 ``conflict`` 都必须带可读原因。"""
    reg, store = dt.default_registry()
    rels = [d.relpath for d in dt.scan_declared(registry=reg, store=store)
            if not d.is_skipped][:25]
    for c in sweep(registry=reg, store=store, relpaths=rels):
        if c.agreement == "conflict":
            expect(c.notes, f"conflict 必须带原因：{c.describe()}")
            expect(c.inferred_family is not None)


# ══════════════════════════════════════════════════════════════
# ★ agree_structure：结构等价 ≠ 不一致
# ══════════════════════════════════════════════════════════════
def test_same_structure_helper():
    from eosop_pro.registry import identify as idm

    expect(idm.same_structure("hyades_eos", "hyades_eos"), "自反")
    expect(idm.same_structure("hyades_eos", "hyades_opacity"), "同组")
    expect(idm.same_structure("hyades_opacity", "hyades_eos"), "同组（对称）")
    expect(not idm.same_structure("hyades_eos", "multi_opacity"), "异组")
    expect(not idm.same_structure(None, "hyades_eos"), "None 不算等价")


def test_struct_equiv_groups_share_a_count_formula():
    """★ 结构等价组内的族必须**真的**共用同一条计数公式。

    否则 ``agree_structure`` 会变成"给不一致开脱"的借口。
    这里用 ``parsers.base.PAYLOAD_LAYOUTS`` 交叉验证。
    """
    from eosop_pro.parsers.base import PAYLOAD_LAYOUTS
    from eosop_pro.registry import identify as idm

    for grp in idm.STRUCT_EQUIV:
        known = [f for f in grp if f in PAYLOAD_LAYOUTS]
        if len(known) >= 2:
            fn = PAYLOAD_LAYOUTS[known[0]]
            for other in known[1:]:
                for (nr, nt, ng) in ((20, 20, 1), (31, 46, 3), (2, 2, 1)):
                    expect_eq(fn(nr, nt, None, ng),
                              PAYLOAD_LAYOUTS[other](nr, nt, None, ng),
                              f"{known[0]} 与 {other} 的计数公式应相同")


def test_hyades_opacity_is_agree_structure_not_mismatch():
    """★ 回归：37 个 ``hyades/Opacity/opc_*.dat`` 曾被报成 ``order_mismatch``。

    声明 ``hyades_opacity``（对），反演说 ``hyades_eos``（也对 —— 二者共用
    ``L = 2 + nr + nt + 2*nr*nt``）。旧实现把它们记成 37 条 mismatch，
    淹没了真正的 conflict。新实现判为 ``agree_structure`` 并说明原因。
    """
    c = identify("hyades/Opacity/opc_1031.dat")
    expect_eq(c.declared_first, "hyades_opacity")
    expect_eq(c.inferred_family, "hyades_eos")
    expect_eq(c.agreement, "agree_structure",
              f"应判为结构等价，实测 {c.agreement}")
    expect(any("结构等价" in n for n in c.notes),
           f"必须带可读原因，实测 {c.notes}")


def test_agree_structure_not_used_for_unrelated_families():
    """反例：不相干的两个族不得被判为 agree_structure。"""
    from eosop_pro.registry.identify import TypeComparison
    from eosop_pro.core.inference import InferenceResult, LayoutCandidate
    from eosop_pro.registry import identify as idm

    fake = InferenceResult(status="ok")
    fake.best = LayoutCandidate(template="mpqeos", family="mpqeos", d1=10, d2=10)
    fake.candidates = [fake.best]
    c = idm.identify("mat_Al-1.0/AL_eos", inference=fake)
    expect(c.agreement != "agree_structure",
           f"mpqeos 与 F1 不同构，不应判 agree_structure：{c.agreement}")


def test_dispatch_fixes_drop_conflict_count():
    """★ 端到端：4 处分派修好后，那 10 个 conflict 文件不再冲突。

    ``order_mismatch`` 是**允许**的结果 —— 它表示"声明第一候选不对，
    靠候选回退救回来了"（``Thermos/mat_Mo/Mo_Ideal_Gas`` 就属此类：
    Thermos 路径规则先给 multi_opacity，内容表明是 F1）。
    关键断言是：**不再有 ``conflict``，且解析结果正确**。
    """
    from eosop_pro.registry.dispatch import parse_declared

    for rel in ("mat_CPC/AU.INV", "Thermos/mat_Mo/Mo_Ideal_Gas",
                "SiO2/eos_21.sesame", "Ta2O5/PowerLawTa2O5_EOS.SESAME_",
                "mat_Au/Au_2003POPHammerRosen_EOS.SESAME"):
        c = identify(rel)
        expect(c.agreement != "conflict",
               f"{rel} 修复后不应再 conflict，实测 {c.agreement}（{c.notes}）")
        expect(c.agreement in ("agree", "agree_structure", "order_mismatch"),
               f"{rel} 分类异常：{c.agreement}")
        s = parse_declared(rel, dt.declare(rel)).snapshot
        expect_eq(s.family, "multi_inverted_eos", f"{rel} 实际解析家族")
        expect_eq(s.status, "ok", f"{rel} 实际状态")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
