"""cn4 → MULTI (F1/F2) 转换评估 —— 与 mat_CELIA CH 文件对比。

独立裸跑::

    python test_cn4_to_multi.py          # 不接入 run_all（与 test_celia_combined 同策略）

产物（``parsers/test/_out/cn4_to_multi/``）::

    CH_from_cn4_eos        cn4 → F1（no_e0 布局）
    CH_from_cn4_rosseland  cn4 Rosseland → F2（6 群）
    CH_from_cn4_planck     cn4 Planck 吸收 → F2（6 群）
    *.png                  对比图（英文标注）
    report.html            评估报告（口径声明 + 统计表 + 图）
    summary.txt

口径（2026-11-14 用户裁定）:
* de ≡ E_total = e_ion + e_ele（no_e0 布局）；IONMIX 能量零点在冷态
  （T=0 时 E≡0），故 de 即文献口径 E−E_c（SESAME 301−306），不引入假冷曲线。
* 单位链: P J/cm3 ÷1e5 → Mbar；E J/g ÷1e5 → Mbar*cm3/g；T eV（writer 写 K）。
* 不透明度: cn4 grupbd=6 群（边界 0.1..1e5 eV）与 MULTI C_1G/C_20G/C_100G
  群数不同 —— **除非边界相同，否则只转换+绘图，不做数值对比**。
* 物理声明: cn4=IONMIX 模型产物，mat_CELIA=SESAME/Celia 产物；
  对比是"转换正确性 + 数值邻近度评估"，非模型一致性验证。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # parsers/test/
import _bootstrap                                          # noqa: F401,E402
import _runner
from _runner import expect, expect_eq, main                # noqa: F401,E402
from _common import out_dir, write_summary, log            # noqa: F401,E402

import base64
import html as _html
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eosop_pro import config
from eosop_pro.parsers.cn4_io import parse_cn4, cn4_to_parsed_tables
from eosop_pro.parsers.multi_eos_reader import parse_all as f1_parse
from eosop_pro.parsers.multi_opacity import parse_all as f2_parse
from eosop_pro.convert.invert_eos import to_Te_grid
from eosop_pro.convert.writers_multi import (
    write_multi_eos_from_cn4,
    write_multi_opacity_from_cn4,
)
from eosop_pro.grid.monotonic import make_log_uniform
from eosop_pro.test.eosopdata._samples import first_cn4

_REPO = Path(__file__).resolve().parents[4]
_MAT = _REPO / "src" / "Multi1D++Portable20241128" / "matter++" / "mat_CELIA"
_CH_IEOS = _MAT / "CH_ieos"
_MULTI_OPAC_FILES = {n: _MAT / f"C_{n}G.{ext}"
                     for n in (1, 20, 100) for ext in ("PLANCK", "ROSS")}
_C_AN = _MAT / "C_AN.PLANCK"
_OUT = out_dir("cn4_to_multi")

_N_DE = 60                    # F1 目标 de 轴点数
_N_TE_CMP = 48                # 对比 Te 轴点数

_CACHE: dict = {}


# ── 惰性加载与转换（幂等自足） ─────────────────────────────────────
def _cn4():
    if "cn4" in _CACHE:
        return _CACHE["cn4"]
    p = first_cn4()
    if p is None:
        _CACHE["cn4"] = None
        return None
    cn4 = parse_cn4(p)
    _CACHE["cn4"] = (p, cn4, cn4_to_parsed_tables(cn4))
    return _CACHE["cn4"]


def _ensure_convert():
    """执行转换并写出 3 个文件；返回 meta dict（幂等）。"""
    if "conv" in _CACHE:
        return _CACHE["conv"]
    src = _cn4()
    if src is None:
        _CACHE["conv"] = None
        return None
    _cn4_path, cn4, tables = src
    eos, ross, pabs, _pems = tables
    meta = {"cn4_path": _cn4_path, "cn4": cn4, "tables": tables}
    meta["f1_path"] = write_multi_eos_from_cn4(
        eos, _OUT / "CH_from_cn4_eos", n_de=_N_DE,
        table_id=7590)   # SESAME 7590 = polystyrene（与 mat_CELIA/CH_ieos 同编号惯例）
    meta["f2_ross_path"] = write_multi_opacity_from_cn4(
        ross, _OUT / "CH_from_cn4_rosseland", avgatw=cn4.avgatw)
    meta["f2_planck_path"] = write_multi_opacity_from_cn4(
        pabs, _OUT / "CH_from_cn4_planck", avgatw=cn4.avgatw)
    meta["f1"] = f1_parse(str(meta["f1_path"]))[0]
    meta["f2_ross"] = f2_parse(str(meta["f2_ross_path"]))
    meta["f2_planck"] = f2_parse(str(meta["f2_planck_path"]))
    _CACHE["conv"] = meta
    return meta


def _ch_eos():
    if "ch" in _CACHE:
        return _CACHE["ch"]
    if not _CH_IEOS.exists():
        _CACHE["ch"] = None
        return None
    tabs = f1_parse(str(_CH_IEOS))
    t = tabs[0]
    if "E" not in t.fields:                      # E = de + e0（with_e0 布局）
        ne, nr = t.field_shape["P"]
        de = np.asarray(t.axes["de"])
        e0 = np.asarray(t.fields.get("e0_cold", [0.0] * nr))
        E2d = np.full((ne, nr), np.nan)
        for i in range(ne):
            for j in range(nr):
                E2d[i, j] = de[i] + e0[j]
        t.fields["E"] = E2d.reshape(-1).tolist()
        t.field_shape["E"] = (ne, nr)
        t.field_units["E"] = "Mbar*cm3/g"
    _CACHE["ch"] = t
    return t


def _load_multi_opac(path: Path):
    if not path.exists():
        return None
    tabs = f2_parse(str(path))
    return tabs[0] if tabs else None


# ── 插值工具 ──────────────────────────────────────────────────────
def _interp_rho(fields: dict, rho_own, rho_q) -> dict:
    """把 (n_Te, n_rho_own) 的场沿 log10(rho) 插值到 rho_q。NaN 列跳过。"""
    lr = np.log10(np.asarray(rho_own, dtype=float),
                  where=np.asarray(rho_own, dtype=float) > 0,
                  out=np.full(len(rho_own), np.nan))
    lq = np.log10(np.asarray(rho_q, dtype=float))
    out = {}
    for nm, M in fields.items():
        M = np.asarray(M, dtype=float)
        good = np.isfinite(lr)
        out[nm] = np.vstack([np.interp(lq, lr[good], M[i, :][good])
                             for i in range(M.shape[0])])
    return out


def _rel_stats(a, ref):
    """相对误差统计（以 ref 为基准）；仅取两者有限处。"""
    m = np.isfinite(a) & np.isfinite(ref)
    if not m.any():
        return None
    rel = np.abs(a[m] - ref[m]) / np.maximum(np.abs(ref[m]), 1e-30)
    return {"n": int(m.sum()), "median": float(np.median(rel)),
            "p90": float(np.percentile(rel, 90)), "max": float(rel.max())}


# ── 图（英文标注，Agg） ───────────────────────────────────────────
def _img_tag(png: Path) -> str:
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" style="max-width:96%">'
    # 供 _build_report 使用


def _plot_heat(ax, M, rho, yv, title, *, ylab="log10(Te [eV])"):
    lr = np.log10(rho)
    ly = np.log10(yv)
    im = ax.imshow(M, aspect="auto", origin="lower",
                   extent=[lr[0], lr[-1], ly[0], ly[-1]], cmap="viridis")
    ax.set_xlabel("log10(rho [g/cm3])")
    ax.set_ylabel(ylab)
    ax.set_title(title, fontsize=10)
    plt.colorbar(im, ax=ax, shrink=0.85)


def _plot_f1_curves(meta, ch) -> list:
    """T(de) / P(de) 曲线对比（公共 rho 窗口两端）+ 生成表 T 热图。"""
    pngs = []
    gen = meta["f1"]
    rho_gen = np.asarray(gen.axes["rho"])
    de = np.asarray(gen.axes["de"])
    P = np.asarray(gen.fields["P"]).reshape(gen.field_shape["P"])
    T = np.asarray(gen.fields["T"]).reshape(gen.field_shape["T"])
    ch_rho = np.asarray(ch.axes["rho"])
    ch_de = np.asarray(ch.axes["de"])
    ch_P = np.asarray(ch.fields["P"]).reshape(ch.field_shape["P"])
    ch_T = np.asarray(ch.fields["T"]).reshape(ch.field_shape["T"])

    # 公共 rho 窗口: CH 正网格 ∩ cn4 范围（排除 rho=0 真空列）
    lo = max(rho_gen[rho_gen > 0].min(), ch_rho[ch_rho > 0].min())
    hi = min(rho_gen.max(), ch_rho.max())
    pos = ch_rho[ch_rho > 0]
    picks = sorted({float(pos[np.argmin(np.abs(pos - lo))]),
                    float(pos[np.argmin(np.abs(pos - hi))])})

    fig, axes = plt.subplots(2, len(picks), figsize=(6.4 * len(picks), 7),
                             squeeze=False, sharex="col")
    for k, rq in enumerate(picks):
        jg = int(np.argmin(np.abs(np.log10(rho_gen) - np.log10(rq))))
        jc = int(np.argmin(np.abs(ch_rho - rq)))
        axes[0][k].loglog(de, T[:, jg], label=f"cn4->F1 (rho={rq:.1f})")
        axes[0][k].loglog(ch_de, ch_T[:, jc], "--", label=f"CH_ieos (rho={rq:.1f})")
        axes[0][k].set_ylabel("T [eV]")
        axes[0][k].legend(fontsize=8)
        axes[0][k].set_title(f"T vs de @ rho={rq:.1f} g/cm3", fontsize=10)
        axes[1][k].loglog(de, P[:, jg], label="cn4->F1")
        axes[1][k].loglog(ch_de, ch_P[:, jc], "--", label="CH_ieos")
        axes[1][k].set_ylabel("P [Mbar]")
        axes[1][k].set_xlabel("de [Mbar*cm3/g]")
        axes[1][k].legend(fontsize=8)
    fig.tight_layout()
    p1 = _OUT / "f1_curves.png"
    fig.savefig(p1, dpi=110)
    plt.close(fig)
    pngs.append(p1)

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    _plot_heat(ax, T, rho_gen, de, "cn4->F1 T(rho,de) [eV]",
               ylab="log10(de [Mbar*cm3/g])")
    ax.set_title("cn4->F1 T field (no_e0 layout)", fontsize=10)
    fig.tight_layout()
    p2 = _OUT / "f1_heatmap_T.png"
    fig.savefig(p2, dpi=110)
    plt.close(fig)
    pngs.append(p2)
    return pngs


def _plot_f2(meta) -> list:
    """cn4 生成 F2 与 MULTI 灰/多群 PLANCK 的 log10(kappa) 热图（仅绘图）。"""
    panels = []
    for key, title in (("f2_ross", "cn4->F2 Rosseland (6-group mean)"),
                       ("f2_planck", "cn4->F2 Planck abs (6-group mean)")):
        t = meta[key][0]
        fname = next(iter(t.fields))
        M = np.asarray(t.fields[fname]).reshape(t.field_shape[fname])
        panels.append((M.mean(axis=0), np.asarray(t.axes["rho"]),
                       np.asarray(t.axes["Te"]), title))
    for path, title in ((_C_AN, "MULTI C_AN.PLANCK (gray)"),
                        (_MAT / "C_20G.PLANCK", "MULTI C_20G.PLANCK (20-group mean)")):
        t = _load_multi_opac(path)
        if t is None:
            continue
        fname = next(iter(t.fields))
        M = np.asarray(t.fields[fname]).reshape(t.field_shape[fname])
        if M.ndim == 3:                       # 多群：群均值（仅定性绘图）
            M = M.mean(axis=0)
        panels.append((M, np.asarray(t.axes["rho"]),
                       np.asarray(t.axes["Te"]), title))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    for ax, (M, rho, Te, title) in zip(axes.ravel(), panels):
        _plot_heat(ax, M, rho, Te, title)
    fig.suptitle("log10(kappa [cm2/g]) -- plot-only (group boundaries differ)",
                 fontsize=11)
    fig.tight_layout()
    p = _OUT / "f2_heatmaps.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    return [p]


# ── 对比计算 ──────────────────────────────────────────────────────
def _compare_f1(meta, ch) -> dict:
    gen = meta["f1"]
    Te_q = np.geomspace(1.0, 19998.6, _N_TE_CMP)
    rho_gen = np.asarray(gen.axes["rho"])
    rho_ch = np.asarray(ch.axes["rho"])
    lo = max(rho_gen[rho_gen > 0].min(), rho_ch[rho_ch > 0].min())
    hi = min(rho_gen.max(), rho_ch.max())
    rho_q = np.geomspace(lo, hi, 5)

    res_g = to_Te_grid(gen, Te_q, fields=("P", "E"), log_value=("P",))
    res_c = to_Te_grid(ch, Te_q, fields=("P", "E"), log_value=("P",))
    g = _interp_rho(res_g.fields, rho_gen, rho_q)
    c = _interp_rho(res_c.fields, rho_ch, rho_q)
    return {"rho_q": rho_q, "Te_q": Te_q,
            "P": _rel_stats(g["P"], c["P"]),
            "E": _rel_stats(g["E"], c["E"]),
            "coverage_g": res_g.coverage, "coverage_c": res_c.coverage,
            "window": (float(lo), float(hi))}


def _bounds_table(meta) -> list:
    cn4 = meta["cn4"]
    rows = [("cn4 (IONMIX, grupbd=6)",
             str(cn4.ngrups), str([round(b, 3) for b in cn4.group_bounds]))]
    for n in (1, 20, 100):
        t = _load_multi_opac(_MAT / f"C_{n}G.PLANCK")
        if t is None:
            rows.append((f"C_{n}G.PLANCK", "MISSING", "-"))
            continue
        b = t.group_bounds
        rows.append((f"C_{n}G.PLANCK",
                     str(t.n_groups if t.n_groups else "?"),
                     str([round(x, 3) for x in b]) if b else "-"))
    t = _load_multi_opac(_C_AN)
    if t is not None:
        rows.append(("C_AN.PLANCK (gray)", "1", "-"))
    return rows


# ── 测试 ──────────────────────────────────────────────────────────
def test_convert_f1():
    meta = _ensure_convert()
    if meta is None:
        log("  SKIP: 无可用 cn4 样品")
        return
    t = meta["f1"]
    expect("de" in t.axes and "rho" in t.axes, "F1 读回须有 rho/de 轴")
    expect("e0_cold" not in t.fields, "F1 应为 no_e0 布局")
    ne, nr = t.field_shape["P"]
    expect_eq((ne, nr), (_N_DE, meta["cn4"].ndens), "F1 形状 (n_de,n_rho)")
    P = np.asarray(t.fields["P"])
    T = np.asarray(t.fields["T"])
    expect(bool(np.isfinite(P).all()), "F1 P 无 NaN（edge 延拓）")
    expect(bool(np.isfinite(T).all()), "F1 T 无 NaN")
    expect(T.min() > 0 and P.min() > 0, "F1 P/T 全正（log 一致性）")
    d = np.asarray(t.axes["de"])
    expect(bool((np.diff(d) > 0).all()), "de 轴单调升")
    log(f"  F1: {meta['f1_path'].name}  rho [{rho_fmt(t)}]  de [{d[0]:.3g},{d[-1]:.3g}] Mbar*cm3/g")


def rho_fmt(t):
    r = t.axes["rho"]
    return f"{r[0]:.3g},{r[-1]:.3g}] g/cm3"


def test_f1_roundtrip():
    """转换链闭合：生成 F1 再反演回 (rho,Te)，与 cn4 原始 P/E 比较。"""
    meta = _ensure_convert()
    if meta is None:
        return
    cn4, tables = meta["cn4"], meta["tables"]
    eos = tables[0]
    Te_q = np.asarray(eos.axes["Te"])
    # cn4 原始（已换算单位）
    P_ref = np.asarray([v * 1e-5 for v in eos.fields["P"]]).reshape(eos.field_shape["P"])
    E_ref = np.asarray([v * 1e-5 for v in eos.fields["E"]]).reshape(eos.field_shape["E"])
    res = to_Te_grid(meta["f1"], Te_q, fields=("P", "E"), log_value=("P",))
    P_g = res.fields["P"]
    E_g = res.fields["E"]
    sP = _rel_stats(P_g, P_ref)
    sE = _rel_stats(E_g, E_ref)
    expect(sP is not None and sP["median"] < 0.10,
           f"F1 往返 P 中位相对误差 <10%（实测 {sP['median']:.2%}）")
    expect(sE is not None and sE["median"] < 0.10,
           f"F1 往返 E 中位相对误差 <10%（实测 {sE['median']:.2%}）")
    _CACHE["roundtrip"] = {"P": sP, "E": sE}
    log(f"  往返闭合: P median={sP['median']:.2%} p90={sP['p90']:.2%} max={sP['max']:.2%}; "
        f"E median={sE['median']:.2%}")


def test_convert_f2():
    meta = _ensure_convert()
    if meta is None:
        return
    cn4 = meta["cn4"]
    for key in ("f2_ross", "f2_planck"):
        tabs = meta[key]
        expect(len(tabs) == 1, f"{key}: 多群子表应归并为 1 张表")
        t = tabs[0]
        expect_eq(t.n_groups, cn4.ngrups, f"{key}: 群数 = cn4 ngrups")
        b = np.asarray(t.group_bounds)
        expect(bool(np.allclose(b, cn4.group_bounds, rtol=1e-6)),
               f"{key}: 群边界与 cn4 一致")
        fname = next(iter(t.fields))
        v = np.asarray(t.fields[fname])
        expect(bool((v > -20).all() and (v < 20).all()),
               f"{key}: log10(kappa) 范围合理")
        log(f"  {key}: {t.table_key} ng={t.n_groups} "
            f"klog10 [{v.min():.2f},{v.max():.2f}]")


def test_group_bounds_vs_multi():
    meta = _ensure_convert()
    if meta is None:
        return
    rows = _bounds_table(meta)
    cn4_bounds = [round(b, 3) for b in meta["cn4"].group_bounds]
    match = any(str(cn4_bounds) == r[2] and r[1] not in ("MISSING", "1")
                for r in rows[1:])          # rows[0] 是 cn4 自身，必须排除
    expect(not match, "群边界不同 → 按裁定只绘图不数值对比（记录决策）")
    _CACHE["bounds_rows"] = rows
    for r in rows:
        log(f"  bounds: {r[0]}  ng={r[1]}  {r[2][:60]}")


def test_f1_vs_ch_ieos():
    meta = _ensure_convert()
    if meta is None or not _CH_IEOS.exists():
        log("  SKIP: mat_CELIA/CH_ieos 不存在")
        return
    ch = _ch_eos()
    cmp_res = _compare_f1(meta, ch)
    _CACHE["f1_cmp"] = cmp_res
    for nm in ("P", "E"):
        s = cmp_res[nm]
        expect(s is not None, f"F1 vs CH_ieos: {nm} 有公共可比点")
        log(f"  vs CH_ieos {nm}: n={s['n']} median={s['median']:.2%} "
            f"p90={s['p90']:.2%} max={s['max']:.2%}")
    log(f"  rho 对比窗口: {cmp_res['window'][0]:.3g}..{cmp_res['window'][1]:.3g} g/cm3"
        f"（CH_ieos rho 网格低端密、高端疏；与 cn4 rho≤216 在窗口内重叠）")


def test_multi_report():
    meta = _ensure_convert()
    if meta is None:
        return
    pngs = []
    if _CH_IEOS.exists():
        pngs += _plot_f1_curves(meta, _ch_eos())
    pngs += _plot_f2(meta)
    _CACHE["pngs"] = pngs

    cmp_res = _CACHE.get("f1_cmp")
    rt = _CACHE.get("roundtrip", {})
    bounds_rows = _CACHE.get("bounds_rows", [])
    cn4 = meta["cn4"]
    eos = meta["tables"][0]

    def _stats_html(nm, s):
        if s is None:
            return "<td>-</td><td>-</td><td>-</td><td>-</td>"
        return (f"<td>{s['n']}</td><td>{s['median']:.2%}</td>"
                f"<td>{s['p90']:.2%}</td><td>{s['max']:.2%}</td>")

    rows_cmp = ""
    if cmp_res:
        rows_cmp += ("<tr><td>P (vs CH_ieos)</td>" + _stats_html("P", cmp_res["P"]) + "</tr>"
                     "<tr><td>E (vs CH_ieos)</td>" + _stats_html("E", cmp_res["E"]) + "</tr>")
    if "P" in rt:
        rows_cmp += ("<tr><td>P (cn4 往返闭合)</td>" + _stats_html("P", rt["P"]) + "</tr>"
                     "<tr><td>E (cn4 往返闭合)</td>" + _stats_html("E", rt["E"]) + "</tr>")

    rows_b = "".join(f"<tr><td>{_html.escape(a)}</td><td>{b}</td>"
                     f"<td><code>{_html.escape(c[:80])}</code></td></tr>"
                     for a, b, c in bounds_rows)

    imgs = "".join(f"<h3>{_html.escape(p.stem)}</h3>{_img_tag(p)}" for p in pngs)
    products = "".join(
        f"<li><code>{_html.escape(str(p.relative_to(_OUT)))}</code></li>"
        for p in [meta["f1_path"], meta["f2_ross_path"], meta["f2_planck_path"]])

    html_doc = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>cn4 → MULTI 转换评估报告</title>
<style>
body{{font-family:Segoe UI,Microsoft YaHei,sans-serif;margin:2em auto;max-width:1080px;
     color:#1e1e1e;background:#fafafa}}
h1{{border-bottom:3px solid #3572b0;padding-bottom:.3em}}
h2{{color:#3572b0;margin-top:1.6em}}
table{{border-collapse:collapse;margin:.8em 0}}
td,th{{border:1px solid #bbb;padding:4px 10px;font-size:.92em}}
th{{background:#e8eef5}}
code{{background:#eee;padding:1px 4px;border-radius:3px}}
.note{{background:#fff7e0;border-left:4px solid #e0a800;padding:.6em 1em;margin:.8em 0}}
.decl{{background:#eaf3ea;border-left:4px solid #3a8a3a;padding:.6em 1em;margin:.8em 0}}
</style></head><body>
<h1>cn4 → MULTI (F1/F2) 转换评估报告</h1>
<p>生成时间（UTC）：<span id="ts"></span><script>
document.getElementById("ts").textContent=new Date().toISOString();</script><br>
cn4 样品：<code>{_html.escape(str(meta['cn4_path']))}</code>
（{cn4.species_label}，ntemp={cn4.ntemp}, ndens={cn4.ndens}, ngrups={cn4.ngrups}，
&lt;A&gt;={cn4.avgatw:.4f} amu [{cn4.atomwt_source}]）</p>

<h2>1. 转换口径声明（2026-11-14 用户裁定）</h2>
<div class="decl">
<p><b>de 口径（no_e0 布局）</b>：de ≡ E_total = e_ion + e_ele。依据：
① 一手文档 <i>MULTI使用的SESAME数据文件格式.docx</i> 仅保证
"pressures at energy de[i]+e0"、"e0=冷能量"，文件层面 E_total = de + e0；
② IONMIX 能量零点构造性位于冷态（T=0 时 E≡0），故 cn4 侧 E_c≡0，
de 即文献口径 E−E_c（SESAME 301−306 分表之差），<b>不引入假冷曲线</b>。
若未来需与绝对冷能表混用，可补 with_e0 变体（e0(ρ)=E(ρ,T_min)）。</p>
<p><b>单位链</b>：P：J/cm³ ÷1e5 → Mbar；E：J/g ÷1e5 → Mbar·cm³/g；
T：eV（F1 文件按 MULTI 约定写 Kelvin）；κ：cm²/g（F2 存 log10）。</p>
<p><b>不透明度对比策略</b>：cn4 {cn4.ngrups} 群（边界 0.1–1e5 eV）与
MULTI C_1G/C_20G/C_100G 群数不同 → <b>除非边界相同，只转换+绘图，不做数值对比</b>。</p>
</div>
<div class="note"><b>物理声明</b>：cn4 是 IONMIX 模型产物，mat_CELIA 是
SESAME/Celia 产物 —— 本报告的对比是"转换正确性 + 数值邻近度评估"，
<b>不是</b>两个物理模型的一致性验证。</div>

<h2>2. 转换产物</h2>
<ul>{products}</ul>
<p>F1：no_e0 布局，de 轴 log10 等距 {_N_DE} 点
[{np.geomspace(1,1,1).size and ''}{_fmt_range(meta, 'de')}]；
往返反演覆盖率见 §3。</p>

<h2>3. 数值评估</h2>
<table><tr><th>对比项</th><th>n</th><th>median</th><th>p90</th><th>max</th></tr>
{rows_cmp}</table>
<p>往返闭合 = 生成 F1 → 再反演 (rho,Te) → 与 cn4 原始场比较（检验转换链自身精度）。
vs CH_ieos = 同口径换算后与 MULTI 官方 CH 表比较（检验跨模型邻近度）。</p>
<div class="note">rho 对比窗口受限于轴重叠：CH_ieos rho 线性网格 0–20880 g/cm³
（步长≈208.8），cn4 rho 上限 {max(meta['f1'].axes['rho']):.1f} g/cm³ →
有效窗口仅 {cmp_res['window'][0]:.1f}–{cmp_res['window'][1]:.1f} g/cm³。
全程对比见曲线图（定性）。</div>

<h2>4. 不透明度群边界对照（裁定：边界不同 → 只绘图）</h2>
<table><tr><th>文件</th><th>群数</th><th>群边界 (eV)</th></tr>{rows_b}</table>

<h2>5. 图</h2>
{imgs}
</body></html>"""
    rp = _OUT / "report.html"
    rp.write_text(html_doc, encoding="utf-8", newline="\n")
    log(f"  report: {rp}")
    write_summary("cn4_to_multi", [
        f"cn4: {meta['cn4_path'].name} ({cn4.species_label})",
        f"F1: {meta['f1_path'].name} no_e0 n_de={_N_DE}",
        f"F2: {meta['f2_ross_path'].name} / {meta['f2_planck_path'].name} ng={cn4.ngrups}",
        f"roundtrip: {rt}",
        f"vs CH_ieos: {cmp_res}",
    ])
    expect(rp.exists(), "report.html 已生成")


def _fmt_range(meta, axis):
    t = meta["f1"]
    v = t.axes[axis]
    return f"{v[0]:.3g} – {v[-1]:.3g} " + ("Mbar*cm3/g" if axis == "de" else "g/cm3")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
