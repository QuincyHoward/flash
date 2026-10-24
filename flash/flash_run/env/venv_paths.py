#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""venv_paths.py — 三平台虚拟环境路径的**唯一事实源**（2026-10-24 解耦改造）
═══════════════════════════════════════════════════════════════════════════════

设计约束（违反任何一条都会让"单一事实源"失效）：
  1. **纯 stdlib**：只允许 `os` / `sys` / `pathlib` / `typing`。
     禁止 `from .`，禁止 `from flash.x import ...` —— 本模块会被部署侧在
     `pip install` **之前**按文件路径加载，那时 flash 尚不可导入。
  2. **模块级零副作用、零缓存**：同一文件会被加载成两个模块对象
     （运行时 `flash.flash_run.env.venv_paths`、部署侧 `_flash_venv_paths`），
     不共享状态、不注册 sys.modules。
  3. **root 由调用方显式传入**：禁止靠本文件 `__file__` 反推（部署侧与
     包内运行时看到的相对层级不同，正是历史上 7 处副本互相漂移的根源）。
  4. `repo_root()` 找不到源码树时**返回 None**（唯一允许的软化），
     **绝不回落 `sys.executable`** —— 历史 bug 就是因为静默回落，
     导致超算上拿到登录节点 python3.6.8，报 "h5py 缺失" 而非 "venv 找错"。

背景：改造前 venv 解析散落 7 处，且「根正确但命名旧」与「命名正确但根错位」
并存，无一处完全正确（详见 docs/功能模块解耦与流程梳理计划.md §1.6）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

#: 源码树判据（须同时存在）：证明这是 git clone / sdist 解包后的完整仓库根
_ROOT_MARKERS = ("pyproject.toml", "start_flash.py")

#: 超算命名环境默认名（可由 FLASH_HPC_VENV_NAME 覆盖）
_DEFAULT_HPC_VENV_NAME = ".venv-hpc-nce"

KINDS = ("local", "hpc")


def _is_file(p: Path) -> bool:
    """`Path.is_file()` 的安全版。

    ★ 2026-10-24 实测缺陷：仓库里 `.venv-linux/bin/python` 在 **Windows** 上
    是符号链接，`is_file()` 直接抛 `OSError: [WinError 1920] 系统无法访问此文件`，
    而不是返回 False。探测循环因此**整体崩溃**，把一个"没有这个 venv"的
    正常情况变成进程级异常。
    """
    try:
        return p.is_file()
    except OSError:
        return False


# ── 根定位 ────────────────────────────────────────────────

def repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """向上探测源码树根（含 pyproject.toml 且含 start_flash.py）。

    Args:
        start: 起点目录；缺省 = 本文件所在目录。
    Returns:
        仓库根 Path；找不到（如 wheel 安装态 site-packages）返回 ``None``。
        ★ 调用方**不得**把 None 当作"用系统 python 即可"，必须显式报错。
    """
    if start is None:
        start = Path(__file__).resolve().parent
    cur = Path(start).resolve()
    for cand in (cur, *cur.parents):
        if all(_is_file(cand / m) for m in _ROOT_MARKERS):
            return cand
    return None


def _require_root(root: Optional[Path]) -> Path:
    if root is None:
        raise RuntimeError(
            "无法定位源码树根（需同时包含 pyproject.toml 与 start_flash.py）。\n"
            "  这是 wheel/site-packages 安装态的预期行为；请显式传入 root，\n"
            "  或设置 FLASH_VENV_DIR 指向目标虚拟环境。"
        )
    return Path(root)


# ── 平台标签与命名 ────────────────────────────────────────

def platform_tag() -> str:
    """本机平台标签: 'win' | 'mac' | 'linux'。"""
    if os.name == "nt":
        return "win"
    if sys.platform.startswith("darwin"):
        return "mac"
    return "linux"


def hpc_venv_name() -> str:
    """超算侧命名环境目录名（默认 .venv-hpc-nce）。"""
    return os.environ.get("FLASH_HPC_VENV_NAME", "").strip() or _DEFAULT_HPC_VENV_NAME


def _venv_inner(kind: str) -> tuple:
    """venv 内解释器的相对路径分量。"""
    if os.name == "nt":
        return ("Scripts", "python.exe")
    return ("bin", "python")


# ── 目录与解释器 ──────────────────────────────────────────

def venv_dir(root: Optional[Path], kind: str = "local") -> Path:
    """本平台/超算的 venv **目录**（不做存在性判断）。

    ``kind="local"`` → ``<root>/.venv-<平台标签>``（如 .venv-win / .venv-linux）
    ``kind="hpc"``   → ``<root>/.venv-hpc-nce``
    """
    root = _require_root(root)
    if kind not in KINDS:
        raise ValueError(f"未知 kind={kind!r}，可用: {KINDS}")
    if kind == "hpc":
        return root / hpc_venv_name()
    return root / f".venv-{platform_tag()}"


def candidates(root: Optional[Path], kind: str = "local") -> List[Path]:
    """按优先级列出候选 venv 目录（供报错信息与 --check-env 展示）。

    ★ Windows 上 ``kind="hpc"`` **不做本地探测**（超算 venv 不在本机，
      探测只会产生"缺失"误报）；仅当 `FLASH_VENV_DIR` 显式指定时才返回它。
    """
    out: List[Path] = []
    env = os.environ.get("FLASH_VENV_DIR", "").strip()
    if env:
        out.append(Path(env))
    if kind == "hpc" and os.name == "nt":
        return out
    root = _require_root(root)
    out.append(venv_dir(root, kind))
    if kind == "local":
        # 兼容旧的无后缀 .venv（历史环境），排在最后
        out.append(root / ".venv")
    return out


def venv_python(root: Optional[Path], kind: str = "local") -> Optional[Path]:
    """解析 venv 解释器路径。

    优先级：``FLASH_VENV_DIR`` > ``venv_dir(kind)`` > ``<root>/.venv``（仅 local）。
    ★ 返回 ``None`` 表示"确实没有"，调用方必须显式报错，**禁止**回落
      ``sys.executable``（见模块 docstring 约束 4）。
    """
    for d in candidates(root, kind):
        py = Path(d).joinpath(*_venv_inner(kind))
        if _is_file(py):
            return py
    return None


def require_venv_python(root: Optional[Path], kind: str = "local") -> Path:
    """同 :func:`venv_python`，但找不到时抛 ``RuntimeError`` 并列出候选。"""
    py = venv_python(root, kind)
    if py is not None:
        return py
    cands = candidates(root, kind)
    shown = "\n".join(f"    {c}" for c in cands) or "    (无候选：Windows 上不探测超算 venv)"
    raise RuntimeError(
        f"未找到 {kind} 虚拟环境解释器，候选目录均已尝试：\n{shown}\n"
        f"  修复：① 运行 start_flash.py 创建环境；或 ② 设置 FLASH_VENV_DIR 指向现有 venv。"
    )
