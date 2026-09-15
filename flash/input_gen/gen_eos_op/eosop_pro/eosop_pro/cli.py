"""``eosop_pro`` 命令行入口 —— 所有动作的唯一实现，``scripts/*.py`` 只是薄包装。

用法::

    python -m eosop_pro.cli parse   <relpath>      # 解析单文件并打印摘要
    python -m eosop_pro.cli infer   <relpath>      # 通用反演报告（阶段 B）
    python -m eosop_pro.cli identify [<relpath>]   # 声明 vs 内容 比对
    python -m eosop_pro.cli zeff                   # Z̄ 盘点并写报告
    python -m eosop_pro.cli convert <relpath> --out o.cn4          # 默认转 cn4
    python -m eosop_pro.cli convert <relpath> --to hyades_eos --out o.dat
    python -m eosop_pro.cli h5      <relpath> --out o.h5
    python -m eosop_pro.cli plot    <relpath> --outdir outputs/plots
    python -m eosop_pro.cli targets                # 列出可转换目标

批量（与 ``scripts/*.py`` / ``scripts/run_all.bat`` 一一对应）::

    python -m eosop_pro.cli inventory              # 全量文件清单与目录画像
    python -m eosop_pro.cli extract-docs           # 抽取 doc/docx/pdf → docs/extracted
    python -m eosop_pro.cli audit                  # 阶段 A 全量声明式审计（覆盖率闸口）
    python -m eosop_pro.cli convert-all            # 批量写双轨 HDF5
    python -m eosop_pro.cli plot-all               # 批量 QA 出图
    python -m eosop_pro.cli infer-unknown [<rel>]  # 零先验反演（单个 or 未决集合）
    python -m eosop_pro.cli prune-reports          # 报告目录只留最新一批

所有路径均可给出相对于 ``matter++`` 的相对路径。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _resolve(rel: str) -> Path:
    from . import config
    p = Path(rel)
    if p.exists():
        return p
    return config.MATTER(rel)


def cmd_targets(args) -> int:
    from .convert import list_targets
    print("可转换目标：")
    for t in list_targets():
        print(f"  {t.name:<22} {t.description}")
        if t.requires_fields:
            print(f"      needs fields: {', '.join(t.requires_fields)}")
    return 0


def cmd_parse(args) -> int:
    from .registry import declared_types as dt
    from .registry.dispatch import parse_declared
    rel = args.relpath
    d = dt.declare(rel)
    out = parse_declared(rel, d)
    s = out.snapshot
    print(f"文件        : {rel}")
    print(f"声明类型    : {d.family}  (来源 {d.source}；候选 {d.families})")
    print(f"状态        : {s.status}")
    print(f"实际家族    : {s.family}")
    print(f"分派规则    : {s.dispatch_rule}")
    print(f"维度        : nr={s.nr} nt={s.nt} ng={s.n_groups}")
    print(f"计数        : actual={s.n_numbers_actual} expected={s.n_numbers_expected} delta={s.count_delta}")
    print(f"单位来源    : {s.unit_source}")
    for t in out.tables:
        print(f"  → {t.table_key}: {t.summary()}")
    for n in s.diagnostics[:8]:
        print(f"    · {n}")
    return 0 if s.is_ok else 1


def cmd_infer(args) -> int:
    from .core.inference import infer_file
    r = infer_file(_resolve(args.relpath))
    print(r.report())
    return 0 if r.ok else 1


def cmd_identify(args) -> int:
    from .registry.identify import identify, sweep, write_report
    if args.relpath:
        c = identify(args.relpath)
        print(c.describe())
        for n in c.notes:
            print("  · " + n)
        return 0
    comps = sweep()
    csv_p, md_p = write_report(comps)
    print(f"比对 {len(comps)} 个文件 → {csv_p.name} / {md_p.name}")
    from collections import Counter
    print(Counter(c.agreement for c in comps).most_common())
    return 0


def cmd_zeff(args) -> int:
    from .registry.zeff_inventory import ZeffInventory
    inv = ZeffInventory()
    inv.build()
    csv_p, md_p = inv.write_reports()
    print("Z̄ 盘点:", inv.summary())
    print(f"报告 → {csv_p.name} / {md_p.name}")
    return 0


def cmd_convert(args) -> int:
    from .convert import convert, get_target
    from .registry import declared_types as dt
    from .registry.dispatch import parse_declared
    rel = args.relpath
    out = parse_declared(rel, dt.declare(rel))
    if not out.tables:
        print(f"无法解析 {rel}（status={out.snapshot.status}）", file=sys.stderr)
        return 1
    tbl = out.tables[0]
    tgt = get_target(args.to)
    if getattr(args, "invert", False):
        # --invert：先反演到 (rho,Te) 再写，故坐标轴检查交由 writer 负责
        ok, why = True, ""
        if "*" not in tgt.requires and tbl.kind not in tgt.requires:
            ok, why = False, f"kind {tbl.kind!r} 不在 {tgt.requires} 中"
        elif [f for f in tgt.requires_fields if f not in tbl.fields]:
            ok, why = False, f"缺少场 {[f for f in tgt.requires_fields if f not in tbl.fields]}"
    else:
        ok, why = tgt.can_write(tbl)
    if not ok:
        print(f"{tbl.table_key} 不能写为 {args.to}: {why}", file=sys.stderr)
        return 1
    inv = getattr(args, "invert", False)
    extra: dict = {}
    if (getattr(args, "izgas", None) or getattr(args, "fracsp", None)
            or getattr(args, "atomwt", None)):
        if args.to != "cn4":
            print("警告: --izgas/--fracsp/--atomwt 仅用于 cn4 目标，已忽略",
                  file=sys.stderr)
        else:
            if args.izgas:
                extra["izgas"] = [int(x) for x in args.izgas.split(",")]
            if args.fracsp:
                extra["fracsp"] = [float(x) for x in args.fracsp.split(",")]
            if args.atomwt:
                extra["atomwt"] = [float(x) for x in args.atomwt.split(",")]
    if inv:
        p = convert(tbl, args.out, target=args.to, skip_axes_check=True,
                    invert=True, **extra)
    else:
        p = convert(tbl, args.out, target=args.to, **extra)
    print(f"{tbl.table_key} -> {args.to}: {p}")
    return 0


def cmd_h5(args) -> int:
    from .grid.unified_grid import build_all_grids
    from .registry import declared_types as dt
    from .registry.dispatch import parse_declared
    from .writer.h5_writer import write_material_h5
    rel = args.relpath
    out = parse_declared(rel, dt.declare(rel))
    if not out.tables:
        print(f"无法解析 {rel}", file=sys.stderr)
        return 1
    grids = build_all_grids(out.tables, A=args.A)
    p = write_material_h5(args.out or f"{out.tables[0].table_key}.h5",
                          material={"material_name": out.tables[0].table_key,
                                    "source_relpath": rel},
                          tables=out.tables, grids=grids, A=args.A)
    print(f"写出 {p}（{len(out.tables)} 表，{len(grids)} 套统一网格）")
    return 0


def cmd_plot(args) -> int:
    from . import config
    from .parsers import multi_opacity as f2
    from .plotting import qa_plots
    rel = args.relpath
    od = Path(args.outdir or config.PLOTS_DIR)
    t = f2.parse(config.MATTER(rel), rel)
    stem = Path(rel).stem
    made = []
    if "kappa" in t.fields:
        made.append(qa_plots.plot_opacity_heatmap(t, "kappa",
                                                  out_path=od / f"{stem}_kappa.png"))
    if "Z" in t.fields:
        made.append(qa_plots.plot_zeff(t, "Z", out_path=od / f"{stem}_zeff.png"))
    print(f"出图 {len(made)} 张 → {od}")
    return 0


# ══════════════════════════════════════════════════════════════
# 批量动作 —— 与 scripts/*.py 一一对应
# ══════════════════════════════════════════════════════════════
def cmd_inventory(args) -> int:
    """② matter++ 全量文件清单与目录画像。"""
    from . import batch
    batch.inventory(outdir=args.outdir, matter_dir=args.matter_dir,
                    report_dir=args.report_dir)
    return 0


def cmd_extract_docs(args) -> int:
    """① 抽取 doc/docx/pptx/xlsx/pdf/xmind → docs/extracted/。"""
    from . import docsrc
    res = docsrc.extract_all(args.root, outdir=args.outdir)
    for r in res:
        print(r.describe())
    ok = sum(1 for r in res if r.ok)
    print("-" * 70)
    print(f"抽取 {ok}/{len(res)} 份成功 -> "
          f"{args.outdir or docsrc.config.EXTRACTED_DIR}")
    return 0 if ok else 1


def cmd_audit(args) -> int:
    """③ 阶段 A 全量声明式审计。"""
    from . import batch
    r = batch.audit_sweep(outdir=args.outdir, multigroup=args.multigroup,
                          matter_dir=args.matter_dir, report_dir=args.report_dir,
                          limit=args.limit)
    return 0 if r["pass"] else 1


def cmd_convert_all(args) -> int:
    """⑤ 批量写双轨 HDF5。"""
    from . import batch
    batch.convert_all(outdir=args.outdir, limit=args.limit,
                      only_families=tuple(args.family or ()),
                      only_relpaths=tuple(args.relpath or ()),
                      include_multigroup=args.multigroup,
                      with_unified=not args.native_only,
                      with_native=not args.unified_only,
                      report_dir=args.report_dir,
                      n_x=args.n_x, n_Te=args.n_te)
    return 0


def cmd_plot_all(args) -> int:
    """⑥ 批量 QA 出图（PPT 级、全英文）。"""
    from . import batch
    batch.plot_all(outdir=args.outdir, limit=args.limit,
                   only_families=tuple(args.family or ()),
                   report_dir=args.report_dir)
    return 0


def cmd_infer_unknown(args) -> int:
    """阶段 B：零先验反演（给 relpath 就单文件，否则扫全部未决文件）。"""
    from . import batch
    if args.relpath:
        r = batch.infer_unknown(args.relpath, outdir=args.outdir, dump=not args.no_dump)
        return 0 if r["ok"] else 1
    batch.infer_unrecognized(from_report=args.from_report, outdir=args.outdir,
                             limit=args.limit, rescan=args.rescan,
                             report_dir=args.report_dir)
    return 0


def cmd_prune_reports(args) -> int:
    """① 报告目录保留策略：每类只留最新 N 批（固定名报告不动）。"""
    from . import prune
    prune.prune_reports(outdir=args.outdir, keep=args.keep,
                        dry_run=args.dry_run)
    return 0


# ══════════════════════════════════════════════════════════════
# cn4 专题动作 —— 二维彩图 / 一维曲线 / EOS 路径 / 群大图
# ══════════════════════════════════════════════════════════════
def cmd_cn4_plot(args) -> int:
    """单个 cn4 文件出图（彩图 / 曲线 / 群大图 三选一）。"""
    from .parsers.cn4_io import load_cn4
    from .plotting import cn4_plots as P

    tbl = load_cn4(args.cn4)
    print(f"文件: {args.cn4}")
    print(f"成分: {tbl.species_label}  网格: ntemp={tbl.ntemp} ndens={tbl.ndens} "
          f"ngrups={tbl.ngrups}")

    if args.all_groups:
        outs = P.plot_all_opacity_figures(tbl, outdir=args.outdir or "plots",
                                          transmission_L=args.length)
        for o in outs:
            print(f"  [+] {o}")
        return 0

    if args.group is not None:
        o = P.plot_opacity_group_figure(tbl, args.group, outfile=args.out,
                                        transmission_L=args.length)
        print(f"output: {o}")
        return 0

    if args.kind == "curve":
        for q in args.quantity:
            for fn, tag in ((P.plot_vs_temperature, "vs_T"),
                            (P.plot_vs_density, "vs_nion")):
                o = fn(tbl, q, ig=args.ig, outfile=None)
                print(f"output: {o}")
        return 0

    # 默认: 二维彩图
    for q in args.quantity:
        o = P.plot_quantity_heatmap(
            tbl, q, args.x_axis, args.y_axis, ig=args.ig,
            outfile=args.out, transmission_L=args.length,
            cmap=args.cmap, zlog=None if not args.zlog else True,
            xlog=not args.no_xlog, ylog=not args.no_ylog)
        print(f"quantity={q} x={args.x_axis} y={args.y_axis}")
        print(f"output: {o}")
    return 0


def cmd_cn4_plot_all(args) -> int:
    """批量：目录下全部 ``.cn4`` 出图（多文件流水线入口）。"""
    from . import batch
    r = batch.plot_cn4_all(
        outdir=args.outdir, cn4_dir=args.cn4_dir, limit=args.limit,
        quantities=tuple(args.quantity) if args.quantity else None,
        axes_pairs=tuple(tuple(p.split("-")) for p in args.axes) if args.axes else None,
        curves=tuple(args.curve) if args.curve else None,
        opacity_figures=args.opacity_figures, transmission_L=args.length,
        report_dir=args.report_dir)
    return 0 if r.get("n_plots", 0) or not r.get("errors") else 1


def cmd_cn4_paths(args) -> int:
    """cn4 EOS 路径研究：等温 / 等压 / 等熵 / 雨贡纽 / P-V 图。"""
    from .parsers.cn4_io import load_cn4
    from .plotting import cn4_paths as E

    tbl = load_cn4(args.cn4)
    print(f"文件: {args.cn4}  成分: {tbl.species_label}")
    od = args.outdir or "."
    what = args.what

    if what == "isotherm":
        x, P, e, o = E.trace_isotherm(
            tbl, T_idx=args.t_idx, T=args.temp, x_axis=args.x_axis,
            outfile=f"{od}/isotherm.png")
        print(f"[isotherm] {len(x)} pts -> {o}")
    elif what == "isobar":
        T_c, n_c, o = E.trace_isobar(tbl, args.pressure,
                                     outfile=f"{od}/isobar.png")
        print(f"[isobar] {len(T_c)} pts -> {o}")
    elif what == "isentrope":
        s = E.compute_entropy(tbl)
        T_c, n_c, o = E.trace_isentrope(
            tbl, s, s0_idx=(args.i0, args.j0), outfile=f"{od}/isentrope.png")
        print(f"[isentrope] {len(T_c)} pts -> {o}")
    elif what == "hugoniot":
        rho_c, P_c, Us, Up, o = E.trace_hugoniot(
            tbl, ref_idx=(args.i0, args.j0), rho0=args.rho0, T0=args.temp,
            outfile=f"{od}/hugoniot.png", n_rho=args.n_rho, n_T=args.n_T)
        o2 = E.plot_usup_vs_pressure(Us, Up, P_c,
                                     outfile=f"{od}/hugoniot_usup_vs_P.png")
        print(f"[hugoniot] {len(rho_c)} pts -> {o} | {o2}")
    elif what == "pv":
        s = E.compute_entropy(tbl)
        rho_c, P_c, Us, Up, _ = E.trace_hugoniot(
            tbl, ref_idx=(args.i0, args.j0), n_rho=args.n_rho, n_T=args.n_T,
            outfile=f"{od}/_tmp_hug.png")
        rho_ref = float(rho_c[len(rho_c) // 2]) if len(rho_c) else None
        T_ref = float(tbl.temperature[args.j0])
        o = E.plot_pv_diagram(tbl, T_ref, s, rho_ref, rho_c, P_c,
                             outfile=f"{od}/pv_diagram.png")
        print(f"[pv] -> {o}")
    elif what == "probe":
        o, info = E.plot_interpolated_probe(
            tbl, args.rho0, args.temp or float(tbl.temperature[0]),
            outfile=f"{od}/interp_probe.png")
        print(f"[probe] {info} -> {o}")
    else:
        print(f"未知 --what {what!r}", file=sys.stderr)
        return 1
    return 0


def cmd_cn4_fit(args) -> int:
    """cn4 关系拟合：幂律 / 指数 / 理想气体 / 通用。"""
    from .parsers.cn4_io import load_cn4
    from .plotting import cn4_fit as F

    tbl = load_cn4(args.cn4)
    od = args.outdir or "."
    what = args.what

    if what == "ideal_gas":
        slope, r2, o = F.fit_ideal_gas(tbl, T_idx=args.t_idx,
                                       outfile=f"{od}/fit_ideal_gas.png")
        print(f"[ideal_gas] slope={slope:.6e} Mbar/cc, R2={r2:.6f} -> {o}")
        return 0

    # 幂律/指数/通用：需要显式 x/y 场
    import numpy as np
    field = np.asarray(tbl.field(args.field), dtype=float).reshape(
        tbl.ndens, tbl.ntemp)
    j = args.t_idx
    x = np.asarray(tbl.density, dtype=float)
    y = field[:, j]
    if what == "power":
        a, b, r2, o = F.fit_power_law(x, y, xlabel=r"$n_i$ (cm$^{-3}$)",
                                      ylabel=args.field,
                                      outfile=f"{od}/fit_power_law.png")
        print(f"[power] a={a:.6g} b={b:.6f} R2={r2:.6f} -> {o}")
    elif what == "exp":
        a, b, r2, o = F.fit_exponential(x, y, xlabel=r"$n_i$ (cm$^{-3}$)",
                                        ylabel=args.field,
                                        outfile=f"{od}/fit_exponential.png")
        print(f"[exp] a={a:.6g} b={b:.6f} R2={r2:.6f} -> {o}")
    else:
        print(f"未知 --what {what!r}", file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eosop_pro", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("targets", help="列出可转换目标").set_defaults(func=cmd_targets)

    p = sub.add_parser("parse", help="解析单文件"); p.add_argument("relpath")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("infer", help="通用反演（阶段 B）"); p.add_argument("relpath")
    p.set_defaults(func=cmd_infer)

    p = sub.add_parser("identify", help="声明 vs 内容 比对")
    p.add_argument("relpath", nargs="?", default=None); p.set_defaults(func=cmd_identify)

    sub.add_parser("zeff", help="Z̄ 盘点").set_defaults(func=cmd_zeff)

    p = sub.add_parser("convert", help="跨格式转换")
    p.add_argument("relpath")
    p.add_argument("--to", default="cn4",
                   help="目标格式（默认 cn4；可选值见 targets 子命令）")
    p.add_argument("--out", required=True)
    p.add_argument("--izgas", default=None,
                   help="cn4 目标：原子序数列表，逗号分隔（如 6 或 1,6）")
    p.add_argument("--fracsp", default=None,
                   help="cn4 目标：归一化丰度列表（单元素可省）")
    p.add_argument("--atomwt", default=None,
                   help="cn4 目标：原子量列表，逗号分隔（可选）")
    p.add_argument("--invert", action="store_true",
                   help="源表为 (rho,de) 基时先反演到 (rho,Te)")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("h5", help="写单表 HDF5")
    p.add_argument("relpath"); p.add_argument("--out", default=None)
    p.add_argument("--A", type=float, default=None); p.set_defaults(func=cmd_h5)

    p = sub.add_parser("plot", help="QA 出图（单文件）")
    p.add_argument("relpath"); p.add_argument("--outdir", default=None)
    p.set_defaults(func=cmd_plot)

    # ── 批量 ───────────────────────────────────────────────────
    p = sub.add_parser("inventory", help="② 全量文件清单与目录画像")
    p.add_argument("--outdir", default=None)
    p.add_argument("--matter-dir", dest="matter_dir", default=None)
    p.add_argument("--report-dir", dest="report_dir", default=None,
                   help="报告落盘目录（缺省 outputs/reports；测试用）")
    p.set_defaults(func=cmd_inventory)

    p = sub.add_parser("extract-docs", help="① 抽取说明文档 → docs/extracted")
    p.add_argument("--root", default=None)
    p.add_argument("--outdir", default=None)
    p.set_defaults(func=cmd_extract_docs)

    p = sub.add_parser("audit", help="③ 阶段 A 全量声明式审计")
    p.add_argument("--outdir", default=None)
    p.add_argument("--matter-dir", dest="matter_dir", default=None)
    p.add_argument("--limit", type=int, default=0,
                   help="只审计前 N 个声明文件（0 = 全量）")
    p.add_argument("--multigroup", action="store_true",
                   help="额外解析 LEDCOP 多群段（显著更慢）")
    p.add_argument("--report-dir", dest="report_dir", default=None,
                   help="报告落盘目录（缺省 outputs/reports；测试用）")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("convert-all", help="⑤ 批量写双轨 HDF5")
    p.add_argument("--outdir", default=None)
    p.add_argument("--limit", type=int, default=0, help="0 = 不设上限")
    p.add_argument("--family", action="append", default=None,
                   help="只处理指定家族（可重复）")
    p.add_argument("--multigroup", action="store_true")
    p.add_argument("--native-only", dest="native_only", action="store_true")
    p.add_argument("--unified-only", dest="unified_only", action="store_true")
    p.add_argument("--n-x", dest="n_x", type=int, default=None)
    p.add_argument("--n-te", dest="n_te", type=int, default=None)
    p.add_argument("--report-dir", dest="report_dir", default=None,
                   help="报告落盘目录（缺省 outputs/reports；测试用）")
    p.add_argument("--relpath", action="append", default=None,
                   help="只处理指定相对路径（可重复；顺序即处理顺序）")
    p.set_defaults(func=cmd_convert_all)

    p = sub.add_parser("plot-all", help="⑥ 批量 QA 出图")
    p.add_argument("--outdir", default=None)
    p.add_argument("--limit", type=int, default=40, help="0 = 不设上限")
    p.add_argument("--family", action="append", default=None)
    p.add_argument("--report-dir", dest="report_dir", default=None,
                   help="报告落盘目录（缺省 outputs/reports；测试用）")
    p.set_defaults(func=cmd_plot_all)

    p = sub.add_parser("prune-reports",
                       help="① 报告目录保留策略（每类只留最新 N 批）")
    p.add_argument("--outdir", default=None)
    p.add_argument("--keep", type=int, default=1, help="每类保留的批次数（默认 1）")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="只列不删")
    p.set_defaults(func=cmd_prune_reports)

    p = sub.add_parser("infer-unknown",
                       help="④ 零先验反演；给 relpath 则单文件，否则扫全部未决文件")
    p.add_argument("relpath", nargs="?", default=None)
    p.add_argument("--outdir", default=None)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--from-report", dest="from_report", default=None,
                   help="复用指定的 audit_all.*.csv 挑未决文件（默认取最新）")
    p.add_argument("--rescan", action="store_true",
                   help="忽略审计报告，重新全树扫描（慢，~2 分钟）")
    p.add_argument("--no-dump", dest="no_dump", action="store_true")
    p.add_argument("--report-dir", dest="report_dir", default=None,
                   help="报告落盘目录（缺省 outputs/reports；测试用）")
    p.set_defaults(func=cmd_infer_unknown)

    # ── cn4 专题 ───────────────────────────────────────────────
    p = sub.add_parser("cn4-plot", help="单个 cn4 出图（彩图/曲线/群大图）")
    p.add_argument("cn4", help=".cn4 文件路径")
    p.add_argument("--kind", choices=("heatmap", "curve"), default="heatmap",
                   help="heatmap=二维彩图（默认）；curve=一维变化曲线")
    p.add_argument("-q", "--quantity", action="append", default=None,
                   help="物理量名（可重复）；缺省按 kind 取默认集")
    p.add_argument("-x", "--x-axis", dest="x_axis", default="T",
                   choices=("T", "tele", "nion", "nele", "rho"))
    p.add_argument("-y", "--y-axis", dest="y_axis", default="nion",
                   choices=("T", "tele", "nion", "nele", "rho"))
    p.add_argument("--ig", type=int, default=1, help="不透明度群号 (1-based)")
    p.add_argument("-L", "--length", type=float, default=0.01,
                   help="透射率特征长度 L (cm)")
    p.add_argument("-g", "--group", type=int, default=None,
                   help="输出该群的 2x2 大图")
    p.add_argument("-A", "--all-groups", dest="all_groups", action="store_true",
                   help="输出全部群的 2x2 大图")
    p.add_argument("-o", "--out", default=None, help="输出 PNG 路径")
    p.add_argument("--outdir", default=None, help="批量大图的输出目录")
    p.add_argument("--cmap", default="cubehelix")
    p.add_argument("--zlog", action="store_true", help="颜色对数色标")
    p.add_argument("--no-xlog", action="store_true", help="x 轴线性")
    p.add_argument("--no-ylog", action="store_true", help="y 轴线性")
    p.set_defaults(func=cmd_cn4_plot)

    p = sub.add_parser("cn4-plot-all", help="批量：目录下全部 .cn4 出图")
    p.add_argument("--cn4-dir", dest="cn4_dir", default=None,
                   help="含 .cn4 的目录（缺省 matter++/Ionmix 或 eos_op_data）")
    p.add_argument("--outdir", default=None)
    p.add_argument("--limit", type=int, default=0, help="0 = 不设上限")
    p.add_argument("-q", "--quantity", action="append", default=None,
                   help="二维彩图物理量（可重复）")
    p.add_argument("--axes", action="append", default=None,
                   help="轴组合 'X-Y'，如 'T-nion'（可重复）")
    p.add_argument("--curve", action="append", default=None,
                   help="一维曲线物理量（可重复）")
    p.add_argument("--opacity-figures", dest="opacity_figures",
                   action="store_true", help="额外输出每个能群的 2x2 大图")
    p.add_argument("-L", "--length", type=float, default=0.01,
                   help="透射率特征长度 L (cm)")
    p.add_argument("--report-dir", dest="report_dir", default=None)
    p.set_defaults(func=cmd_cn4_plot_all)

    p = sub.add_parser("cn4-paths", help="cn4 EOS 路径：等温/等压/等熵/雨贡纽/P-V")
    p.add_argument("cn4")
    p.add_argument("--what", required=True,
                   choices=("isotherm", "isobar", "isentrope", "hugoniot",
                            "pv", "probe"))
    p.add_argument("--t-idx", dest="t_idx", type=int, default=10,
                   help="温度网格索引")
    p.add_argument("--i0", type=int, default=0, help="密度网格索引")
    p.add_argument("--j0", type=int, default=0, help="温度网格索引（参考态）")
    p.add_argument("--temp", type=float, default=None, help="温度数值 (eV)")
    p.add_argument("--pressure", type=float, default=None, help="等压线 P (J/cm^3)")
    p.add_argument("--rho0", type=float, default=None, help="参考质量密度 (g/cm^3)")
    p.add_argument("--x-axis", dest="x_axis", default="rho",
                   choices=("rho", "nion"), help="等温线横轴")
    p.add_argument("--n-rho", dest="n_rho", type=int, default=240)
    p.add_argument("--n-T", dest="n_T", type=int, default=80)
    p.add_argument("--outdir", default=None)
    p.set_defaults(func=cmd_cn4_paths)

    p = sub.add_parser("cn4-fit", help="cn4 关系拟合：幂律/指数/理想气体")
    p.add_argument("cn4")
    p.add_argument("--what", required=True,
                   choices=("ideal_gas", "power", "exp"))
    p.add_argument("--field", default="p_ion", help="被拟合的物理量场名")
    p.add_argument("--t-idx", dest="t_idx", type=int, default=0,
                   help="固定温度索引")
    p.add_argument("--outdir", default=None)
    p.set_defaults(func=cmd_cn4_fit)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
