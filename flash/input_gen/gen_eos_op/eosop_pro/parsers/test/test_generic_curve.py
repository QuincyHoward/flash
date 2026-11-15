"""generic_curve 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "generic_curve"
_PATTERNS = ("ionpot*",)


def test_generic_curve_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("generic_curve", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_generic_curve_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("generic_curve")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_generic_curve_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect_eq(sorted(named), [], "generic_curve 是兜底族：只应登记 '*' 条目")
    expect("*" in entries, "缺 '*' 兜底条目")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<6} unit={fc.unit:<8} kind={fc.kind:<20} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("generic_curve_dict", lines)
    # 兜底族设计立场（parsers/generic_curve.py 模块头）：无来源、不猜测
    fc = entries["*"]
    expect_eq(fc.unit, "unknown", "兜底族单位必须诚实登记为 unknown")
    expect_eq(fc.kind, "none", "兜底族无可指认来源")
    expect_eq(tags_label(fc), "uk, uv", "无源未核查 -> 'uk, uv'")
    # 未登记列名走兜底（查询永不崩溃）
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), fc)


def test_generic_curve_specific():
    # 全列 uk,uv：轴 x 与全部 colN 字段单位一律 unknown（解析器不猜语义）
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "CURVE", "generic_curve 表 kind 应为 CURVE")
    # 轴单位
    au = getattr(tb, "axis_units", {})
    for name, unit in au.items():
        expect_eq(unit, "unknown",
                  f"轴 {name!r} 单位必须 unknown（无文档不猜测）")
    # 字段：colN 命名 + unknown 单位
    fu = getattr(tb, "field_units", {})
    expect(len(fu) >= 1, "至少应有一个数据列")
    for name, unit in sorted(fu.items()):
        expect(name.startswith("col"),
               f"字段名 {name!r} 应按 colN 命名（绝不因文件名猜物理量）")
        expect_eq(unit, "unknown", f"字段 {name!r} 单位必须 unknown")
    us = getattr(tb, "unit_source", "")
    log(f"  unit_source={us!r}")
    expect("none" in us, "unit_source 应如实登记 'none（列语义无文档）'")
    # 控制字典对任意 colN 的查询也应返回 unknown / uk,uv
    from eosop_pro.registry.field_checks import field_check, tags_label
    for name in sorted(fu):
        fc = field_check(_FAMILY, name)
        expect_eq(fc.unit, "unknown")
        log(f"  {name}: tags='{tags_label(fc)}'")
    log(f"  sample: {path}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
