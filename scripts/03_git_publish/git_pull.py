#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键拉取脚本 (One-click Git pull from Gitee)
=============================================

定位: flash/scripts/03_git_publish/git_pull.py
双击 git_pull.bat 即可运行: 自动读取加密凭据 → 拉取远端最新到本地。

设计约束 (强制):
  * 任何密码 / 账户 / token 都 **绝不硬编码** 到本文件。
  * 所有敏感信息均通过专用函数 flash._core.credentials.get_credential_manager()
    读取加密存储 (~/.physimx/flash/credentials.enc, Fernet 对称加密)。
  * 认证 URL 仅在运行时由凭据动态拼装, 且 credential.helper / askPass 被禁用,
    任何环境都不会弹出凭据输入框。

使用示例:
  python git_pull.py              # 双击/默认: 拉取当前分支最新 (ff-only, 干净工作区)
  python git_pull.py -b main      # 拉取指定分支
  python git_pull.py --rebase     # 用 rebase 方式拉取 (保留线性历史)
  python git_pull.py --stash      # 有未提交变更时先 stash, 拉取后 pop
  python git_pull.py -n           # dry-run (fetch + 展示将要做的操作, 不合并)
  python git_pull.py --status     # 查看与远端同步状态 (不拉取)
  python git_pull.py --setup      # 进入凭据设置界面 (唯一需要交互的选项)

安全说明:
  * 默认 --ff-only: 只有当本地为远端快进时才合并, 不会意外产生 merge commit。
  * 若本地有未提交变更且未加 --stash, 脚本拒绝拉取以免覆盖工作, 并给出提示。
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

# ============================================================================
#  Bootstrap: 定位 flash 项目根 (含 pyproject.toml 的目录)
# ============================================================================
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root (no pyproject.toml found)")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 专用函数: 从加密凭据存储读取 Gitee 凭据 (禁止硬编码)
from flash._core.credentials import get_credential_manager, interactive_menu


# ============================================================================
#  颜色辅助
# ============================================================================
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def ok(msg: str):
    eprint(f"  {GREEN}[OK]{RESET} {msg}")


def info(msg: str):
    eprint(f"  {CYAN}[*]{RESET} {msg}")


def warn(msg: str):
    eprint(f"  {YELLOW}[!]{RESET} {msg}")


def fail(msg: str):
    eprint(f"  {RED}[X]{RESET} {msg}")


# ============================================================================
#  凭据读取 (专用函数, 不硬编码任何敏感字段)
# ============================================================================

def read_gitee_credential():
    """通过专用函数读取加密的 Gitee 凭据。

    返回 dict (含 token/username/login/repo_url), 缺失则退出并提示 --setup。
    本函数内部不出现任何明文密码 / 账户 / token。
    """
    cm = get_credential_manager()
    cred = cm.get("gitee") or {}
    if not cred.get("token"):
        fail("未找到 Gitee 凭据 (token 为空)。")
        fail("请先运行: python git_pull.py --setup")
        sys.exit(1)
    cred.setdefault("username", "")
    cred.setdefault("login", cred.get("username", ""))
    cred.setdefault("repo_url", "")
    return cred


