#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""audit_portable.py — 场景可移植性全树审计（场景收纳整理改造 P0）
════════════════════════════════════════════════════════════════════════

扫描 flash/scenarios 全树，定位所有"目录位置绑定"引用，分级输出：

  ERROR  移动场景目录即失效（必改）
    - parents[N] 固定层级定位（AST 判定代码行，跳过注释/字符串）
    - scene.json 的 module/script/input_rel_dir/gen_script 绝对路径绑定
    - 跨场景 import（flash.scenarios.<pkg> 引用非自身、非共享区）
  WARN   需人工核对（改前先确认语义）
    - 内嵌 shell 的 $SCRIPT_DIR/../../ 相对跳级引用
    - .sh/.bat 中回退式硬编码
  INFO   允许的共享区引用 / 文档路径（仅记录）

用法::

    python audit_portable.py                 # 全树审计，打印 + 落报告
    python audit_portable.py --strict        # 存在 ERROR 时退出码 1
    python audit_portable.py --json out.json # 额外输出机器可读报告

报告落位: scripts/relocate/reports/audit_<时间戳>.txt
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 根定位（与 run.py 同款：向上搜 pyproject.toml + start_flash.py）──
_HERE = Path(__file__).resolve()
for _c in (_HERE, *_HERE.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        REPO = _c
        break
else:
    raise SystemExit("[X] 无法定位仓库根（需含 pyproject.toml + start_flash.py）")

SCEN = REPO / "flash" / "scenarios"

#: 排除的目录名/通配（运行产物、缓存、备份）
EXCLUDE_PARTS = {
    "__pycache__", ".git", "flash_output", "sim_output", "sim_output_plots",
    "logs_archive", "database", "sim_input", "sim_input_si",
}
EXCLUDE_GLOBS = ("runs_*", "*_output", "_backup_*", "*.egg-info", "NNNNNN", "results")

#: 共享区（允许被任意场景 import 的 flash.scenarios 二级包）
SHARED_TOPS = {"core", "scripts", "common"}

_PY_EXTS = {".py"}
_REPORT_DIR = _HERE.parent / "reports"

_find_parents = re.compile(r"\.parents\[(\d+)\]")
_find_reljump = re.compile(r"\$SCRIPT_DIR/(?:\.\./)+")
_find_slash_pkg = re.compile(r"[\"']flash/scenarios/[^\"']+[\"']")


def _is_excluded(rel: Path) -> bool:
    for part in rel.parts:
        if part in EXCLUDE_PARTS:
            return True
        for g in EXCLUDE_GLOBS:
            if g.endswith("*") and part.startswith(g[:-1]):
                return True
            if g.startswith("*") and part.endswith(g[1:]):
                return True
            if part == g:
                return True
    return False


def _iter_files():
    for p in sorted(SCEN.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(SCEN)
        if _is_excluded(rel.parent):
            continue
        if p.suffix in _PY_EXTS or p.suffix in {".sh", ".bat"} or \
           (p.suffix == ".json" and p.name.startswith("scene")):
            yield p, rel


def _own_pkg(py: Path) -> str:
    """文件所属场景根的包路径（相对 scenarios 的点分）。"""
    return _scene_root(py).relative_to(SCEN).as_posix().replace("/", ".")


def _is_own_or_shared(own: str, imported: str) -> str:
    """返回分类: ok / shared / cross。"""
    if not imported.startswith("flash.scenarios"):
        return "ok"
    rest = imported[len("flash.scenarios."):].split(".")
    top = rest[0] if rest else ""
    if top in SHARED_TOPS:
        return "shared"
    own_parts = own.split(".") if own else []
    # 自身判定：own 是 import 的前缀（导入自身子模块）或 import 是 own 的
    # 前缀（导入自身所在包/上级包）—— 两者都随场景整体移动，均视为 ok
    if own_parts:
        n = min(len(own_parts), len(rest))
        if rest[:n] == own_parts[:n]:
            return "ok"
    return "cross"


def _scene_root(f: Path) -> Path:
    """文件所属"可移动单元"根：最近的含 scene*.json 的祖先目录；
    无 manifest 的工具目录 → 所属分区一级目录（scripts/ 则为其自身）。"""
    d = f.resolve().parent
    for cand in (d, *d.parents):
        if cand == SCEN:
            break
        if any(cand.glob("scene*.json")):
            return cand
    for cand in (d, *d.parents):
        if cand.parent == SCEN:
            return cand          # 分区一级目录（如 private/SNB、scripts）
    return SCEN


def audit_py(py: Path, rel: Path, findings: list) -> None:
    src = py.read_text(encoding="utf-8", errors="replace")
    own = _own_pkg(py)
    sroot = _scene_root(py)
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        findings.append(("WARN", str(rel), e.lineno or 0,
                         f"AST 解析失败（跳过代码级检查）: {e}"))
        tree = None

    # 1) AST: parents[N] —— 按解析目标是否逃逸场景根分级
    if tree is not None:
        srclines = src.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
                    and node.value.attr == "parents":
                line = srclines[node.lineno - 1].strip() if node.lineno <= len(srclines) else ""
                # parents[N] 解析目标 ≈ 文件祖先第 N 级目录
                try:
                    n = ast.literal_eval(node.slice)
                    target = py.resolve().parents[n] if len(py.resolve().parents) > n else None
                except (ValueError, SyntaxError, IndexError):
                    target = None
                if target is None:
                    findings.append(("ERROR", str(rel), node.lineno,
                                     f"parents[N] 动态索引（无法判定）: {line[:110]}"))
                elif sroot == SCEN or not (target == sroot or sroot in target.parents):
                    findings.append(("ERROR", str(rel), node.lineno,
                                     f"parents[N] 逃逸场景根(→{target.name}): {line[:110]}"))
                else:
                    findings.append(("INFO", str(rel), node.lineno,
                                     f"parents[N] 场景内部相对引用: {line[:110]}"))
        # 2) AST: flash.scenarios.* import
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                if m.startswith("flash.scenarios"):
                    kind = _is_own_or_shared(own, m)
                    if kind == "cross":
                        findings.append(("ERROR", str(rel), node.lineno,
                                         f"跨场景 import: {m}"))
                    elif kind == "shared":
                        findings.append(("INFO", str(rel), node.lineno,
                                         f"共享区引用: {m}"))

    # 3) 正则兜底：动态 import/字符串形式的包路径（含 flash/scenarios 斜杠形式）
    for m in _find_slash_pkg.finditer(src):
        ln = src[:m.start()].count("\n") + 1
        findings.append(("WARN", str(rel), ln,
                         f"斜杠包路径字面量（核对是否 manifest 字段/文档）: {m.group(0)[:110]}"))

    # 4) 注释行残留的 parents[N]（AST 抓不到的，仅提示）
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s.startswith("#") and _find_parents.search(line):
            findings.append(("INFO", str(rel), i, f"注释中的 parents[N]: {s[:110]}"))


def audit_manifest(mf: Path, rel: Path, findings: list) -> None:
    try:
        raw = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        findings.append(("ERROR", str(rel), 0, f"JSON 解析失败: {e}"))
        return
    if not isinstance(raw, dict):
        return
    bind_fields = ("module", "attr_module", "script", "input_rel_dir", "gen_script")
    hpc = raw.get("hpc") or {}
    for k in bind_fields:
        v = raw.get(k) or hpc.get(k)
        if not v:
            continue
        v = str(v)
        # 绝对包路径（flash.scenarios.… 或 flash/scenarios/…）→ 位置绑定
        if v.startswith("flash.scenarios") or v.startswith("flash/"):
            # 相对形式（以 . 开头）或纯文件名 → 可移植
            findings.append(("ERROR", str(rel), 0, f"manifest 绝对绑定 [{k}]: {v}"))
        elif k == "script" and "/" in v and not v.startswith("./"):
            findings.append(("ERROR", str(rel), 0, f"manifest 仓库根相对 script: {v}"))
        elif k in ("input_rel_dir", "gen_script") and v.startswith("flash/"):
            findings.append(("ERROR", str(rel), 0, f"manifest 仓库根相对 [{k}]: {v}"))
        # 跨场景字段引用其他目录（../ 或分类层级）已在 manifest 字段里，核对
        if ".." in v:
            findings.append(("WARN", str(rel), 0, f"manifest 含 .. 跳级 [{k}]: {v}"))


def audit_shell(sh: Path, rel: Path, findings: list) -> None:
    try:
        src = sh.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for i, line in enumerate(src.splitlines(), 1):
        if _find_reljump.search(line):
            findings.append(("WARN", str(rel), i,
                             f"$SCRIPT_DIR 相对跳级: {line.strip()[:110]}"))
        if re.search(r"flash[\\/]scenarios[\\/](public|private|flash_demo)", line) \
                and not line.strip().startswith("#"):
            findings.append(("WARN", str(rel), i,
                             f"shell 内层级路径: {line.strip()[:110]}"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="场景可移植性审计")
    ap.add_argument("--strict", action="store_true", help="存在 ERROR 时退出码 1")
    ap.add_argument("--json", dest="json_out", default="", help="额外输出 JSON 报告路径")
    args = ap.parse_args(argv)

    findings: list = []   # (level, file, line, msg)
    n_files = 0
    for p, rel in _iter_files():
        n_files += 1
        if p.suffix == ".py":
            audit_py(p, rel, findings)
        elif p.suffix == ".json":
            audit_manifest(p, rel, findings)
        else:
            audit_shell(p, rel, findings)

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f[0]], f[1], f[3]))

    counts = {lv: sum(1 for f in findings if f[0] == lv) for lv in ("ERROR", "WARN", "INFO")}
    lines = [
        "=" * 78,
        f"场景可移植性审计  {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"扫描根: {SCEN}   文件数: {n_files}",
        f"ERROR={counts['ERROR']}  WARN={counts['WARN']}  INFO={counts['INFO']}",
        "=" * 78,
    ]
    cur_lv = None
    for lv, f, ln, msg in findings:
        if lv != cur_lv:
            lines.append(f"\n── {lv} " + "─" * 60)
            cur_lv = lv
        lines.append(f"[{f}:{ln}] {msg}")

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rpt = _REPORT_DIR / f"audit_{datetime.now():%Y%m%d_%H%M%S}.txt"
    rpt.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[ok] 报告已写入 {rpt}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"counts": counts, "findings": [
                {"level": lv, "file": f, "line": ln, "msg": msg}
                for lv, f, ln, msg in findings]}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"[ok] JSON 已写入 {args.json_out}")

    return 1 if (args.strict and counts["ERROR"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
