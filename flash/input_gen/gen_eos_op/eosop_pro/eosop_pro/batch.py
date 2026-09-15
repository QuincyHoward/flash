"""批处理编排 —— ``audit`` / ``inventory`` / ``convert-all`` / ``plot-all`` /
``infer-unknown`` 的唯一实现。

``cli.py`` 只做参数解析，``scripts/*.py`` 只做薄包装，真正的逻辑全在这里，
这样每个动作都能被 ``test/`` 直接调用测试，而不是只能靠命令行跑。

五个动作与它们回答的问题
------------------------
==================  ============================================================
动作                 回答什么问题
==================  ============================================================
``inventory``       matter++ 里到底有什么？按后缀/目录/编码/行尾分布如何？
``audit``           按**声明类型**逐文件解析，覆盖率闸口过不过？谁解析不了、为什么？
``convert-all``     能解析的表能不能写出双轨 HDF5（native 逐字 + unified 插值）？
``plot-all``        数据长什么样？能不能出 PPT 级英文图？
``infer-unknown``   给一个**没有任何声明**的文件，零先验能不能反演出结构？
==================  ============================================================

★ 纪律：每个动作都产出 ``outputs/reports/<name>.<stamp>.{csv,json,md}``，
头部写明数据来源、生成时刻、样本总数——结论必须可回溯到具体文件。
"""

from __future__ import annotations

import collections
import re
import time
from pathlib import Path
from typing import Iterable, Sequence

from . import config, reporting

__all__ = [
    "inventory",
    "audit_sweep",
    "convert_all",
    "plot_all",
    "plot_cn4_all",
    "infer_unknown",
    "infer_unrecognized",
]


# ══════════════════════════════════════════════════════════════
# ① inventory —— matter++ 全量文件清单与目录画像
# ══════════════════════════════════════════════════════════════
def _profile_one(p: Path) -> dict:
    """单个文件的画像（字节层信息只读文件头，代价 O(1)）。"""
    from .core.byteclass import classify_file

    try:
        st = p.stat()
    except OSError as exc:                                   # pragma: no cover
        return {"relpath": p.name, "error": str(exc)}
    rec = {
        "relpath": config.matter_rel(p),
        "dir": config.matter_rel(p.parent),
        "name": p.name,
        "suffix": p.suffix.lower() or "(none)",
        "size_bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
    }
    try:
        bc = classify_file(p)
        rec.update(kind=bc.kind, encoding=bc.encoding or "",
                   newline=bc.newline, has_bom=int(bc.has_bom),
                   has_nul=int(bc.has_nul),
                   printable_ratio=round(bc.printable_ratio, 4))
    except OSError:                                          # pragma: no cover
        rec.update(kind="error", encoding="", newline="", has_bom=0,
                   has_nul=0, printable_ratio=0.0)
    return rec


def inventory(*, outdir: str | Path | None = None,
              matter_dir: str | Path | None = None,
              report_dir: str | Path | None = None) -> dict:
    """② ``matter++`` 全量文件清单 + 目录画像。

    ``outdir``   报告落盘目录（缺省 ``config.REPORTS_DIR``）
    ``report_dir``同 ``outdir`` 的显式别名（★ 测试用：避免污染真实 outputs）
    """
    root = Path(matter_dir) if matter_dir else config.MATTER_DIR
    od = Path(outdir or report_dir) if (outdir or report_dir) else config.REPORTS_DIR
    od.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    rows = [_profile_one(p) for p in files]
    elapsed = time.time() - t0

    by_suffix = collections.Counter(r.get("suffix", "?") for r in rows)
    by_kind = collections.Counter(r.get("kind", "?") for r in rows)
    by_enc = collections.Counter(r.get("encoding", "?") for r in rows)
    by_nl = collections.Counter(r.get("newline", "?") for r in rows)
    bytes_by_suffix: dict[str, int] = collections.defaultdict(int)
    for r in rows:
        bytes_by_suffix[r.get("suffix", "?")] += int(r.get("size_bytes") or 0)

    top_dirs = collections.Counter(r.get("dir", "?") for r in rows).most_common(20)
    total_bytes = sum(int(r.get("size_bytes") or 0) for r in rows)
    stamp = reporting.now_stamp()

    csv_p = reporting.write_csv(
        od / f"inventory.{stamp}.csv", rows,
        ["relpath", "dir", "name", "suffix", "size_bytes", "mtime",
         "kind", "encoding", "newline", "has_bom"])
    json_p = reporting.write_json(od / f"inventory.{stamp}.json", {
        "generated_utc": reporting.utc_now(),
        "root": str(root),
        "total_files": len(rows),
        "total_bytes": total_bytes,
        "elapsed_s": round(elapsed, 2),
        "by_suffix": dict(by_suffix),
        "bytes_by_suffix": dict(bytes_by_suffix),
        "by_kind": dict(by_kind),
        "by_encoding": dict(by_enc),
        "by_newline": dict(by_nl),
        "files": rows,
    })

    md = [reporting.md_header(
        "matter++ 全量文件清单与目录画像", str(root), len(rows),
        extra=[("总体积", f"{total_bytes / 2**20:.1f} MiB"),
               ("耗时", f"{elapsed:.1f} s")])]
    md.append("## 1. 按后缀计数 / 体积\n")
    md.append(reporting.md_table(
        [{"suffix": s, "files": n, "bytes": bytes_by_suffix[s],
          "MiB": f"{bytes_by_suffix[s] / 2**20:.2f}",
          "pct_files": f"{100.0 * n / max(len(rows), 1):.1f}%"}
         for s, n in by_suffix.most_common()],
        ["suffix", "files", "bytes", "MiB", "pct_files"]))
    md.append("\n## 2. 按字节层类型计数\n")
    md.append(reporting.counter_table(by_kind, "kind", "files"))
    md.append("\n## 3. 按编码计数\n")
    md.append(reporting.counter_table(by_enc, "encoding", "files"))
    md.append("\n## 4. 按行尾计数\n")
    md.append(reporting.counter_table(by_nl, "newline", "files"))
    md.append("\n## 5. 文件数最多的 20 个目录\n")
    md.append(reporting.md_table(
        [{"dir": d, "files": n} for d, n in top_dirs], ["dir", "files"],
        shorten_to=90))
    md.append("\n## 6. 非文本文件（跳过但登记）\n")
    non_text = [r for r in rows if r.get("kind") not in ("text", "mixed")]
    md.append(reporting.md_table(
        [{"relpath": r["relpath"], "kind": r.get("kind"),
          "size_bytes": r.get("size_bytes")} for r in non_text],
        ["relpath", "kind", "size_bytes"], max_rows=80, shorten_to=80))
    md_p = reporting.write_md(od / f"inventory.{stamp}.md", "\n".join(md))

    stats = {"total_files": len(rows), "total_bytes": total_bytes,
             "elapsed_s": round(elapsed, 2), "by_suffix": dict(by_suffix),
             "by_kind": dict(by_kind), "csv": str(csv_p), "md": str(md_p),
             "json": str(json_p)}
    print(f"文件总数 {len(rows)}  总体积 {total_bytes / 2**20:.1f} MiB  "
          f"耗时 {elapsed:.1f} s")
    for s, n in by_suffix.most_common(15):
        print(f"  {s:<12} {n:>5}  {bytes_by_suffix[s] / 2**20:>9.2f} MiB")
    print(f"报告 → {csv_p.name} / {json_p.name} / {md_p.name}")
    return stats


