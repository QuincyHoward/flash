#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paths.py — 全库统一路径/身份解析入口（硬编码唯一收纳处）。

背景（2026-10-27 全库硬编码审计，见仓库根《硬编码位置及修改计划.md》）：
  历史代码把 Windows 用户名、WorkBuddy 托管 Python、超算家目录、仓库绝对路径
  写散在各脚本/README/bat 中 ⇒ 换机器/换账号即失效，且公开仓库泄漏身份。
  本模块是这些值的**唯一**合法来源；新增代码禁止再写死。

约定（铁律）：
  * 本模块只依赖 stdlib（json/os/sys/pathlib），可被 deploy/ 下的独立脚本
    通过 ``sys.path.insert(0, str(repo_root()))`` 直接导入，无需安装 flash。
  * 用户名/家目录一律**运行期解析**，绝不作为字面量出现在仓库任何文件中。
  * 解析顺序统一为：环境变量 → ~/.physimx 配置 → 动态探测 → 显式报错。
    除 ``repo_root()`` 外没有"猜默认值"的路径 —— 静默猜错比报错更危险。

对外 API 一览：
  repo_root()            仓库根（由 __file__ 推导，机器无关）
  win_home()             Windows 用户家目录（Path.home()）
  managed_python()       WorkBuddy 托管 Python 解释器（用户名无关）
  win_home_in_wsl()      WSL 视角的 Windows 家目录（/mnt/c/Users/<user>）
  hpc_ssh_username()     超算 SSH 用户名（hpc_accounts.json）
  hpc_home()             超算家目录（env FLASH_HPC_HOME 或账户 remote_home 字段）
  hpc_home_required()    同上，但解析失败时给出可操作报错（推荐部署脚本使用）
  hpc_target_dirs()      超算部署目录三元组 (REMOTE_HOME, TARGET_DIR, PKG_DIR)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

__all__ = [
    "repo_root",
    "win_home",
    "managed_python",
    "win_home_in_wsl",
    "hpc_ssh_username",
    "hpc_home",
    "hpc_home_required",
    "hpc_target_dirs",
]

# ── 本地仓库 ────────────────────────────────────────────────

def repo_root() -> Path:
    """仓库根目录。由本文件位置推导（flash/_core/paths.py → parents[2]），
    与克隆位置/盘符/机器无关，替代一切写死的仓库绝对路径字面量。"""
    return Path(__file__).resolve().parents[2]


# ── Windows 本地环境 ────────────────────────────────────────

def win_home() -> Path:
    """当前用户 Windows 家目录（%USERPROFILE%），替代写死的 ``C:\\Users\\<用户名>``。"""
    return Path.home()


def managed_python() -> Path:
    """WorkBuddy 托管 Python 解释器（用户名无关）。

    解析顺序：
      1. 环境变量 ``FLASH_MANAGED_PYTHON``（显式指定，最高优先）；
      2. ``%USERPROFILE%\\.workbuddy\\binaries\\python\\envs\\default\\...``；
      3. ``%USERPROFILE%\\.workbuddy\\binaries\\python\\versions\\<ver>\\python.exe``
         （取版本号最大的一个）；
      4. 回退 ``sys.executable``（总能成立，保证调用方不崩）。
    """
    env = os.environ.get("FLASH_MANAGED_PYTHON")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    home = win_home()
    wb = home / ".workbuddy" / "binaries" / "python"
    if sys.platform == "win32":
        cand = wb / "envs" / "default" / "Scripts" / "python.exe"
        if cand.is_file():
            return cand
        versions = sorted(
            (p for p in (wb / "versions").glob("*/python.exe") if p.is_file()),
            key=lambda p: p.parent.name,
        )
        if versions:
            return versions[-1]
    # 非 Windows 或托管 Python 不存在：回退当前解释器
    return Path(sys.executable)