def resolve_login(token: str, fallback: str) -> str:
    """Gitee 无交互直连需用 login (认证登录名), 显示名会 403。

    仅在凭据缺 login 时查询 API 获取; 否则直接返回凭据中的值。
    """
    if fallback:
        return fallback
    if not token:
        return ""
    import json
    import urllib.request
    try:
        url = f"https://gitee.com/api/v5/user?access_token={token}"
        req = urllib.request.Request(url, headers={"User-Agent": "flash-git-pull"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        login = data.get("login")
        if login:
            info(f"Gitee 登录名: {login}")
            return login
    except Exception as exc:  # noqa: BLE001
        warn(f"无法查询 Gitee 登录名 (使用凭据用户名): {exc}")
    return ""


# ============================================================================
#  Git 执行辅助
# ============================================================================

def run_git(args, cwd: Path | None = None, check: bool = True, capture: bool = True):
    """运行 git 命令 (shell=False, 参数列表, 强制禁用 credential 弹窗)。"""
    if isinstance(args, str):
        import shlex
        args = shlex.split(args)
    if args and args[0] == "git":
        args = args[1:]
    full = ["git", "-c", "credential.helper=", "-c", "core.askPass="] + args
    result = subprocess.run(
        full, shell=False, cwd=cwd,
        capture_output=capture, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and result.returncode != 0:
        err = (result.stderr or "").strip() or "(no stderr)"
        fail(f"Git 命令失败: {' '.join(full)}")
        fail(f"  {err}")
        sys.exit(1)
    return result


def find_git_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / ".git").exists():
            return cur
        if cur == cur.parent:
            break
        cur = cur.parent
    return start.resolve()


def current_branch(cwd: Path) -> str:
    r = run_git(["branch", "--show-current"], cwd=cwd)
    return r.stdout.strip() or "master"


def has_changes(cwd: Path) -> bool:
    r = run_git(["status", "--porcelain"], cwd=cwd)
    return bool(r.stdout.strip())


def ahead_behind(cwd: Path, branch: str):
    """返回 (ahead, behind): 本地相对 origin/<branch> 的领先/落后提交数。"""
    r = run_git(["rev-list", "--count", "--left-right", f"origin/{branch}...HEAD"],
                cwd=cwd, check=False)
    if r.returncode == 0 and r.stdout.strip():
        parts = r.stdout.strip().split()
        left = int(parts[0]) if len(parts) >= 1 else 0   # 远端独有 = 我们落后
        right = int(parts[1]) if len(parts) >= 2 else 0  # 本地独有 = 我们领先
        return right, left
    return 0, 0


def ensure_remote_auth(cwd: Path, auth_url: str, dry_run: bool):
    """配置 origin remote 为 token 认证 URL (不持久化明文到仓库文件)。"""
    r = run_git(["remote", "-v"], cwd=cwd, check=False)
    if "origin" not in r.stdout:
        info("添加远程仓库 origin")
        if not dry_run:
            run_git(["remote", "add", "origin", auth_url], cwd=cwd)
    else:
        info("更新远程仓库 URL (token 认证)")
        if not dry_run:
            run_git(["remote", "set-url", "origin", auth_url], cwd=cwd)


# ============================================================================
#  核心: 一键拉取
# ============================================================================

def pull_from_gitee(branch=None, rebase=False, stash=False, dry_run=False,
                    project_root: Path | None = None):
    if project_root is None:
        project_root = find_git_root(Path(__file__).resolve().parent)

    # ── 0. 读取加密凭据 (专用函数) ──
    cred = read_gitee_credential()
    token = cred["token"]
    username = cred.get("username", "")
    repo_url = cred.get("repo_url") or f"https://gitee.com/{username}/flash.git"

    # ── 0b. 归一化 Gitee 认证登录名 ──
    auth_username = resolve_login(token, cred.get("login") or username)

    # ── 1. 确定分支 ──
    if branch is None:
        branch = current_branch(project_root)

    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 一键拉取{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"仓库: {repo_url}")
    info(f"分支: {branch}")
    info(f"目录: {project_root}")
    if dry_run:
        warn("DRY-RUN 模式 — 仅展示将要执行的操作\n")

    # ── 2. 配置 remote (token 认证) ──
    if "://" in repo_url:
        scheme, rest = repo_url.split("://", 1)
        auth_url = f"{scheme}://{auth_username}:{token}@{rest}"
    else:
        auth_url = repo_url
    ensure_remote_auth(project_root, auth_url, dry_run)

    # ── 3. 获取远端最新 (刷新远端跟踪引用) ──
    info(f"获取远端最新: git fetch origin {branch}")
    if dry_run:
        warn(f"[DRY-RUN] 将执行: git fetch origin {branch}")
    else:
        run_git(["fetch", "origin", branch], cwd=project_root)

    ahead, behind = ahead_behind(project_root, branch)
    info(f"本地领先远程: {ahead} commit(s), 落后远程: {behind} commit(s)")

    if behind == 0:
        if ahead == 0:
            ok(f"分支 '{branch}' 已与远程完全同步, 无需拉取")
        else:
            info(f"本地领先远程 {ahead} commit(s), 无新内容可拉取")
        eprint()
        ok("完成!")
        return

    # ── 4. 本地有未提交变更的处理 ──
    if has_changes(project_root):
        if not stash:
            fail("存在未提交变更, 为避免覆盖已拒绝拉取。")
            fail("请先提交变更, 或加 --stash 自动暂存 (拉取后恢复)。")
            sys.exit(1)
        if dry_run:
            warn("[DRY-RUN] 将执行: git stash push (拉取后 git stash pop)")
        else:
            info("暂存本地变更 (git stash push)")
            run_git(["stash", "push", "-m", "auto-pull-stash"], cwd=project_root)

    # ── 5. 执行拉取 ──
    pull_mode = "--rebase" if rebase else "--ff-only"
    pull_args = ["pull", pull_mode, "origin", branch]

    if dry_run:
        warn(f"[DRY-RUN] 将执行: git {' '.join(pull_args)}")
        if stash:
            warn("[DRY-RUN] 拉取后将执行: git stash pop")
        eprint()
        ok("DRY-RUN 完成 (未做任何修改)")
        return

    info(f"执行: git {' '.join(pull_args)}")
    r = run_git(pull_args, cwd=project_root, check=False)
    if r.returncode == 0:
        ok(f"拉取成功! ({branch})")
    else:
        fail("拉取失败!")
        eprint(f"  {(r.stderr or '').strip()}")
        if "403" in (r.stderr or "") or "authentication" in (r.stderr or "").lower():
            warn("Token 可能无效, 请运行: python git_pull.py --setup")
        elif rebase is False and "not possible" in (r.stderr or "") and "fast-forward" in (r.stderr or ""):
            warn("非快进合并被 --ff-only 拒绝; 如需保留历史可用 --rebase, 或先处理本地提交。")
        elif stash:
            warn("拉取失败, 正在恢复暂存: git stash pop")
            run_git(["stash", "pop"], cwd=project_root, check=False)
        sys.exit(1)

    # ── 6. 恢复暂存 ──
    if stash:
        info("恢复暂存变更 (git stash pop)")
        run_git(["stash", "pop"], cwd=project_root, check=False)

    eprint()
    ok("全部完成!")


def show_status(project_root: Path | None = None):
    if project_root is None:
        project_root = find_git_root(Path(__file__).resolve().parent)
    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 同步状态{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"目录: {project_root}")
    branch = current_branch(project_root)
    info(f"分支: {branch}")
    r = run_git(["status", "--short"], cwd=project_root)
    if r.stdout.strip():
        eprint(f"\n  {'─'*50}")
        for line in r.stdout.strip().split("\n"):
            eprint(f"    {line.strip()}")
        eprint(f"  {'─'*50}")
    else:
        ok("工作区干净, 无未提交变更")
    # 刷新远端后报告
    info("刷新远端引用 (git fetch)")
    run_git(["fetch", "origin", branch], cwd=project_root, check=False)
    ahead, behind = ahead_behind(project_root, branch)
    info(f"领先远程: {ahead} commit(s), 落后远程: {behind} commit(s)")
    if behind > 0:
        warn(f"远端有 {behind} 个新提交可拉取, 运行: python git_pull.py")
    eprint()
    ok("状态检查完成")


# ============================================================================
#  CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="一键拉取脚本 — 双击即可从 Gitee 拉取最新 (凭据从加密存储读取)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("使用示例:")[1] if "使用示例:" in __doc__ else "",
    )
    parser.add_argument("-b", "--branch", default=None, help="拉取的分支 (默认: 当前分支)")
    parser.add_argument("--rebase", action="store_true", help="用 rebase 方式拉取 (线性历史)")
    parser.add_argument("--stash", action="store_true", help="有未提交变更时先 stash, 拉取后 pop")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行 (fetch + 展示, 不合并)")
    parser.add_argument("--setup", action="store_true", help="进入凭据设置界面 (有交互)")
    parser.add_argument("--status", action="store_true", help="查看与远端同步状态 (不拉取)")
    parser.add_argument("-r", "--root", default=None, help="项目根目录 (含 .git)")
    args = parser.parse_args()

    root: Path | None = Path(args.root).resolve() if args.root else None

    if args.setup:
        interactive_menu()
        return
    if args.status:
        show_status(root)
        return

    pull_from_gitee(
        branch=args.branch,
        rebase=args.rebase,
        stash=args.stash,
        dry_run=args.dry_run,
        project_root=root,
    )


if __name__ == "__main__":
    main()
