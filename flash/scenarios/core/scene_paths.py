# -*- coding: utf-8 -*-
"""scene_paths.py — 场景脚本统一根定位入口（场景收纳整理改造 P1）
════════════════════════════════════════════════════════════════════════

★ 目的：消灭场景脚本中 ``Path(__file__).resolve().parents[N]`` 固定层级
  引用 —— 层级假设在场景目录被移动/重新归类后立即失效。

★ 用法（场景脚本内）::

    from flash.scenarios.core.scene_paths import repo_root, scenarios_root

    _ROOT = repo_root()          # 仓库根（含 pyproject.toml + start_flash.py）
    _SCEN = scenarios_root()     # flash/scenarios 包目录

  需要定位"自身场景目录"时不要用本模块，直接 ``Path(__file__).resolve().parent``
  —— ``__file__`` 天然随场景移动。

★ 实现：向上逐级探测锚点文件（pyproject.toml + start_flash.py），
  与 run.py / catalog.repo_root() 同款语义；带结果缓存。
"""
from __future__ import annotations

from pathlib import Path

__all__ = ["repo_root", "scenarios_root", "flash_pkg_root", "has_repo_anchor"]

_CACHE: dict = {}


def has_repo_anchor(cand: Path) -> bool:
    """目录是否具备仓库根锚点（pyproject.toml + start_flash.py）。"""
    return (cand / "pyproject.toml").is_file() and (cand / "start_flash.py").is_file()


def repo_root() -> Path:
    """仓库根（含 pyproject.toml + start_flash.py），失败显式报错。"""
    if "repo" in _CACHE:
        return _CACHE["repo"]
    here = Path(__file__).resolve()
    for cand in (here, *here.parents):
        if has_repo_anchor(cand):
            _CACHE["repo"] = cand
            return cand
    raise RuntimeError(
        "无法定位仓库根（需含 pyproject.toml 与 start_flash.py）；"
        "若在裁剪发布包中运行，请改用包内相对定位")


def scenarios_root() -> Path:
    """flash/scenarios 包目录（场景发现基准）。"""
    if "scen" in _CACHE:
        return _CACHE["scen"]
    p = repo_root() / "flash" / "scenarios"
    if not p.is_dir():
        raise RuntimeError(f"scenarios 包目录不存在: {p}")
    _CACHE["scen"] = p
    return p


def flash_pkg_root() -> Path:
    """flash 包目录（仓库根/flash）。"""
    return repo_root() / "flash"