# ══════════════════════════════════════════════════════════════
# ② audit —— 阶段 A 全量声明式审计
# ══════════════════════════════════════════════════════════════
def audit_sweep(*, outdir: str | Path | None = None,
                multigroup: bool = False,
                matter_dir: str | Path | None = None,
                report_dir: str | Path | None = None,
                limit: int = 0) -> dict:
    """按声明类型逐文件解析全树，产出三份报告并给出覆盖率闸口。

    ``limit`` > 0 时只审计前 N 个声明文件（自检/冒烟用；报告头部会注明是**截断**运行，
    避免把截断结果误当全量结论）。

    闸口定义：``已解析(ok + ok_unverified) + 已跳过 == 审计样本数``，
    且 ``error`` / ``count_mismatch`` / ``unrecognized`` 清单可逐条定性。
    """
    from .registry import declared_types as dt
    from .registry.annotation_store import AnnotationStore
    from .registry.dispatch import parse_declared
    from .registry.material import MaterialRegistry

    od = Path(outdir or report_dir) if (outdir or report_dir) else config.REPORTS_DIR
    od.mkdir(parents=True, exist_ok=True)
    stamp = reporting.now_stamp()

    t0 = time.time()
    print("[1/3] 建立注释索引与材料注册表 ...")
    store = AnnotationStore().build()
    reg = MaterialRegistry(build_annotations=False)
    print(f"      伴随注释文件 {len(store.companions)} 个；材料 {len(reg.records)} 条")

    print("[2/3] 声明式类型扫描 ...")
    dts = dt.scan_declared(matter_dir, registry=reg, store=store)
    n_declared = len(dts)
    if limit:
        dts = dts[:limit]
    print(f"      共 {n_declared} 个文件" + (f"（本次审计前 {len(dts)} 个）" if limit else ""))

    print("[3/3] 逐文件解析 ...")
    snaps = []
    for i, d in enumerate(dts, 1):
        snaps.append(parse_declared(
            d.relpath, d, registry=reg, store=store,
            include_multigroup=multigroup).snapshot)
        if i % 200 == 0:
            print(f"      {i}/{len(dts)} ...")

    elapsed = time.time() - t0
    total = len(snaps)
    by_status = collections.Counter(s.status for s in snaps)
    by_family = collections.Counter(s.family for s in snaps if s.family)
    by_source = collections.Counter(d.source for d in dts)
    by_declared = collections.Counter(d.family for d in dts)
    units = collections.Counter(s.unit_source for s in snaps if s.unit_source)

    resolved = by_status["ok"] + by_status["ok_unverified"]
    skipped = by_status["skipped_non_numeric"]
    problems = [s for s in snaps
                if s.status in ("error", "count_mismatch", "binary_suspect",
                                "unrecognized", "ambiguous_layout", "type_conflict")]

    rows = [s.as_row() for s in snaps]
    csv_p = reporting.write_csv(od / f"audit_all.{stamp}.csv", rows)
    json_p = reporting.write_json(od / f"audit_all.{stamp}.json", {
        "generated_utc": reporting.utc_now(),
        "source_dir": str(config.MATTER_DIR),
        "n_declared_total": n_declared,
        "truncated": bool(limit),
        "total_files": total,
        "elapsed_s": round(elapsed, 2),
        "reconciled": resolved + skipped == total,
        "by_status": dict(by_status),
        "by_family": dict(by_family),
        "by_dispatch_source": dict(by_source),
        "by_declared_family": dict(by_declared),
        "unit_sources": dict(units),
        "snapshots": rows,
    })

    md = [reporting.md_header(
        "阶段 A 全量审计报告", str(config.MATTER_DIR), total,
        extra=[("声明文件总数", n_declared),
               ("本次审计样本", f"{total}" + ("（**截断**）" if limit else "（全量）")),
               ("耗时", f"{elapsed:.1f} s"),
               ("已解析", f"{resolved} (`ok` {by_status['ok']} + "
                          f"`ok_unverified` {by_status['ok_unverified']})"),
               ("已跳过", f"{skipped}"),
               ("问题文件", f"**{len(problems)}**"),
               ("闸口", "已解析 + 已跳过 == 审计样本数 → "
                        f"{'✅ 通过' if resolved + skipped == total else '❌ 未通过'}")])]

    md.append("## 1. 按状态计数\n")
    md.append(reporting.counter_table(by_status, "status", "files"))
    md.append("\n## 2. 按家族计数（实际使用的解析器）\n")
    md.append(reporting.counter_table(by_family, "family", "files"))
    md.append("\n## 3. 按声明来源计数\n")
    md.append(reporting.counter_table(by_source, "dispatch_source", "files"))
    md.append("\n## 4. 按声明家族计数\n")
    md.append(reporting.counter_table(by_declared, "declared_family", "files"))
    md.append("\n## 5. 单位来源计数（声明 vs 默认）\n")
    md.append(reporting.counter_table(units, "unit_source", "files"))

    md.append(f"\n## 6. 问题文件清单（{len(problems)}）\n")
    md.append(reporting.md_table(
        [{"status": s.status, "relpath": s.relpath, "family": s.family or "-",
          "declared": s.declared_type or "-",
          "delta": "" if s.count_delta is None else s.count_delta,
          "first_diagnostic": (s.diagnostics[0] if s.diagnostics else "")}
         for s in problems],
        ["status", "relpath", "family", "declared", "delta", "first_diagnostic"],
        max_rows=150, shorten_to=90))

    cm = [s for s in snaps if s.status == "count_mismatch"]
    md.append(f"\n## 7. `count_mismatch` 明细（{len(cm)}）\n")
    md.append(reporting.md_table(
        [{"relpath": s.relpath, "family": s.family or "-",
          "actual": s.n_numbers_actual, "expected": s.n_numbers_expected,
          "delta": s.count_delta, "header_raw": s.header_raw} for s in cm],
        ["relpath", "family", "actual", "expected", "delta", "header_raw"],
        max_rows=120, shorten_to=80))

    warned = [s for s in snaps if s.is_ok and any(
        k in " ".join(s.diagnostics) for k in ("raw_tail", "未声明", "非有限值", "⚠️"))]
    md.append(f"\n## 8. 成功但有告警的文件（{len(warned)}）\n")
    md.append(reporting.md_table(
        [{"relpath": s.relpath, "family": s.family or "-",
          "warn": next((d for d in s.diagnostics
                        if "⚠️" in d or "未声明" in d
                        or "非有限值" in d or "raw_tail" in d), "")}
         for s in warned],
        ["relpath", "family", "warn"], max_rows=120, shorten_to=95))

    md_p = reporting.write_md(od / f"audit_all.{stamp}.md", "\n".join(md))

    print()
    print("=" * 66)
    print(f"声明文件总数        : {n_declared}")
    print(f"本次审计样本        : {total}{'  (TRUNCATED)' if limit else ''}")
    print(f"已解析 (ok+unverif) : {resolved}")
    print(f"已跳过              : {skipped}")
    print(f"问题文件            : {len(problems)}")
    print(f"闸口 已解析+已跳过==样本 : "
          f"{'PASS' if resolved + skipped == total else 'FAIL'}")
    print(f"耗时                : {elapsed:.1f} s")
    print("-" * 66)
    for k, v in by_status.most_common():
        print(f"  {k:<22} {v}")
    print("-" * 66)
    for k, v in by_family.most_common():
        print(f"  {k:<22} {v}")
    print("=" * 66)
    print(f"报告: {csv_p.name} / {json_p.name} / {md_p.name}")

    return {"total": total, "n_declared_total": n_declared, "truncated": bool(limit),
            "resolved": resolved, "skipped": skipped,
            "problems": len(problems), "elapsed_s": round(elapsed, 2),
            "pass": resolved + skipped == total,
            "by_status": dict(by_status), "by_family": dict(by_family),
            "csv": str(csv_p), "json": str(json_p), "md": str(md_p)}