def win_home_in_wsl() -> str:
    """WSL 视角下的 Windows 家目录（如 ``/mnt/c/Users/<user>``）。

    用户名运行期探测（``cmd.exe /c echo %USERNAME%``），探测失败时回退
    环境变量 ``FLASH_WIN_HOME``；两者皆缺则抛 RuntimeError（不猜）。
    仅在 WSL 内调用（Linux 平台）；Windows 平台直接返回 win_home() 字符串。
    """
    if os.name == "nt":
        return str(win_home())
    env = os.environ.get("FLASH_WIN_HOME")
    if env:
        return env.rstrip("/")
    import subprocess
    try:
        out = subprocess.run(
            ["cmd.exe", "/c", "echo %USERNAME%"],
            capture_output=True, text=True, timeout=15,
        )
        user = (out.stdout or "").strip().splitlines()
        user = user[-1].strip() if user else ""
    except Exception:
        user = ""
    if user and user != "%USERNAME%":
        cand = Path(f"/mnt/c/Users/{user}")
        if cand.is_dir():
            return str(cand)
    raise RuntimeError(
        "[paths] 无法确定 WSL 内的 Windows 家目录："
        "请设置环境变量 FLASH_WIN_HOME=/mnt/c/Users/<你的Windows用户名>"
    )


# ── 超算（身份只来自 ~/.physimx，绝不入库）────────────────

_HPC_ACCOUNTS_FILE = Path.home() / ".physimx" / "flash" / "hpc_accounts.json"


def _load_accounts() -> Dict:
    """直接读 hpc_accounts.json（不经 credentials 包，避免 import 链）。"""
    try:
        with open(_HPC_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def hpc_ssh_username(account: str = "flash_ssh") -> str:
    """超算 SSH 用户名（取 hpc_accounts.json 的 ssh_username，去掉 @CLUSTER 后缀）。"""
    acct = _load_accounts().get("accounts", {}).get(account, {})
    raw = str(acct.get("ssh_username", "") or "")
    return raw.split("@", 1)[0] if raw else ""


def hpc_home(account: str = "flash_ssh") -> Optional[str]:
    """超算家目录（如 ``/publicfs01/fs1-e/home/<user>``）。

    解析顺序：
      1. 环境变量 ``FLASH_HPC_HOME``（显式指定，最高优先）；
      2. hpc_accounts.json 中该账户的 ``remote_home`` 字段（明文配置在
         ~/.physimx 下，**不入库**，无泄漏）；
      3. 解析失败返回 None（调用方决定报错或跳过；本模块不猜）。
    """
    env = os.environ.get("FLASH_HPC_HOME")
    if env:
        return env.rstrip("/")
    acct = _load_accounts().get("accounts", {}).get(account, {})
    remote_home = str(acct.get("remote_home", "") or "").rstrip("/")
    return remote_home or None


def hpc_home_required(account: str = "flash_ssh") -> str:
    """hpc_home() 的严格版：解析失败时抛出带修复指引的 RuntimeError。"""
    home = hpc_home(account)
    if not home:
        raise RuntimeError(
            "[paths] 无法确定超算家目录（绝不硬编码）。请按以下任一方式配置：\n"
            "  1) export FLASH_HPC_HOME=/path/to/home   # 会话级\n"
            f"  2) 在 {_HPC_ACCOUNTS_FILE} 的 accounts.{account} 中加\n"
            '     "remote_home": "/path/to/home" 字段   # 持久（文件在 ~/.physimx，不入库）'
        )
    return home


def hpc_target_dirs(account: str = "flash_ssh") -> Tuple[str, str, str]:
    """超算部署目录三元组 (REMOTE_HOME, TARGET_DIR, PKG_DIR)。

    目录布局（PhySimX/PhySimX/simulation/flash/{flash_sim,flash_sim_pkg}）
    是部署约定，与账号无关；家目录部分由 hpc_home() 运行期解析。
    """
    home = hpc_home_required(account)
    base = f"{home}/PhySimX/PhySimX/simulation/flash"
    return home, f"{base}/flash_sim", f"{base}/flash_sim_pkg"


if __name__ == "__main__":  # 自检：python -m flash._core.paths
    print(f"repo_root        = {repo_root()}")
    print(f"win_home         = {win_home()}")
    print(f"managed_python   = {managed_python()}")
    print(f"hpc_ssh_username = {hpc_ssh_username() or '(未配置)'}")
    print(f"hpc_home         = {hpc_home() or '(未配置)'}")
