"""multi_eos 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++/mat_Al-1.0/AL_eos（F1 MULTI SESAME 倒置表）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / (rho, de) 布局互证。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "multi_eos"
_PATTERNS = ("AL_eos",)


def test_multi_eos_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("multi_eos", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")


def test_multi_eos_representative_plots():
    """F1 自变量是 (rho, de)（无 Te 轴）→ isobars 不适用，走 gridmap 兜底
    （2D 场画在其原生 (de, rho) 平面并注明）。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("multi_eos")
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields(tables, str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_multi_eos_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, tags_label
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    for name in ("rho", "de", "P", "e0_cold"):
        fc = entries[name]
        log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    # 一级文档（MULTI SESAME docx）有源 + 2026-11-14 操作者视图裁定 ->
    # checked，标记整体省略
    expect_eq(tags_label(entries["rho"]), "",
              "rho 已于 2026-11-14 裁定 checked -> 标记省略")
    expect_eq(tags_label(entries["P"]), "",
              "P 已于 2026-11-14 裁定 checked -> 标记省略")
    expect_eq(tags_label(entries["*"]), "uk, uv",
              "未登记名兜底条目应为 uk, uv")


def test_multi_eos_layout_crosscheck():
    """布局互证：轴为 (rho, de)；P 场形状 = (ne, nr)；计数守恒。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    expect("rho" in t.axes and "de" in t.axes,
           f"F1 自变量轴应为 (rho, de)，实得 {sorted(t.axes)}")
    nr, ne = len(t.axes["rho"]), len(t.axes["de"])
    expect_eq(t.field_shape.get("P"), (ne, nr),
              "P 场形状应为 (ne, nr)（T/de-major，rho 快变）")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "计数守恒")
    log(f"  layout: {t.layout_rule}  (nr, ne) = ({nr}, {ne})")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
