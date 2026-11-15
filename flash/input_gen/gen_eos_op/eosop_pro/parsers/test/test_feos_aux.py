"""feos_aux 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "feos_aux"
_PATTERNS = ("*.PAR", "*.cst", "*.mexport",
             "*.critical.dat", "*.isobaric.dat", "*.INV")


def test_feos_aux_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("feos_aux", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_feos_aux_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("feos_aux")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_feos_aux_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect_eq(sorted(named), [],
              "feos_aux 无一级来源：只应登记 '*' 兜底条目")
    expect("*" in entries, "缺 '*' 兜底条目")
    fc = entries["*"]
    row = f"* unit={fc.unit} kind={fc.kind} tags='{tags_label(fc)}'"
    log("  " + row)
    write_summary("feos_aux_dict", [row])
    expect_eq(fc.unit, "unknown", "辅助参数文件载荷语义待核，单位诚实 unknown")
    expect_eq(fc.kind, "none", "无可指认来源（中间产物草稿不作依据）")
    expect_eq(tags_label(fc), "uk, uv", "无源未核查 -> 'uk, uv'")
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), fc)


def test_feos_aux_specific():
    # raw_values 语义诚实登记（unknown）；分节 key=value 抽取真实行为
    from eosop_pro.parsers.feos_aux import parse_sections
    sections, _notes = parse_sections([
        "% comment",
        "Q-table:",
        "a = 1.0",
        "b = 2.0",
        "",
        "Units:",
        "c = 3.0",
    ])
    expect("Q-table" in sections and sections["Q-table"].get("a") == "1.0",
           "节内 key=value 抽取")
    expect(sections.get("Units", {}).get("c") == "3.0", "多节抽取")
    log("  parse_sections 合成样例断言通过")

    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "AUX", "FEOS 辅助文件按 AUX 登记")
    # 全部数值按原样存 raw_values，单位诚实 unknown
    fu = getattr(tb, "field_units", {})
    if "raw_values" in fu:
        expect_eq(fu["raw_values"], "unknown",
                 "raw_values 是未解码载荷，单位不得冒充有单位")
        log("  raw_values: unit=unknown（辅助文件语义按 key 名溯源，不参与网格）")
    else:
        log("  SKIP: 本样品无数值载荷（纯参数文件）")
    # 计数：n_numbers_expected = None（非定长表）
    expect(tb.n_numbers_expected is None,
           "辅助文件无数值计数公式 -> expected 应为 None")
    expect_eq(tb.unit_source, "none (辅助参数文件)")
    log(f"  sample: {path}")
    log(f"  notes: {tb.notes}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
