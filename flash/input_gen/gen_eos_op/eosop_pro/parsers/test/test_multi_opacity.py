"""multi_opacity 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++/Thermos 树（``*.dat``，行 1 带标签/类型码的 F2 不透明度表）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / 行 1 类型码反解互证。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "multi_opacity"
_PATTERNS = ("*.dat",)       # 全树 .dat 名匹配；limit 放宽以越过前段不可解析文件

#: F2 全部受控 KIND（KIND_BY_LABEL ∪ KIND_BY_F2 ∪ 多群 MUGROUP）
_KNOWN_KINDS = {"PLANCK", "ROSSELAND", "MUGROUP", "ZEFF", "ZEFF2",
                "EMISSIVITY", "NONLTE"}


def test_multi_opacity_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS, limit=600)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("multi_opacity", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")


def test_multi_opacity_representative_plots():
    sample = find_parseable(_FAMILY, _PATTERNS, limit=600)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("multi_opacity")
    # 热图只对 2D 场适用（多群 3D 场形状 (ng, nt, nr) 会由 heatmap 拒绝 → SKIP-plot）
    field = "kappa" if "kappa" in t.fields else (
        sorted(t.fields)[0] if t.fields else "")
    if field:
        shape = t.field_shape.get(field, ())
        if len(shape) == 2:
            from eosop_pro.plotting.qa.qa_plots import plot_opacity_heatmap
            try_plot(
                lambda: plot_opacity_heatmap(t, field=field,
                                             out_path=str(out / "opacity_heatmap.png")),
                out / "opacity_heatmap.png", f"opacity_heatmap:{field}")
        else:
            log(f"  SKIP-plot: opacity_heatmap（字段 {field!r} 为 "
                f"{len(shape)}D 群场，形状 {shape}）")
    # 全字段批量兜底（含多群逐群图 + _report.txt）
    try:
        from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
        rep = plot_table_all_fields(tables, str(out), family=_FAMILY)
        pngs = list(out.rglob("*.png"))
        log(f"  plot: gridmap n_plots={rep.get('n_plots', '?')} pngs={len(pngs)}")
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: gridmap_all_fields -> {type(exc).__name__}: {exc}")


def test_multi_opacity_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, tags_label
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    for name in ("rho", "Te", "kappa", "Z"):
        fc = entries[name]
        log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    # rho/Te/kappa 有一级文档来源 + 2026-11-14 操作者视图裁定 -> checked 省略；
    # Z（NZ 段）= 2026-11-14 45 元素族校准裁定 log10(zbar) -> checked 省略
    expect_eq(tags_label(entries["rho"]), "",
              "rho 已于 2026-11-14 裁定 checked -> 标记省略")
    expect_eq(tags_label(entries["Z"]), "",
              "Z 已于 2026-11-14 族校准裁定 log10(zbar) checked -> 标记省略")
    expect_eq(entries["Z"].unit, "log10(zbar)",
              "Z 单位登记 = log10(zbar)（裁定口径）")


def test_multi_opacity_header_typecode():
    """行 1 类型码反解：表头行的 (nr, nt) 应与轴长度互证；kind 属受控词表。"""
    sample = find_parseable(_FAMILY, _PATTERNS, limit=600)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    from eosop_pro.parsers.multi_opacity import parse_header
    hdr = parse_header(t.header_raw)
    log(f"  header row1: label={hdr['label']!r} f2={hdr['f2']} "
        f"nr={hdr['nr']} nt={hdr['nt']}")
    expect_eq(hdr["nr"], len(t.axes["rho"]),
              "行 1 类型码行的 nr 应与 rho 轴长度一致")
    expect_eq(hdr["nt"], len(t.axes["Te"]),
              "行 1 类型码行的 nt 应与 Te 轴长度一致")
    expect(t.kind in _KNOWN_KINDS,
           f"kind={t.kind!r} 应属受控 KIND 词表 {_KNOWN_KINDS}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
