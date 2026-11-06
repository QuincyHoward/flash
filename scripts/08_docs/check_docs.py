# -*- coding: utf-8 -*-
"""check_docs — README/GUIDE/SKILL/AGENTS 文档机器校验（文档防回归门禁）。

扫描指定根下全部 README*.md / *GUIDE*.md / SKILL.md / AGENTS.md，校验四类问题：
  1. 相对路径链接：Markdown 链接与行内代码路径指向的文件/目录必须存在；
  2. Python 模块引用：`flash.xxx.yzz` 形式的模块路径必须能定位到 .py；
  3. 元信息块：每个 README 头部必须有「最后核对：YYYY-MM-DD」行（防腐化锚）；
  4. 敏感信息启发式：sk- 开头 key、password=/token= 赋值、明文 IPv4。

违规输出清单，退出码非 0（阻断 commit）。
用法：
    python scripts/08_docs/check_docs.py                # 全仓（默认排除区自动跳过）
    python scripts/08_docs/check_docs.py --root flash/_core
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DEFAULT_EXCLUDES = {
    "__pycache__", ".git", ".venv-win", ".venv-linux", ".pytest_cache",
    "PlasmaPy", "flash_output", "sim_output", "flash_input", "sim_input",
    "sim_input_si", "artifacts", "database", "logs_archive", "test_output",
    "reports", "inputfiles", "node_modules", "_legacy_diags",
    "temp_delete",
    # 上游知识库浅克隆（不入 git；含 18 个第三方 SKILL.md/AGENTS.md，不纳入门禁）
    "temp",
    # WorkBuddy 本地生成物（skills/ 的镜像副本，避免重复扫描）
    ".workbuddy",
    # pytest 基线外测试区（--ignore），不纳入文档体系
    "hdf5ploter_easy", "newpara", "remote_connect",
}

MD_PATTERNS = ("README*.md", "*GUIDE*.md", "README.md", "SKILL.md", "AGENTS.md")

# 行内代码或裸路径中形如 flash/xxx/yyy 的仓库内路径（排除 URL、锚点）
REPO_PATH_RE = re.compile(r"`(flash/[\w\-./]+?)`")
# flash.x.y.z 模块引用
MODULE_RE = re.compile(r"`(flash(?:\.[a-z_][\w]*){2,})`")
# Markdown 相对链接 [text](target) —— 排除 http/锚点/纯代码块
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#\s]+)\)")
DATE_RE = re.compile(r"最后核对[：:]\s*\d{4}-\d{2}-\d{2}")
SENSITIVE_RES = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),            # API key
    re.compile(r"(?i)\b(password|passwd|token|secret)\s*[=:]\s*['\"]?[^\s'\"]{6,}"),
    # IPv4（VERSIONISH 标记 → 降级 WARN）; 排除形如 hdf5/1.8.3.1 的版本号
    re.compile(r"(?<![\w/.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])(?#VERSIONISH)"),
]

SUFFIXES = ("", ".py", ".md", ".json", ".txt", ".toml", ".cfg", ".sh", ".bat", ".F90", ".f90")


def _iter_mds(root: Path):
    for pat in MD_PATTERNS:
        for p in sorted(root.rglob(pat)):
            if any(x in p.parts for x in DEFAULT_EXCLUDES):
                continue
            if p.is_file():
                yield p


def _resolve(base: Path, target: str) -> Path | None:
    t = target.strip()
    if not t or t.startswith(("http", "~", "$", "/", "\\")):
        return None
    t = t.split("#", 1)[0].rstrip("/").replace("%20", " ")
    if not t:
        return None
    cand = (base / t).resolve()
    if cand.exists():
        return cand
    for suf in SUFFIXES[1:]:
        if (base / (t + suf)).exists():
            return cand.with_name(t + suf)
    # 也可能是相对仓库根的路径
    cand2 = (REPO / t).resolve()
    if cand2.exists():
        return cand2
    for suf in SUFFIXES[1:]:
        if (REPO / (t + suf)).exists():
            return REPO / (t + suf)
    return None


def _module_exists(mod: str) -> bool:
    parts = mod.split(".")
    if parts[0] != "flash":
        return True  # 非 flash 模块不校验
    rel = Path(*parts)
    for cand in (REPO / rel.with_suffix(".py"),
                 REPO / rel / "__init__.py",
                 REPO / rel):
        if cand.exists():
            return True
    # 末段可能是函数/类属性（如 ...execution.resolve_target）——父路径是模块即通过
    if len(parts) > 2:
        parent = Path(*parts[:-1])
        if (REPO / parent.with_suffix(".py")).exists() or (REPO / parent / "__init__.py").exists():
            return True
    return False


def check_file(md: Path, findings: list) -> None:
    rel = md.relative_to(REPO)
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        findings.append(("ERROR", str(rel), f"读取失败: {e}"))
        return
    head = text[:1500]

    # 3. 元信息块（README* / SKILL.md / AGENTS.md 均须防腐锚点）
    if (md.name.lower().startswith("readme")
            or md.name in ("SKILL.md", "AGENTS.md")) and not DATE_RE.search(head):
        findings.append(("WARN", str(rel), "头部缺「最后核对：YYYY-MM-DD」元信息块"))

    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
        # 4. 敏感信息（代码块内外都查）
        for rx in SENSITIVE_RES:
            m = rx.search(line)
            if m and "example" not in line.lower() and "占位" not in line:
                # IPv4 规则降为 WARN（版本号/子网表述无法自动区分, 人工复核）;
                # 真实凭据类(sk-/password=/token=)保持 ERROR
                lv = "WARN" if "VERSIONISH" in rx.pattern else "ERROR"
                findings.append((lv, f"{rel}:{i}", f"疑似敏感信息: {m.group(0)[:24]}…"))

        if in_code or s.startswith((">", "#")) and not s.startswith("#!"):
            pass
        # 1. 仓库路径引用
        for m in REPO_PATH_RE.finditer(line):
            if _resolve(md.parent, m.group(1)) is None:
                findings.append(("WARN", f"{rel}:{i}", f"路径疑似不存在: {m.group(1)}"))
        # 2. 模块引用
        for m in MODULE_RE.finditer(line):
            if not _module_exists(m.group(1)):
                findings.append(("WARN", f"{rel}:{i}", f"模块疑似不存在: {m.group(1)}"))
        # 1b. Markdown 相对链接
        for m in LINK_RE.finditer(line):
            tgt = m.group(1)
            if tgt.startswith(("http", "mailto")):
                continue
            if _resolve(md.parent, tgt) is None:
                findings.append(("ERROR", f"{rel}:{i}", f"相对链接失效: {tgt}"))


def main() -> int:
    ap = argparse.ArgumentParser(description="README/GUIDE 机器校验门禁")
    ap.add_argument("--root", default=".", help="扫描根（默认仓库根）")
    ap.add_argument("--strict", action="store_true", help="WARN 也算失败")
    a = ap.parse_args()
    root = Path(a.root)
    root = root.resolve() if root.is_absolute() else (REPO / root).resolve()
    if not root.is_dir():
        print(f"[X] 目录不存在: {root}", file=sys.stderr)
        return 2

    findings: list = []
    n = 0
    seen: set[Path] = set()
    for md in _iter_mds(root):
        rp = md.resolve()
        if rp in seen:                     # 多模式匹配同一文件去重
            continue
        seen.add(rp)
        n += 1
        check_file(md, findings)

    errs = [f for f in findings if f[0] == "ERROR"]
    warns = [f for f in findings if f[0] == "WARN"]
    print(f"[check_docs] 扫描 {n} 篇文档 · ERROR={len(errs)} · WARN={len(warns)}")
    for lv, loc, msg in errs[:40]:
        print(f"  [{lv}] {loc}  {msg}")
    if len(errs) > 40:
        print(f"  … 其余 {len(errs) - 40} 条 ERROR 略")
    for lv, loc, msg in warns[:15]:
        print(f"  [{lv}] {loc}  {msg}")
    rc = 1 if (errs or (a.strict and warns)) else 0
    print("[ok] 通过" if rc == 0 else "[X] 未通过")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
