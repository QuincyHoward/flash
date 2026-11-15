"""ledcop_zeff 产物核查 —— 解析统计 + 代表性图像（人工核查用）。"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "ledcop_zeff"
_PATTERNS = ("*.NoFree", "*.AvSqFree")


def test_ledcop_zeff_parse_statistics():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    stats = table_stats(path, tables)
    for ln in stats:
        log("  " + ln)
    write_summary("ledcop_zeff", stats)
    expect(len(tables) >= 1, "find_parseable 成功但 tables 为空")


def test_ledcop_zeff_representative_plots():
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    _path, tables = found
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    outroot = out_dir("ledcop_zeff")
    marker = outroot / "_plots_done.txt"

    def _do():
        rep = plot_table_all_fields(tables, outroot, family=_FAMILY)
        log(f"  plots={rep['n_plots']} skipped={len(rep['skipped'])}")
        marker.write_text(f"n_plots={rep['n_plots']}\n",
                          encoding="utf-8", newline="\n")

    try_plot(_do, marker, "plot_table_all_fields")


def test_ledcop_zeff_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    entries = FIELD_CHECKS.get(_FAMILY)
    expect(entries is not None, f"FIELD_CHECKS 缺少 {_FAMILY} 族登记")
    expect("*" in entries, "缺 '*' 兜底条目")
    named = {k: v for k, v in entries.items() if k != "*"}
    expect(set(named) >= {"rho", "Te", "NoFree", "AvSqFree"},
           f"命名字段不全：{sorted(named)}")
    lines = []
    for fld, fc in sorted(entries.items()):
        row = (f"{fld:<10} unit={fc.unit:<8} kind={fc.kind:<20} "
               f"tags='{tags_label(fc)}'")
        log("  " + row)
        lines.append(row)
    write_summary("ledcop_zeff_dict", lines)
    # 来源规约：rho/Te = 一级文档（docx Zeff 节）；NoFree/AvSqFree = LANL TOPS FAQ
    expect_eq(entries["rho"].kind, "primary document")
    expect_eq(entries["Te"].kind, "primary document")
    expect_eq(entries["Te"].unit, "keV", "Zeff 族 Te 文件原生 keV（与不透明度族 eV 区分）")
    expect_eq(entries["NoFree"].kind, "primary document")
    expect_eq(entries["AvSqFree"].kind, "primary document")
    for fld, fc in named.items():
        expect_eq(tags_label(fc), "uv", f"{fld}: 有源未核查 -> 'uv'")
    expect_eq(tags_label(entries["*"]), "uk, uv", "兜底条目无源 -> 'uk, uv'")
    expect_eq(field_check(_FAMILY, "nosuchfield_xyz"), entries["*"])


def test_ledcop_zeff_specific():
    # 魔数 0.1234567E+000：4 数头首字段是 LEDCOP 格式哨兵值（非物理量）
    from eosop_pro.parsers.ledcop_zeff import LEDCOP_MAGIC
    expect_eq(LEDCOP_MAGIC, 0.1234567)
    found = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(found):
        return
    path, tables = found
    tb = tables[0]
    expect_eq(tb.family, _FAMILY)
    # 表头 4 数：[魔数, 1.0, NR, NT] —— 首字段应与魔数相符
    from eosop_pro.core.numbers import fortran_numbers as fn
    hdr = fn.extract_numbers(tb.header_raw)
    expect_eq(len(hdr), 4, f"LEDCOP 表头应为 4 数，实测 {len(hdr)}")
    expect(abs(hdr[0] - LEDCOP_MAGIC) < 1e-6,
           f"首字段 {hdr[0]!r} 应为魔数 {LEDCOP_MAGIC}")
    expect(any("魔数匹配" in n for n in tb.notes),
           "解析器应登记 'LEDCOP 魔数匹配' 注记")
    # 值字段名来自文件名 token：AvSqFree -> Z2/ZEFF2，NoFree -> Z/ZEFF
    base = path.name.lower()
    if "avsqfree" in base:
        expect_eq(tb.kind, "ZEFF2")
        expect("Z2" in tb.fields, "AvSqFree 文件值字段应登记为 Z2")
        log("  语义: AvSqFree = <Z^2>（自由电子数平方均值，LANL TOPS FAQ Q7）")
    else:
        expect_eq(tb.kind, "ZEFF")
        expect("Z" in tb.fields, "NoFree 文件值字段应登记为 Z")
        log("  语义: NoFree = <Z>（每离子平均自由电子数，LANL TOPS FAQ Q1）")
    # 计数守恒 4 + NR + NT + NR*NT
    expect_eq(tb.n_numbers_seen, tb.n_numbers_expected, "计数守恒")
    # 轴：log10 rho (g/cm3) / log10 T (keV 原生 -> eV)
    expect_eq(tb.axis_units.get("rho"), "g/cm3")
    expect_eq(tb.axis_units.get("Te"), "eV")
    expect(tb.axis_log10.get("rho") and tb.axis_log10.get("Te"),
           "rho/Te 应登记为 log10 轴")
    log(f"  sample: {path}")
    log(f"  notes: {tb.notes}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
