#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键推送脚本 (One-click Git push to Gitee)
==========================================

定位: flash/scripts/03_git_publish/git_push.py
双击 git_push.bat 即可运行: 自动读取加密凭据 → 自动提交 → 推送到 Gitee。

设计约束 (强制):
  * 任何密码 / 账户 / token 都 **绝不硬编码** 到本文件。
  * 所有敏感信息均通过专用函数 flash._core.credentials.get_credential_manager()
    读取加密存储 (~/.physimx/flash/credentials.enc, Fernet 对称加密)。
  * 认证 URL 仅在运行时由凭据动态拼装, 且 credential.helper / askPass 被禁用,
    任何环境都不会弹出凭据输入框。

使用示例:
  python git_push.py              # 双击/默认: 自动提交 + 推送到当前分支
  python git_push.py -m "msg"     # 自定义提交信息
  python git_push.py -b main      # 推送到指定分支
  python git_push.py -f           # 强制推送
  python git_push.py -n           # dry-run (只展示不执行)
  python git_push.py --status     # 查看 git 状态 (不推送)
  python git_push.py --setup      # 进入凭据设置界面 (唯一需要交互的选项)

钩子机制 (通过 git 命令自动触发):
  - git commit → pre-commit: Black 格式检查 + 导入检查
  - git push   → pre-push:   框架 pytest 测试
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

# ============================================================================
#  Bootstrap: 定位 flash 项目根 (含 pyproject.toml 的目录)
#  使 flash 包可被导入 (flash/_core/credentials)。脚本可独立搬迁。
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
# ★ 依赖自检: 凭据库是 Fernet 加密存储, 需要 cryptography。该包**惰性导入**
#   (在 get_credential_manager() 内部), 所以必须在这里显式探测, 否则用户只会
#   看到调用深处的裸 ImportError。缺失时给出可直接照做的提示。
try:
    from flash._core.credentials import get_credential_manager, interactive_menu
    import cryptography  # noqa: F401
except ModuleNotFoundError as _exc:
    if "cryptography" in str(_exc):
        sys.exit(
            "\n  [X] 当前解释器缺少依赖 cryptography (凭据库为 Fernet 加密存储)。\n"
            f"      正在使用的解释器: {sys.executable}\n"
            "      请改用含该依赖的解释器运行, 或在当前解释器上安装:\n"
            f'        "{sys.executable}" -m pip install cryptography\n'
        )
    raise

# 同目录的认证工具: credential helper 统一入口 (避免与 git_pull.py 各写一份)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from _git_auth import auth_prefix, ensure_clean_remote  # noqa: E402


# ============================================================================
#  颜色辅助 (输出到 stderr, 不影响 stdout 捕获)
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
        fail("请先运行: python git_push.py --setup")
        sys.exit(1)
    # 兜底默认值由凭据动态提供, 不写死
    cred.setdefault("username", "")
    cred.setdefault("login", cred.get("username", ""))
    cred.setdefault("repo_url", "")
    return cred


def resolve_login(token: str, fallback: str) -> str:
    """Gitee 无交互直连需用 login (认证登录名), 显示名会 403。

    仅在凭据缺 login 时查询 API 获取; 否则直接返回凭据中的值。
    返回空串表示获取失败 (调用方回退到 fallback)。
    """
    if fallback:
        return fallback
    if not token:
        return ""
    import json
    import urllib.request
    try:
        # ★ 鉴权走请求头，token 不进 URL（URL 会留在日志/异常信息里）
        url = "https://gitee.com/api/v5/user"
        req = urllib.request.Request(url, headers={
            "User-Agent": "flash-git-push",
            "Authorization": f"token {token}",
        })
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
    """运行 git 命令 (shell=False, 参数列表, 强制禁用 credential 弹窗)。

    注入 -c credential.helper= 与 -c core.askPass= 确保任何环境都不弹出
    凭据输入框; 认证完全依赖 remote URL 中嵌入的 login:token。
    传入字符串时按 shlex 切分 (仅用于无动态引号场景)。
    """
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
    """向上查找含 .git 的目录。"""
    cur = start.resolve()
    for _ in range(10):
        if (cur / ".git").exists():
            return cur
        if cur == cur.parent:
            break
        cur = cur.parent
    return start.resolve()


