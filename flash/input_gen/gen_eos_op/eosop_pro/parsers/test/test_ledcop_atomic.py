"""ledcop_atomic 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

样品：matter++/ATOMIC/Al.txt（F5 LEDCOP 灰度不透明度，锚点状态机解析）。
四类测试：解析统计 / 代表性图像 / 控制字典一致性 / 文件内嵌单位声明核查。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY = "ledcop_atomic"
_PATTERNS = ("Al.txt",)


def test_ledcop_atomic_parse_statistics():
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("ledcop_atomic", lines)
    log("\n".join(lines))
    t = tables[0]
    expect(len(tables) >= 1, "至少解析出 1 张表")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected,
              "灰度行计数守恒 n_t * n_rho * 5 列")


def test_ledcop_atomic_representative_plots():
    """(rho, Te) 基：Ross 热图 + NoFree 的 Zeff 型曲线（均走真实 plotting 层）。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    out = out_dir("ledcop_atomic")
    if "Ross" in t.fields and len(t.field_shape.get("Ross", ())) == 2:
        from eosop_pro.plotting.qa.qa_plots import plot_opacity_heatmap
        try_plot(
            lambda: plot_opacity_heatmap(t, field="Ross",
                                         out_path=str(out / "opacity_heatmap_Ross.png")),
            out / "opacity_heatmap_Ross.png", "opacity_heatmap:Ross")
    if "NoFree" in t.fields:
        from eosop_pro.plotting.qa.qa_plots import plot_zeff
        try_plot(
            lambda: plot_zeff(t, field="NoFree",
                              out_path=str(out / "zeff_nofree.png")),
            out / "zeff_nofree.png", "zeff:NoFree")


def test_ledcop_atomic_dictionary_consistency():
    from eosop_pro.registry.field_checks import FIELD_CHECKS, tags_label
    expect(_FAMILY in FIELD_CHECKS, f"{_FAMILY} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY]
    for name in ("rho", "Te", "Ross", "Planck", "No. Free", "Av Sq Free"):
        fc = entries[name]
        log(f"  tags_label({name!r}) = {tags_label(fc)!r}  unit={fc.unit}")
    # rho/Te/Ross/Planck 为文件内声明（in-file declaration，未核查 -> uv）；
    # No. Free / Av Sq Free 说明 .doc 乱码不可引用（无源未核查 -> uk, uv）
    expect_eq(tags_label(entries["Ross"]), "uv",
              "Ross 有文件内声明来源、未核查 -> 应为 uv")
    expect_eq(tags_label(entries["No. Free"]), "uk, uv",
              "'No. Free' 无可指认来源且未核查 -> 应为 uk, uv")


def test_ledcop_atomic_infile_units():
    """文件头第 3 行应内嵌单位声明（cm**2/gm / keV / gm/cc）。"""
    sample = find_parseable(_FAMILY, _PATTERNS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        head = [ln.rstrip("\n") for ln in fh.read().splitlines()[:5]]
    decl = [ln for ln in head if "cm**2/gm" in ln]
    log(f"  in-file decl: {decl[0].strip() if decl else '(未找到)'}")
    expect(decl, "文件头应含内嵌单位声明 'Opacities in cm**2/gm, T in keV, "
                 "density in gm/cc'")
    t = tables[0]
    expect("Ross" in t.fields and "Planck" in t.fields,
           f"灰度列应切分为 Ross/Planck/NoFree/AvSqFree，实得 {sorted(t.fields)}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
