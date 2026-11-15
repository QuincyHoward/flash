"""cn4 生成数据核查 —— IONMIX 新产物（_{n}g 群数后缀命名）解析 + 绘图 + HTML 报告。

数据源: gen_eos_op/ionmix/Ionmix_run/outputfiles/cn4/ 下符合新命名规范的 cn4
    Z{Z:02d}_{frac:.2f}[-Z...]*_{ngrups}g-{YYYYmmdd_HHMM}.cn4
    以及 eos_op_data 的 CH 参考表（优先，用户指定 report 只含它）。
样例缺失时全部 SKIP（不 FAIL）。被测解析器 = cn4_io.py，产物归入
_out/cn4_io/generated/（与解析器核查产物分层）:
    <stem>/            每文件一个绘图子目录（plot_table_all_fields 批量出图）
    report.html        图文并茂核查报告（base64 内嵌图像）
    data_summary.txt   数据核查统计
"""
import _bootstrap            # noqa: F401
import _runner               # noqa: F401
from _runner import expect, expect_eq, main
from _common import out_dir, log

import base64
import datetime
import html as _html
import re
from pathlib import Path

# 生成产物根: parsers/test -> parsers -> eosop_pro -> gen_eos_op
_GEN_ROOT = Path(__file__).resolve().parents[3] / "ionmix" / "Ionmix_run" / "outputfiles" / "cn4"
# 追加核查的已注册参考表（旧命名无群数后缀；用户指定纳入完整报告）
_EXTRA_FILES = (
    Path(__file__).resolve().parents[3] / "eos_op_data" / "Gen_eos_op_data"
    / "Z06_0.50-Z01_0.50-20260708_0850" / "Z06_0.50-Z01_0.50-20260708_0850.cn4",
)
_NAME_RE = re.compile(r"^Z\d{2}_[\d.]+(?:-Z\d{2}_[\d.]+)*_\d+g-\d{8}_\d{4}\.cn4$")
_MAX_FILES = 4          # 报告最多核查的生成文件数（控制图像量）
# 被测解析器是 cn4_io.py —— 产物归入 _out/cn4_io/generated/（用户 2026-11-14 裁定迁移）
_OUT = out_dir("cn4_io") / "generated"


def _find_generated() -> list:
    """报告焦点文件：**优先 CH 参考表**（用户 2026-11-14 指定 report.html
    只含 Z06 CH 示例）；参考表缺失时回退到 Ionmix_run 新命名生成产物。"""
    extras = [p for p in _EXTRA_FILES if p.exists()]
    if extras:
        return sorted(extras)
    if not _GEN_ROOT.exists():
        return []
    return sorted(p for p in _GEN_ROOT.rglob("*.cn4") if _NAME_RE.match(p.name))


def _load_record(cn4: Path) -> dict:
    """解析一个生成 cn4 → 记录 dict（含 4 张拆表与统计行）。"""
    from eosop_pro.parsers.cn4_io import load_cn4, cn4_to_parsed_tables

    t = load_cn4(str(cn4))
    try:    # 生成产物相对 outputfiles；追加的参考表相对 gen_eos_op 根
        rel = cn4.relative_to(_GEN_ROOT.parent)
    except ValueError:
        rel = cn4.relative_to(_GEN_ROOT.parents[3])
    tables = cn4_to_parsed_tables(t, relpath=str(rel))
    m = re.search(r"_(\d+)g-", cn4.name)
    ngrups_name = int(m.group(1)) if m else None
    lines = [
        f"file    : {cn4.name}",
        f"size    : {cn4.stat().st_size:,} bytes",
        f"ntemp   : {t.ntemp}   ndens: {t.ndens}   ngrups: {t.ngrups}",
        f"name _Ng: {ngrups_name}   header ngrups match: {ngrups_name == t.ngrups}",
    ]
    for tb in tables:
        lines.append(f"  table {tb.table_key}: kind={tb.kind} axes="
                     f"{ {k: len(v) for k, v in tb.axes.items()} }")
        for f in sorted(tb.fields):
            lines.append(f"    field {f}: [{tb.field_units.get(f, '?')}]")
    return {"path": cn4, "table": t, "tables": tables,
            "ngrups_name": ngrups_name, "stats": lines}


# ── 模块级缓存：_runner 按名字序执行，各测试经 _ensure_* 幂等自足 ──
_RECORDS: list = []
_PLOTS_DONE = False


