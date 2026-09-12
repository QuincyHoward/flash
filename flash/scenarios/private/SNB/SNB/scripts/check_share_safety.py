#!/usr/bin/env python3
"""SNB 分享前安全检查器 ── 防止 F90 源码 / 凭据外泄
═══════════════════════════════════════════════════════════════════════════════

**分享规则**：分享方法，不分享实现。
  ❌ F90 源码及其变体        ❌ 会生成 F90 的 py 脚本
  ❌ 逐字引用算法片段的文档   ❌ 凭据 / 密钥 / 账号
  ✅ par 配置  ✅ 驱动/分析/绘图 py  ✅ 说明与流程文档

**双重校验**（缺一不可）
  ① 类型闸门: `git add -n --all` 干跑 → 会被提交的源码类文件必须为 0
     （若只看内容扫描, 而 .gitignore 配错放行了 *.F90, 源码根本进不了扫描列表）
  ② 内容闸门: 扫描待提交的文本文件 → Fortran 特征串 / 密钥模式必须 0 命中
     （若只看类型闸门, 把 F90 粘进放行类型 .md/.py 就绕过了）

用法:
    python check_share_safety.py                  # 全仓库检查
    python check_share_safety.py --root <dir>     # 指定仓库根
    python check_share_safety.py --quiet          # 仅在失败时输出
    python check_share_safety.py --list-ok        # 额外列出通过的文件

退出码: 0 = 安全; 1 = 发现风险 (禁止提交); 2 = 环境问题 (非 git 仓库等)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# ── ① 类型闸门: 一律不得入库的源码/二进制类型 ─────────────────
#   注: .cn4 (EOS/opacity 表) 未列入 —— 本项目 .gitignore 明确白名单放行,
#       如需收紧请在此加入 ".cn4" 并同步改 .gitignore。
#   ★ 2026-09-12 对抗测试补漏: 原先只有 .f90/.f/.for/.f77/.ftn/.inc,
#     实测 `leak.f95` **两个闸门都不报**、可原样提交 → 现补齐 Fortran 家族
#     与常见编译产物扩展名。**新增语言/后缀时务必回来补这里。**
FORBIDDEN_SUFFIXES = (
    ".f90", ".f", ".for", ".f77", ".f95", ".f03", ".f08", ".ftn", ".fpp", ".inc",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cu", ".cuh",   # C/C++
    ".o", ".a", ".so", ".mod", ".pyc", ".pyd", ".dll", ".exe",  # 编译产物
)

# ══════════════════════════════════════════════════════════════
# 扩展名判定改为「**二进制黑名单**」而非「文本白名单」
# ══════════════════════════════════════════════════════════════
# ★ 2026-09-12 对抗测试补漏: 原先 `TEXT_SUFFIXES` 是白名单 ——
#   任何**未列出的扩展名**（如 `.f95` / `.rst` / `.ipynb` / 自造后缀）
#   都会被静默跳过。**内容闸门不该有"未知即放行"的默认**。
#   现改为: 除① 已由类型闸门拦下的源码类、② 明确的二进制格式 之外,
#   其余一律**当文本扫**（并做 NUL 字节嗅探 + 体积上限兜底）。
BINARY_SUFFIXES = (
    ".h5", ".hdf5", ".cn4", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif",
    ".tiff", ".pdf", ".zip", ".gz", ".bz2", ".xz", ".tar", ".7z", ".rar",
    ".pt", ".npz", ".npy", ".pkl", ".mat", ".mp4", ".avi", ".mov", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
)

# 单文件体积上限: 超过则只扫前 N 字节（防大日志拖垮检查）
MAX_SCAN_BYTES = 4 * 1024 * 1024

# ── ② 内容闸门 ────────────────────────────────────────────────
# ★ 判据设计要点: 可分享文档**允许**出现
#     · 文件名 / 模块名 (如 diff_advanceTherm.F90, hy_slopeLimiters)
#     · par 参数名   (如 rt_useMGD, diff_eleFlMode)
#     · 函数/子程序名 (如 call RadTrans 的"名字", 不带参数)
#   但**不允许**出现真正带语法的**代码语句** (声明 / 赋值 / 带参调用 / 下标访问)。
#   故先把 "*.F90/*.f90" 文件名剔除, 再用**代码语句正则**判定, 避免误报。
_FNAME_RE = re.compile(r"[\w./\\-]+\.(?:F90|f90|F|f)\b", re.IGNORECASE)

CODE_PATTERNS = (
    (r"(?i)\bsolnvec\s*\(", "解向量下标访问语句"),
    (r"(?i)\bimplicit\s+none\b", "Fortran 声明"),
    (r"(?i)\bintent\s*\(\s*(?:in|out|inout)\b", "Fortran 哑元声明"),
    (r"(?i)\bend\s*subroutine\b", "子程序结束语句"),
    (r"(?i)\bend\s*do\b|\benddo\b", "DO 结束语句"),
    (r"(?i)^\s*(?:call|use)\s+\w+\s*\(", "带参调用/引用语句"),
    (r"(?i)\breal\s*,\s*(?:dimension|intent|pointer|save)", "Fortran 变量声明"),
    # ★ 解向量访问规则按 FLASH 宏约定收紧为「全大写 + 大写 `_VAR` 后缀 + 左括号」:
    #   FLASH 的下标访问是形如 <全大写宏名>( 的写法;
    #   原先的大小写不敏感版 `\w+_var\(` 会误伤 Python 里合法的蛇形命名
    #   (实测: 名为 read + _var 的读取函数被误报为源码泄漏)
    #   → 现要求首字符大写、后缀为大写 `_VAR`、紧跟左括号且首参后接逗号。
    (r"\b[A-Z][A-Z0-9_]*_VAR\s*\(\s*\w+\s*,", "解向量宏下标访问"),
    (r"(?i)\b=\s*-?\s*\(\s*$", "表达式赋值延续"),
    (r"(?i)\b(?:do|if)\s*\(.*\)\s*then\b", "Fortran 控制语句"),
)

# 密钥 / 凭据模式
SECRET_PATTERNS = (
    (r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{3,}", "明文口令"),
    (r"(?i)\b(secret|token|api[_-]?key|access[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}", "密钥/token"),
    (r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥"),
    (r"\bscfa\d{4}\b|\bsch\d{4}\b", "疑似超算账号"),
    (r"(?i)\b(ssh|scp)\b.*@[a-z0-9.-]+\.[a-z]{2,}", "SSH 连接串"),
)

# 允许出现的"安全上下文"——命中这些词的行不判为泄漏 (降低误报)
WHITELIST_HINTS = (
    "示例", "占位", "placeholder", "your_", "<your", "example",
    "例如", "如下", "检查", "禁止", "不得", "检测", "扫描", "标记",
    "演示", "格式", "样例", "已公开", "已知",
)

# ── 已确认的"公开已知项"例外清单 ───────────────────────────────
# 仅用于**不再新增**的乐观豁免: 这些内容在提交历史中**早已公开**
# (2026-09-11 核查: 31 个已提交文件含超算账号名), 清理历史需用户决定,
# 在此之前对本清单内的文件放行账号类告警, 但**仍检查 F90 与其它密钥**。
# ⚠️ 不要在此加入新的未知项; 历史清理见 docs/06_分享与保密规则.md §6。
KNOWN_PUBLIC_ALLOWLIST = (
    "flash/scenarios/private/tracer/SNB/SNBOneCH_ml/README.md",
    "flash/scenarios/private/SNB/SNBtest/Test/t001/README.md",
)

def _scan_skip(f: Path) -> bool:
    """是否**跳过内容扫描**：源码类（已被类型闸门拦）、明确的二进制格式。"""
    suf = f.suffix.lower()
    if suf in FORBIDDEN_SUFFIXES or suf in BINARY_SUFFIXES:
        return True
    return False


def _read_text(path: Path) -> str | None:
    """尽量当文本读；二进制（含 NUL）返回 None。

    体积超上限时只读前 MAX_SCAN_BYTES（大日志不至于拖垮检查，
    且 F90 片段通常出现在文件前部）。
    """
    try:
        with path.open("rb") as fh:
            raw = fh.read(MAX_SCAN_BYTES + 1)
    except OSError:
        return None
    if b"\x00" in raw[:8192]:
        return None
    return raw.decode("utf-8", errors="replace")


def _run(cmd: List[str], cwd: Path) -> Tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def git_root(start: Path) -> Path | None:
    code, out = _run(["git", "rev-parse", "--show-toplevel"], start)
    return Path(out.strip()) if code == 0 and out.strip() else None


def commit_candidates(root: Path) -> Tuple[int, List[Path]]:
    """返回「可能被提交的文件」= **已暂存 ∪ 未跟踪 ∪ 已修改**。

    ★★ 2026-09-12 对抗测试补漏（**致命 fail-open**）：
      原实现只用 `git add -n --all` 的干跑输出。但该命令**只报告"将被新增"的
      文件** —— **已经 `git add` 暂存的文件不在其中**（它已在索引里，无需再 add）。
      实测：未暂存的 `leak.md`（含逐字 F90）被拦 rc=1；一旦 `git add` 之后，
      检查器**完全看不到它**并 rc=0 报"安全可提交" —— 而暂存内容正是要提交的内容。
      现改为三路并集：
        ① `git diff --cached`        —— 已暂存（将要提交）
        ② `git ls-files --others`    —— 未跟踪（未被 .gitignore 忽略）
        ③ `git ls-files --modified`  —— 已修改（未暂存）
      任一命令失败 → 返回 rc≠0，由调用方**判为环境问题并拒绝放行（fail-closed）**。
    """
    files: set[Path] = set()
    cmds = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        ["git", "ls-files", "--others", "--exclude-standard"],
        ["git", "ls-files", "--modified", "--exclude-standard"],
    )
    for cmd in cmds:
        code, out = _run(cmd, root)
        if code != 0:
            return 2, []
        for line in out.splitlines():
            s = line.strip()
            if s:
                files.add(root / s)
    return 0, sorted(files)


def check_types(files: List[Path]) -> List[Tuple[Path, str]]:
    bad = []
    for f in files:
        suf = f.suffix.lower()
        if suf in FORBIDDEN_SUFFIXES or f.name.endswith(".mod"):
            bad.append((f, f"源码/二进制类型 {suf or f.name}"))
    return bad


def check_dirs(files: List[Path], root: Path) -> List[Tuple[Path, str]]:
    """按目录规则拦截: 本地保留层 / 场景产物 / 源码快照。

    ★ 目录闸门不可省: 仅靠"类型闸门"挡不住 `tools_local/*.py`
      （它扩展名是放行的 .py, 但内容会写入 F90, 必须整目录排除）。
    """
    risky = ("/variants/", "/source/", "/tools_local/",
             "/flash_input/", "/flash_output/", "/src/")
    bad = []
    for f in files:
        s = f.as_posix()
        if "/SNBtest/src/" in s:
            bad.append((f, "位于 FLASH 源码快照目录"))
            continue
        for r in risky:
            if r == "/src/":
                continue
            if r in s:
                bad.append((f, f"位于受保护目录 {r}"))
                break
    return bad


def check_contents(files: List[Path], root: Path,
                   list_ok: bool = False) -> List[Tuple[Path, str]]:
    bad: List[Tuple[Path, str]] = []
    ok: List[Path] = []
    for f in files:
        if _scan_skip(f):
            continue            # 源码类(已被类型闸门拦下) 或 明确二进制 → 不读
        txt = _read_text(f)
        if txt is None:
            continue

        # ★ 先剔除文件名 (diff_advanceTherm.F90 → 占位), 避免"文件名"被误判为代码
        scan = _FNAME_RE.sub("<F90FILE>", txt)

        hits: List[str] = []
        rel = f.relative_to(root).as_posix() if root in f.parents or root == f.parent else f.as_posix()
        allow_account = rel in KNOWN_PUBLIC_ALLOWLIST
        for pat, desc in CODE_PATTERNS:
            for mt in re.finditer(pat, scan, flags=re.MULTILINE):
                line_no = scan[:mt.start()].count("\n") + 1
                ctx = scan.splitlines()[line_no - 1] if line_no <= len(scan.splitlines()) else ""
                if any(h in ctx for h in WHITELIST_HINTS):
                    continue
                hits.append(f"{desc}: {mt.group(0).strip()[:48]!r} (行 {line_no})")
                break
        for pat, desc in SECRET_PATTERNS:
            if allow_account and "账号" in desc:
                continue          # 已在历史中公开, 豁免 (见 KNOWN_PUBLIC_ALLOWLIST)
            for mt in re.finditer(pat, scan):
                line_no = scan[:mt.start()].count("\n") + 1
                ctx = scan.splitlines()[line_no - 1] if line_no <= len(scan.splitlines()) else ""
                if any(h in ctx for h in WHITELIST_HINTS):
                    continue
                hits.append(f"{desc}: {mt.group(0)[:40]!r} (行 {line_no})")
                break

        if hits:
            for h in hits:
                bad.append((f, h))
        else:
            ok.append(f)
    if list_ok:
        print(f"\n  ── 通过内容检查的文件 ({len(ok)}) ──")
        for f in sorted(ok):
            print(f"    OK  {f.relative_to(root).as_posix()}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 分享前安全检查器")
    ap.add_argument("--root", default=None, help="仓库根 (默认自动探测)")
    ap.add_argument("--quiet", action="store_true", help="仅在失败时输出")
    ap.add_argument("--list-ok", action="store_true", help="列出通过的文件")
    args = ap.parse_args()

    start = Path(args.root).resolve() if args.root else Path.cwd()
    root = git_root(start)
    if root is None:
        print(f"[X] 不是 git 仓库: {start}")
        return 2
    if not args.quiet:
        print("=" * 74)
        print(f" SNB 分享前安全检查  仓库根 = {root}")
        print("  规则: 分享方法, 不分享实现 (F90 / F90 生成器 / 算法引用 / 凭据)")
        print("=" * 74)

    rc, files = commit_candidates(root)
    if rc != 0:
        # ★ fail-closed: git 查询失败时**绝不放行**（原先返回 0 = "安全" 属误报）
        print(f"[X] 无法枚举待提交文件 (git 查询失败, rc={rc}) —— 判为环境问题")
        print("    请确认当前目录是 git 仓库且 git 可用; 修复后重跑。")
        return 2
    if not files:
        print("[!] 暂存区与工作树均为空 (无可提交内容) —— 无风险, 通过")
        return 0
    if not args.quiet:
        print(f"\n  待提交文件总数: {len(files)}"
              f"  (已暂存 ∪ 未跟踪 ∪ 已修改)")

    bad_types = check_types(files)
    bad_dirs = check_dirs(files, root)
    bad_cont = check_contents(files, root, args.list_ok)

    # ── 报告 ────────────────────────────────────────────────
    if not args.quiet:
        print(f"\n  ── ① 类型闸门 (源码/二进制) ──────────────────────")
        if bad_types:
            for f, why in bad_types:
                print(f"    [X] {f.relative_to(root).as_posix()}\n        原因: {why}")
        else:
            print("    OK  无源码/二进制类型被提交 ✓")

        print(f"\n  ── ①b 受保护目录闸门 ─────────────────────────────")
        if bad_dirs:
            for f, why in bad_dirs:
                print(f"    [X] {f.relative_to(root).as_posix()}\n        原因: {why}")
        else:
            print("    OK  无受保护目录内容 ✓")

        print(f"\n  ── ② 内容闸门 (算法片段 / 凭据) ───────────────────")
        if bad_cont:
            for f, why in bad_cont:
                print(f"    [X] {f.relative_to(root).as_posix()}\n        命中: {why}")
        else:
            print("    OK  无算法片段 / 凭据命中 ✓")

    total = len(bad_types) + len(bad_dirs) + len(bad_cont)
    print()
    if total:
        print("=" * 74)
        print(f" [X] 发现 {total} 项分享风险 —— **禁止提交**")
        print("     处置见 docs/06_分享与保密规则.md")
        print("=" * 74)
        return 1
    print("=" * 74)
    print(" [OK] 分享安全检查通过 —— 可以提交 ✓")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
