"""feos_native 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "feos_native"
_PATTERNS = ("*.feos",)


def test_feos_native_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("feos_native", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_feos_native_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("feos_native")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_feos_native_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    expect("*" in entries, "缺 '*' 兜底条目")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect(set(named) >= {"rho", "Te", "P", "Pe", "Pi", "Ei", "Ee", "Qtot"},
           f"命名字段不全：{sorted(named)}")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<12} unit={fc.unit:<8} kind={fc.kind:<6} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("feos_native_dict", lines)
    # 布局定案：全部命名条目 kind=source code（FE-01_TABTOOLS.C 锚点）
    for fld, fc in entries.items():
        if fld == "*":
            continue
        expect_eq(fc.kind, "source code",
                  f"{fld}: 布局已由源码定案，kind 应为 source code")
    expect_eq(entries["Qtot"].unit, "-",
              "Qtot 是无量纲平均电离（每化学式总量）")
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), entries["*"])


def test_feos_native_specific():
    # 前导哨兵 + 16 块解码定案行为
    from eosop_pro.parsers.feos_native import (HEADER_FIELDS, LINE1_FIELDS,
                                               FEOS_BLOCKS, grid_length)
    expect_eq(len(HEADER_FIELDS), 10, "行 0 固定 10 字段")
    expect_eq(len(LINE1_FIELDS), 10, "行 1 固定 10 参数")
    expect_eq(len(FEOS_BLOCKS), 16, "16 个二维块")
    # grid_length 兼容保留：单调前缀定长（哨兵语义已由确定性布局接管）
    expect_eq(grid_length([1.0, 2.0, 3.0], 0, 4), 3)
    expect_eq(grid_length([1.0, 2.0, 3.0, 4.0], 0, 4), 4)
    log("  grid_length 单调前缀断言通过")

    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    expect_eq(tb.kind, "EOS_TOTAL")
    # 计数公式闭合
    expect(tb.n_numbers_expected is not None,
           "布局定案后必须给出精确计数公式")
    expect_eq(tb.n_numbers_seen, tb.n_numbers_expected,
              "计数公式应闭合")
    # 轴严格单调且为正（前导哨兵已修剪）
    axes = getattr(tb, "axes", {})
    if "rho" in axes:
        rho = axes["rho"]
        expect(all(b > a for a, b in zip(rho, rho[1:])),
               "rho 网格应严格单调递增（哨兵修剪后）")
        expect(rho[0] > 0, "rho 首点应为正（前导 0.0 哨兵已修剪）")
        expect_eq(tb.axis_units.get("rho"), "g/cm3")
        expect_eq(tb.axis_units.get("Te"), "eV")
        log(f"  网格: rho={len(rho)} 点, Te={len(axes.get('Te', []))} 点")
    else:
        log("  SKIP: 样品网格未定位（数据不足）")
    # 16 块字段与单位（原生 cgs + eV）
    fu = getattr(tb, "field_units", {})
    if "Pi" in fu:
        expect_eq(fu["Pi"], "dyn/cm2", "Pi 原生单位 dyn/cm2")
        expect_eq(fu["Ei"], "erg/g", "Ei 原生单位 erg/g")
        log(f"  已解码字段: {len(fu)} 个（16 块 + Qtot + Q）")
    else:
        log("  SKIP: 本样品无解码块字段")
    log(f"  sample: {path}")
    log(f"  notes: {tb.notes}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
