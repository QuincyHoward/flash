"""A3 —— 材料注册表（三源合并）+ 单位注记表测试。

实测基准
* ``material.base``: **251** 个 ``MATERIAL`` 块；``A``/``Z``/``NAME``/``RHO`` 各 251、
  ``FORMULA`` 245、``PLANCK``/``ROSSELAND`` 各 236、``EOS`` 217、**``ZEFF`` 130**、
  ``EEOS``/``IEOS`` 各 36
* ``DatabaseIndex.xml``: **98** 个 ``<EOS>`` + **36** 个 ``<Opacity>``，全部带 ``Zbar``
* ``EOS.list`` **84** 行 / ``Opacity.list`` **36** 行
* ⚠️ ``material.list`` 是**空文件**，不可作索引
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
from eosop_pro.registry.database_index import (
    DatabaseIndex, kind_from_sesame_id, parse_database_index, sesame_digit_of)
from eosop_pro.registry.eos_list import RegistryLists, parse_eos_list, parse_opacity_list
from eosop_pro.registry.material import MaterialRegistry
from eosop_pro.registry.material_base import MaterialBase, parse_material_base
from eosop_pro.registry.units_registry import UnitsRegistry, infer_T_from_logT_range


# ── material.base ──────────────────────────────────────────────
def test_material_base_block_count():
    mb = MaterialBase()
    expect_eq(len(mb.entries), 251, "MATERIAL 块数")
    expect_eq(mb.n_eos, 217, "声明 EOS 的材料数")
    expect_eq(mb.n_zeff, 130, "声明 ZEFF 的材料数")
    s = mb.summary()
    expect_eq(s["materials"], 251)
    expect(s["table_refs"] > 800, f"表引用数，实测 {s['table_refs']}")


def test_material_base_entry_fields():
    mb = MaterialBase()
    mid41 = mb.by_mid(41)
    expect(mid41 is not None, "应有 MID41")
    expect_eq(mid41.formula, "Al")
    expect(abs((mid41.A or 0) - 26.982) < 1e-9, f"A={mid41.A}")
    expect(abs((mid41.Z or 0) - 13) < 1e-9, f"Z={mid41.Z}")
    expect(mid41.eos_relpath is not None, "应有 EOS 引用")


def test_material_base_table_refs_kinds():
    mb = MaterialBase()
    mid9 = mb.by_mid(9)
    expect(mid9 is not None, "应有 MID9")
    ks = {r.key for r in mid9.refs}
    for k in ("EOS", "PLANCK", "ROSSELAND", "NONLTE", "ZEFF"):
        expect(k in ks, f"MID9 应有 {k}，实测 {ks}")
    expect_eq(mid9.zeff_relpath, "mat_Au-1.0/AU_op03z")


def test_material_base_rem_comments_captured():
    mb = MaterialBase()
    mid2 = mb.by_mid(2)
    expect(len(mid2.comments) > 0, "REM 注释应被收集")


def test_material_base_parse_direct():
    entries = parse_material_base(config.MATERIAL_BASE)
    expect(len(entries) == 251)
    expect(any(e.is_user_material for e in entries), "应有 MID>10000 的用户材料")


# ── DatabaseIndex.xml ──────────────────────────────────────────
def test_database_index_counts():
    di = DatabaseIndex()
    s = di.summary()
    expect_eq(s["eos"], 98)
    expect_eq(s["opacity"], 36)
    expect_eq(s["with_zbar"], 134, "全部条目都带 Zbar")
    expect(s["preferred"] > 0, "应有 Preferred 标志")
    expect(s["two_temperature"] > 0, "应有 Two-temperature 标志")
    expect(s["electron_table"] > 0 and s["ion_table"] > 0, "应有电子/离子表")


def test_database_index_lookup_by_file():
    di = DatabaseIndex()
    hits = di.by_file("hyades/sesame/eos_41.dat")
    expect(len(hits) > 0, "应按文件反查到条目")
    expect_eq(hits[0].material, "Aluminum")
    expect(abs((hits[0].zbar or 0) - 13) < 1e-9, f"Zbar={hits[0].zbar}")


def test_sesame_digit_uses_minus_four():
    """★ 类型位是**从右数第 4 位**（早先用 ``[3]`` 是错的）。"""
    expect_eq(sesame_digit_of("20202000"), "2")
    expect_eq(sesame_digit_of("27003003"), "3")
    expect_eq(sesame_digit_of(27004000), "4")
    expect_eq(sesame_digit_of("27005003"), "5")
    expect_eq(kind_from_sesame_id("20202000"), "ZEFF")
    expect_eq(kind_from_sesame_id("27003003"), "PLANCK")
    expect_eq(kind_from_sesame_id("27004000"), "ROSSELAND")
    expect_eq(kind_from_sesame_id("27005003"), "EMISSIVITY")


# ── *.list ─────────────────────────────────────────────────────
def test_list_counts_and_missing_fields():
    expect_eq(len(parse_eos_list()), 84)
    expect_eq(len(parse_opacity_list()), 36)
    rl = RegistryLists()
    expect_eq(rl.summary()["eos_list"], 84)
    expect_eq(rl.summary()["opacity_list"], 36)
    # 实测有缺字段的行（1032 Polystyrene 只有 1 个数值）
    expect(rl.by_no(1032) is not None, "应有 1032")
    p = rl.by_no(1032)
    expect(p.zbar is not None, "缺字段行仍应填出 Zbar")
    del rl


# ── 三源合并 ───────────────────────────────────────────────────
def test_registry_merge_summary():
    reg = MaterialRegistry(build_annotations=False)
    s = reg.summary()
    expect_eq(s["materials"], 251)
    expect_eq(s["with_zeff"], 130)
    expect_eq(s["with_eos"], 217)
    expect_eq(s["with_zinfl"], 251, "全部材料都有名义 Z")
    expect(s["distinct_files"] > 500, f"distinct_files={s['distinct_files']}")
    expect(s.get("src:material.base") == 251)
    expect(s.get("src:DatabaseIndex", 0) > 0)
    expect(s.get("src:EOS.list/Opacity.list", 0) > 0)


def test_registry_for_file_and_h5_name():
    reg = MaterialRegistry(build_annotations=False)
    recs = reg.for_file("mat_Au-1.0/AU_eos")
    expect(len(recs) > 0, "AU_eos 应被某个材料引用")
    r = recs[0]
    expect(r.label in ("Gold", "Au", "MID9", "Gold (MID9)") or "Gold" in r.label,
           f"label={r.label}")
    expect("/" not in r.h5_stem and " " not in r.h5_stem, f"h5_stem={r.h5_stem}")


def test_registry_source_diff():
    reg = MaterialRegistry(build_annotations=False)
    d = reg.source_diff()
    expect(isinstance(d["index_only"], list))


# ── 单位注记表 ─────────────────────────────────────────────────
def test_infer_T_from_logT_range():
    """logT_max ≥ 4.5 → eV；≤ 2.5 → keV（实测两组无重叠）。"""
    ev = infer_T_from_logT_range([-1.4, 0.0, 5.0])
    expect(ev is not None and ev.unit == "eV", f"{ev}")
    kev = infer_T_from_logT_range([-4.4, 0.0, 2.0])
    expect(kev is not None and kev.unit == "keV", f"{kev}")
    mid = infer_T_from_logT_range([-1.0, 1.0, 3.5])
    expect(mid is None, "落在阈值之间应无法判定（宁可返回 None 也不猜）")


def test_units_registry_declares_zeff_units_by_companion():
    """★ 关键：``*_Zeff.dat`` → keV、``*_Z.dat`` → eV，来源是伴随文件声明。"""
    ur = UnitsRegistry()
    eff = ur.decide_T("Thermos/mat_Al/Al_Zeff.dat")
    raw = ur.decide_T("Thermos/mat_Al/Al_Z.dat")
    expect_eq(eff.unit, "keV")
    expect_eq(raw.unit, "eV")
    expect_eq(eff.source, "companion", f"应来自伴随声明，实测 {eff.source}")
    expect(eff.unit != raw.unit, "两者必须被区分（表头/行数完全相同）")


def test_units_registry_envelope_fallback_used_when_no_declaration():
    ur = UnitsRegistry()
    d = ur.decide_T("mat_Simulated/nothing_Zeff_unknown.dat", logT=[-4.0, 0.0, 2.0])
    expect_eq(d.source, "envelope", f"无声明时应落包络，实测 {d}")
    expect_eq(d.unit, "keV")


def test_units_registry_default_when_nothing_available():
    ur = UnitsRegistry()
    d = ur.decide_T("mat_Simulated/xyz_unknown.dat")
    expect_eq(d.source, "config_default")
    expect_eq(d.unit, "eV")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
