#!/usr/bin/env python3
"""校验 Markdown 文档里的图片引用能否正常显示
═══════════════════════════════════════════════════════════════════════════════

为什么需要它
------------
Markdown 图片能否显示，取决于**引用路径相对于 .md 文件自身**是否正确。
常见踩坑:
  · 用了 Windows 反斜杠（`..\\images\\x.png`）→ 多数渲染器解析失败
  · 路径里有空格却没做 URL 编码（`%20`）→ 断链
  · 相对层级写错（md 在 `docs/` 而图在 `images/`，须用 `../images/`）
  · 图片文件其实不存在 / 文件名大小写不符（Linux 上是硬错误）

本脚本对给定 .md 逐个解析 `![alt](path)` 与 `<img src="path">`，
把引用按**该 md 所在目录**解析成绝对路径，报告:
  ① 文件是否存在  ② 是否用了非 POSIX 分隔符  ③ 是否含未编码空格
  ④ 是否用了绝对路径（可移植性差）  ⑤ 是否为网络 URL（跳过本地检查）

退出码: 0 = 全部可显示；1 = 存在断链或不合规引用。

用法
----
    python verify_md_images.py <file.md> [<file2.md> ...]
    python verify_md_images.py --dir <目录>          # 递归校验目录下所有 .md
    python verify_md_images.py --dir <目录> --quiet  # 只输出问题
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# ![alt](path) 或 ![alt](<path with spaces>) —— 允许可选 "title"
RE_MD_IMG = re.compile(
    r"!\[[^\]]*\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^)\s]+))"
    r"(?:\s+\"[^\"]*\")?\s*\)")
# <img src="path" ...>
RE_HTML_IMG = re.compile(r"<img[^>]*\bsrc\s*=\s*[\"'](?P<path>[^\"']+)[\"']",
                         re.IGNORECASE)
URL_PREFIXES = ("http://", "https://", "data:", "//")


def find_refs(text: str) -> List[Tuple[int, str]]:
    """返回 (行号, 引用路径)。"""
    out: List[Tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in RE_MD_IMG.finditer(line):
            out.append((lineno, m.group("angle") or m.group("plain")))
        for m in RE_HTML_IMG.finditer(line):
            out.append((lineno, m.group("path")))
    return out


def check(md: Path, quiet: bool = False) -> int:
    if not md.exists():
        print(f"[X] 文件不存在: {md}")
        return 1
    text = md.read_text(encoding="utf-8", errors="replace")
    refs = find_refs(text)

    print("=" * 78)
    print(f" 校验图片引用: {md.name}")
    try:
        print(f" 所在目录: {md.parent}")
    except LookupError:                                    # pragma: no cover
        pass
    print("=" * 78)
    if not refs:
        print("  (文档中没有任何图片引用)")
        return 0

    bad = 0
    for lineno, raw in refs:
        issues: List[str] = []
        if raw.startswith(URL_PREFIXES):
            print(f"  line {lineno:>4}: {raw}   [网络 URL —— 跳过本地检查]")
            continue
        # ① 反斜杠
        if "\\" in raw:
            issues.append("使用了反斜杠（应改为 POSIX 正斜杠 '/'）")
        # ② 空格未编码
        if " " in raw:
            issues.append("路径含空格且未做 %20 编码")
        # ③ 绝对路径
        if Path(raw).is_absolute() or re.match(r"^[A-Za-z]:", raw):
            issues.append("使用了绝对路径（不可移植）")
        # ④ 文件是否存在（相对该 md 所在目录解析）
        target = (md.parent / raw.replace("\\", "/")).resolve()
        exists = target.exists()
        if not exists:
            issues.append(f"文件不存在 → 解析为 {target}")

        if issues:
            bad += 1
            print(f"  line {lineno:>4}: {raw}")
            for it in issues:
                print(f"            [X] {it}")
        elif not quiet:
            size = target.stat().st_size // 1024
            print(f"  line {lineno:>4}: {raw}")
            print(f"            [OK] 可显示  ({size} KB)")

    print("-" * 78)
    if bad:
        print(f"  [X] {bad}/{len(refs)} 个引用**有问题** —— 文档中不会正常显示")
        return 1
    print(f"  [OK] 全部 {len(refs)} 个引用均可正常显示")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="校验 md 图片引用能否正常显示")
    ap.add_argument("files", nargs="*", help="要校验的 .md 文件")
    ap.add_argument("--dir", default=None, help="递归校验该目录下所有 .md")
    ap.add_argument("--quiet", action="store_true", help="只输出有问题的引用")
    args = ap.parse_args()

    targets: List[Path] = [Path(f) for f in args.files]
    if args.dir:
        targets += sorted(Path(args.dir).rglob("*.md"))
    if not targets:
        ap.print_help()
        return 2

    rc = 0
    for md in targets:
        rc |= check(md, args.quiet)
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
