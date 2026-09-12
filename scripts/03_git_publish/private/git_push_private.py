#!/usr/bin/env python3
"""
私有 Gitee 推送脚本 (独立于公开推送)
====================================

与 scripts/03_git_publish/git_push.py (推送到 physimx 公开仓) 完全分离:

  * 目标固定为私有备份仓 https://gitee.com/quincyhoward/flash.git
  * 认证凭据从 _core/credentials 加密存储读取 (token 不出现在仓库文件里)
  * token 经 base64 放在 `-c http.extraHeader` 中, 不写进 remote URL,
    也不持久化任何含 token 的 remote 配置, origin (公开仓) 不被触碰
  * 本文件是整个 flash 包中唯一允许出现 "quincyhoward" 用户名的地方

用法:
  python git_push_private.py              # 自动提交 + 推送到私有仓
  python git_push_private.py -m "msg"     # 自定义提交信息
  python git_push_private.py -b main      # 推指定分支 (默认当前分支)
  python git_push_private.py -f           # 强制推送
  python git_push_private.py -n           # dry-run (只展示不执行)
  python git_push_private.py --status     # 查看本地与私有仓差异 (不推送)
  python git_push_private.py --check      # 连通性检查 (ls-remote, 不推送)
"""

import argparse
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
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ★ 依赖自检: 凭据库是 Fernet 加密存储, 需要 cryptography。该包**惰性导入**
#   (在 get_credential_manager() 内部), 必须显式探测, 否则只会看到调用深处的裸 ImportError。
try:
    from flash._core.credentials import get_credential_manager
    import cryptography  # noqa: F401
except ModuleNotFoundError as _exc:
    if "cryptography" in str(_exc):
        sys.exit(
            "\n  [X] 当前解释器缺少依赖 cryptography (凭据库为 Fernet 加密存储)。\n"
            f"      正在使用的解释器: {sys.executable}\n"
            f'      请改用含该依赖的解释器, 或安装: "{sys.executable}" -m pip install cryptography\n'
        )
    raise

# 父目录的认证工具: credential helper 统一入口 (与 git_push/pull 共用一份实现)
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
from _git_auth import auth_prefix  # noqa: E402

# 私有目标仓 (全包唯一 quincyhoward 位置)
PRIVATE_REPO = "https://gitee.com/quincyhoward/flash.git"


def _git_auth_prefix() -> list[str]:
    """返回 credential helper 认证前缀 (§见父目录 _git_auth.py)。

    ★ 凭据由 helper 从加密库读取、经**管道**交给 git —— 既不写 .git/config、
      也不出现在命令行 argv 里。
      历史实现用 `-c http.extraHeader="Authorization: Basic <base64>"`：
      token 的 base64 会进 argv (`ps` 可见) 且 base64 可逆解码，已修正。
    """
    prefix = auth_prefix()
    if not prefix:
        raise RuntimeError(
            "未找到 credential helper —— 期望文件: "
            f"{Path(__file__).resolve().parent.parent / '_git_auth.py'}"
        )
    return prefix


