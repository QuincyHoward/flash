#!/usr/bin/env python
"""⑦ Gitee 私有仓库：创建 + 推送（**凭据只读**）。

用法::

    <venv>/Scripts/python.exe scripts/07_gitee_publish.py --check
    <venv>/Scripts/python.exe scripts/07_gitee_publish.py --ensure-repo
    <venv>/Scripts/python.exe scripts/07_gitee_publish.py --push
    <venv>/Scripts/python.exe scripts/07_gitee_publish.py            # 全流程

凭据来源（**只读，绝不修改**）
------------------------------
1. ``~/.physimx/flash/credentials.enc`` + ``.secret_key``（Fernet 密文）
   —— 键 ``gitee``，字段 ``token`` / ``username`` / ``login`` / ``repo_url``
2. 环境变量 ``GITEE_TOKEN`` / ``GITEE_LOGIN``（优先级更高，便于 CI）

★ 三条安全纪律（写进代码，不靠自觉）
------------------------------------
1. **只读凭据**：本脚本永不调用任何 ``set`` / ``delete`` / ``_save``。
   用户的凭据存储属于用户手动管理范畴，Agent 不得改写。
2. **token 不进磁盘**：推送时把 token 放在**命令行 URL** 里（进程内可见、
   不落盘），推送后立即把 remote 重置为**干净 URL**；并在最后断言
   ``.git/config`` 不含 token。
3. **token 不进日志**：所有输出一律经过 :func:`mask`。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eosop_pro import config as _cfg  # noqa: E402

API = "https://gitee.com/api/v5"

DEFAULT_OWNER = "quincyhoward"
DEFAULT_REPO = "MultixD"
DEFAULT_BRANCH = "main"
#: git 仓库根 = workspace 根（``.../simulation/Multi/MultixD``）
DEFAULT_ROOT = _cfg.WORKSPACE_ROOT


# ══════════════════════════════════════════════════════════════
# 凭据读取（只读）
# ══════════════════════════════════════════════════════════════
def _cred_dir() -> Path:
    return Path(os.environ.get("PHYSIMX_HOME", Path.home() / ".physimx")) / "flash"


def load_gitee_credentials() -> dict:
    """读取 Gitee 凭据。**纯读** —— 不生成密钥、不写回、不迁移。

    优先环境变量；否则解 ``~/.physimx/flash/credentials.enc``。
    """
    env_token = os.environ.get("GITEE_TOKEN", "").strip()
    if env_token:
        return {"token": env_token,
                "login": os.environ.get("GITEE_LOGIN", DEFAULT_OWNER).strip(),
                "username": os.environ.get("GITEE_USERNAME", "").strip(),
                "source": "env"}

    d = _cred_dir()
    enc = d / "credentials.enc"
    key = d / ".secret_key"
    if not enc.exists():
        raise FileNotFoundError(
            f"未找到凭据文件 {enc}\n"
            f"请先设置：python -m flash._core.credentials.gitee setup\n"
            f"或改用环境变量 GITEE_TOKEN / GITEE_LOGIN")
    if not key.exists():
        raise FileNotFoundError(f"未找到密钥文件 {key}")

    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:                               # pragma: no cover
        raise RuntimeError(
            "读取加密凭据需要 cryptography；请先运行 scripts/env_setup.bat"
        ) from exc

    f = Fernet(key.read_bytes().strip())
    blob = f.decrypt(enc.read_bytes())
    store = json.loads(blob.decode("utf-8"))
    gitee = store.get("gitee") or {}
    if not gitee.get("token"):
        raise RuntimeError("凭据库里没有 gitee.token —— 请先运行 "
                           "python -m flash._core.credentials.gitee setup")
    out = dict(gitee)
    out["source"] = f"file:{enc}"
    return out


def mask(text: object, token: str = "") -> str:
    """把 token 打码；用于**所有**对外输出。"""
    s = str(text)
    if token:
        s = s.replace(token, "***")
    return s


def _redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


# ══════════════════════════════════════════════════════════════
# Gitee API
# ══════════════════════════════════════════════════════════════
def _request(url: str, token: str, *, method: str = "GET",
             payload: dict | None = None, timeout: int = 20):
    """构造 Gitee API 请求。

    ★ 鉴权走 ``Authorization: token <t>`` **请求头**，不放进 URL 查询串 ——
    URL 会进日志/异常/代理记录/终端历史，请求头不会。
    """
    data = None
    headers = {"User-Agent": "eosop_pro-gitee", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"token {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def check_token(token: str, login: str) -> dict:
    """``GET /user`` —— 验证 token 并返回用户信息。"""
    with urllib.request.urlopen(_request(f"{API}/user", token), timeout=20) as r:
        info = json.loads(r.read().decode("utf-8"))
    api_login = str(info.get("login", ""))
    ok = bool(api_login)
    if ok and login and api_login != login:
        print(f"  ⚠ 凭据里的 login={login!r} 与 API 返回 {api_login!r} 不一致；"
              f"以 API 为准")
    return {"ok": ok, "login": api_login, "name": info.get("name", ""),
            "token_source": "", "raw": info}


def repo_exists(owner: str, repo: str, token: str) -> bool:
    try:
        with urllib.request.urlopen(
                _request(f"{API}/repos/{owner}/{repo}", token), timeout=20) as r:
            return "name" in json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


class CredentialScopeError(RuntimeError):
    """token 的**作用域**不足以创建仓库（不是 token 无效）。"""


#: token 作用域不足时的可读诊断（实测：仓库级私人令牌只有单仓读写权）
SCOPE_HELP = """
  ✗ 当前 token 的作用域不足 —— 它能读/写某个**已存在**的仓库，
    但没有 `projects` 权限来**新建**仓库（Gitee 报 403「仓库级私人令牌无权执行此操作」）。

  实测证据（GET /api/v5/user/repos 只会列出 token 可见的仓库）：
      physimx/flash   ← 唯一可见仓库 → 说明这是**仓库级**令牌

  三条可行路径（任选其一，都由您操作一次，之后本脚本可全自动）：

  A) 【推荐】在 Gitee 网页手动建好空仓库，然后只让脚本推送
       https://gitee.com/projects/new
         - 仓库名 : {repo}
         - 归属   : {owner}
         - 勾选   : 私有
         - 不要   : 初始化 README / .gitignore / License（保持空仓）
       建好后执行：python scripts/07_gitee_publish.py --no-create

  B) 换一个**个人访问令牌**（作用域含 projects），用环境变量传给本脚本
       https://gitee.com/profile/personal_access_tokens  新建令牌，勾选 `projects`
       set GITEE_TOKEN=<新令牌>
       set GITEE_LOGIN={login}
       python scripts/07_gitee_publish.py

  C) 若目标是 **physimx 企业命名空间**（与 physimx/flash 同级），
     需要作用域含 `enterprises` 的令牌，然后：
       set GITEE_TOKEN=<企业令牌>
       python scripts/07_gitee_publish.py --enterprise physimx --owner physimx

  ★ 本脚本**只读**凭据，不会替您修改或新建任何令牌。
