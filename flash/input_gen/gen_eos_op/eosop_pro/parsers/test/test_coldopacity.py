"""coldopacity 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "coldopacity"
_PATTERNS = ("*.coldopacity",)


def test_coldopacity_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("coldopacity", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_coldopacity_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("coldopacity")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")

    # 经典一维表：第一列（光子能量）vs 不透明度列的 log-log 散点
    tb = tables[0]
    ax_name = next(iter(tb.axes), None)
    fld_name = next(iter(tb.fields), None)
    if ax_name and fld_name:
        from eosop_pro.plotting.qa.qa_plots import plot_loglog_curve
        out = outroot / "loglog_curve.png"
        try_plot(
            lambda: plot_loglog_curve(
                tb.axes[ax_name], tb.fields[fld_name],
                xlabel=f"{ax_name} ({tb.axis_units.get(ax_name, 'unknown')})",
                ylabel=f"{fld_name} ({tb.field_units.get(fld_name, 'unknown')})",
                title=f"COLDOPACITY_{tb.source_relpath}",
                out_path=str(out)),
            out, "plot_loglog_curve")


def test_coldopacity_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    expect("*" in entries, "缺 '*' 兜底条目（动态列族必备）")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect(set(named) >= {"Eph", "miu"}, f"典型列名条目缺失：{sorted(named)}")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<6} unit={fc.unit:<8} kind={fc.kind:<22} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("coldopacity_dict", lines)
    # 来源规约：两行自描述表头 = in-file declaration
    for fld, fc in entries.items():
        expect_eq(fc.kind, "in-file declaration",
                  f"{fld}: 来源类型应为 in-file declaration")
        expect_eq(tags_label(fc), "uv",
                  f"{fld}: 有源（文件内声明）未核查 -> 'uv'")
    # 逐文件列名可变 -> 任意未登记名走 '*' 兜底
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), entries["*"])


def test_coldopacity_specific():
    # 两行自描述表头（第 1 行列名 / 第 2 行单位）：field_units 与表头逐列一致
    from eosop_pro.parsers.coldopacity import parse_two_line_header
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    names, units, _start = parse_two_line_header(
        path.read_text(encoding="utf-8", errors="replace").splitlines())
    expect_eq(len(names), len(units), "表头列名数与单位数必须相等")
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "COLDOPACITY")
    # 第 1 列 -> 轴；其余 -> fields，逐列与第 2 行表头单位一致
    expect_eq(tb.axis_units.get(names[0]), units[0],
              f"轴 {names[0]!r} 单位应与表头第 2 行一致")
    for j, nm in enumerate(names[1:], start=1):
        expect(nm in tb.fields, f"列名 {nm!r} 应登记为 field")
        expect_eq(tb.field_units.get(nm), units[j],
                  f"field_units[{nm!r}] 应与表头单位 {units[j]!r} 一致")
    log(f"  header: names={names} units={units}（逐文件内嵌声明，人工核对 eV/cm2/g）")
    expect_eq(tb.unit_source, "declared:inline (2-line header)")
    expect_eq(tb.n_numbers_seen, tb.n_numbers_expected, "行×列计数守恒")
    log(f"  sample: {path}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