def run_git(args, cwd: Path, check: bool = True, auth: bool = True):
    """运行 git 命令。

    ★ 一律 `shell=False` + 参数列表：避免经 cmd.exe/sh 拼接字符串带来的
      引号歧义与注入风险（历史实现用 shell=True 拼 `git commit -m "<msg>"`）。
      传入字符串时用 shlex 切分（能正确处理双引号包裹的段落）。
    """
    if isinstance(args, str):
        import shlex
        args = shlex.split(args)
    if args and args[0] == "git":
        args = args[1:]
    full = ["git"]
    if auth:
        full += _git_auth_prefix()
    full += ["-c", "core.askPass="] + list(args)
    result = subprocess.run(
        full, shell=False, cwd=cwd,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and result.returncode != 0:
        sys.stderr.write(f"[X] git 失败: {' '.join(list(args)[:6])}\n")
        sys.stderr.write(f"    {(result.stderr or result.stdout or '').strip()}\n")
        sys.exit(1)
    return result


def find_git_root(start_dir: Path) -> Path:
    current = start_dir.resolve()
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return start_dir.resolve()


def auto_commit_message(cwd: Path) -> str:
    r = run_git("git status --short", cwd, check=False)
    lines = [line.strip() for line in r.stdout.strip().split("\n") if line.strip()]
    if not lines:
        return "Auto commit [no changes detected]"
    added = sum(1 for l in lines if l.startswith("??") or l.startswith("A"))
    modified = sum(1 for l in lines if l.startswith("M"))
    deleted = sum(1 for l in lines if l.startswith("D"))
    parts = []
    if added:
        parts.append(f"+{added}")
    if modified:
        parts.append(f"~{modified}")
    if deleted:
        parts.append(f"-{deleted}")
    filenames = [line.split()[-1] for line in lines[:3]]
    ts = time.strftime("%Y-%m-%d %H:%M")
    file_str = ", ".join(filenames)
    if len(filenames) < len(lines):
        file_str += f" (+{len(lines) - len(filenames)} more)"
    return f"auto({','.join(parts)}): {file_str} [{ts}]"


def remote_sha(cwd: Path, branch: str) -> str | None:
    """查询私有仓 refs/heads/<branch> 的远端 SHA。"""
    r = run_git(f'ls-remote {PRIVATE_REPO} refs/heads/{branch}', cwd, check=False)
    if r.returncode == 0:
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == f"refs/heads/{branch}":
                return parts[0]
    return None


def push_private(branch, force, commit_msg, dry_run, project_root):
    r = run_git("git rev-parse --abbrev-ref HEAD", project_root)
    branch = branch or (r.stdout.strip() or "master")

    # 自动提交
    r = run_git("git status --short", project_root, check=False)
    has_changes = bool(r.stdout.strip())
    if has_changes:
        if dry_run:
            print("[DRY-RUN] 将自动提交全部变更")
        else:
            msg = commit_msg or auto_commit_message(project_root)
            print(f"提交: {msg}")
            run_git("git add -A", project_root)
            run_git(["commit", "-m", msg], project_root)
    else:
        print("无未提交变更")

    # 推送 (带认证, 一次性 URL, 不改 remote)
    push_cmd = f"push {PRIVATE_REPO} {branch}"
    if force:
        push_cmd += " --force"
    print(f"推送到私有仓: {PRIVATE_REPO} (branch={branch})")
    if dry_run:
        print(f"[DRY-RUN] git {push_cmd}")
        return
    r = run_git(push_cmd, project_root, check=False)
    if r.returncode == 0:
        print("推送成功!")
    else:
        sys.stderr.write(f"推送失败:\n  {(r.stderr or r.stdout or '').strip()}\n")
        sys.exit(1)


def show_status(project_root):
    r = run_git("git rev-parse --abbrev-ref HEAD", project_root)
    branch = r.stdout.strip() or "master"
    print(f"分支: {branch}")
    r = run_git("git status --short", project_root, check=False)
    if r.stdout.strip():
        print("本地变更:")
        for line in r.stdout.strip().split("\n"):
            print(f"  {line.strip()}")
    else:
        print("工作区干净")
    remote = remote_sha(project_root, branch)
    if remote is None:
        print(f"私有仓无分支 {branch} (需首次推送)")
        return
    local = run_git("git rev-parse HEAD", project_root, check=False).stdout.strip()
    ahead = run_git(f"git rev-list --count {remote}..HEAD", project_root, check=False).stdout.strip()
    behind = run_git(f"git rev-list --count HEAD..{remote}", project_root, check=False).stdout.strip()
    print(f"私有仓 {branch}: {remote[:10]} | 领先 {ahead} | 落后 {behind} | 本地 {local[:10]}")


def main():
    parser = argparse.ArgumentParser(
        description="私有 Gitee 推送 — 推送私有备份仓 (读加密 token, 不改公开 remote)",
    )
    parser.add_argument("-b", "--branch", default=None, help="推送的分支 (默认: 当前分支)")
    parser.add_argument("-m", "--message", default=None, help="自定义提交信息")
    parser.add_argument("-f", "--force", action="store_true", help="强制推送")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行 (只展示不执行)")
    parser.add_argument("--status", action="store_true", help="查看与私有仓差异 (不推送)")
    parser.add_argument("--check", action="store_true", help="连通性检查 (ls-remote)")
    args = parser.parse_args()

    project_root = find_git_root(Path(__file__).resolve().parent)
    print(f"仓库: {project_root}")

    if args.check:
        try:
            sha = remote_sha(project_root, "master")
            print(f"私有仓可达: {PRIVATE_REPO} (master={sha[:10] if sha else '(无)'})")
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"连通性检查失败: {exc}\n")
            sys.exit(1)
        return
    if args.status:
        show_status(project_root)
        return
    push_private(args.branch, args.force, args.message, args.dry_run, project_root)


if __name__ == "__main__":
    main()