# ══════════════════════════════════════════════════════════════
# ③ convert-all —— 批量写双轨 HDF5
# ══════════════════════════════════════════════════════════════
def _A_for(relpath: str, reg) -> float | None:
    """从材料注册表取原子量 ``A``（``nion_Te`` 轨的 x 轴换算要用）。"""
    try:
        recs = reg.for_file(relpath)
    except Exception:                                        # pragma: no cover
        return None
    for r in recs:
        if r.A:
            return float(r.A)
    return None


def _h5_name_for(relpath: str) -> str:
    """由 ``matter++`` 相对路径生成**唯一**的 h5 文件名。

    ★ 这是一个实测抓到的真 bug：初版用 ``parent__stem.h5``，
    而 ``Path(...).stem`` 会**切掉最后一个点之后的部分**，于是 7 个
    ATOMIC 文件全部撞到同一个名字::

        ATOMIC/Al.txt                        → ATOMIC__Al.h5
        ATOMIC/Al.NoFree                     → ATOMIC__Al.h5    ← 覆盖
        ATOMIC/Al.AvSqFree                   → ATOMIC__Al.h5    ← 覆盖
        ATOMIC/Al.GrayOpacity_PLANCK         → ATOMIC__Al.h5    ← 覆盖
        ATOMIC/Al.GrayOpacity_ROSSELAND      → ATOMIC__Al.h5    ← 覆盖
        ATOMIC/Al.MultiGroupOpacity_PLANCK   → ATOMIC__Al.h5    ← 覆盖
        ATOMIC/Al.MultiGroupOpacity_ROSSELAND→ ATOMIC__Al.h5    ← 覆盖

    全树统计：992 个"已写"里只有 770 个不同的文件名 ——
    **222 个文件被静默覆盖**。报告里的 ``n_written`` 看起来没问题，
    只有拿它和实际文件数**对账**才能发现。

    现在改成"全路径 + 全部点号都换掉"，保证一一映射::

        ATOMIC/Al.NoFree          → ATOMIC__Al_NoFree.h5
        ATOMIC/Al.txt             → ATOMIC__Al_txt.h5
        hyades/sesame/eos_41.dat  → hyades__sesame__eos_41_dat.h5
    """
    s = str(relpath).replace("\\", "/")
    s = s.replace("/", "__")            # 目录分隔 → 双下划线
    s = s.replace(".", "_")             # 所有点号 → 单下划线
    s = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff-]+", "_", s)
    s = re.sub(r"_{3,}", "__", s)
    return f"{s.strip('_') or 'file'}.h5"


