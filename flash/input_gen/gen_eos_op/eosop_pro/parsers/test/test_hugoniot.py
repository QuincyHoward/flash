"""hugoniot 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "hugoniot"
_PATTERNS = ("*.hug",)


def test_hugoniot_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("hugoniot", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_hugoniot_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("hugoniot")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_hugoniot_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    expect("*" in entries, "缺 '*' 兜底条目")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect(set(named) >= {"Rho", "T", "P", "E", "Us", "Up"},
           f"命名字段不全：{sorted(named)}")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<10} unit={fc.unit:<8} kind={fc.kind:<22} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("hugoniot_dict", lines)
    # 来源规约：hugoniot 全部条目 = in-file declaration（'# name [unit]' 头）
    for fld, fc in entries.items():
        expect_eq(fc.kind, "in-file declaration",
                  f"{fld}: 来源类型应为 in-file declaration")
        expect_eq(tags_label(fc), "uv",
                  f"{fld}: 有源（文件内声明）未核查 -> 'uv'")
    # 未登记列名走 '*' 兜底
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), entries["*"])


def test_hugoniot_specific():
    # 缩放因子剥离（[scale unit] 变体）：parse_column_header 真实行为断言
    from eosop_pro.parsers.hugoniot import parse_column_header
    cols = parse_column_header("Rho[g/cm^3]  T [eV]         P [Mbar]")
    expect_eq(cols, [("Rho", "g/cm^3"), ("T", "eV"), ("P", "Mbar")],
              "裸 '[unit]' 写法")
    cols2 = parse_column_header(
        "# Rho [1.000000e+000 g/cm^3]  P [1.000000e+012 dyne/cm^2]")
    expect_eq(cols2, [("Rho", "g/cm^3 (x1.0e+00)"),
                      ("P", "dyne/cm^2 (x1.0e+12)")],
              "[scale unit] 变体：缩放因子剥离后以 '(xN)' 保留")
    log("  parse_column_header 两种写法断言通过")

    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "HUGONIOT")
    # 逐文件单位全部来自注释头，不得为空
    fu = getattr(tb, "field_units", {})
    au = getattr(tb, "axis_units", {})
    for name, unit in {**au, **fu}.items():
        expect(bool(unit), f"{name!r} 的单位为空（注释头应逐列声明）")
        if "(x" in unit:
            log(f"  scale-variant column: {name} [{unit}]")
    # 计数守恒（首列作轴）
    expect_eq(tb.n_numbers_seen, tb.n_numbers_expected,
              "payload 行×列应计数守恒")
    log(f"  header_raw: {tb.header_raw.strip()}")
    log(f"  notes: {tb.notes}")
    log(f"  sample: {path}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