def has_changes(cwd: Path) -> bool:
    r = run_git(["status", "--porcelain"], cwd=cwd)
    return bool(r.stdout.strip())


def count_ahead(cwd: Path, branch: str) -> int:
    r = run_git(["rev-list", "--count", f"origin/{branch}..HEAD"], cwd=cwd, check=False)
    if r.returncode == 0 and r.stdout.strip():
        return int(r.stdout.strip())
    return 0


def auto_commit_message(cwd: Path) -> str:
    """根据 git status --short 自动生成提交信息。"""
    r = run_git(["status", "--short"], cwd=cwd)
    lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
    if not lines:
        return "Auto commit [no changes detected]"
    added = sum(1 for l in lines if l.startswith("??") or l.startswith("A"))
    modified = sum(1 for l in lines if l.startswith("M"))
    deleted = sum(1 for l in lines if l.startswith("D"))
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
    filenames = [l.split()[-1] for l in lines[:3]]
    ts = time.strftime("%Y-%m-%d %H:%M")
    fstr = ", ".join(filenames)
    if len(filenames) < len(lines):
        fstr += f" (+{len(lines) - len(filenames)} more)"
    return f"auto({','.join(parts)}): {fstr} [{ts}]"


def input_with_timeout(prompt: str, timeout: float = 5.0) -> str | None:
    """非交互环境下直接返回 None; 交互终端下等待 timeout 秒可选输入。"""
    if not sys.stdin.isatty():
        return None
    try:
        print(prompt, flush=True)
    except Exception:
        return None

    bucket: dict = {}

    def _reader():
        try:
            bucket["val"] = input()
        except EOFError:
            bucket["val"] = None
        except Exception:
            bucket["val"] = None

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout)
    return bucket.get("val") if not t.is_alive() else None


# ============================================================================
#  核心: 一键推送
# ============================================================================