def _check_name_collisions(relpaths: Sequence[str]) -> dict[str, str]:
    """检查 h5 命名是否一一映射；有冲突则加数字后缀并返回改名表。

    ★ 即使上面的方案已经一一映射，仍然保留这道保险 —— 万一将来有人改了
    命名规则或遇到怪异路径，**宁可改名也不要静默覆盖**。
    """
    seen: dict[str, str] = {}
    used: set[str] = set()
    for rel in relpaths:
        nm = _h5_name_for(rel)
        if nm not in used:
            used.add(nm)
            seen[rel] = nm
            continue
        i = 2
        while f"{nm[:-3]}_{i}.h5" in used:
            i += 1
        alt = f"{nm[:-3]}_{i}.h5"
        used.add(alt)
        seen[rel] = alt
    return seen


def _is_2d(table) -> bool:
    return any(len(s) == 2 for s in table.field_shape.values())


def _has_grid_axes(table) -> bool:
    """表是否有可插值的原生坐标轴（``(rho,Te)`` 或 ``(rho,de)``）。

    统一轨的插值需要这两根轴；缺一根就无从重采样，只能保留 native。
    """
    ax = table.axes
    return "rho" in ax and ("Te" in ax or "de" in ax)


def convert_all(*, outdir: str | Path | None = None,
                limit: int = 0,
                only_families: Sequence[str] = (),
                only_relpaths: Sequence[str] = (),
                include_multigroup: bool = False,
                with_unified: bool = True,
                with_native: bool = True,
                report_dir: str | Path | None = None,
                n_x: int | None = None, n_Te: int | None = None) -> dict:
    """批量把可解析的表写成 HDF5（默认**双轨**：native 逐字 + unified 两套网格）。

    ``limit=0`` 表示不设上限。默认跳过 LEDCOP 多群段（体积/耗时都大）——
    需要时显式 ``include_multigroup=True``。
    """
    from .grid.unified_grid import build_all_grids
    from .registry import declared_types as dt
    from .registry.annotation_store import AnnotationStore
    from .registry.dispatch import parse_declared
    from .registry.material import MaterialRegistry
    from .writer.h5_writer import write_material_h5

    od = Path(outdir) if outdir else config.H5_DIR
    od.mkdir(parents=True, exist_ok=True)
    rdir = Path(report_dir) if report_dir else config.REPORTS_DIR
    rdir.mkdir(parents=True, exist_ok=True)
    stamp = reporting.now_stamp()

    t0 = time.time()
    print("[1/4] 索引 ...")
    store = AnnotationStore().build()
    reg = MaterialRegistry(build_annotations=False)
    dts = dt.scan_declared(registry=reg, store=store)

    families = {f.lower() for f in only_families}
    #: ★ 显式指定文件集（POSIX 相对路径）。给定时**按给定顺序**处理，
    #: 便于精确复现/回归单个文件，不受全树扫描顺序影响。
    relset = [str(r).replace("\\", "/") for r in only_relpaths]
    print("[2/4] 逐文件解析 + 写 h5 ...")
    rows: list[dict] = []
    grid_meta: list[dict] = []
    n_written = n_skipped = n_failed = 0
    if relset:
        by_rel = {d.relpath: d for d in dts}
        dts = [by_rel[r] for r in relset if r in by_rel]
        missing = [r for r in relset if r not in by_rel]
        if missing:
            print(f"      ⚠ 以下路径不在声明扫描结果中，已跳过：{missing[:5]}")
    # ★ 预先把 h5 名字全部算好并**检查冲突**（见 _h5_name_for 的长注释：
    #   初版用 Path().stem 导致 222 个文件静默互相覆盖）。
    names = _check_name_collisions([d.relpath for d in dts])
    n_renamed = sum(1 for r, n in names.items() if n != _h5_name_for(r))
    if n_renamed:
        print(f"      ⚠ {n_renamed} 个文件的 h5 名与其它文件冲突，已加数字后缀")
    for i, d in enumerate(dts, 1):
        if families and (d.family or "").lower() not in families:
            continue
        if limit and n_written >= limit:
            break
        try:
            out = parse_declared(d.relpath, d, registry=reg, store=store,
                                include_multigroup=include_multigroup)
        except Exception as exc:                             # pragma: no cover
            n_failed += 1
            rows.append({"relpath": d.relpath, "declared": d.family,
                         "status": "exception", "error": f"{type(exc).__name__}: {exc}"})
            continue
        s = out.snapshot
        if not out.ok:
            n_skipped += 1
            rows.append({"relpath": d.relpath, "declared": d.family,
                         "status": s.status,
                         "error": s.diagnostics[0] if s.diagnostics else ""})
            continue

        tables = list(out.tables)
        if not with_native:
            # 只写统一轨时，没有 (rho,Te) / (rho,de) 坐标轴的表无从插值
            tables = [t for t in tables if _has_grid_axes(t)]
        if not tables:
            n_skipped += 1
            continue

        A = _A_for(d.relpath, reg)
        grids = build_all_grids(tables, A=A, n_x=n_x, n_Te=n_Te) if with_unified else None
        # ★ 退化轴范围会让 build_all_grids 略过某些 gid（甚至全部略过）。
        #   实测：Thermos/mat_Mo/Mo_Ideal_Gas 的 rho 网格是 [0.0, 1.0]，
        #   过滤非正值后只剩一个点 → 范围退化。只开 unified 轨时会写出空文件，
        #   所以这里计入 skipped 而不是让 write_material_h5 抛异常。
        unified_skipped = ""
        if with_unified and not grids:
            if not with_native:
                n_skipped += 1
                rows.append({"relpath": d.relpath, "declared": d.family,
                             "status": s.status,
                             "error": "unified-only 且轴范围退化 → 无轨可写"})
                continue
            unified_skipped = "degenerate-range"

        stem = Path(d.relpath).stem
        h5_name = names[d.relpath]          # ★ 冲突安全的唯一名
        try:
            p = write_material_h5(
                od / h5_name,
                material={"material_name": stem, "family": s.family,
                          "declared_type": s.declared_type,
                          "source_relpath": d.relpath, "A_amu": A},
                tables=tables, grids=grids if with_unified else None, A=A,
                native_track=with_native,
                extra_root_attrs={"pipeline": "convert_all", "stage": "A"})
        except Exception as exc:                             # pragma: no cover
            n_failed += 1
            rows.append({"relpath": d.relpath, "declared": d.family,
                         "status": "write_failed",
                         "error": f"{type(exc).__name__}: {exc}"})
            continue

        n_written += 1
        rows.append({
            "relpath": d.relpath, "declared": d.family, "status": s.status,
            "family": s.family, "n_tables": len(tables),
            "n_numbers": s.n_numbers_actual, "A_amu": A,
            "h5": str(Path(p).relative_to(od).as_posix()),
            "h5_bytes": Path(p).stat().st_size,
            "unified_skipped": unified_skipped,
        })
        if grids:
            for gid, g in grids.items():
                grid_meta.append({"relpath": d.relpath, "gid": gid,
                                  "x_axis": g.x_axis,
                                  "x_min": g.x[0], "x_max": g.x[-1],
                                  "n_x": len(g.x), "n_Te": len(g.Te),
                                  "Te_min_eV": g.Te[0], "Te_max_eV": g.Te[-1]})
        if i % 100 == 0:
            print(f"      {i}/{len(dts)} ... 已写 {n_written}")

    elapsed = time.time() - t0
    total_bytes = sum(r.get("h5_bytes", 0) for r in rows if isinstance(r.get("h5_bytes"), int))
    by_family = collections.Counter(r.get("family", "-") or "-"
                                    for r in rows if r.get("h5"))
    by_status = collections.Counter(r.get("status", "?") for r in rows)
    # ★ 对账：盘上的 .h5 数必须等于"已写"数。
    #   这条检查是本项目**唯一**能发现"静默覆盖"的手段 ——
    #   初版用 Path().stem 命名时 n_written=992 但盘上只有 770 个文件，
    #   若不与磁盘对账，报告看起来完全正常。
    n_on_disk = len(list(od.glob("*.h5")))
    if n_on_disk < n_written:
        msg = (f"⚠️ h5 命名冲突：报告 n_written={n_written}，"
               f"但盘上只有 {n_on_disk} 个 .h5 —— {n_written - n_on_disk} 个被覆盖！")
        print("      " + msg)
    else:
        msg = ""

    csv_p = reporting.write_csv(rdir / f"convert_all.{stamp}.csv", rows)
    json_p = reporting.write_json(rdir / f"convert_all.{stamp}.json", {
        "generated_utc": reporting.utc_now(),
        "source_dir": str(config.MATTER_DIR), "out_dir": str(od),
        "n_written": n_written, "n_skipped": n_skipped, "n_failed": n_failed,
        "n_h5_on_disk": n_on_disk, "reconciled": n_on_disk == n_written,
        "total_bytes": total_bytes, "elapsed_s": round(elapsed, 2),
        "with_unified": with_unified, "with_native": with_native,
        "include_multigroup": include_multigroup,
        "by_family": dict(by_family), "by_status": dict(by_status),
        "grids": grid_meta, "rows": rows,
    })

    md = [reporting.md_header(
        "批量 HDF5 写出报告", str(config.MATTER_DIR), len(rows),
        extra=[("输出目录", f"`{od}`"),
               ("已写 h5", f"**{n_written}**"),
               ("跳过（不可解析）", n_skipped),
               ("失败", n_failed),
               ("轨道", ("native + unified" if with_unified and with_native
                        else "native only" if with_native else "unified only")),
               ("总体积", f"{total_bytes / 2**20:.1f} MiB"),
               ("耗时", f"{elapsed:.1f} s"),
               ("对账", "盘上 .h5 数 == 已写数 → "
                        f"{'✅ 通过' if n_on_disk == n_written else '❌ 未通过'}"
                        + (f"（{msg}）" if msg else ""))])]
    md.append("## 1. 按家族计数（成功写出）\n")
    md.append(reporting.counter_table(by_family, "family", "h5"))
    md.append("\n## 2. 按状态计数\n")
    md.append(reporting.counter_table(by_status, "status", "rows"))
    md.append("\n## 3. 写出清单\n")
    md.append(reporting.md_table(
        [r for r in rows if r.get("h5")],
        ["relpath", "family", "n_tables", "n_numbers", "A_amu", "h5", "h5_bytes"],
        max_rows=200, shorten_to=70))
    bad = [r for r in rows if not r.get("h5")]
    md.append(f"\n## 4. 未写出清单（{len(bad)}）\n")
    md.append(reporting.md_table(
        bad, ["relpath", "declared", "status", "error"], max_rows=120, shorten_to=95))
    md_p = reporting.write_md(rdir / f"convert_all.{stamp}.md", "\n".join(md))

    print("-" * 66)
    print(f"已写 h5 : {n_written}   跳过 : {n_skipped}   失败 : {n_failed}")
    print(f"总体积  : {total_bytes / 2**20:.1f} MiB    耗时 : {elapsed:.1f} s")
    print(f"报告    : {csv_p.name} / {json_p.name} / {md_p.name}")
    return {"n_written": n_written, "n_skipped": n_skipped, "n_failed": n_failed,
            "n_h5_on_disk": n_on_disk, "reconciled": n_on_disk == n_written,
            "total_bytes": total_bytes, "out_dir": str(od),
            "elapsed_s": round(elapsed, 2), "csv": str(csv_p), "md": str(md_p),
            "json": str(json_p)}


