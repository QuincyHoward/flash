"""mat_CELIA (CH 聚苯乙烯, MID201) 集成测试 —— CH_ieos + C_AN.PLANCK 组合核查。

独立测试（**不接入** parsers/test/run_all.py，用户 2026-11-14 裁定）：
单文件裸跑 ``python eosop_pro/parsers/test/test_multi/test_celia_combined.py``。

被测文件（matter++/mat_CELIA/）：
- ``CH_ieos``      multi_eos (F1)：首行数值表头 ``7590 / 0 / 101 / 100``
- ``C_AN.PLANCK``  multi_opacity (F2)：首行 ``1 / PLANCK 1 / 20 / 20``（单群灰；
  material.base 中同时充当 MID201 的 PLANCK 与 ROSSELAND）
- ``material.base`` MID201 段 REM 备注（POLYSTYRENE / SESAME 7590 / MURAKAMI 1990 /
  MFP 公式）—— 溯源证据，数据文件本身无文本头

操作者视图边界（用户提供的查看工具标注）作为**语义交叉验证**证据：
单位假设（P dyne/cm2 vs Mbar、E erg/g vs Mbar*cm3/g、T eV 原生 vs Kelvin）
逐场比对后已于 2026-11-14 由用户裁定 —— 解析器约定正确，field_checks
F1 全族 + F2 rho/Te/kappa 已转 checked，字典已重生成。
与 Z06 cn4 的数值对比为本轮骨架（TODO 清单），后续单独实现。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # parsers/test/
import _bootstrap            # noqa: F401,E402  父级四层幂等注入
import _runner               # noqa: F401,E402
from _runner import expect, expect_eq, main           # noqa: E402
from _common import out_dir, write_summary, log, try_plot, table_stats  # noqa: E402

import base64
import html as _html         # noqa: E402
from pathlib import Path as _P                        # noqa: E402

# 仓库根: test_multi -> parsers/test -> parsers -> eosop_pro -> gen_eos_op
_REPO = Path(__file__).resolve().parents[4]
_MAT = _REPO / "src" / "Multi1D++Portable20241128" / "matter++" / "mat_CELIA"
_CH_IEOS = _MAT / "CH_ieos"
_C_AN = _MAT / "C_AN.PLANCK"
_MATERIAL_BASE = _MAT / "material.base"
_OUT = out_dir("test_multi")

# ── 操作者视图（用户提供的查看工具边界标注；uv 证据，非文件内容） ──
OP_CH = {"table_id": 7590, "nr": 101, "ne": 100, "rho_max": 20880.0,
         "e0_max": 3.70145e15, "de_max": 3.13208e16,
         "P_max": 4.89085e20, "T_max": 32001.1}
OP_PL = {"rho": (1e-6, 100.0), "Te": (1.0, 1e5), "klog10": (-14.0, 14.0)}

# 模块级缓存（_runner 按名字序执行，各测试经 _ensure_* 幂等自足）
_CACHE: dict = {}


def _load_eos():
    """CH_ieos → (path, tables)，幂等缓存。"""
    if "eos" in _CACHE:
        return _CACHE["eos"]
    if not _CH_IEOS.exists():
        _CACHE["eos"] = None
        return None
    from eosop_pro.parsers.multi_eos_reader import parse_all
    tables = parse_all(str(_CH_IEOS))
    _CACHE["eos"] = (_CH_IEOS, tables)
    return _CACHE["eos"]


def _load_opacity():
    """C_AN.PLANCK → (path, tables)，幂等缓存。"""
    if "op" in _CACHE:
        return _CACHE["op"]
    if not _C_AN.exists():
        _CACHE["op"] = None
        return None
    from eosop_pro.parsers.multi_opacity import parse_all
    tables = parse_all(str(_C_AN))
    _CACHE["op"] = (_C_AN, tables)
    return _CACHE["op"]


# ── 单位假设交叉验证（证据记录，不裁决） ─────────────────────────
def _unit_crosscheck_lines(t) -> list:
    from eosop_pro.core import config
    p_max, e_max = max(t.fields["P"]), max(t.fields["E"])
    t_raw_max = max(t.fields["T"]) / config.EV_PER_K          # 解析器已 ×8.617e-5
    rows = []
    for name, raw, ops_a, ops_b, par_unit in (
        # 操作者视图: P dyne/cm2, E erg/g, T eV 原生
        # 解析器约定: P Mbar(=dyne/cm2×1e-12), E Mbar·cm3/g(=erg/g×1e-12), T Kelvin(=eV×1.16e4)
        ("P", p_max, OP_CH["P_max"], OP_CH["P_max"] / 1e12, "Mbar（解析器约定）"),
        ("E", e_max, OP_CH["de_max"], OP_CH["de_max"] / 1e12, "Mbar*cm3/g（解析器约定）"),
        ("T(原生值)", t_raw_max, OP_CH["T_max"], OP_CH["T_max"] / config.EV_PER_K,
         "Kelvin→eV（×8.617e-5）"),
    ):
        r_a = raw / ops_a if ops_a else float("nan")
        r_b = raw / ops_b if ops_b else float("nan")
        pick = "操作者视图" if abs(r_a - 1) < abs(r_b - 1) else "解析器约定"
        rows.append(f"{name}: 原生最大值={raw:.4e} | 若操作者视图({ops_a:.3e}) 比值={r_a:.3g} | "
                    f"若解析器约定({ops_b:.3e}) 比值={r_b:.3g} → 更接近【{pick}】"
                    f"（{par_unit}）")
    rows.append("裁定记录（2026-11-14 人工确认）：比值证据全部倾向解析器约定 —— "
                "操作者工具的 dyne/cm2、erg/g、eV 标注为其显示层换算值；"
                "field_checks 已按此转 checked=True（F1 全族 + F2 rho/Te/kappa），"
                "字典已重生成。")
    return rows


def test_ch_ieos_parse():
    """CH_ieos（F1 反演 EOS）：数值表头/维度/布局/tail/单位假设证据。"""
    sample = _load_eos()
    if sample is None:
        log("  SKIP: mat_CELIA/CH_ieos 不存在")
        return
    path, tables = sample
    from eosop_pro.parsers.multi_eos_reader import parse_header
    hdr = parse_header(path.read_text(encoding="utf-8", errors="replace").splitlines()[0])
    expect_eq(int(round(hdr["table_id"])), OP_CH["table_id"], "table_id = SESAME 7590")
    expect_eq(int(hdr["nr"]), OP_CH["nr"], "nr=101")
    expect_eq(int(hdr["ne"]), OP_CH["ne"], "ne=100")
    t = tables[0]
    expect_eq(t.n_numbers_seen, t.n_numbers_expected,
              f"计数守恒（20508 = with_e0 公式 + 2 tail；seen={t.n_numbers_seen}）")
    expect("raw_tail" in t.fields, "尾部 2 个未声明数值显式登记 raw_tail")
    expect_eq(len(t.axes["rho"]), OP_CH["nr"], "rho 轴 101 点")
    expect_eq(len(t.axes["de"]), OP_CH["ne"], "de 轴 100 点")
    expect_eq(t.field_shape.get("P"), (OP_CH["ne"], OP_CH["nr"]), "P 形状 (ne,nr)=(100,101)")
    expect(abs(t.axes["rho"][-1] - OP_CH["rho_max"]) < 1e-6 * OP_CH["rho_max"],
           "rho 轴末端 ≈20880 g/cm3（与操作者视图一致）")
    lines = table_stats(path, tables) + ["", "── 单位假设交叉验证 ──"] + _unit_crosscheck_lines(t)
    write_summary("test_multi", lines)
    log("\n".join(lines))


def test_c_an_planck_parse():
    """C_AN.PLANCK（F2 单群灰）：标识符表头/轴范围/κ 存储证据。"""
    sample = _load_opacity()
    if sample is None:
        log("  SKIP: mat_CELIA/C_AN.PLANCK 不存在")
        return
    path, tables = sample
    from eosop_pro.parsers.multi_opacity import parse_header
    hdr = parse_header(path.read_text(encoding="utf-8", errors="replace").splitlines()[0])
    expect_eq(int(hdr["nr"]), 20, "nr=20")
    expect_eq(int(hdr["nt"]), 20, "nt=20")
    t = tables[0]
    expect(t.kind.upper().startswith("PLANCK"), f"kind={t.kind} 为 PLANCK 灰（非多群 M）")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "计数守恒（444）")
    rho = t.axes["rho"]
    te = t.axes["Te"]
    expect(abs(rho[0] / OP_PL["rho"][0] - 1) < 0.05 and abs(rho[-1] / OP_PL["rho"][1] - 1) < 0.05,
           f"rho 轴范围 [{rho[0]:.3g},{rho[-1]:.3g}] ≈ 操作者视图 [1e-6,100] g/cm3")
    expect(abs(te[0] / OP_PL["Te"][0] - 1) < 0.05 and abs(te[-1] / OP_PL["Te"][1] - 1) < 0.05,
           f"Te 轴范围 [{te[0]:.3g},{te[-1]:.3g}] ≈ 操作者视图 [1,1e5] eV")
    kname, kval = next(iter(t.fields.items()))
    kmax = max(abs(v) for v in kval)
    lines = table_stats(path, tables) + [
        "",
        f"κ 场 {kname!r}: 数值范围 ±{kmax:.3g} → "
        + ("存储为 log10(cm2/g)（操作者视图 Opacity(log10) [-14,14] 相符）"
           if kmax <= 14 else "存储为线性 cm2/g"),
        f"单文件双角色：material.base 中 PLANCK 与 ROSSELAND 均指向 C_AN.PLANCK",
    ]
    write_summary("test_multi", lines + [""])
    log("\n".join(lines))


def test_material_base_combo():
    """material.base MID201 段：组合关系 + REM 备注逐字提取（溯源证据）。"""
    if not _MATERIAL_BASE.exists():
        log("  SKIP: material.base 不存在")
        return
    lines = _MATERIAL_BASE.read_text(encoding="utf-8", errors="replace").splitlines()
    idx = next((i for i, ln in enumerate(lines) if "POLYSTYRENE" in ln), None)
    if idx is None:
        log("  SKIP: 未找到 POLYSTYRENE REM 段")
        return
    section = lines[max(0, idx - 1): idx + 12]
    rem = [ln.strip() for ln in section if ln.strip().startswith("REM")]
    expect(len(rem) >= 4, f"提取 {len(rem)} 条 REM 备注（POLYSTYRENE/SESAME/MURAKAMI/MFP）")
    joined = "\n".join(section)

    def _map_line(kind):
        hits = [ln for ln in section if ln.strip().startswith(kind)]
        return hits[0].split()[-1] if hits else None

    eos = _map_line("EOS")
    pl = _map_line("PLANCK")
    ro = _map_line("ROSSELAND")
    expect_eq(eos, "CH_ieos", f"MID201 EOS → {eos}")
    expect_eq(pl, "C_AN.PLANCK", f"MID201 PLANCK → {pl}")
    expect_eq(ro, "C_AN.PLANCK", f"MID201 ROSSELAND → {ro}（单文件双角色）")
    _CACHE["rem"] = rem
    lines = ["── material.base MID201 组合关系 ──",
             f"EOS       → {eos}", f"PLANCK    → {pl}", f"ROSSELAND → {ro}",
             "", "── REM 溯源备注（逐字） ──"] + rem + [""]
    write_summary("test_multi", lines)
    log("\n".join(lines))


def test_combined_plots():
    """组合出图：EOS (rho,de) 原生平面 + 不透明度 (rho,Te) 彩图 + 反演骨架。"""
    eos = _load_eos()
    op = _load_opacity()
    if eos is None or op is None:
        log("  SKIP: 样例缺失")
        return
    _, eos_tables = eos
    _, op_tables = op
    t = eos_tables[0]
    # ① EOS 原生 (rho, de) 平面
    try_plot(lambda: _plots_all(eos_tables, _OUT / "CH_ieos"),
             _OUT / "CH_ieos", "eos_all_fields")
    # ② 不透明度 (rho, Te) 彩图
    kname = next(iter(op_tables[0].fields))
    from eosop_pro.plotting.qa.qa_plots import plot_opacity_heatmap
    try_plot(lambda: plot_opacity_heatmap(op_tables[0], kname,
                                          out_path=str(_OUT / "C_AN_PLANCK_heatmap.png")),
             _OUT / "C_AN_PLANCK_heatmap.png", "planck_heatmap")
    # ③ 反演骨架（为 cn4 对比铺路）：de 基 → (rho, Te)
    from eosop_pro.convert.invert_eos import is_de_based, to_Te_grid
    if not is_de_based(t):
        log("  SKIP-plot: CH_ieos 非 de 基（意外）")
        return
    import numpy as np
    from eosop_pro.plotting.qa.gridmap import plot_multi_curve
    T_ev = t.fields["T"]
    te_lo, te_hi = min(T_ev), max(T_ev)
    te_targets = np.logspace(np.log10(max(te_lo, 1e-2)),
                             np.log10(min(te_hi, 3.2e4)), 24)
    inv = to_Te_grid(t, te_targets, fields=("P",), log_value=("P",))
    P2d = inv.fields["P"]                      # (n_Te, n_rho)
    rho = t.axes["rho"]
    curves = [(f"Te={te:.3g} eV", rho, P2d[i])
              for i, te in enumerate(te_targets) if i % 4 == 0]
    out = _OUT / "CH_ieos_inverted_P_isotherms.png"
    try_plot(lambda: plot_multi_curve(curves, xlabel="rho (g/cm3)",
                                      ylabel="P (Mbar)",
                                      title="CH_ieos inverted P(rho) isotherms "
                                            "[skeleton: T unit TBD, see summary]",
                                      outfile=str(out)),
             out, "inverted_isotherms")
    log(f"  反演骨架: to_Te_grid OK（{len(te_targets)} 个 Te 目标），"
        "T 单位假设待核实 → 对比 cn4 前必须裁定")


def _plots_all(tables, outdir):
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields
    return plot_table_all_fields(tables, str(outdir), family="multi_eos")


def test_cn4_comparison_stub():
    """cn4 对比骨架：定位并解析 Z06 参考表，登记 TODO（本轮无数值对比）。"""
    from eosopdata._samples import first_cn4
    cn4 = first_cn4()
    if cn4 is None:
        log("  SKIP: 未找到 Z06 cn4 参考表")
        return
    from eosop_pro.parsers.cn4_io import load_cn4, cn4_to_parsed_tables
    t = load_cn4(str(cn4))
    tables = cn4_to_parsed_tables(t)
    expect_eq(len(tables), 4, "Z06 cn4 拆 4 表（EOS/ROSS/PABS/PEMS）")
    todo = [
        "DONE-1 单位裁定（2026-11-14 人工确认，已关闭）：CH_ieos 原生 P max=4.89e8 Mbar"
        "（=操作者视图 4.89e20 dyne/cm2 ÷1e12）、T 原生 3.714e8 K ×8.617e-5 ≈ 32003 eV"
        "（=操作者视图 32001.1 eV）——操作者工具的 dyne/cm2/eV 标注是换算后显示值。"
        "field_checks 已转 checked（F1 全族 + F2 rho/Te/kappa），字典已重生成",
        "TODO-2 EOS 对比口径：CH_ieos 为 (rho,de) 基 → invert_eos.to_Te_grid 反演 P/E；"
        "cn4 EOS 在 (nion,Te) 网格（rho 为派生场）→ 经 rho 轴对齐"
        "（build_grid_for_tables + resample_2d）",
        "TODO-3 不透明度对比口径：C_AN.PLANCK 为单群灰（PLANCK 1），"
        "cn4 为 6 群（opac_planck_abs）→ 需定义灰化口径（如 Planck 加权群平均）或仅并排可视化",
        "TODO-4 材料差异备注：cn4 为 IONMIX 计算的 Z06_0.50-Z01_0.50（C/H 1:1 原子比），"
        "mat_CELIA 为 SESAME 7590 聚苯乙烯 + Murakami 解析不透明度——"
        "两者物理模型不同，差值大属预期，对比目标是量级与趋势",
    ]
    _CACHE["todo"] = todo
    lines = ["── cn4 对比骨架 ──", f"参考表: {cn4}", f"ntemp={t.ntemp} ndens={t.ndens} ngrups={t.ngrups}",
             ""] + todo
    write_summary("test_multi", lines)
    log("\n".join(lines))


# ── HTML 报告 ────────────────────────────────────────────────────
def _img_tag(png: Path) -> str:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{_html.escape(png.name)}">'
            f"<figcaption>{_html.escape(png.name)}</figcaption></figure>")


def _build_report() -> Path:
    import datetime
    rem = _CACHE.get("rem", [])
    todo = _CACHE.get("todo", [])
    rem_html = "".join(f"<li><code>{_html.escape(r)}</code></li>" for r in rem) or "<li>（未提取）</li>"
    todo_html = "".join(f"<li>{_html.escape(x)}</li>" for x in todo)
    eos_head = _html.escape(_CH_IEOS.read_text(encoding="utf-8", errors="replace").splitlines()[0]) \
        if _CH_IEOS.exists() else "（文件缺失）"
    op_head = _html.escape(_C_AN.read_text(encoding="utf-8", errors="replace").splitlines()[0]) \
        if _C_AN.exists() else "（文件缺失）"
    pngs = sorted(_OUT.rglob("*.png"))
    gallery = "".join(_img_tag(p) for p in pngs) or "<p>（无图像）</p>"
    page = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>mat_CELIA 集成核查报告</title>
<style>
  body {{ font-family: "Segoe UI","Microsoft YaHei",sans-serif; margin: 2em auto; max-width: 1150px; color: #222; }}
  h1 {{ border-bottom: 3px solid #7c4db0; padding-bottom: .3em; }}
  section {{ border: 1px solid #ccc; border-radius: 8px; padding: 1em 1.5em; margin: 1.5em 0; background: #fafafa; }}
  h2 {{ color: #7c4db0; }}  table {{ border-collapse: collapse; }}  td, th {{ border: 1px solid #bbb; padding: 3px 10px; font-size: .9em; }}
  th {{ background: #f1ebf8; }}
  .gallery {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  figure {{ margin: 0; text-align: center; }}  figure img {{ max-width: 380px; border: 1px solid #999; }}
  figcaption {{ font-size: .75em; color: #555; }}
  pre.inp {{ background: #f4f4f4; padding: .6em; font-size: .85em; overflow-x: auto; }}
</style></head><body>
<h1>mat_CELIA（CH 聚苯乙烯 MID201）集成核查报告</h1>
<p>生成: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ｜ 被测: CH_ieos (F1 multi_eos) +
   C_AN.PLANCK (F2 multi_opacity) ｜ 独立测试（不接 run_all）</p>

<section><h2>1. 溯源备注（material.base MID201 段 REM，逐字）</h2>
  <ul>{rem_html}</ul>
  <p>这四条是操作者视图（含单位标注）的出处——数据文件本身从第 1 行起即 4×15 定宽数值。</p></section>

<section><h2>2. 文件首行原文与判读</h2>
  <h3>CH_ieos</h3><pre class="inp">{eos_head}</pre>
  <p>4 数表头：table_id=<b>7590</b>（SESAME 聚苯乙烯材料码）· rho0=0 · nr=<b>101</b> · ne=<b>100</b>；
     后接 rho(101) → de(100) → e0(101) → P(101×100) → T(101×100)，尾部 2 个未声明数值
     （raw_tail 显式登记，与 BE_eos_i 先例一致）。</p>
  <h3>C_AN.PLANCK</h3><pre class="inp">{op_head}</pre>
  <p>表号 1 · 标识符 <b>PLANCK 1</b>（单群灰，区别于多群 "PLANCK M"）· nr=20 · nt=20；
     后接 log10(ρ) 20 点（-6..2 → 1e-6..100 g/cm³）+ log10(T) 20 点（0..5 → 1..1e5 eV）
     + 400 个 κ（log10 cm²/g，±14 范围）。</p></section>

<section><h2>3. MID201 组合关系（material.base）</h2>
  <table><tr><th>角色</th><th>文件</th></tr>
  <tr><td>EOS</td><td><code>CH_ieos</code></td></tr>
  <tr><td>PLANCK</td><td><code>C_AN.PLANCK</code></td></tr>
  <tr><td>ROSSELAND</td><td><code>C_AN.PLANCK</code>（单文件双角色）</td></tr></table></section>

<section><h2>4. 单位假设对照（操作者视图 vs 解析器约定）—— ✅ 2026-11-14 已裁定</h2>
  <p>详见 <code>_out/test_multi/summary.txt</code> 交叉验证节。三处疑点：
     ① T：操作者视图标注 eV 原生 [0, 32001.1]，解析器按 F1 惯例 Kelvin→eV（×8.617e-5）；
     ② E/de：erg/g vs Mbar·cm³/g（差 1e12）；③ P：dyne/cm² vs Mbar（差 1e12）。
     逐场比值证据全部倾向解析器约定 —— <b>用户已确认（2026-11-14）：操作者工具标注为
     换算后显示值，解析器约定正确</b>；field_checks F1 全族 + F2 rho/Te/kappa 已转
     checked，字典已重生成。</p></section>

<section><h2>5. 核查图像（{len(pngs)} 张）</h2>
  <div class="gallery">{gallery}</div></section>

<section><h2>6. 与 Z06 cn4 对比 —— TODO（本轮骨架）</h2><ul>{todo_html}</ul></section>
</body></html>"""
    rpt = _OUT / "report.html"
    rpt.write_text(page, encoding="utf-8", newline="\n")
    log(f"  report: {rpt}  ({rpt.stat().st_size:,} bytes, {len(pngs)} images)")
    return rpt


def test_multi_report():
    """汇总 → 图文 HTML 报告（_out/test_multi/report.html）。"""
    if _load_eos() is None and _load_opacity() is None:
        log("  SKIP: 样例缺失")
        return
    rpt = _build_report()
    expect(rpt.exists() and rpt.stat().st_size > 5_000, "HTML 报告生成")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