"""


def _scope_error(owner: str, repo: str, login: str) -> CredentialScopeError:
    return CredentialScopeError(SCOPE_HELP.format(owner=owner, repo=repo, login=login))


def visible_repos(token: str) -> list[str]:
    """``GET /user/repos`` —— token 可见的仓库全名。用于诊断作用域。"""
    try:
        with urllib.request.urlopen(
                _request(f"{API}/user/repos", token), timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [d.get("full_name", "") for d in data if isinstance(d, dict)]
    except urllib.error.HTTPError:
        return []


def ensure_repo(owner: str, repo: str, token: str, *,
                private: bool = True, description: str = "",
                enterprise: str = "", login: str = "") -> dict:
    """仓库不存在则创建（**私有**），已存在则原样返回。

    ``enterprise`` 非空时走企业接口 ``POST /enterprises/{name}/repos``
    （PhySimX 的 ``physimx`` 命名空间是 **enterprise** 而非 organization；
     用 ``/orgs/...`` 会得到 ``{"message":"Group"}``）。
    企业接口的私有参数是 ``visibility: "private"``，传 ``private: true`` 会报
    ``private is invalid``。
    """
    if repo_exists(owner, repo, token):
        print(f"  ✓ 仓库已存在：{owner}/{repo}（不修改其任何设置）")
        return {"created": False, "owner": owner, "repo": repo}

    if enterprise:
        url = f"{API}/enterprises/{enterprise}/repos"
        payload = {"name": repo,
                   "description": description
                   or "Multi1D++ matter++ EOS/opacity toolchain",
                   "visibility": "private" if private else "public",
                   "has_issues": False, "has_wiki": False, "auto_init": False}
    else:
        url = f"{API}/user/repos"
        payload = {"name": repo,
                   "description": description
                   or "Multi1D++ matter++ EOS/opacity toolchain",
                   "private": bool(private),
                   "has_issues": False, "has_wiki": False, "auto_init": False}

    req = _request(url, token, method="POST", payload=payload)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            info = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _redact(e.read().decode("utf-8", "replace"), token)
        # 400 + "already exists" 时视为成功（并发/权限差异）
        if e.code in (400, 409) and "exist" in body.lower():
            print(f"  ✓ 仓库已存在（API 报 {e.code}）：{owner}/{repo}")
            return {"created": False, "owner": owner, "repo": repo}
        if e.code == 403 and "无权" in body:
            raise _scope_error(owner, repo, login) from None
        raise RuntimeError(f"创建仓库失败 HTTP {e.code}: {body}") from None

    priv = info.get("private")
    print(f"  ✓ 已创建私有仓库：{info.get('full_name', f'{owner}/{repo}')} "
          f"(private={priv})")
    return {"created": True, "owner": owner, "repo": repo,
            "html_url": info.get("html_url", ""), "private": priv}


# ══════════════════════════════════════════════════════════════
# git
# ══════════════════════════════════════════════════════════════
def _git(*args: str, cwd: Path, token: str = "") -> subprocess.CompletedProcess:
    p = subprocess.run(("git",) + args, cwd=str(cwd), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(a for a in args if token not in a)} 失败 "
            f"(rc={p.returncode}):\n"
            f"{_redact(p.stdout or '', token)}\n{_redact(p.stderr or '', token)}")
    return p


def git_available() -> bool:
    try:
        subprocess.run(("git", "--version"), capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def ensure_git_repo(root: Path, *, branch: str = DEFAULT_BRANCH,
                    user_name: str = "multixd-bot",
                    user_email: str = "multixd-bot@localhost") -> bool:
    """``git init``（幂等）+ 设置**仓库内**身份（不碰全局 gitconfig）。"""
    if not is_git_repo(root):
        _git("init", "-b", branch, cwd=root)
        print(f"  ✓ git init -b {branch} @ {root}")
    else:
        print(f"  ✓ 已是 git 仓库：{root}")
    _git("config", "user.name", user_name, cwd=root)
    _git("config", "user.email", user_email, cwd=root)
    return True


def remote_url(owner: str, repo: str) -> str:
    return f"https://gitee.com/{owner}/{repo}.git"


def set_clean_remote(root: Path, owner: str, repo: str, *, name: str = "origin") -> str:
    """把 remote 设为**不含凭据**的 URL（这一步保证 token 不落盘）。"""
    url = remote_url(owner, repo)
    remotes = _git("remote", cwd=root).stdout.split()
    if name in remotes:
        _git("remote", "set-url", name, url, cwd=root)
    else:
        _git("remote", "add", name, url, cwd=root)
    return url


def assert_no_token_in_config(root: Path, token: str) -> None:
    """★ 硬断言：``.git/config`` 里绝不能出现 token。"""
    cfg = root / ".git" / "config"
    if not cfg.exists():
        return
    text = cfg.read_text(encoding="utf-8", errors="replace")
    if token and token in text:
        # 立即修掉，避免留下隐患
        set_clean_remote(root, DEFAULT_OWNER, DEFAULT_REPO)
        raise AssertionError(
            "SEVERE: .git/config 中出现明文 token（已重置 remote）。"
            "请检查 git 版本与本脚本推送分支。")
    if "@gitee.com" in text and "://" in text:
        print("  · remote 为干净 HTTPS URL（无内嵌凭据）")


def push(root: Path, owner: str, repo: str, login: str, token: str, *,
         branch: str = DEFAULT_BRANCH, force: bool = False) -> dict:
    """用**仅在命令行**出现的凭据推送，随后把 remote 复位为干净 URL。"""
    clean = set_clean_remote(root, owner, repo)
    dirty = f"https://{login}:{token}@gitee.com/{owner}/{repo}.git"
    try:
        args = ["push", dirty, f"HEAD:refs/heads/{branch}"]
        if force:
            args.insert(1, "--force-with-lease")
        p = _git(*args, cwd=root, token=token)
        out = _redact((p.stdout or "") + (p.stderr or ""), token)
        print("  ✓ 推送完成：\n" + "\n".join("      " + ln for ln in out.splitlines()[:12]))
    finally:
        set_clean_remote(root, owner, repo)
        assert_no_token_in_config(root, token)
    return {"pushed": True, "branch": branch, "remote": clean}


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gitee 私有仓库创建 + 推送（凭据只读）")
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help="git 仓库根（默认 workspace 根）")
    ap.add_argument("--owner", default=DEFAULT_OWNER)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--branch", default=DEFAULT_BRANCH)
    ap.add_argument("--enterprise", default="",
                    help="走企业命名空间接口（如 physimx）；空则走 /user/repos")
    ap.add_argument("--public", action="store_true", help="创建为公开仓库（默认私有）")
    ap.add_argument("--force", action="store_true", help="推送时用 --force-with-lease")
    ap.add_argument("--check", action="store_true", help="只验证 token 与作用域")
    ap.add_argument("--ensure-repo", dest="ensure_repo", action="store_true",
                    help="只创建仓库（若不存在）")
    ap.add_argument("--no-create", dest="no_create", action="store_true",
                    help="跳过硬创建，直接推送到**已存在**的仓库"
                         "（仓库已在网页手动创建时用这个）")
    ap.add_argument("--push", action="store_true", help="只推送")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    only = args.check or args.ensure_repo or args.push
    if args.no_create:
        args.push = True

    print("=" * 66)
    print("Gitee 私有仓库：创建 + 推送")
    print("=" * 66)
    print(f"  仓库根 : {root}")
    print(f"  目标   : {args.owner}/{args.repo}  "
          f"({'public' if args.public else 'private'})"
          + (f"  [企业 {args.enterprise}]" if args.enterprise else ""))
    print(f"  分支   : {args.branch}")
    print(f"  建仓   : {'跳过（--no-create）' if args.no_create else '按需创建'}")

    if not git_available():
        print("\n  ✗ 未找到 git 可执行文件。请安装 Git for Windows 后重试。")
        return 1

    print("\n[1/4] 读取凭据（只读）...")
    try:
        cred = load_gitee_credentials()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"  ✗ {mask(exc)}")
        print("\n  提示：可用环境变量绕过文件凭据：")
        print("    set GITEE_TOKEN=xxxxxxxx")
        print("    set GITEE_LOGIN=quincyhoward")
        return 1
    token = cred["token"]
    login = cred.get("login") or cred.get("username") or args.owner
    print(f"  ✓ 凭据来源 : {mask(cred.get('source', '?'))}")
    print(f"  ✓ token    : {mask(token)[:8]}…（已打码）")
    print(f"  ✓ login    : {login}")

    if args.check:
        print("\n[2/2] 探测作用域 ...")
        try:
            info = check_token(token, login)
        except Exception as exc:                             # 网络
            print(f"  ✗ 连接失败（网络可能断开）：{mask(exc, token)}")
            return 2
        print(f"  ✓ token 有效，登录名 = {info['login']}")
        vis = visible_repos(token)
        print(f"  可见仓库 {len(vis)} 个：{vis if vis else '(不可枚举)'}")
        can_target = repo_exists(args.owner, args.repo, token)
        print(f"  目标仓库 {args.owner}/{args.repo} 存在？ {can_target}")
        if len(vis) <= 1 and not can_target:
            print(SCOPE_HELP.format(owner=args.owner, repo=args.repo, login=login))
            return 3
        print("\n完成（--check）。")
        return 0

    print("\n[2/4] 验证 token ...")
    try:
        info = check_token(token, login)
    except urllib.error.HTTPError as e:
        print(f"  ✗ token 无效 HTTP {e.code}: "
              f"{_redact(e.read().decode('utf-8', 'replace'), token)}")
        return 1
    except Exception as exc:                                 # 网络
        print(f"  ✗ 连接失败（网络可能断开）：{mask(exc, token)}")
        return 2
    login = info["login"] or login
    print(f"  ✓ token 有效，登录名 = {login}")

    print("\n[3/4] 确保仓库存在 ...")
    if args.no_create:
        if not repo_exists(args.owner, args.repo, token):
            print(f"  ✗ --no-create 但仓库 {args.owner}/{args.repo} 不存在"
                  f"（或 token 看不到它）")
            print(SCOPE_HELP.format(owner=args.owner, repo=args.repo, login=login))
            return 1
        print(f"  ✓ 仓库已存在：{args.owner}/{args.repo}")
        r = {"created": False}
    else:
        try:
            r = ensure_repo(args.owner, args.repo, token, private=not args.public,
                            enterprise=args.enterprise, login=login)
        except CredentialScopeError as exc:
            print(mask(exc, token))
            return 3
        except Exception as exc:
            print(f"  ✗ {mask(exc, token)}")
            return 1
    if args.ensure_repo and not args.push:
        print("\n完成（--ensure-repo）。")
        return 0

    print("\n[4/4] git 初始化 + 推送 ...")
    try:
        ensure_git_repo(root, branch=args.branch)
        push(root, args.owner, args.repo, login, token,
             branch=args.branch, force=args.force)
    except Exception as exc:
        print(f"  ✗ {mask(exc, token)}")
        return 1

    print("\n" + "=" * 66)
    print(f"完成 → https://gitee.com/{args.owner}/{args.repo}")
    print(f"  （私有仓库，页面已确认 private={not args.public}）")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