# ══════════════════════════════════════════════════════════════
# ④ plot-all —— 批量 QA 出图
# ══════════════════════════════════════════════════════════════
def plot_all(*, outdir: str | Path | None = None,
             limit: int = 40,
             only_families: Sequence[str] = (),
             report_dir: str | Path | None = None) -> dict:
    """批量 QA 出图：EOS 等密度线 / 不透明度热图 / Z̄ 曲线。

    ``limit`` 默认 **40**（防止一次生成上千张图把目录淹掉）；
    传 ``0`` 表示不设上限。
    """
    from .plotting import qa_plots
    from .registry import declared_types as dt
    from .registry.annotation_store import AnnotationStore
    from .registry.dispatch import parse_declared
    from .registry.material import MaterialRegistry

    od = Path(outdir) if outdir else config.PLOTS_DIR
    od.mkdir(parents=True, exist_ok=True)
    rdir = Path(report_dir) if report_dir else config.REPORTS_DIR
    rdir.mkdir(parents=True, exist_ok=True)
    stamp = reporting.now_stamp()

    t0 = time.time()
    store = AnnotationStore().build()
    reg = MaterialRegistry(build_annotations=False)
    dts = dt.scan_declared(registry=reg, store=store)
    families = {f.lower() for f in only_families}

    rows: list[dict] = []
    n_made = 0
    for d in dts:
        if limit and n_made >= limit:
            break
        if families and (d.family or "").lower() not in families:
            continue
        try:
            out = parse_declared(d.relpath, d, registry=reg, store=store)
        except Exception:                                    # pragma: no cover
            continue
        if not out.ok:
            continue
        stem = _h5_name_for(d.relpath)[:-3]      # ★ 同 convert_all 的冲突安全命名
        for t in out.tables:
            if limit and n_made >= limit:
                break
            try:
                _plot_one(t, stem, od, qa_plots)
                n_made += 1
                rows.append({"relpath": d.relpath, "table": t.table_key,
                             "family": t.family, "kind": t.kind,
                             "figures": _figs_for(t)})
            except Exception as exc:
                rows.append({"relpath": d.relpath, "table": t.table_key,
                             "family": t.family, "kind": t.kind,
                             "figures": "",
                             "error": f"{type(exc).__name__}: {exc}"})
    elapsed = time.time() - t0

    csv_p = reporting.write_csv(rdir / f"plot_all.{stamp}.csv", rows)
    json_p = reporting.write_json(rdir / f"plot_all.{stamp}.json", {
        "generated_utc": reporting.utc_now(), "out_dir": str(od),
        "n_figures_sets": n_made, "elapsed_s": round(elapsed, 2),
        "rows": rows})
    md = [reporting.md_header(
        "QA 出图报告", str(config.MATTER_DIR), len(rows),
        extra=[("输出目录", f"`{od}`"), ("成功出图组数", n_made),
               ("耗时", f"{elapsed:.1f} s")])]
    md.append("\n## 出图明细\n")
    md.append(reporting.md_table(
        rows, ["relpath", "family", "kind", "figures", "error"],
        max_rows=120, shorten_to=80))
    md_p = reporting.write_md(rdir / f"plot_all.{stamp}.md", "\n".join(md))
    print(f"出图 {n_made} 组 -> {od}    耗时 {elapsed:.1f} s")
    print(f"报告: {csv_p.name} / {md_p.name}")
    return {"n_figures_sets": n_made, "out_dir": str(od),
            "elapsed_s": round(elapsed, 2), "csv": str(csv_p), "md": str(md_p),
            "json": str(json_p)}


