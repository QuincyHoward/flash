#!/usr/bin/env python3
"""
统一的 Git 推送脚本
=====================

双击执行流程:
  1. 从 _core/credentials 读取 Gitee 加密凭据
  2. 自动检测未提交变更 → 自动生成提交信息 → git add/commit (触发 pre-commit 钩子)
  3. git push 到远程仓库 (触发 pre-push 钩子)
  4. 全程无需手动输入

使用示例:
  python git_push.py              # 双击/默认: 自动提交 + 推送
  python git_push.py -m "msg"     # 自定义提交信息
  python git_push.py -b main      # 推送到指定分支
  python git_push.py -f           # 强制推送
  python git_push.py --tag v1.0.003   # 打标签 + 推送 (先跑测试)
  python git_push.py --setup      # 进入凭据设置界面 (有交互)
  python git_push.py --status     # 查看当前状态 (不推送)
  python git_push.py -n           # dry-run 模式 (只显示将要做的操作)

所有操作中, --setup 是唯一需要交互的选项, 其余均可双击/命令行一键执行。

钩子机制 (自动触发):
  - git commit → pre-commit: Black 格式检查 + 导入检查
  - git push   → pre-push:   框架 pytest 测试
  - --tag 模式 → 额外运行全局测试 (同 git-tag-with-test.sh)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ============================================================================
#  Bootstrap: find flash project root (独立包模式, 可任意搬迁)
# ============================================================================
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# 注: 旧版"runpy 转模块方式 + flash 目录别名"引导已废弃 (scripts/ 按功能分类后
# 不再存在 flash.scripts 模块路径)。直接脚本运行即可, 尾部 __main__ 会调用 main()。

# ============================================================================
#  从 _core/credentials 读取凭据 (使用模块化 API)
# ============================================================================
from flash._core.credentials import get_credential_manager, interactive_menu


# ============================================================================
#  辅助函数
# ============================================================================

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def eprint(*args, **kwargs):
    """彩色输出"""
    print(*args, **kwargs, file=sys.stderr)


def ok(msg: str):
    eprint(f"  {GREEN}✅{RESET} {msg}")


def info(msg: str):
    eprint(f"  {CYAN}ℹ️{RESET} {msg}")


def warn(msg: str):
    eprint(f"  {YELLOW}⚠️{RESET} {msg}")


def fail(msg: str):
    eprint(f"  {RED}❌{RESET} {msg}")


def run_git(cmd: str, cwd: Path | None = None, check: bool = True,
            capture: bool = True) -> subprocess.CompletedProcess:
    """执行 git 命令。返回 CompletedProcess 对象。

    显式指定 utf-8 编码避免 Windows 上 GBK 解码 UTF-8 输出时报错。

    无交互直连 (统一):
      所有 git 命令注入 `-c credential.helper=` 与 `-c core.askPass=`,
      命令行级禁用任何 credential helper (含 WorkBuddy PortableGit 的
      helper-selector 弹窗来源), 认证完全依赖 remote URL 中嵌入的
      login:token (由 push_to_gitee 统一设置)。任何环境都不会弹窗。
    """
    if cmd.startswith("git "):
        cmd = "git -c credential.helper= -c core.askPass= " + cmd[4:]
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=capture, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else "(no stderr)"
        fail(f"Git 命令失败: {cmd}")
        fail(f"  {err_msg}")
        sys.exit(1)
    return result


def find_git_root(start_dir: Path) -> Path:
    """向上查找包含 .git 的目录。"""
    current = start_dir.resolve()
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return start_dir.resolve()


def has_untracked_files(cwd: Path) -> bool:
    """检查是否有未跟踪的文件。"""
    r = run_git("git status --porcelain", cwd=cwd)
    return bool(r.stdout.strip())


def count_commits_ahead(cwd: Path, branch: str) -> int:
    """检查本地比远程多几个 commit。"""
    r = run_git(f"git rev-list --count origin/{branch}..HEAD", cwd=cwd, check=False)
    if r.returncode == 0 and r.stdout.strip():
        return int(r.stdout.strip())
    return 0


def auto_commit_message(cwd: Path) -> str:
    """根据 git status --short 自动生成提交信息。"""
    r = run_git("git status --short", cwd=cwd)
    lines = [line.strip() for line in r.stdout.strip().split("\n") if line.strip()]
    if not lines:
        return "Auto commit [no changes detected]"

    # 统计变更类型
    modified = sum(1 for l in lines if l.startswith("M") or l.startswith(" M"))
    added = sum(1 for l in lines if l.startswith("A") or l.startswith("??") or l.startswith("A "))
    deleted = sum(1 for l in lines if l.startswith("D") or l.startswith(" D"))
    renamed = sum(1 for l in lines if l.startswith("R"))

    parts = []
    if added:
        parts.append(f"+{added}")
    if modified:
        parts.append(f"~{modified}")
    if deleted:
        parts.append(f"-{deleted}")
    if renamed:
        parts.append(f"R{renamed}")

    # 提取文件名 (最多 3 个)
    filenames = []
    for line in lines:
        name = line.split()[-1] if len(line.split()) >= 2 else line
        filenames.append(name)
        if len(filenames) >= 3:
            break

    ts = time.strftime("%Y-%m-%d %H:%M")
    file_str = ", ".join(filenames)
    if len(filenames) < len(lines):
        file_str += f" (+{len(lines) - len(filenames)} more)"

    return f"auto({','.join(parts)}): {file_str} [{ts}]"


# ============================================================================
#  核心推送逻辑
# ============================================================================

def push_to_gitee(
    branch: str | None = None,
    force: bool = False,
    commit_msg: str | None = None,
    tag: str | None = None,
    dry_run: bool = False,
    project_root: Path | None = None,
):
    """执行完整推送流程 (自动提交 + 推送, 触发钩子)。"""
    if project_root is None:
        project_root = find_git_root(Path(__file__).resolve().parent)

    # ── 0. 读取凭据 ──
    cm = get_credential_manager()
    gitee_cred = cm.get("gitee")
    if not gitee_cred:
        fail("未找到 Gitee 凭据。请先运行: python git_push.py --setup")
        sys.exit(1)

    token = gitee_cred.get("token", "")
    username = gitee_cred.get("username", "")
    repo_url = gitee_cred.get("repo_url", f"https://gitee.com/{username}/flash.git")

    # ── 0b. Gitee 认证用户名归一化 ──
    # Gitee git-over-HTTPS 认证使用登录名 (login), 而非显示名 (name)。
    # 凭据中可能只存了显示名 (如 "QuincyHoward"), 直接用于认证 URL 会 403
    # "The token username invalid"。优先使用凭据中的 login 字段,
    # 缺失时查询 API 获取真实 login。
    auth_username = gitee_cred.get("login") or username
    if token and not gitee_cred.get("login"):
        try:
            import urllib.request
            import json as _json
            _api_req = urllib.request.Request(
                f"https://gitee.com/api/v5/user?access_token={token}",
                headers={"User-Agent": "flash-git-push"},
            )
            _resp = urllib.request.urlopen(_api_req, timeout=15)
            _data = _json.loads(_resp.read().decode("utf-8"))
            _login = _data.get("login")
            if _login:
                auth_username = _login
                if auth_username != username:
                    info(f"Gitee 登录名: {auth_username} (凭据显示名: {username})")
        except Exception as _e:  # noqa: BLE001
            warn(f"无法查询 Gitee 登录名 (使用凭据用户名): {_e}")

    # ── 1. 确定分支 ──
    if branch is None:
        r = run_git("git branch --show-current", cwd=project_root)
        branch = r.stdout.strip()
        if not branch:
            branch = "master"

    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 推送工具{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"仓库: {repo_url}")
    info(f"用户: {username} (认证: {auth_username})")
    info(f"分支: {branch}")
    info(f"目录: {project_root}")

    if dry_run:
        warn("DRY-RUN 模式 — 仅展示将要执行的操作\n")

    # ── 2. 配置 git remote (使用 token 认证) ──
    if "://" in repo_url:
        parts = repo_url.split("://")
        auth_url = f"{parts[0]}://{auth_username}:{token}@{parts[1]}"
    else:
        auth_url = repo_url

    r = run_git("git remote -v", cwd=project_root, check=False)
    if "origin" not in r.stdout:
        info("添加远程仓库 origin")
        if not dry_run:
            run_git(f'git remote add origin "{auth_url}"', cwd=project_root)
    else:
        info("更新远程仓库 URL (token 认证)")
        if not dry_run:
            run_git(f'git remote set-url origin "{auth_url}"', cwd=project_root)

    # ── 3. 检查并提交 ──
    has_changes = has_untracked_files(project_root)
    if has_changes:
        if dry_run:
            warn(f"[DRY-RUN] 将执行: git add -A && git commit -m '{commit_msg or '(auto)'}'")
        else:
            ok("发现未提交变更，执行自动提交...")

            # 自动生成提交信息
            msg = commit_msg if commit_msg else auto_commit_message(project_root)
            info(f"提交信息: {msg}")

            # git add + commit (触发 pre-commit 钩子)
            run_git("git add -A", cwd=project_root)
            run_git(f'git commit -m "{msg}"', cwd=project_root)
            ok("提交成功!")
    else:
        info("没有未提交的变更")

    # ── 4. 打标签 (可选, 触发全局测试) ──
    if tag:
        eprint()
        info(f"准备打标签: {tag}")
        # ── 委托 run_global_tests.py 执行全局测试 ──
        test_script = project_root / "scripts" / "run_global_tests.py"
        if not test_script.exists():
            fail(f"测试脚本不存在: {test_script}")
            sys.exit(1)

        eprint()
        info("运行全局测试 (run_global_tests.py)...")
        if not dry_run:
            # 设置 PYTHONPATH, 复用 git_push 的环境变量
            test_env = os.environ.copy()
            parent_path = str(project_root.parent)
            existing = test_env.get("PYTHONPATH", "")
            paths = [p for p in existing.split(";") if p] if existing else []
            if parent_path not in paths:
                paths.insert(0, parent_path)
            test_env["PYTHONPATH"] = ";".join(paths)

            r = subprocess.run(
                [sys.executable, str(test_script)],
                cwd=project_root, capture_output=False,
                encoding="utf-8", errors="replace",
                env=test_env,
            )
            if r.returncode != 0:
                fail("全局测试失败, 标签操作中止")
                sys.exit(1)
            ok("全局测试通过!")
            eprint()

        # ── 创建本地标签 ──
        if dry_run:
            info(f"[DRY-RUN] 将创建标签: {tag}")
        else:
            run_git(f'git tag -a {tag} -m "{tag}"', cwd=project_root)
            ok(f"标签 {tag} 已创建")

    # ── 5. 执行推送 (触发 pre-push 钩子) ──
    ahead = count_commits_ahead(project_root, branch)
    if ahead == 0 and not has_changes and not force and not tag:
        info(f"分支 '{branch}' 已与远程同步, 无需推送")
        eprint()
        ok("完成!")
        return

    eprint()
    push_cmd = f"git push origin {branch}"
    if force:
        push_cmd += " --force"
        warn("强制推送模式!")

    if dry_run:
        warn(f"[DRY-RUN] 将执行: {push_cmd}")
    else:
        info(f"执行: {push_cmd}")
        r = run_git(push_cmd, cwd=project_root, check=False)
        if r.returncode == 0:
            ok(f"推送成功! ({branch})")
        else:
            fail(f"推送失败!")
            eprint(f"  {r.stderr.strip()}")
            if "403" in r.stderr or "authentication" in r.stderr.lower():
                warn("Token 可能无效, 请运行: python git_push.py --setup")
            elif "no upstream" in r.stderr.lower():
                warn(f"分支未设置上游, 尝试: git push --set-upstream origin {branch}")
            sys.exit(1)

    # ── 6. 如果同时打了标签, 推送标签 ──
    if tag and not dry_run:
        ok(f"推送标签: {tag}")
        run_git(f"git push origin {tag}", cwd=project_root, check=False)

    eprint()
    ok("全部完成!")


def show_status(project_root: Path | None = None):
    """显示当前 git 状态 (不推送)。"""
    if project_root is None:
        project_root = find_git_root(Path(__file__).resolve().parent)

    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 状态检查{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"目录: {project_root}")

    # 分支
    r = run_git("git branch --show-current", cwd=project_root)
    branch = r.stdout.strip() or "(detached HEAD)"
    info(f"分支: {branch}")

    # 状态
    r = run_git("git status --short", cwd=project_root)
    if r.stdout.strip():
        eprint(f"\n  {'─'*50}")
        eprint(f"  变更文件:")
        for line in r.stdout.strip().split("\n"):
            eprint(f"    {line.strip()}")
        eprint(f"  {'─'*50}")
    else:
        ok("工作区干净, 无未提交变更")

    # 远程同步状态
    r = run_git("git rev-list --count --left-right origin/HEAD...HEAD",
                cwd=project_root, check=False)
    if r.returncode == 0 and r.stdout.strip():
        parts = r.stdout.strip().split()
        ahead = parts[0] if len(parts) >= 1 else "?"
        behind = parts[1] if len(parts) >= 2 else "?"
        info(f"领先远程: {ahead} commit(s), 落后远程: {behind} commit(s)")

    eprint()
    ok("状态检查完成")


# ============================================================================
#  CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="统一的 Git 推送脚本 — 双击即可自动提交 + 推送",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python git_push.py                          # 默认: 自动提交 + 推送
  python git_push.py -m "fix: update params"  # 自定义提交信息
  python git_push.py -b main                  # 推送到 main 分支
  python git_push.py -f                       # 强制推送
  python git_push.py -n                       # dry-run 试运行
  python git_push.py --tag v1.0               # 打标签 + 推送 (先跑测试)
  python git_push.py --status                 # 查看状态 (不推送)
  python git_push.py --setup                  # 设置/更新凭据 (唯一需要交互)
        """,
    )
    parser.add_argument("-b", "--branch", default=None, help="推送的分支 (默认: 当前分支)")
    parser.add_argument("-m", "--message", default=None, help="自定义提交信息 (默认: 自动生成)")
    parser.add_argument("-f", "--force", action="store_true", help="强制推送")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行 (只展示不执行)")
    parser.add_argument("--tag", default=None, help="创建并推送标签 (例如 v1.0)")
    parser.add_argument("--setup", action="store_true", help="进入凭据设置界面 (有交互)")
    parser.add_argument("--status", action="store_true", help="查看当前 git 状态 (不推送)")
    parser.add_argument("-r", "--root", default=None, help="项目根目录 (包含 .git)")

    args = parser.parse_args()

    project_root: Path | None = None
    if args.root:
        project_root = Path(args.root).resolve()
    else:
        project_root = find_git_root(Path(__file__).resolve().parent)

    # --setup: 进入凭据管理
    if args.setup:
        interactive_menu()
        return

    # --status: 只看状态
    if args.status:
        show_status(project_root)
        return

    # 默认: 推送
    push_to_gitee(
        branch=args.branch,
        force=args.force,
        commit_msg=args.message,
        tag=args.tag,
        dry_run=args.dry_run,
        project_root=project_root,
    )


if __name__ == "__main__":
    main()
