# -*- coding: utf-8 -*-
"""anchors.py — 跨场景**数据文件**逻辑锚点（场景收纳整理改造 P1）
════════════════════════════════════════════════════════════════════════

★ 定位：锚点表只解决"场景 A 需要读场景 B 目录下的**数据/资源文件**"
  （如 SNB 场景共用 t001 的 source_patches）。**Python 代码级复用不走
  锚点** —— 一律抽到 ``flash/scenarios/common/`` 共享包（位置固定），
  场景之间保持零 import（子场景独立性原则，2026-11-04）。

★ 锚点表：``flash/scenarios/_scene_anchors.json``::

    { "SNB.t001": "private/SNB/SNBtest/Test/t001", ... }

  值为相对 scenarios 根的 POSIX 路径。``relocate_scene.py`` 移动目录后
  自动重写命中条目。

用法::

    from flash.scenarios.core.anchors import anchor, try_anchor

    d = anchor("SNB.t001")        # 未登记 → KeyError（显式失败）
    d = try_anchor("SNB.x")       # 未登记 → None
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

__all__ = ["anchor", "try_anchor", "anchors_table", "anchors_file"]

_anchors_file: Optional[Path] = None


def anchors_file() -> Path:
    """锚点表文件路径（scenarios 根下）。"""
    global _anchors_file
    if _anchors_file is None:
        from flash.scenarios.core.scene_paths import scenarios_root
        _anchors_file = scenarios_root() / "_scene_anchors.json"
    return _anchors_file


def anchors_table() -> dict:
    """读锚点表（缺文件 → 空表）。"""
    f = anchors_file()
    if not f.is_file():
        return {}
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def try_anchor(key: str) -> Optional[Path]:
    """按逻辑名解析锚点目录；未登记返回 None。"""
    rel = anchors_table().get(key)
    if not rel:
        return None
    from flash.scenarios.core.scene_paths import scenarios_root
    p = scenarios_root() / str(rel).replace("\\", "/")
    return p


def anchor(key: str) -> Path:
    """按逻辑名解析锚点目录；未登记显式报错（防路径漂移成谜题）。"""
    p = try_anchor(key)
    if p is None:
        known = ", ".join(sorted(anchors_table())) or "（空）"
        raise KeyError(f"未知场景锚点: {key!r}；请在 _scene_anchors.json 登记。可用: {known}")
    return p