def _figs_for(t) -> str:
    tags = []
    if _is_2d(t) and "rho" in t.axes and "Te" in t.axes:
        if "P" in t.fields:
            tags.append("eos_isobars")
        if "E" in t.fields:
            tags.append("eos_energy")
    if "kappa" in t.fields:
        tags.append("opacity_heatmap")
    if "Z" in t.fields:
        tags.append("zeff")
    return " ;; ".join(tags)


def _plot_one(t, stem: str, od: Path, qa) -> None:
    """对单张表尽量多出图；不适用的图种静默跳过。"""
    made = []
    if _is_2d(t) and "rho" in t.axes and "Te" in t.axes:
        for fld, tag in (("P", "P"), ("E", "E")):
            if fld in t.fields:
                try:
                    qa.plot_eos_isobars(t, fld, out_path=od / f"{stem}_{tag}.png")
                    made.append(tag)
                except (ValueError, KeyError):
                    pass
    if "kappa" in t.fields and len(t.field_shape.get("kappa", ())) == 2:
        try:
            qa.plot_opacity_heatmap(t, "kappa", out_path=od / f"{stem}_kappa.png")
            made.append("kappa")
        except (ValueError, KeyError):
            pass
    if "Z" in t.fields and len(t.field_shape.get("Z", ())) == 2:
        try:
            qa.plot_zeff(t, "Z", out_path=od / f"{stem}_zeff.png")
            made.append("zeff")
        except (ValueError, KeyError):
            pass
    if not made:
        raise ValueError("no applicable plot type for this table")


