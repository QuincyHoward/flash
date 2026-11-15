"""snop_input 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "snop_input"
_PATTERNS = ("*.SNOP",)


def test_snop_input_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("snop_input", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_snop_input_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("snop_input")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")

    # 参数溯源文件无 (rho,T) 网格；FG 群边界（eV）可画序列图
    tb = tables[0]
    fg = getattr(tb, "group_bounds", None) or []
    if fg:
        from eosop_pro.plotting.qa.qa_plots import plot_loglog_curve
        out = outroot / "fg_group_bounds.png"
        try_plot(
            lambda: plot_loglog_curve(
                list(range(1, len(fg) + 1)), fg,
                xlabel="group index",
                ylabel="FG (eV, SNOP.MANUAL)",
                title=f"SNOP FG group bounds (n={len(fg)})",
                out_path=str(out)),
            out, "plot_loglog_curve(FG)")
    else:
        log("  SKIP-plot: 样品无 FG 群边界")


def test_snop_input_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    expect("*" in entries, "缺 '*' 兜底条目")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect(set(named) >= {"T1", "T2", "X1", "X2", "FG"},
           f"namelist 参数条目不全：{sorted(named)}")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<6} unit={fc.unit:<8} kind={fc.kind:<20} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("snop_input_dict", lines)
    # 来源规约：T1/T2/X1/X2/FG = 一级手册 doc/SNOP.MANUAL 逐字单位
    for fld in ("T1", "T2", "X1", "X2", "FG"):
        expect_eq(entries[fld].kind, "primary document",
                  f"{fld}: 来源应为 SNOP.MANUAL")
        expect_eq(tags_label(entries[fld]), "uv", f"{fld}: 有源未核查 -> 'uv'")
    expect_eq(entries["T1"].unit, "keV")
    expect_eq(entries["T2"].unit, "keV")
    expect_eq(entries["X1"].unit, "keV")
    expect_eq(entries["X2"].unit, "keV")
    expect_eq(entries["FG"].unit, "eV")
    expect_eq(tags_label(entries["*"]), "uk, uv", "兜底条目无源 -> 'uk, uv'")
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), entries["*"])


def test_snop_input_specific():
    # namelist 参数抽取（T1/T2/X1/X2/FG）：parse_namelist 合成样例断言
    from eosop_pro.parsers.snop_input import PARAM_UNITS, parse_namelist
    # 静态单位表（逐字来自 SNOP.MANUAL）：T1/T2/X1/X2 = keV，FG = eV
    expect_eq(PARAM_UNITS["T1"], "keV")
    expect_eq(PARAM_UNITS["T2"], "keV")
    expect_eq(PARAM_UNITS["X1"], "keV")
    expect_eq(PARAM_UNITS["X2"], "keV")
    expect_eq(PARAM_UNITS["FG"], "eV")
    name, scalars, fg = parse_namelist([
        "&daten",
        "  NT=20, NR=20, NG=20,",
        "  T1=0.001, T2=100,",
        "  X1=0.001, X2=10,",
        "  FG(1) = 1,10,50,",
        "/",
    ])
    expect_eq(name, "daten", "namelist 名应为 daten")
    expect_eq(scalars.get("T1"), 0.001, "T1 抽取")
    expect_eq(scalars.get("T2"), 100.0, "T2 抽取")
    expect_eq(fg, [1.0, 10.0, 50.0], "FG 群边界数组抽取")
    log("  parse_namelist 合成样例断言通过")

    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "AUX", "SNOP 输入是参数溯源文件，kind 应为 AUX")
    expect_eq(tb.unit_source, "declared:doc/SNOP.MANUAL")
    # 单位声明注记：样品中出现过的 PARAM_UNITS 参数逐一登记 [keV]/[eV]
    for k, u in PARAM_UNITS.items():
        if k in scalars:
            expect(any(f"{k} [{u}]" in n for n in tb.notes),
                   f"notes 应含单位声明 {k} [{u}]")
    ng = getattr(tb, "n_groups", None)
    got_fg = getattr(tb, "group_bounds", None) or []
    log(f"  namelist 参数: T1={scalars.get('T1')} T2={scalars.get('T2')} "
        f"X1={scalars.get('X1')} X2={scalars.get('X2')} NG={ng}")
    log(f"  FG 群边界 {len(got_fg)} 个（单位 eV，SNOP.MANUAL；T1/T2/X1/X2 keV）"
        " —— 供人工核对 keV/eV")
    log(f"  sample: {path}")
    log(f"  notes: {tb.notes}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