def _ensure_records() -> int:
    """幂等加载生成产物记录（已加载则直接返回数量）。"""
    if _RECORDS:
        return len(_RECORDS)
    files = _find_generated()
    if not files:
        return 0
    lines = [f"gen root: {_GEN_ROOT}", f"found  : {len(files)}", ""]
    for cn4 in files[:_MAX_FILES]:
        rec = _load_record(cn4)
        _RECORDS.append(rec)
        lines += rec["stats"] + [""]
        # 群数后缀与文件头 ngrups 必须一致（命名规范守护；旧命名无后缀则跳过）
        if rec["ngrups_name"] is not None:
            expect(rec["ngrups_name"] == rec["table"].ngrups,
                   f"{cn4.name}: 文件名群数 {rec['ngrups_name']} == 头部 ngrups {rec['table'].ngrups}")
        expect(len(rec["tables"]) == 4,
               f"{cn4.name}: cn4_to_parsed_tables 应拆 4 表")
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "data_summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    log("\n".join(lines))
    return len(_RECORDS)


def _ensure_plots() -> None:
    """幂等批量出图（已出则跳过）。"""
    global _PLOTS_DONE
    if _PLOTS_DONE or not _RECORDS:
        return
    from eosop_pro.plotting.qa.gridmap import plot_table_all_fields

    for rec in _RECORDS:
        stem = rec["path"].stem
        sub = _OUT / stem
        sub.mkdir(parents=True, exist_ok=True)
        try:
            res = plot_table_all_fields(rec["tables"], str(sub), max_groups=3)
            rec["plots"] = [str(Path(res["outdir"]) / p) for p in res.get("plots", [])]
            log(f"  plots[{stem}]: {len(rec['plots'])} 张（skip {len(res.get('skipped', []))}）")
        except Exception as exc:  # noqa: BLE001 —— 绘图失败降级为无图报告
            rec["plots"] = []
            log(f"  SKIP-plot[{stem}]: {type(exc).__name__}: {exc}")
    _PLOTS_DONE = True


def test_cn4_generated_parse_statistics():
    """发现生成产物并逐文件解析统计（计数/单位/表结构）。"""
    if not _ensure_records():
        log("  SKIP: outputfiles/cn4 下无新命名（_{n}g）生成产物；先运行 Ionmix_run/gen_*.py")


def test_cn4_generated_representative_plots():
    """逐文件批量出图（EOS 场彩图 + 群不透明度 + 截断曲线）。"""
    if not _ensure_records():
        log("  SKIP: 无已解析生成产物")
        return
    _ensure_plots()


def _img_tag(png: Path) -> str:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{_html.escape(png.name)}">'
            f"<figcaption>{_html.escape(png.name)}</figcaption></figure>")


_SRC_CN4 = "eosop_pro/parsers/cn4_io.py"