# ══════════════════════════════════════════════════════════════
# ⑤ infer-unknown —— 零先验通用反演
# ══════════════════════════════════════════════════════════════
def infer_unknown(relpath: str, *, outdir: str | Path | None = None,
                  dump: bool = True) -> dict:
    """对**单个任意文件**做零先验结构反演，报告结构解与判定。

    这是 :mod:`eosop_pro.core.inference` 的命令行外壳：即使没有任何声明、
    没有伴随注释、没有扩展名，也要给出 ``ok`` / ``ambiguous`` / ``unrecognized``
    三态之一，并把所有候选**列全**而不是硬猜一个。
    """
    from .core.inference import infer_file

    od = Path(outdir) if outdir else config.INFERENCE_DIR
    od.mkdir(parents=True, exist_ok=True)
    p = Path(relpath)
    if not p.exists():
        p = config.MATTER(relpath)
    r = infer_file(p)
    print(r.report())
    if dump:
        stamp = reporting.now_stamp()
        safe = config.matter_rel(p).replace("/", "__")
        reporting.write_md(od / f"{safe}.{stamp}.md", r.report())
    return {"relpath": config.matter_rel(p), "ok": r.ok,
            "status": getattr(r, "status", ""),
            "n_candidates": len(getattr(r, "candidates", []) or [])}


#: 视为"未决"的快照状态（需要交给阶段 B 反演）
UNRESOLVED_STATUSES = ("unrecognized", "ambiguous_layout", "error", "count_mismatch")


def _problem_relpaths_from_report(csv_path: str | Path) -> list[str]:
    """从 ``audit_all.*.csv`` 里读出状态为 UNRESOLVED 的文件（**复用证据**）。"""
    import csv as _csv

    out: list[str] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in _csv.DictReader(fh):
            if row.get("status") in UNRESOLVED_STATUSES and row.get("relpath"):
                out.append(row["relpath"])
    return out


def latest_audit_report(outdir: str | Path | None = None) -> Path | None:
    """找最新的 ``audit_all.*.csv``（用于阶段 B 复用阶段 A 的结论）。"""
    od = Path(outdir) if outdir else config.REPORTS_DIR
    if not od.is_dir():
        return None
    cands = sorted(od.glob("audit_all.*.csv"))
    return cands[-1] if cands else None


def infer_unrecognized(*, from_report: str | Path | None = None,
                       outdir: str | Path | None = None,
                       limit: int = 0, rescan: bool = False,
                       report_dir: str | Path | None = None) -> dict:
    """对**阶段 A 判为未决**的文件批量反演。

    这是"两段式执行"的收口动作：阶段 A 解不了的文件，全部交给阶段 B 的
    零先验反演，逐个列出候选，不留未决项。

    ★ 默认**复用阶段 A 的审计 CSV**（``audit_all.*.csv``）来挑选目标 ——
    重新全树解析一遍要 ~2 分钟，而审计报告里已经写清了 ``status``。
    只有 ``rescan=True`` 或找不到报告时才重新扫描。
    """
    from .core.inference import infer_file

    od = Path(outdir) if outdir else config.INFERENCE_DIR
    od.mkdir(parents=True, exist_ok=True)
    stamp = reporting.now_stamp()

    report = Path(from_report) if from_report else latest_audit_report()
    source = ""
    if report and report.exists() and not rescan:
        targets = _problem_relpaths_from_report(report)
        source = f"audit-report:{report.name}"
        print(f"复用审计报告 {report.name} → {len(targets)} 个未决文件")
    else:
        from .registry import declared_types as dt
        from .registry.annotation_store import AnnotationStore
        from .registry.dispatch import parse_declared
        from .registry.material import MaterialRegistry

        store = AnnotationStore().build()
        reg = MaterialRegistry(build_annotations=False)
        targets = []
        for d in dt.scan_declared(registry=reg, store=store):
            out = parse_declared(d.relpath, d, registry=reg, store=store)
            if out.snapshot.status in UNRESOLVED_STATUSES:
                targets.append(d.relpath)
        source = "full-rescan"
    if limit:
        targets = targets[:limit]

    rows = []
    for rel in targets:
        r = infer_file(config.MATTER_DIR / rel)
        rows.append({"relpath": rel, "ok": r.ok,
                     "status": getattr(r, "status", ""),
                     "n_candidates": len(getattr(r, "candidates", []) or [])})
        reporting.write_md(
            od / f"{rel.replace('/', '__')}.{stamp}.md", r.report())

    rdir = Path(report_dir) if report_dir else config.REPORTS_DIR
    rdir.mkdir(parents=True, exist_ok=True)
    csv_p = reporting.write_csv(rdir / f"infer_unknown.{stamp}.csv", rows)
    n_ok = sum(1 for r in rows if r["ok"])
    print(f"反演 {len(rows)} 个未决文件；零先验解出 {n_ok} 个（来源 {source}）")
    print(f"报告 → {csv_p.name} / {od}")
    return {"n_targets": len(rows), "n_ok": n_ok, "source": source,
            "csv": str(csv_p)}


