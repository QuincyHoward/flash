#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
keep_private_only.py — 反 gitignore: 只保留私有(忽略)文件, 删除公开(被跟踪)文件, 删除 .git
============================================================================================

用途
----
便于**保存私有项目**: 把本机目录精简为"只含 .gitignore 忽略的私有文件"
(如凭据、测试数据、本地产物、runs 等), 删除所有被 git 跟踪的公开文件
(这些文件 Gitee 远程仓库已有, 删除不损失), 最后删除 `.git` 目录
**确保删除后不会向远端推送**。

与正常 git 相反:
  - 正常: 保留被跟踪文件, 忽略文件不提交
  - 本脚本: 保留忽略(私有)文件, 删除被跟踪(公开)文件

用法 (在项目根目录执行)
-----------------------
    python scripts/07_private_keep/keep_private_only.py             # 交互式确认后执行
    python scripts/07_private_keep/keep_private_only.py --dry-run   # 仅预览, 不删除
    python scripts/07_private_keep/keep_private_only.py --preview   # 同 --dry-run

安全机制 (交互式确认, 双保险)
-----------------------------
  1. 第一步: 打印统计与文件预览, 需输入 y/yes 继续
  2. 第二步: 打印最终确认警告, 需输入固定短语 "DELETE-PRIVATE" 才执行
  3. 删除前将 .git 重命名为 .git.private-bak-<时间戳> (可手动恢复),
     确认无误后可自行删除该备份
  4. 全程不触碰忽略文件 (私有文件原样保留)

注意事项
--------
  - 本脚本自身位于 scripts/ 下, 若 scripts/ 被 git 跟踪, 脚本文件也会被列入
    "待删除公开文件"。运行前请将脚本复制到项目目录之外 (或运行后从备份取回)。
  - 删除操作不可逆, 请先 --dry-run 查看预览。
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── 颜色 (Windows 兼容) ─────────────────────────────────────
if os.name == "nt":
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
CYAN = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"


def eprint(msg: str = "") -> None:
    print(msg, file=sys.stderr, flush=True)


def find_project_root() -> Path:
    """向上查找同时含 .git 与 .gitignore 的目录 (项目根)。"""
    cur = Path(__file__).resolve().parent
    for _ in range(12):
        if (cur / ".git").exists() and (cur / ".gitignore").exists():
            return cur
        if cur == cur.parent:
            break
        cur = cur.parent
    raise SystemExit("[FATAL] 未找到项目根 (需同时存在 .git 与 .gitignore)")


