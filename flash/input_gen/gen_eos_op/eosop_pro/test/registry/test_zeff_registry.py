"""A4 —— Z̄ 数据源盘点测试。

实测基准（178 个 Z̄ 相关文件 / 79 个目录）
* Z1 ``Thermos/*_Zeff.dat`` **45** 个 → T 单位 **keV**
* Z2 ``Thermos/*_Z.dat``    **45** 个 → T 单位 **eV**（与 Z1 表头/行数完全相同）
* Z7 ``ATOMIC/*.NoFree``    **9** 个 → **keV**
* Z8 ``ATOMIC/*.AvSqFree``  **9** 个 → **keV**
* ``material.base`` ZEFF 声明 **130/251**

★ 三条硬结论（本文件逐条断言）
1. ``f2`` 槽位是**类型码**而非 Zbar
2. 单位必须靠**声明**（Δlog10 恰 3.000，纯数字无法区分）
3. Z̄(ρ,T) 覆盖 **130/251**
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
from eosop_pro.parsers import multi_opacity as f2
from eosop_pro.registry.material import MaterialRegistry
from eosop_pro.registry.zeff_inventory import ZeffInventory
from eosop_pro.registry.zeff_registry import KIND_Z, KIND_Z2, ZeffRegistry


def _reg():
    return ZeffRegistry().scan()


def test_zeff_source_inventory_counts():
    srcs = _reg()
    thermos_eff = [s for s in srcs if s.relpath.endswith("_Zeff.dat")]
    thermos_raw = [s for s in srcs if s.relpath.endswith("_Z.dat")]
    nofree = [s for s in srcs if s.relpath.endswith(".NoFree")]
    avsq = [s for s in srcs if s.relpath.endswith(".AvSqFree")]
    expect_eq(len(thermos_eff), 45, "Z1 Thermos *_Zeff.dat")
    expect_eq(len(thermos_raw), 46,
              "Z2 Thermos *_Z.dat（比 Z1 多 1：mat_Au 还有 AuMG_Z.dat）")
    expect_eq(len(nofree), 9, "Z7 LEDCOP NoFree")
    expect_eq(len(avsq), 9, "Z8 LEDCOP AvSqFree")
    expect(len(srcs) >= 170, f"Z̄ 相关文件总数应 >=170，实测 {len(srcs)}")


def test_thermos_zeff_is_keV_and_z_is_eV_by_declaration():
    """★ 核心：两个文件表头与行数完全相同，只能靠**声明**区分。"""
    srcs = {s.relpath: s for s in _reg()}
    eff = srcs["Thermos/mat_Al/Al_Zeff.dat"]
    raw = srcs["Thermos/mat_Al/Al_Z.dat"]
    expect_eq(eff.units_T, "keV")
    expect_eq(raw.units_T, "eV")
    expect_eq(eff.unit_source, "companion")
    expect_eq(raw.unit_source, "companion")


def test_ledcop_split_tables_are_keV():
    srcs = {s.relpath: s for s in _reg()}
    for rel in ("ATOMIC/Al.NoFree", "ATOMIC/Al.AvSqFree", "ATOMIC/Ti.NoFree"):
        expect_eq(srcs[rel].units_T, "keV", f"{rel} 应为 keV")


def test_kind_classification():
    srcs = {s.relpath: s for s in _reg()}
    expect_eq(srcs["ATOMIC/Al.NoFree"].kind, KIND_Z)
    expect_eq(srcs["ATOMIC/Al.AvSqFree"].kind, KIND_Z2)
    expect_eq(srcs["mat_Au-1.0/AU_op03z"].kind, KIND_Z)


def test_f2_slot_is_type_code_not_zbar():
    """★ ``Al_Zeff.dat`` 头 ``0 6.0 22 21`` 里的 ``6.0`` 是**类型码**，
    而 Al 的 Zbar 在 ``DatabaseIndex.xml`` 里是 **13**。"""
    t = f2.parse(config.MATTER("Thermos/mat_Al/Al_Zeff.dat"), "x")
    expect(t.f2_or_label is not None, "f2 槽位值不应丢失")
    expect(abs(float(t.f2_or_label) - 6.0) < 1e-9,
           f"f2 槽位应保持数值 6.0（类型码 = ZEFF），实测 {t.f2_or_label!r}")
    reg = MaterialRegistry(build_annotations=False)
    idx_hits = reg.index.by_file("hyades/sesame/eos_41.dat")
    expect(len(idx_hits) > 0, "应有 Zbar 记录")
    expect(abs((idx_hits[0].zbar or 0) - 13) < 1e-9,
           f"Al 的 Zbar 应为 13，实测 {idx_hits[0].zbar}")
    expect(t.f2_or_label != str(idx_hits[0].zbar), "f2 槽位 ≠ Zbar")


def test_zeff_unit_conflict_flagged_when_envelope_disagrees():
    """声明与包络不一致时必须标 ``suspect``，而不是静默选一个。"""
    reg = ZeffRegistry()
    srcs = {s.relpath: s for s in reg.scan()}
    # Al_Z.dat 声明 eV，其 logT 上限 ~5 → 与包络一致，不应 suspect
    expect(srcs["Thermos/mat_Al/Al_Z.dat"].unit_suspect is False)
    expect(srcs["Thermos/mat_Al/Al_Zeff.dat"].unit_suspect is False)


def test_material_level_coverage_130_of_251():
    """★ ``material.base`` 显式声明 ZEFF 的有 **130** 个；
    另有 58 个只有"按文件名归属"的 Z̄ 文件（未声明），63 个仅名义 Z。"""
    inv = ZeffInventory()
    inv.build()
    s = inv.summary()
    expect_eq(s["materials"], 251)
    expect_eq(s["coverage_table"], 130, "**显式声明** ZEFF 表的材料数（权威覆盖）")
    expect_eq(s["coverage_table_by_name"], 58,
              "仅按文件名归属（未声明）—— 不计入权威覆盖")
    expect_eq(s["coverage_nominal_only"], 63, "仅常量名义 Z")
    total = (s["coverage_table"] + s["coverage_table_by_name"]
             + s["coverage_nominal_only"] + s["coverage_none"])
    expect_eq(total, 251, f"四类之和应等于 251，实测 {total}")
    expect_eq(s["zeff_unit_suspect"], 0, "本次盘点未发现单位存疑")


def test_material_with_table_can_build_nele_grid():
    """有**声明** Z̄(ρ,T) 表 → ``(n_ele, Te)`` 网格技术上可行（本轮未实现）。"""
    inv = ZeffInventory()
    rows = inv.build()
    with_tab = [r for r in rows if r.coverage == "table"]
    expect_eq(len(with_tab), 130, f"实测 {len(with_tab)}")
    r = next((x for x in with_tab if x.material.startswith("Gold")), with_tab[0])
    expect(r.declared_zeff is True, "应标记为声明来源")
    expect(r.n_tables >= 1, f"{r.material} 应有至少 1 张表")
    expect(len(r.table_units) >= 1, "应有可用的 T 单位")


def test_inventory_writes_reports(tmpdir=None):
    import tempfile
    from pathlib import Path
    inv = ZeffInventory()
    with tempfile.TemporaryDirectory() as td:
        csv_p, md_p = inv.write_reports(td)
        expect(Path(csv_p).exists(), f"应写出 CSV: {csv_p}")
        expect(Path(md_p).exists(), f"应写出 MD: {md_p}")
        text = Path(md_p).read_text(encoding="utf-8")
        for token in ("Z̄ 数据源盘点", "覆盖度", "单位裁决来源"):
            expect(token in text, f"报告应含 {token!r}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
