"""feos_tabdata 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "feos_tabdata"
_PATTERNS = ("*.data.txt",)


def test_feos_tabdata_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("feos_tabdata", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_feos_tabdata_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("feos_tabdata")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_feos_tabdata_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect_eq(sorted(named), [],
              "feos_tabdata 无本地列名文档：只应登记 '*' 兜底条目")
    expect("*" in entries, "缺 '*' 兜底条目")
    fc = entries["*"]
    row = (f"* unit={fc.unit} kind={fc.kind} tags='{tags_label(fc)}'")
    log("  " + row)
    write_summary("feos_tabdata_dict", [row])
    expect_eq(fc.unit, "unknown", "colN 语义待核，单位诚实 unknown")
    expect_eq(fc.kind, "none", "无一级列名文档 -> 无可指认来源")
    expect_eq(tags_label(fc), "uk, uv", "无源未核查 -> 'uk, uv'")
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), fc)


def test_feos_tabdata_specific():
    # raw_values/colN 语义诚实登记：全列 colN 命名 + unknown 单位，不冒充有单位
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "AUX", "ShowEOS TSV 导出表按 AUX 登记")
    fu = getattr(tb, "field_units", {})
    expect(len(fu) >= 3, f"TSV 导出表应 >=3 列，实测 {len(fu)}")
    for name, unit in sorted(fu.items()):
        expect(name.startswith("col"),
               f"字段名 {name!r} 应按 colN 命名（无列名文档不猜语义）")
        expect_eq(unit, "unknown",
                  f"列 {name!r} 单位必须诚实登记 unknown")
    # 计数守恒
    expect_eq(tb.n_numbers_seen, tb.n_numbers_expected, "行×列计数守恒")
    # col0/col1 是索引 -> 解析器显式注记，防止被误当物理量
    expect(any("col0/col1" in n and "索引" in n for n in tb.notes),
           "notes 应显式标注 col0/col1 为行/列索引")
    expect_eq(tb.unit_source, "none (列语义无本地文档)")
    log(f"  列数={len(fu)}，全部 unit=unknown（语义待人工核查）")
    log(f"  sample: {path}")
    log(f"  notes: {tb.notes}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
