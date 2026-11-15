"""hyades_eos 产物核查 —— 解析统计 + 代表性图像（人工核查用）。

一个文件覆盖共用 F3 解析器的 3 个族：
``hyades_eos``（qeos_*）/ ``hyades_opacity``（opc_*）/ ``sesame_dat``（eos_*）。
四类测试：各族解析统计 / 代表性图像 / 控制字典一致性 / L 计数公式交叉校验。
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, write_summary, log, sample_or_skip, try_plot, table_stats
from eosopdata._samples import find_parseable

_FAMILY_EOS = "hyades_eos"
_FAMILY_OPAC = "hyades_opacity"
_FAMILY_SESAME = "sesame_dat"

_PATTERNS = {
    _FAMILY_EOS: ("qeos_*.dat",),
    _FAMILY_OPAC: ("opc_*.dat",),
    _FAMILY_SESAME: ("eos_*.dat",),
}

#: find_parseable 结果缓存（同进程各族只扫一次；值为 (path, tables) | None）
_CACHE: dict[str, tuple | None] = {}


def _get(family: str):
    if family not in _CACHE:
        _CACHE[family] = find_parseable(family, _PATTERNS[family])
    return _CACHE[family]


def test_hyades_eos_parse_statistics():
    sample = _get(_FAMILY_EOS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("hyades_eos", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")


def test_hyades_opacity_parse_statistics():
    sample = _get(_FAMILY_OPAC)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("hyades_eos", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")
    expect("Rosseland" in tables[0].fields and "Planck" in tables[0].fields,
           "opc_* 两数组应判序为 [Rosseland, Planck] 两字段")


def test_sesame_dat_parse_statistics():
    sample = _get(_FAMILY_SESAME)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    lines = table_stats(path, tables)
    write_summary("hyades_eos", lines)
    log("\n".join(lines))
    expect(len(tables) >= 1, "至少解析出 1 张表")


def test_hyades_representative_plots():
    """EOS 表画等压线（field=P）；不透明度表画热图（field=Rosseland）。"""
    out = out_dir("hyades_eos")
    from eosop_pro.plotting.qa.qa_plots import plot_eos_isobars, plot_opacity_heatmap
    jobs = (
        (_FAMILY_EOS, "P", plot_eos_isobars),
        (_FAMILY_SESAME, "P", plot_eos_isobars),
        (_FAMILY_OPAC, "Rosseland", plot_opacity_heatmap),
    )
    for family, field, fn in jobs:
        sample = _get(family)
        if not sample:
            log(f"  SKIP-plot: {family} 无样例")
            continue
        t = sample[1][0]
        if field not in t.fields:
            log(f"  SKIP-plot: {family} 无字段 {field!r} "
                f"(fields={sorted(t.fields)})")
            continue
        try_plot(
            lambda t=t, field=field, fn=fn: fn(
                t, field=field,
                out_path=str(out / f"{family}_{field}.png")),
            out / f"{family}_{field}.png", f"{family}:{field}")


def test_hyades_dictionary_consistency():
    """三族共用 _HYADES 条目（rho/Te/P/E/kappa 有 Hyades doc 一级来源）。"""
    from eosop_pro.registry.field_checks import FIELD_CHECKS, tags_label
    for family in (_FAMILY_EOS, _FAMILY_OPAC, _FAMILY_SESAME):
        expect(family in FIELD_CHECKS, f"{family} 应已注册字段控制字典")
    entries = FIELD_CHECKS[_FAMILY_EOS]
    for name in ("rho", "Te", "P", "kappa", "raw_tail"):
        fc = entries[name]
        log(f"  tags_label({name}) = {tags_label(fc)!r}  unit={fc.unit}")
    expect_eq(tags_label(entries["rho"]), "uv",
              "rho 有一级文档来源、未核查 -> 应为 uv")
    expect_eq(tags_label(entries["raw_tail"]), "uk, uv",
              "尾部残余值无任何一级来源 -> 应为 uk, uv")


def test_hyades_eos_dims_crosscheck():
    """L 计数公式交叉校验：payload 维度 (nr, nt) 应满足 2*nr*nt+nr+nt+2 = L。"""
    from eosop_pro.parsers.hyades_eos import parse_header_line, solve_dims
    sample = _get(_FAMILY_EOS)
    if not sample_or_skip(sample):
        return
    path, tables = sample
    t = tables[0]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    hdr = parse_header_line(lines[1])            # 行 2 = id zbar abar rho0 L
    sols = solve_dims(hdr["L"])
    nr, nt = len(t.axes["rho"]), len(t.axes["Te"])
    log(f"  L={hdr['L']} payload 维度 (nr, nt)=({nr}, {nt})；"
        f"可行解数={len(sols)}")
    expect((nr, nt) in sols or (nt, nr) in sols,
           f"payload 维度 ({nr},{nt}) 应在 L={hdr['L']} 的可行解集内")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
