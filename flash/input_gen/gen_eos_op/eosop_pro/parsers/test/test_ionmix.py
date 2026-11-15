"""ionmix 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++/Ionmix 树的 ``*.cn4``（完整 18 块，kind=cn4_eos）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / 轴场单位抽查。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "ionmix"
_PATTERNS = ("*.cn4",)


def test_ionmix_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("ionmix", lines)
    log("\n".join(lines))
    expect_eq(len(tables), 1, ".cn4 应产出 1 张总表")
    expect_eq(tables[0].kind, "cn4_eos", ".cn4 总表 kind 应为 cn4_eos")


def test_ionmix_representative_plots():
    """cn4 轴为 (nion, Te)（无 rho 轴）→ isobars 不适用，走 gridmap 批量兜底。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("ionmix")
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields([t], str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_ionmix_dictionary_consistency():
    from eosop_pro.registry.field_checks import (
        FIELD_CHECKS, family_check_stats, tags_label)
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    log(f"  family_check_stats({_FAMILY}) = {family_check_stats(_FAMILY)}")
    for name in ("T", "nion", "zbar", "opac_rosseland"):
        if name in entries:
            fc = entries[name]
            log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    expect_eq(tags_label(entries["zbar"]), "",
              "cn4 全 18 块已人工核查 -> 标记应省略")


def test_ionmix_field_units_spotcheck():
    """轴/场单位抽查：nion 轴（源文件列名 densnn）单位含 cm；p_ion 为 J/cm3。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    nion_unit = t.axis_units.get("nion", "")
    log(f"  axis_units[nion] = {nion_unit!r}（源文件列名 densnn）")
    expect("cm" in nion_unit, f"nion（densnn）单位应含 cm：{nion_unit!r}")
    p_ion_unit = t.field_units.get("p_ion", "")
    log(f"  field_units[p_ion] = {p_ion_unit!r}")
    expect_eq(p_ion_unit, "J/cm3", "p_ion 单位应为 J/cm3（abjt_03.f :4693）")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "计数守恒")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
