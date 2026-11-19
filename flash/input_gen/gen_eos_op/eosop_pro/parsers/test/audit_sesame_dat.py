# -*- coding: utf-8 -*-
"""``hyades/sesame/`` 文件夹全量读取评估（审计脚本，非 pytest 收集对象）。

背景（2026-11-15 计划 cosmic-nebula-babbage-8a4M6cYp）
----------------------------------------------------
用户要求对 ``matter++/hyades/sesame/``（97 文件）做**全量读取评估**：
变体全部尝试解析，失败/异常显式登记，不静默跳过。

两层设计（防止 generic_curve 兜底掩盖真相）：

* 层 1 解析器级：逐文件直调 :func:`eosop_pro.parsers.hyades_eos.parse_all`，
  记录成败/异常、维度、计数、补零、DOS EOF、头部五数、行宽/字段宽证据、
  **payload 非数值残留**（截断指数 token 的前置诊断）。
* 层 2 分派级：:func:`eosop_pro.registry.schema.declared_types.declare` +
  :func:`eosop_pro.registry.identify.dispatch.parse_declared`，
  记录候选族、source、最终 status 与 dispatch_rule
  （可发现 last-resort generic_curve 是否接管数据表）。

产出
----
``parsers/test/_out/sesame_audit.json``（机读，回归测试冻结引用）
``parsers/test/_out/sesame_audit.md``（人读摘要）

用法::

    python audit_sesame_dat.py            # 全量审计
    python audit_sesame_dat.py eos_332    # 只审计文件名含该子串的文件
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401  # sys.path 四层注入

from eosop_pro import config
from eosop_pro.core.numbers import fortran_numbers as fn
from eosop_pro.parsers import hyades_eos
from eosop_pro.registry.identify import dispatch
from eosop_pro.registry.schema.declared_types import declare

OUT_DIR = Path(__file__).resolve().parent / "_out"
SESAME_REL = "hyades/sesame"
DIR = config.MATTER_DIR / SESAME_REL

_EOS_NAME_RE = re.compile(r"^eos_(\d+)\.dat$", re.I)

#: 编号约定（逐字出处：doc/Hyades 数据格式说明.doc；archive/06 §1.3 为其转述）
#: <998 常规单温 / 2001-2999 电子流 / 3001-3999 离子流 / 1001-1999 灰度不透明度
ID_FLOW_RANGES = ((2001, 2999, "electron"), (3001, 3999, "ion"),
                  (1001, 1999, "gray-opacity"))


def _flow_of(num: int) -> str | None:
    for lo, hi, tag in ID_FLOW_RANGES:
        if lo <= num <= hi:
            return tag
    return None


def _width_evidence(lines: list[str], header_idx: int) -> dict:
    """从首个 payload 行提取行宽/字段宽证据（布局变体诊断）。"""
    for ln in lines[header_idx + 1:]:
        toks = fn.FORTRAN_NUM_RE.findall(ln)
        if len(toks) >= 2 and not fn.has_letters(ln):
            n = len(toks)
            return {"first_payload_line_len": len(ln.rstrip("\r\n")),
                    "numbers_per_line": n,
                    "field_width_est": round(len(ln.rstrip("\r\n")) / n, 1)}
    return {"first_payload_line_len": None, "numbers_per_line": None,
            "field_width_est": None}


def audit_layer1(abs_path: Path, rel: str) -> dict:
    """层 1：直调 F3 解析器。"""
    rec: dict = {"file": rel, "size_bytes": abs_path.stat().st_size}
    try:
        doc_lines = None
        try:
            from eosop_pro.core.text.textio import read_text
            doc = read_text(abs_path)
            doc_lines = doc.lines
        except Exception as exc:                       # noqa: BLE001
            rec["layer1"] = {"status": "error",
                             "error": f"read_text: {type(exc).__name__}: {exc}"}
            return rec
        if not any(ln.strip() for ln in doc_lines):
            rec["layer1"] = {"status": "skip_empty_file"}
            return rec

        # 头部证据（独立于解析器成败）
        nonblank = [i for i, ln in enumerate(doc_lines) if ln.strip()]
        head = {"comment_line": doc_lines[nonblank[0]].strip()}
        if len(nonblank) >= 2:
            try:
                h = hyades_eos.parse_header_line(doc_lines[nonblank[1]])
                head.update({"id": h["id"], "zbar": h["zbar"],
                             "abar": h["abar"], "rho0": h["rho0"], "L": h["L"]})
                nm = _EOS_NAME_RE.match(abs_path.name)
                if nm:
                    head["filename_id"] = int(nm.group(1))
                    head["id_matches_filename"] = (int(nm.group(1)) == h["id"])
                    head["id_flow"] = _flow_of(h["id"])
            except Exception as exc:                   # noqa: BLE001
                head["header_error"] = f"{type(exc).__name__}: {exc}"
        rec["header"] = head

        # payload 非数值残留（截断指数 token 前置诊断；正常 F3 payload 应为空）
        if len(nonblank) >= 2:
            payload_text = "\n".join(doc_lines[nonblank[1] + 1:])
            residue = fn.non_numeric_residue(payload_text)
            # has_letters 只查 [A-Za-z]（DOS EOF \x1a、空白不算字母）
            head["payload_residue"] = " ".join(residue.split())[:40] or None
            head["payload_has_letters"] = fn.has_letters(payload_text)
        rec.update(_width_evidence(doc_lines, nonblank[1] if len(nonblank) >= 2 else 0))
        rec["has_dos_eof"] = any(hyades_eos.DOS_EOF in ln for ln in doc_lines)

        tables = hyades_eos.parse_all(abs_path, rel)
        t = tables[0]
        rec["layer1"] = {
            "status": "ok", "family": t.family, "kind": t.kind,
            "nr": len(t.axes.get("rho", [])), "nt": len(t.axes.get("Te", [])),
            "L": head.get("L"), "n_seen": t.n_numbers_seen,
            "n_expected": t.n_numbers_expected,
            "fields": sorted(t.fields), "n_notes": len(t.notes),
            "count_closed": t.n_numbers_seen == t.n_numbers_expected,
        }
    except Exception as exc:                           # noqa: BLE001
        rec["layer1"] = {"status": "error",
                         "error_type": type(exc).__name__,
                         "error": str(exc)[:200]}
    return rec


def audit_layer2(rel: str) -> dict:
    """层 2：声明式识别 + 分派（含兜底链真相）。"""
    rec: dict = {}
    try:
        dt = declare(rel)
        rec["declared_families"] = list(dt.families)
        rec["declared_source"] = dt.source
        rec["declared_evidence"] = dt.evidence
        rec["declared_kind"] = dt.kind
        if dt.is_skipped:
            rec["layer2"] = {"status": "skipped_non_numeric",
                             "reason": dt.evidence}
            return rec
        outcome = dispatch.parse_declared(rel, dt)
        snap = outcome.snapshot
        rec["layer2"] = {
            "status": snap.status,
            "dispatch_rule": snap.dispatch_rule,
            "n_tables": len(outcome.tables),
            "first_table_family": (outcome.tables[0].family
                                   if outcome.tables else None),
            "first_table_kind": (outcome.tables[0].kind
                                 if outcome.tables else None),
            "notes": [n for n in getattr(snap, "notes", [])][:6],
        }
    except Exception as exc:                           # noqa: BLE001
        rec["layer2"] = {"status": "audit_error",
                         "error": f"{type(exc).__name__}: {exc}"[:200]}
    return rec


def main(argv: list[str]) -> int:
    filter_sub = argv[1] if len(argv) > 1 else None
    files = sorted(p for p in DIR.iterdir() if p.is_file())
    if filter_sub:
        files = [p for p in files if filter_sub.lower() in p.name.lower()]
    print(f"sesame/ 全量审计：{len(files)} 文件（目录 {DIR}）")

    records = []
    for i, p in enumerate(files, 1):
        rel = f"{SESAME_REL}/{p.name}"
        rec = audit_layer1(p, rel)
        rec.update(audit_layer2(rel))
        records.append(rec)
        l1 = rec.get("layer1", {})
        print(f"  [{i:>2}/{len(files)}] {p.name:<28} "
              f"L1={l1.get('status', '?'):<10} "
              f"L2={rec.get('layer2', {}).get('status', '?')}")

    # ── 汇总 ──
    def cat(r: dict) -> str:
        l1 = r.get("layer1", {}).get("status", "?")
        l2 = r.get("layer2", {}).get("status", "?")
        if l1 == "ok":
            return "ok"
        if l1 == "skip_empty_file" or l2.startswith("skipped"):
            return "skip"
        if l1 == "error":
            return "error:" + r["layer1"].get("error_type", "?")
        return f"unclassified(L1={l1},L2={l2})"

    for r in records:
        r["category"] = cat(r)
    by_cat: dict[str, list[str]] = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r["file"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "directory": str(DIR),
        "n_files": len(records),
        "category_counts": {k: len(v) for k, v in sorted(by_cat.items())},
        "records": records,
    }
    (OUT_DIR / "sesame_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    md = [f"# sesame/ 全量读取评估（{len(records)} 文件）",
          f"- 生成：{payload['generated_utc']}",
          "- 分类统计："]
    for k, v in sorted(by_cat.items()):
        md.append(f"  - `{k}`: {len(v)}" + ("  → " + ", ".join(v)
                                             if len(v) <= 8 else ""))
    md.append("\n## 逐文件明细\n")
    md.append("| 文件 | 尺寸 | id(流) | NR×NT | 计数闭 | L1 | L2 | dispatch_rule | 证据 |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for r in records:
        h = r.get("header", {})
        l1 = r.get("layer1", {})
        l2 = r.get("layer2", {})
        idflow = (f"{h.get('id')}" + (f"({h['id_flow']})" if h.get("id_flow") else "")
                  if "id" in h else h.get("header_error", "-")[:20])
        dims = (f"{l1.get('nr')}×{l1.get('nt')}" if l1.get("status") == "ok" else "-")
        closed = (str(l1.get("count_closed")) if l1.get("status") == "ok" else "-")
        evid = []
        if r.get("payload_has_letters"):
            evid.append(f"residue={r.get('header', {}).get('payload_residue')!r}")
        if r.get("field_width_est") not in (None, 15.0):
            evid.append(f"width≈{r.get('field_width_est')}")
        if r.get("has_dos_eof"):
            evid.append("DOS_EOF")
        err = l1.get("error", "")
        if err:
            evid.append(err[:60])
        md.append(f"| {r['file'].split('/')[-1]} | {r['size_bytes']} | {idflow} "
                  f"| {dims} | {closed} | {l1.get('status','-')} "
                  f"| {l2.get('status','-')} | {l2.get('dispatch_rule','-')} "
                  f"| {'; '.join(evid) or '-'} |")
    (OUT_DIR / "sesame_audit.md").write_text("\n".join(md) + "\n",
                                             encoding="utf-8", newline="\n")
    print(f"\n产出：{OUT_DIR / 'sesame_audit.json'} / .md")
    print("分类统计：",
          {k: len(v) for k, v in sorted(by_cat.items())})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