def git(cmd: str, root: Path) -> subprocess.CompletedProcess:
    """在项目根执行 git 命令 (无交互直连注入, 只读操作)。"""
    full = "git -c credential.helper= " + cmd if cmd.startswith("git ") else cmd
    return subprocess.run(
        full, shell=True, cwd=str(root),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def collect_files(root: Path) -> dict:
    """收集三类文件 (相对路径, 不含 .git)。

    返回:
        tracked:  被 git 跟踪的公开文件 (待删除)
        untracked: 未跟踪且非忽略的文件 (待删除)
        ignored:  .gitignore 忽略的私有文件 (保留)
    """
    def _list(flag: str) -> list:
        r = git(f"git ls-files --others --ignored --exclude-standard -z" if flag == "ignored"
                else f"git ls-files {flag} -z", root)
        return [p for p in r.stdout.split("\0") if p]

    tracked = [p for p in _list("") if p]                       # 被跟踪
    untracked = _list("--others --exclude-standard")            # 未跟踪非忽略
    ignored = _list("ignored")                                  # 忽略 (私有)

    # 去掉 .git 自身与空项
    def _clean(items):
        return [p.replace("\\", "/") for p in items
                if p and not p.startswith(".git/") and p != ".git"]

    return {
        "tracked": _clean(tracked),
        "untracked": _clean(untracked),
        "ignored": _clean(ignored),
    }


def preview(coll: dict, root: Path) -> None:
    """打印统计与文件预览。"""
    tracked, untracked, ignored = coll["tracked"], coll["untracked"], coll["ignored"]
    print(f"\n{BOLD}══ 文件清单 (项目根: {root}) ══{RESET}")
    print(f"  {GREEN}保留 (忽略/私有): {len(ignored)} 个{RESET}")
    print(f"  {RED}删除 (被跟踪/公开): {len(tracked)} 个{RESET}")
    print(f"  {YELLOW}删除 (未跟踪/非忽略): {len(untracked)} 个{RESET}")
    print(f"  {CYAN}删除 .git 目录 (防止推送){RESET}\n")

    def _show(title, items, color, n=20):
        print(f"  {color}{BOLD}{title} (前 {min(n, len(items))}/{len(items)}){RESET}")
        for p in items[:n]:
            print(f"    {color}- {p}{RESET}")
        if len(items) > n:
            print(f"    {color}  ... 等 {len(items) - n} 个{RESET}")
        print()

    _show("【保留】忽略文件", ignored, GREEN, 15)
    _show("【删除】被跟踪文件", tracked, RED, 20)
    _show("【删除】未跟踪非忽略文件", untracked, YELLOW, 10)


def ask_confirm(prompt: str) -> bool:
    """读取用户输入, 超时(180s)未响应则中止 (不执行任何删除)。"""
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes", "是", "确认")


def delete_public_files(root: Path, coll: dict, dry_run: bool) -> int:
    """删除被跟踪 + 未跟踪非忽略文件。返回删除数。"""
    targets = [Path(root) / p for p in coll["tracked"] + coll["untracked"]]
    removed = 0
    for f in targets:
        if dry_run:
            continue
        try:
            if f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
            else:
                f.unlink(missing_ok=True)
            removed += 1
        except OSError as e:
            eprint(f"  {YELLOW}⚠ 删除失败: {f} ({e}){RESET}")
    # 清理空目录 (自下而上, 只删空的)
    if not dry_run:
        for p in sorted(targets, key=lambda x: len(x.parts), reverse=True):
            d = p.parent
            try:
                while d != root and d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
                    d = d.parent
            except OSError:
                pass
    return removed


def remove_git(root: Path, dry_run: bool) -> Path | None:
    """删除 .git (重命名为备份, 防误删可恢复)。"""
    git_dir = root / ".git"
    if dry_run:
        print(f"  [dry-run] 将删除 .git 目录: {git_dir}")
        return None
    bak = root / f".git.private-bak-{time.strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.move(str(git_dir), str(bak))
        print(f"  {GREEN}✓ .git 已重命名为 {bak.name} (确认无误后可手动删除){RESET}")
        return bak
    except Exception as e:
        eprint(f"  {RED}✗ .git 重命名失败: {e} (可能被进程占用, 请关闭后重试){RESET}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="反 gitignore: 只保留私有文件, 删除公开文件与 .git (防推送)")
    parser.add_argument("--dry-run", "--preview", action="store_true",
                        help="仅预览, 不执行任何删除")
    args = parser.parse_args()
    dry_run = args.dry_run

    root = find_project_root()
    print(f"{BOLD}项目根: {root}{RESET}")

    coll = collect_files(root)
    preview(coll, root)

    if dry_run:
        print(f"{YELLOW}[dry-run] 预览模式, 未执行任何删除。确认后请去掉 --dry-run 再运行。{RESET}\n")
        return 0

    # ── 第一层确认 ─────────────────────────────────────────
    print(f"{BOLD}{RED}⚠⚠  危险操作警告 ⚠⚠{RESET}")
    print(f"  将删除 {len(coll['tracked']) + len(coll['untracked'])} 个公开文件")
    print(f"  并删除 .git (之后无法向远端推送/拉取)")
    print(f"  仅保留 {len(coll['ignored'])} 个忽略(私有)文件")
    if not ask_confirm(f"\n{BOLD}是否继续? 输入 y 继续 (180 秒内不操作则自动中止): {RESET}"):
        print(f"{YELLOW}已中止, 未执行任何操作。{RESET}")
        return 1

    # ── 第二层确认 (固定短语, 防误操作) ────────────────────
    print(f"\n{RED}{BOLD}最终确认:{RESET}")
    print(f"  将删除全部公开文件并移除 .git, 此操作不可逆!")
    answer = input(f"{BOLD}请输入确认短语 DELETE-PRIVATE 以执行: {RESET}").strip()
    if answer != "DELETE-PRIVATE":
        print(f"{YELLOW}确认短语不匹配, 已中止。未执行任何操作。{RESET}")
        return 1

    print(f"\n[1/3] 删除公开文件...")
    n = delete_public_files(root, coll, dry_run=False)
    print(f"  {GREEN}✓ 已删除 {n} 个公开文件{RESET}")

    print(f"[2/3] 删除 .git (防止推送)...")
    bak = remove_git(root, dry_run=False)

    print(f"[3/3] 汇总...")
    print(f"\n  {GREEN}{BOLD}✅ 完成! 目录已精简为纯私有文件。{RESET}")
    print(f"  保留(私有): {len(coll['ignored'])} 个文件")
    print(f"  删除(公开): {n} 个文件")
    print(f"  .git: {'已移除 (备份: ' + str(bak) + ')' if bak else '未移除'}")
    print(f"\n  提示: 备份的 .git.private-bak-* 确认无误后可删除;")
    print(f"        如误操作需恢复, 将备份目录改回 .git 并 git reset --hard 即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