def push_to_gitee(branch=None, force=False, commit_msg=None, dry_run=False,
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
        r = run_git(["branch", "--show-current"], cwd=project_root)
        branch = r.stdout.strip() or "master"

    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 一键推送{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"仓库: {repo_url}")
    info(f"分支: {branch}")
    info(f"目录: {project_root}")

    if dry_run:
        warn("DRY-RUN 模式 — 仅展示将要执行的操作\n")

    # ── 2. 配置 remote：origin **始终指向不含凭据的干净 URL** ──
    #   ★★ 认证由同目录的 credential helper 在**推送那一刻**经管道提供，
    #      **绝不写进 .git/config** —— 否则 token 会以明文长期落盘。
    #      （历史实现曾在此执行 `git remote set-url origin <user>:<token>@…`，
    #        导致每次推送都把明文 token 写进配置；已修正。）
    info("确保 origin 指向不含凭据的 URL（清除历史内嵌 token）")
    ensure_clean_remote(project_root, repo_url, run_git, dry_run=dry_run)

    # 下面这段认证 URL 仅作 helper 缺失时的**回退**，正常路径不会用到。
    if "://" in repo_url:
        scheme, rest = repo_url.split("://", 1)
        auth_url = f"{scheme}://{auth_username}:{token}@{rest}"
    else:
        auth_url = repo_url

    # ── 3. 自动提交 ──
    if has_changes(project_root):
        if dry_run:
            warn(f"[DRY-RUN] 将执行: git add -A && git commit -m '{commit_msg or '(auto)'}'")
        else:
            if commit_msg is None:
                user_msg = input_with_timeout(
                    "  (可选) 输入提交信息, 5 秒内无输入将自动生成: ", timeout=5.0)
                if user_msg and user_msg.strip():
                    commit_msg = user_msg.strip()
            msg = commit_msg if commit_msg else auto_commit_message(project_root)
            info(f"提交信息: {msg}")
            run_git(["add", "-A"], cwd=project_root)
            run_git(["commit", "-m", msg], cwd=project_root)
            ok("提交成功!")
    else:
        info("没有未提交的变更")

    # ── 4. 推送 ──
    ahead = count_ahead(project_root, branch)
    if ahead == 0 and not has_changes(project_root) and not force:
        info(f"分支 '{branch}' 已与远程同步, 无需推送")
        eprint()
        ok("完成!")
        return

    # ★ 认证：用同目录的 credential helper。
    #   凭据由 helper 从加密库读取、经**管道**交给 git ——
    #   既不写入 .git/config，也不出现在命令行参数里（`ps` 看不到）。
    #   （对比：把认证 URL 当 push 参数虽然不落盘，但 token 会进 argv。）
    prefix = auth_prefix()
    if not prefix:
        warn("未找到 credential helper（_git_auth.HELPER_NAME），回退到认证 URL 方式")
        warn("  回退方式会把 token 放进命令行参数，建议尽快修复 helper 缺失问题。")

    push_target = "origin" if prefix else (auth_url if auth_url != repo_url else "origin")
    push_args = prefix + ["push", push_target, branch]
    if force:
        push_args.append("--force")
        warn("强制推送模式!")

    if dry_run:
        warn(f"[DRY-RUN] 将执行: git -c credential.helper=<helper> push {push_target} {branch}"
             + (" --force" if force else ""))
    else:
        info(f"执行: git push {push_target} {branch}"
             + (" --force" if force else "") + "   (凭据经 credential helper 管道传递)")
        r = run_git(push_args, cwd=project_root, check=False)
        if r.returncode == 0:
            ok(f"推送成功! ({branch})")
        else:
            fail("推送失败!")
            stderr = (r.stderr or "").strip()
            eprint(f"  {stderr}")
            if "403" in stderr or "authentication" in stderr.lower():
                warn("Token 可能无效, 请运行: python git_push.py --setup")
            elif "no upstream" in stderr.lower():
                warn(f"分支未设置上游, 尝试: git push --set-upstream origin {branch}")
            sys.exit(1)

    eprint()
    ok("全部完成!")


def show_status(project_root: Path | None = None):
    if project_root is None:
        project_root = find_git_root(Path(__file__).resolve().parent)
    eprint(f"\n  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  Git 状态检查{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"目录: {project_root}")
    r = run_git(["branch", "--show-current"], cwd=project_root)
    branch = r.stdout.strip() or "(detached HEAD)"
    info(f"分支: {branch}")
    r = run_git(["status", "--short"], cwd=project_root)
    if r.stdout.strip():
        eprint(f"\n  {'─'*50}")
        for line in r.stdout.strip().split("\n"):
            eprint(f"    {line.strip()}")
        eprint(f"  {'─'*50}")
    else:
        ok("工作区干净, 无未提交变更")
    r = run_git(["rev-list", "--count", "--left-right", "origin/HEAD...HEAD"],
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
        description="一键推送脚本 — 双击即可自动提交 + 推送到 Gitee (凭据从加密存储读取)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("使用示例:")[1] if "使用示例:" in __doc__ else "",
    )
    parser.add_argument("-b", "--branch", default=None, help="推送的分支 (默认: 当前分支)")
    parser.add_argument("-m", "--message", default=None, help="自定义提交信息 (默认: 自动生成)")
    parser.add_argument("-f", "--force", action="store_true", help="强制推送")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行 (只展示不执行)")
    parser.add_argument("--setup", action="store_true", help="进入凭据设置界面 (有交互)")
    parser.add_argument("--status", action="store_true", help="查看当前 git 状态 (不推送)")
    parser.add_argument("-r", "--root", default=None, help="项目根目录 (含 .git)")
    args = parser.parse_args()

    root: Path | None = Path(args.root).resolve() if args.root else None

    if args.setup:
        interactive_menu()
        return
    if args.status:
        show_status(root)
        return

    push_to_gitee(
        branch=args.branch,
        force=args.force,
        commit_msg=args.message,
        dry_run=args.dry_run,
        project_root=root,
    )


if __name__ == "__main__":
    main()