def _source_section(rec: dict) -> str:
    """§0 cn4 解析源码导读：读取顺序 / 维度确认 / 群确认（含实测验证）。"""
    from eosop_pro.parsers.cn4_io import BLOCK_SPEC, OPACITY_SPEC

    t = rec["table"]
    ntemp, ndens, ngrups = t.ntemp, t.ndens, t.ngrups
    n2d, n3d = ntemp * ndens, ngrups * ntemp * ndens

    # 逐块消费表（与 parse_cn4 的 take() 顺序一一对应）
    rows = [("<b>头部 4 行</b>", "ntemp/ndens (2i10) + 原子序数 + 丰度 + <b>ngrups (i12)</b>",
             "—", "L549-551")]
    pos = 0
    blocks = ([("1 tplsma（温度网格 eV）", ntemp)]
              + [("2 densnn（数密度网格 cm⁻³）", ndens)]
              + [(f"{3+i} {attr}（2D，单位 {unit}）", n2d)
                 for i, (attr, _l, unit, _s) in enumerate(BLOCK_SPEC)]
              + [("15 engrup（群边界 eV）", ngrups + 1)]
              + [(f"{16+i} {attr}（3D 不透明度，{unit}）", n3d)
                 for i, (attr, _l, unit, _s) in enumerate(OPACITY_SPEC)])
    for name, cnt in blocks:
        rows.append((f"<b>{name}</b>", f"{cnt} 个数值",
                     f"[{pos}, {pos + cnt})",
                     "L576-584 take()"))
        pos += cnt
    block_rows = "".join(
        f"<tr><td>{a}</td><td>{b}</td><td><code>{c}</code></td><td>{d}</td></tr>"
        for a, b, c, d in rows)

    engrup = ", ".join(f"{x:.3g}" for x in t.group_bounds)
    opac = next(tb for tb in rec["tables"] if getattr(tb, "n_groups", None))
    return f"""
<section>
  <h2>§0 cn4 解析源码导读 —— 读取顺序 / 维度确认 / 群确认</h2>
  <p>解析入口 <code>{_SRC_CN4} :: parse_cn4 (L516)</code>。以下源码摘录均真实，
     行号为当前版本；实测数据 = 本文件。</p>

  <h3>① 读取顺序：头部 4 行 + 18 个数据块（BLOCK_SPEC 顺序 = OWTF 书写顺序）</h3>
  <table><tr><th>块</th><th>个数</th><th>消费区间 [起, 止)</th><th>源码</th></tr>{block_rows}</table>
  <p><b>总计数守恒公式</b>（<code>expected_number_count (L309)</code>）：
     <code>ntemp + ndens + 12·ntemp·ndens + (ngrups+1) + 3·ngrups·ntemp·ndens</code>
     = {ntemp} + {ndens} + 12·{n2d} + {ngrups + 1} + 3·{n3d} =
     <b>{t.n_numbers_expected}</b>；
     实测消费 <b>{t.n_numbers_seen}</b> —— {'✅ 守恒校验通过' if t.n_numbers_seen == t.n_numbers_expected else '❌ 不守恒'}。</p>

  <h3>② 维度确认：定宽解析 + 计数守恒 + 顺序消费三重校验</h3>
  <pre class="inp">from {_SRC_CN4.replace('/', '.')} import expected_number_count, parse_cn4

# cn4_io.py L553-564（parse_cn4 内部，摘录）:
values = _iter_fixed_width("\\n".join(lines[4:]))   # 4e12.6 定宽逐 token
expected = expected_number_count(ntemp, ndens, ngrups)
if len(values) != expected:
    raise CN4ParseError(f"数值个数不守恒: 实测 {{len(values)}}, 期望 {{expected}}...")

pos = 0
def take(n):            # 顺序消费：块顺序错一位必然在末尾校验暴露
    nonlocal pos; blk = values[pos:pos+n]; pos += n; return blk
if pos != len(values):
    raise CN4ParseError("解析后仍有未消费数值")   # 双保险 (L586)</pre>
  <p>本文件实测：<code>n_numbers_seen == n_numbers_expected == {t.n_numbers_seen}</code>；
     每个 2D 场 reshape 为 <code>(ndens={ndens}, ntemp={ntemp})</code>（温度内循环/密度外循环），
     经 <code>cn4_to_parsed_tables (L1017)</code> 转置为 ParsedTable 约定
     <code>(n_Te={ntemp}, n_x={ndens})</code>（T-major，该动作记入 notes）。</p>

  <h3>③ 群确认：三处独立证据互相锁定 ngrups={ngrups}</h3>
  <ul>
    <li><b>头部第 4 行</b>（格式 982，i12）直接声明 <code>ngrups={ngrups}</code>（L551 解出）；</li>
    <li><b>engrup 块个数反解</b>：群边界数 = ngrups+1，实测 {len(t.group_bounds)} 个
        → ngrups = {len(t.group_bounds)}−1 = <b>{len(t.group_bounds) - 1}</b>，实测值
        [{engrup}]；</li>
    <li><b>3D 块计数反解</b>：每张不透明度块含 ngrups·ntemp·ndens = {ngrups}·{ntemp}·{ndens}
        = {n3d} 个数值，由总守恒公式唯一锁定；</li>
    <li>拆表后 OPAC 表 <code>n_groups={opac.n_groups}</code>、场形状
        <code>(ngrups, n_Te, n_x) = {opac.field_shape.get('opac_rosseland')}</code>，
        群维来自 <b>群外循环</b>（L1147-1153 重排：g 外层 → j(Te) → i(nion)）。</li>
  </ul>
  <pre class="inp"># cn4_io.py L1147-1153（3D 群外循环重排，摘录）:
flat = table.opacities[attr]            # 原始 (ngrups, ndens, ntemp) 顺序
for g in range(table.ngrups):           # 群外循环
    for j in range(table.ntemp):        # 温度中循环
        for i in range(table.ndens):    # 密度内循环
            reordered.append(flat[base + i * table.ntemp + j])
to.fields[label] = reordered            # shape (ngrups, n_Te, n_x)
to.n_groups = table.ngrups</pre>
</section>"""


