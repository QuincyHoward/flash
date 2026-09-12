#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gitee HTTPS 认证的**统一入口** —— 凭据只经 credential helper 管道传递。

背景（为什么要有这个模块）
--------------------------
`git` 走 HTTPS 需要「用户名 + token」。历史上本项目用两种**都不安全**的做法：

| 做法 | token 落 `.git/config` | token 进 argv（`ps` 可见） |
|---|---|---|
| `https://<user>:<token>@host/...` 写进 remote URL | ❌ 明文长期落盘 | — |
| 把认证 URL 当 push/pull 的 URL 参数 | ✅ | ❌ |
| **credential helper（本模块）** | ✅ | ✅ |

第三种由 git 主动调用 helper：git 从 stdin 递来 `protocol=https` / `host=gitee.com`
等 `key=value` 行，helper 从加密库取凭据后从 stdout 回 `username=` / `password=`。
凭据全程只经过**管道**，既不落盘、也不出现在命令行参数里。

用法
----
    from _git_auth import auth_prefix, ensure_clean_remote

    ensure_clean_remote(project_root, repo_url)          # origin 保持无凭据 URL
    r = run_git(auth_prefix() + ["fetch", "origin", b])  # 网络命令带上 helper

★ `auth_prefix()` 里刻意先写一个空的 `credential.helper=`：它**清空** git 已有的
  helper 列表，保证只有本项目这一个 helper 生效（避免系统 GCM 弹窗/抢答）。
"""

from __future__ import annotations

import sys
from pathlib import Path

#: helper 文件名（与本模块同目录）
HELPER_NAME = "_git_credential_helper.py"


def helper_path() -> Path:
    """返回 credential helper 脚本的绝对路径。"""
    return Path(__file__).resolve().parent / HELPER_NAME


def auth_prefix() -> list[str]:
    """返回应注入到 git 命令**之前**的 `-c` 参数列表。

    helper 及其解释器都通过**绝对路径**引用；helper 缺失时返回空列表，
    调用方据此判定是否需要回退（且应显式警告，不要静默降级）。
    """
    hp = helper_path()
    if not hp.is_file():
        return []
    # 用当前解释器执行 helper：与调用方环境天然一致（凭据库需 cryptography）
    py = Path(sys.executable).as_posix()
    return [
        "-c", "credential.helper=",                       # 清空既有 helper（含 GCM）
        "-c", f'credential.helper=!"{py}" "{hp.as_posix()}"',  # 只留本项目的
    ]


def ensure_clean_remote(cwd: Path, repo_url: str, run_git, dry_run: bool = False) -> None:
    """确保 `origin` 指向**不含凭据**的 URL（幂等）。

    既用于首次添加 remote，也用于**清除历史遗留的内嵌 token**——
    旧版脚本会把 `https://<user>:<token>@...` 写进 `.git/config` 并长期留存。
    """
    r = run_git(["remote", "-v"], cwd=cwd, check=False)
    if "origin" not in (r.stdout or ""):
        if not dry_run:
            run_git(["remote", "add", "origin", repo_url], cwd=cwd)
    else:
        if not dry_run:
            run_git(["remote", "set-url", "origin", repo_url], cwd=cwd)
