"""mpqeos 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++ 全树的 ``*.301``（F4 MPQeos/FEOS SESAME 包装表）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / 单位换算抽查。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "mpqeos"
_PATTERNS = ("*.301",)


def test_mpqeos_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("mpqeos", lines)
    log("\n".join(lines))
    t = tables[0]
    expect(len(tables) >= 1, "至少解析出 1 张表")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected,
              "计数守恒 4 + nr + nt + 3*nr*nt")


def test_mpqeos_representative_plots():
    """(rho, Te) 基 EOS 表：等压线（field=P）+ gridmap 全字段兜底。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("mpqeos")
    if "P" in t.fields:
        from eosop_pro.plotting.qa.qa_plots import plot_eos_isobars
        try_plot(
            lambda: plot_eos_isobars(t, field="P",
                                     out_path=str(out / "eos_isobars.png")),
            out / "eos_isobars.png", "eos_isobars:P")
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields(tables, str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_mpqeos_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, tags_label
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    for name in ("rho", "Te", "P", "E", "Z"):
        fc = entries[name]
        log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    # rho/Te/P/E 有 docx MPQeos/SESAME 节一级来源（未核查 -> uv）；
    # Z 段实测含负值、语义待核（风险 R3）-> uk, uv
    expect_eq(tags_label(entries["P"]), "uv",
              "P 有一级文档来源、未核查 -> 应为 uv")
    expect_eq(tags_label(entries["Z"]), "uk, uv",
              "Z 段语义待核（风险 R3）-> 应为 uk, uv")


def test_mpqeos_unit_conversion_spotcheck():
    """单位换算抽查：T Kelvin→eV、P GPa→Mbar、E MJ/kg→Mbar*cm3/g。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    log(f"  unit_source: {t.unit_source}")
    expect_eq(t.axis_units.get("Te"), "eV",
              "T 轴应已由 Kelvin 换算为 eV（config.EV_PER_K）")
    expect_eq(t.field_units.get("P"), "Mbar",
              "P 应已由 GPa 换算为 Mbar（config.MBAR_PER_GPA）")
    expect_eq(t.field_units.get("E"), "Mbar*cm3/g",
              "E 应已由 MJ/kg 换算为 Mbar*cm3/g（config.MBAR_CM3_G_PER_MJ_KG）")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