def test_cn4_generated_html_report():
    """汇总统计 + 图像 → 图文并茂 HTML 报告（report.html）。"""
    if not _ensure_records():
        log("  SKIP: 无可报告的生成产物")
        return
    _ensure_plots()
    sections = []
    for rec in _RECORDS:
        cn4, stem = rec["path"], rec["path"].stem
        inp = cn4.parent / "ionmxinp"
        inp_html = ""
        if inp.exists():
            src = _html.escape(inp.read_text(encoding="utf-8", errors="replace")[:1600])
            inp_html = f"<h3>ionmxinp（前 40 行节选）</h3><pre class=\"inp\">{src}</pre>"
        t = next(tb for tb in rec["tables"] if getattr(tb, "fields", None))  # EOS 拆表
        unit_rows = "".join(
            f"<tr><td><code>{_html.escape(f)}</code></td><td>{_html.escape(str(t.field_units.get(f, '?')))}</td></tr>"
            for f in sorted(t.fields))
        pngs = sorted((Path(_OUT) / stem).rglob("*.png"))
        gallery = "".join(_img_tag(p) for p in pngs) or "<p>（无图像产出）</p>"
        stats_html = "".join(f"<li>{_html.escape(s)}</li>" for s in rec["stats"] if s.strip())
        sections.append(f"""
<section>
  <h2>{_html.escape(cn4.name)}</h2>
  <p class="path">{_html.escape(str(cn4))}</p>
  <ul>{stats_html}</ul>
  <h3>EOS 字段与单位（cn4 族全部 checked，无 uk/uv 项）</h3>
  <table><tr><th>字段</th><th>单位</th></tr>{unit_rows}</table>
  {inp_html}
  <h3>核查图像（{len(pngs)} 张）</h3>
  <div class="gallery">{gallery}</div>
</section>""")

    # §0 源码导读（读取顺序/维度确认/群确认）置于最前
    sections.insert(0, _source_section(_RECORDS[0]))

    page = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>IONMIX 生成 cn4 核查报告</title>
<style>
  body {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; margin: 2em auto; max-width: 1200px; color: #222; }}
  h1 {{ border-bottom: 3px solid #3572b0; padding-bottom: .3em; }}
  section {{ border: 1px solid #ccc; border-radius: 8px; padding: 1em 1.5em; margin: 1.5em 0; background: #fafafa; }}
  h2 {{ color: #3572b0; }}
  table {{ border-collapse: collapse; }}  td, th {{ border: 1px solid #bbb; padding: 2px 10px; font-size: 0.9em; }}
  th {{ background: #eef3f8; }}
  .gallery {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  figure {{ margin: 0; text-align: center; }}
  figure img {{ max-width: 380px; border: 1px solid #999; }}
  figcaption {{ font-size: 0.75em; color: #555; }}
  pre.inp {{ background: #f4f4f4; padding: .6em; font-size: 0.8em; overflow-x: auto; }}
  .path {{ font-size: 0.8em; color: #666; word-break: break-all; }}
</style></head><body>
<h1>IONMIX 生成 cn4 数据核查报告</h1>
<p>生成时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ｜
   数据源: <code>ionmix/Ionmix_run/outputfiles/cn4/</code>（新命名 <code>_&#123;n&#125;g</code> 群数后缀）｜
   解析: <code>eosop_pro.parsers.cn4_io</code> ｜ 绘图: <code>eosop_pro.plotting.qa.gridmap</code></p>
<p>核查要点: 文件名群数 == 头部 ngrups；4 张拆表（EOS / OPAC_ROSS / OPAC_PABS / OPAC_PEMS）；
   18 个 EOS 字段单位（全部 checked，标记省略）。cn4 原始保留 verbatim，绘图轴为 nion(cm^-3)-Te(eV)。</p>
{''.join(sections)}
</body></html>"""
    rpt = _OUT / "report.html"
    rpt.write_text(page, encoding="utf-8", newline="\n")
    log(f"  report: {rpt}  ({rpt.stat().st_size:,} bytes, "
        f"{sum(len(r.get('plots', [])) for r in _RECORDS)} images)")
    expect(rpt.exists() and rpt.stat().st_size > 10_000, "HTML 报告生成且包含图像")
    expect_eq(_html.escape("Z06_0.50") != "", True, "html 模块可用")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
