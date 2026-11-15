"""cn4_io 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：``eos_op_data`` 仓库内首选 .cn4（first_cn4）+ matter++/Ionmix 树。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / cn4→cn4 verbatim 往返。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable, first_cn4

_FAMILY = "ionmix"           # cn4 在 FAMILY_PARSERS / FIELD_CHECKS 中注册为 ionmix
_PATTERNS = ("*.cn4",)


def test_cn4_parse_statistics():
    """eos_op_data 首选样例：完整 18 块解码 + 计数守恒 + 统计落盘。"""
    src = first_cn4()
    if src is None:
        log("  SKIP: eos_op_data 中未找到 .cn4 样例")
        return
    from eosop_pro.parsers.cn4_io import cn4_to_parsed_tables, parse_cn4
    tbl = parse_cn4(str(src))
    tables = cn4_to_parsed_tables(tbl, relpath=src.name)
    lines = table_stats(src, tables)
    lines.append(f"atomwt_source : {tbl.atomwt_source}")
    lines.append(f"count_guard   : {tbl.n_numbers_seen}/{tbl.n_numbers_expected}")
    write_summary("cn4_io", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少适配出 1 张 ParsedTable")
    expect_eq(tbl.n_numbers_seen, tbl.n_numbers_expected, "cn4 计数守恒")


def test_cn4_representative_plots():
    """cn4 轴为 (nion, Te)（无 rho 轴）→ isobars 不适用，走 gridmap 批量兜底。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("cn4_io")
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields([t], str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_cn4_dictionary_consistency():
    from eosop_pro.registry.field_checks import (
        FIELD_CHECKS, family_check_stats, tags_label)
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    log(f"  family_check_stats({_FAMILY}) = {family_check_stats(_FAMILY)}")
    for name in ("T", "nion", "p_ion", "opac_rosseland"):
        if name in entries:
            fc = entries[name]
            log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    # cn4 全 18 块是唯一 checked=True 的族：有源 + 已核查 -> 标记整体省略
    expect_eq(tags_label(entries["p_ion"]), "",
              "p_ion 有源（abjt_03.f + 指南）且已核查 -> 标记应省略")


def test_cn4_roundtrip_byte_identical():
    """convert_cn4_to_cn4（默认 verbatim=True）往返应逐字节一致。"""
    src = first_cn4()
    if src is None:
        log("  SKIP: eos_op_data 中未找到 .cn4 样例")
        return
    from eosop_pro.parsers.cn4_io import convert_cn4_to_cn4
    out = out_dir("cn4_io")
    dst = out / f"roundtrip_{src.name}"
    convert_cn4_to_cn4(str(src), str(dst))
    b_src = src.read_bytes()
    b_dst = dst.read_bytes()
    log(f"  roundtrip: {src.name} {len(b_src)}B -> {dst.name} {len(b_dst)}B")
    expect_eq(b_dst, b_src, "cn4->cn4 verbatim 往返应逐字节一致")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
