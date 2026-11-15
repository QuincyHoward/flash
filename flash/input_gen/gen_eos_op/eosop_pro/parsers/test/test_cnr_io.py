"""cnr_io 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++/Ionmix 树的 ``*.cnr``（legacy late-1986 CONRAD 变体）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / ntrad 计数守恒反解。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_first, find_parseable

_FAMILY = "ionmix"           # .cnr 经 ionmix 适配层出 ParsedTable（kind=cnr_legacy）
_PATTERNS = ("*.cnr",)


def test_cnr_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("cnr_io", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")
    expect_eq(tables[0].kind, "cnr_legacy", ".cnr 适配表 kind 应为 cnr_legacy")


def test_cnr_representative_plots():
    """cnr 适配表的轴为索引轴（无物理网格点，不猜）→ 走 gridmap raw 兜底。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    out = out_dir("cnr_io")
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields(tables, str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_cnr_dictionary_consistency():
    # .cnr 是 legacy 变体，无独立注册族；其适配表挂在 ionmix 族下（kind=cnr_legacy）
    from eosop_pro.registry.field_checks import FIELD_CHECKS, field_check, tags_label
    expect("ionmix" in FIELD_CHECKS, ".cnr 适配表所属的 ionmix 族应已注册")
    fc = field_check("ionmix", "zbar")
    log(f"  tags_label(ionmix.zbar) = {tags_label(fc)!r}  unit={fc.unit}")
    fb = field_check("ionmix", "enrgy")      # 未登记名 -> "*" 兜底条目
    log(f"  tags_label(ionmix.enrgy)[兜底] = {tags_label(fb)!r}  unit={fb.unit}")
    expect_eq(tags_label(fb), "uk, uv", "未登记列名应走兜底条目（无源未核查）")


def test_cnr_ntrad_inverse():
    """ntrad 计数守恒反解：n_values = 2*n2d + (ng+1) + 2*ng*n2d + 2*ntrad*n2d。"""
    from eosop_pro.parsers.cnr_io import parse_cnr, solve_ntrad
    p = find_first(("*.cnr",))
    if p is None:
        log("  SKIP: matter++ 中未找到 .cnr 样例")
        return
    c = parse_cnr(str(p))
    n_values = len(c.raw_tail_values)
    ntrad = solve_ntrad(c.ntemp, c.ndens, c.ngrups, n_values)
    lines = [
        f"sample : {p}",
        f"ntemp={c.ntemp} ndens={c.ndens} ngrups={c.ngrups} n_values={n_values}",
        f"ntrad(solved)={ntrad} ntrad(parsed)={c.ntrad}",
        f"blocks={sorted(c.blocks)} unknown={list(c.unknown_blocks)}",
    ]
    (out_dir("cnr_io") / "ntrad_check.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    log("\n".join(lines))
    if ntrad is None:
        log("  SKIP: ntrad 无法由计数守恒唯一确定（诚实标注，不猜）")
        return
    expect_eq(ntrad, c.ntrad, "反解 ntrad 应与解析器结果一致")
    if "zbar" in c.blocks:
        expect_eq(len(c.blocks["zbar"]), c.n2d, "zbar 块长度应为 ntemp*ndens")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
