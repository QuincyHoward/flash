# -*- coding: utf-8 -*-
"""dump_docstrings — 只读 AST 模块摘要工具（README 体系重建依据）。

遍历指定目录下全部 .py，输出 Markdown 摘要表：
    模块路径 | 行数 | 模块 docstring 首段 | 类(行数) | 顶层函数(行数) | main 入口

设计约束：
- 只用 ast 解析，**不 import、不执行任何代码**（规避副作用与敏感模块）；
- 输出仅写 stdout，不落盘；
- 默认排除 PlasmaPy/、__pycache__、archive*、输出/产物目录。

用法：
    python scripts/08_docs/dump_docstrings.py --root flash/_core
    python scripts/08_docs/dump_docstrings.py --root flash/input_gen --max-line-width 100
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DEFAULT_EXCLUDES = {
    "__pycache__", ".git", ".venv-win", ".venv-linux", ".pytest_cache",
    "PlasmaPy",            # vendored 外部包，永不处理
    "flash_output", "sim_output", "flash_input", "sim_input", "sim_input_si",
    "artifacts", "database", "logs_archive", "test_output",
    "reports", "inputfiles",
}


def _is_excluded(rel_parts: tuple[str, ...]) -> bool:
    for part in rel_parts:
        if part in DEFAULT_EXCLUDES:
            return True
        if part.startswith("archive"):
            return True
    return False


def _first_para(doc: str | None, width: int) -> str:
    """docstring 首段（跳过 ═══/=###/---- 纯装饰线），压成单行。"""
    if not doc:
        return ""
    def _deco(s: str) -> bool:
        t = s.strip()
        return bool(t) and len(set(t)) <= 3 and set(t) <= set("═=─-—_*#~· ")
    body = [ln.strip() for ln in doc.strip().splitlines()]
    lines = []
    for raw in body:
        if not raw:
            if lines:
                break
            continue
        if _deco(raw):
            continue
        lines.append(raw)
        if sum(len(x) + 1 for x in lines) > width:
            break
    text = " ".join(lines)
    return (text[: width - 1] + "…") if len(text) > width else text


def _cls_sig(node: ast.ClassDef) -> str:
    n_methods = sum(1 for x in node.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return f"{node.name}({node.end_lineno - node.lineno + 1}L,{n_methods}m)"


def dump_file(py: Path, rel: Path, width: int) -> tuple[str, int]:
    try:
        src = py.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"| `{rel.as_posix()}` | ? | ⚠️ 读取失败（非 UTF-8 或 IO 错误） | — | — | — |", 0
    lines = src.count("\n") + 1
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return (f"| `{rel.as_posix()}` | {lines} | ⚠️ 语法错误: {e.msg} | — | — | — |", lines)

    doc = ast.get_docstring(tree)
    classes = [_cls_sig(n) for n in tree.body if isinstance(n, ast.ClassDef)]
    funcs = [f"{n.name}({n.end_lineno - n.lineno + 1}L)"
             for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    has_main = any(isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                   for n in tree.body) and "__main__" in src
    entry = ("main()" if any(n.name == "main" for n in tree.body
                             if isinstance(n, ast.FunctionDef)) else
             ("CLI" if has_main else "—"))
    cells = (
        f"`{rel.as_posix()}`", str(lines),
        _first_para(doc, width).replace("|", "\\|"),
        "<br>".join(classes[:4]) + (f" (+{len(classes) - 4})" if len(classes) > 4 else "") or "—",
        "<br>".join(funcs[:4]) + (f" (+{len(funcs) - 4})" if len(funcs) > 4 else "") or "—",
        entry,
    )
    return "| " + " | ".join(cells) + " |", lines


def main() -> int:
    ap = argparse.ArgumentParser(description="只读 AST 模块摘要（README 重建依据）")
    ap.add_argument("--root", required=True, help="扫描根（相对仓库根或绝对路径）")
    ap.add_argument("--max-line-width", type=int, default=90, help="摘要单元格最大宽度")
    a = ap.parse_args()

    root = Path(a.root)
    if not root.is_absolute():
        root = REPO / root
    root = root.resolve()
    if not root.is_dir():
        print(f"[X] 目录不存在: {root}", file=sys.stderr)
        return 2

    total_lines, n_files = 0, 0
    print(f"## {root.relative_to(REPO).as_posix()} 模块摘要（AST 只读，共 ", end="")
    rows = []
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root)
        if _is_excluded(rel.parts):
            continue
        row, lines = dump_file(py, rel, a.max_line_width)
        rows.append(row)
        total_lines += lines
        n_files += 1
    print(f"{n_files} 个 .py，{total_lines} 行）\n")
    print("| 模块 | 行数 | 职责（docstring 首段） | 类 | 顶层函数 | 入口 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