# ══════════════════════════════════════════════════════════════
# ⑦ plot-cn4-all —— cn4 专题批量出图（二维彩图 / 一维曲线 / 群大图）
# ══════════════════════════════════════════════════════════════
def plot_cn4_all(*, outdir: str | Path | None = None,
                 cn4_dir: str | Path | None = None,
                 limit: int = 0,
                 quantities: Sequence[str] | None = None,
                 axes_pairs: Sequence[Sequence[str]] | None = None,
                 curves: Sequence[str] | None = None,
                 opacity_figures: bool = False,
                 transmission_L: float = 0.01,
                 report_dir: str | Path | None = None) -> dict:
    """对目录下**全部 ``.cn4`` 文件**批量出 PPT 级英文图。

    与 :func:`plot_all` 的区别
    --------------------------
    ``plot_all`` 面向 ``matter++`` 的**声明式多家族**表（``ParsedTable``）；
    本函数面向**纯 cn4 一族**，走 :mod:`eosop_pro.cn4` 专用路径，
    因此可用到 cn4 独有的能力：``nele`` 轴散点插值、群不透明度 2x2 大图、
    透射率、EOS 路径（等温/等熵/雨贡纽）。

    设计要点（多文件场景）
    ----------------------
    * **逐文件独立**：单文件失败只登记入 ``errors``，不中断整批
    * **即时释放**：每图落盘即 ``close(fig)``，避免 pyplot 句柄累积
    * **规模可控**：``limit`` 限文件数；``axes_pairs``/``quantities``
      决定每文件的图数（含 ``nele`` 的组合有 scipy 插值开销）

    Args:
        cn4_dir: 含 ``.cn4`` 的目录；``None`` = ``eos_op_data/Gen_eos_op_data``
        limit: 最多处理前 N 个文件（``0`` = 全部）
        quantities: 每个轴组合要画的物理量，默认 ``("zbar","p_ion","e_ele")``
        axes_pairs: 轴组合，默认 ``(("T","nion"),("T","nele"),("T","rho"))``
        curves: 需出一维曲线（vs T / vs n_ion）的物理量
        opacity_figures: 是否每个能群出 2x2 大图

    Returns:
        汇总字典（含 ``csv``/``md``/``json`` 报告路径）
    """
    from glob import glob
    from .cn4.cn4_plots import plot_cn4_directory

    od = Path(outdir) if outdir else (config.PLOTS_DIR / "cn4")
    od.mkdir(parents=True, exist_ok=True)
    rdir = Path(report_dir) if report_dir else config.REPORTS_DIR
    rdir.mkdir(parents=True, exist_ok=True)
    stamp = reporting.now_stamp()

    # ── 定位 cn4 文件 ──
    if cn4_dir:
        root = Path(cn4_dir)
    else:
        root = _default_cn4_root()
    files = sorted(glob(str(root / "**" / "*.cn4"), recursive=True))
    if not files:
        print(f"[!] {root} 下未找到 .cn4 文件")
        return {"n_files": 0, "n_plots": 0, "errors": [], "root": str(root)}

    qs = tuple(quantities) if quantities else ("zbar", "p_ion", "e_ele")
    ap = tuple(tuple(p) for p in axes_pairs) if axes_pairs else (
        ("T", "nion"), ("T", "nele"), ("T", "rho"))
    cv = tuple(curves) if curves else ("zbar",)

    t0 = time.time()
    print(f"cn4 批量出图: {len(files)} 个文件 (root={root})")
    print(f"  轴组合 {ap}")
    print(f"  物理量 {qs}")
    print(f"  曲线   {cv}")
    print(f"  群大图 {'on' if opacity_figures else 'off'}")
    res = plot_cn4_directory(
        files, outdir=od, quantities=qs, axes_pairs=ap, curves=cv,
        opacity_figures=opacity_figures, transmission_L=transmission_L,
        limit=limit, verbose=True)
    elapsed = time.time() - t0

    # ── 报告 ──
    rows = []
    for p in res["plots"]:
        rel = Path(p).relative_to(od).as_posix()
        rows.append({"figure": rel, "dir": Path(rel).parent.as_posix()})
    err_rows = [{"file": f, "error": e} for f, e in res["errors"]]

    csv_p = reporting.write_csv(rdir / f"plot_cn4_all.{stamp}.csv",
                               rows or [{"figure": ""}])
    json_p = reporting.write_json(rdir / f"plot_cn4_all.{stamp}.json", {
        "generated_utc": reporting.utc_now(), "root": str(root),
        "out_dir": str(od), "n_files": res["n_files"],
        "n_plots": res["n_plots"], "n_errors": len(res["errors"]),
        "elapsed_s": round(elapsed, 2),
        "axes_pairs": [list(p) for p in ap], "quantities": list(qs),
        "errors": err_rows})
    md = [reporting.md_header(
        "cn4 批量出图报告", str(root), res["n_files"],
        extra=[("输出目录", f"`{od}`"), ("图数", res["n_plots"]),
               ("失败项", len(res["errors"])), ("耗时", f"{elapsed:.1f} s"),
               ("轴组合", ", ".join(f"{a}-{b}" for a, b in ap)),
               ("物理量", ", ".join(qs))])]
    if err_rows:
        md.append("\n## 失败项\n")
        md.append(reporting.md_table(err_rows, ["file", "error"],
                                     max_rows=60, shorten_to=100))
    md.append("\n## 出图清单\n")
    md.append(reporting.md_table(rows, ["dir", "figure"],
                                 max_rows=200, shorten_to=80))
    md_p = reporting.write_md(rdir / f"plot_cn4_all.{stamp}.md", "\n".join(md))

    print(f"完成: {res['n_files']} 文件 / {res['n_plots']} 图 / "
          f"{len(res['errors'])} 失败  ({elapsed:.1f} s)")
    print(f"报告: {csv_p.name} / {md_p.name}")
    return {"n_files": res["n_files"], "n_plots": res["n_plots"],
            "n_errors": len(res["errors"]), "out_dir": str(od),
            "elapsed_s": round(elapsed, 2), "csv": str(csv_p),
            "md": str(md_p), "json": str(json_p)}


def _default_cn4_root() -> Path:
    """默认 cn4 数据根目录。

    优先 ``matter++/Ionmix``，其次仓库内的 ``eos_op_data/Gen_eos_op_data``
    （后者位于 ``gen_eos_op/`` 下，是本地生成数据的归档位）。
    """
    cand = config.MATTER_DIR / "Ionmix"
    if cand.is_dir():
        return cand
    alt = config.PROJECT_ROOT.parent.parent / "eos_op_data" / "Gen_eos_op_data"
    if alt.is_dir():
        return alt
    return cand
