# -*- coding: utf-8 -*-
"""device_defaults.py — 场景层的**装置默认值**覆盖（场景层唯一归属）
════════════════════════════════════════════════════════════════════════════

★ 为什么从 `flash.flash_run.env.resource_config` 移到这里（2026-10-26）

  `flash_run/env` 是**装置事实源**（分区 / 模块 / 库路径 / 账户 / venv 名），
  **不该出现任何场景名**。上一版把 `SCENE_DEVICE_DEFAULTS` 写进
  `flash_run/env/resource_config.py`，键是 `SNBOneCH` / `SNBVTi` ⇒
  执行层里出现子场景信息。

  ⇒ 现在分成两半：

    · **装置侧**（`flash.flash_run.env.devices`）：account / venv / 分区 ……
      —— 与场景无关，任何场景都能用。
    · **场景侧**（本模块）：`nprocs` 等**由场景物理/网格决定**的值。

★ 用法

    from flash.scenarios.device_defaults import get_scene_nprocs
    NPROCS = get_scene_nprocs("SNBOneCH_ml")      # → 131
"""
from __future__ import annotations

from typing import Dict, Optional

__all__ = ["SCENE_NPROC_DEFAULTS", "get_scene_nprocs"]


#: 场景族前缀 → MPI 进程数。
#:
#: ★ `nprocs` 是**网格定义**而非设备属性：`iProcs × nxb = const`
#:   ⇒ 改核数即改网格（FLASH SystemExit）⇒ 必须由场景层声明。
SCENE_NPROC_DEFAULTS: Dict[str, int] = {
    "SNBOneCH": 131,   # nxb=128, iprocs=131 ⇒ dx=0.0298 µm ≤ 0.03 µm
    "SNBVTi": 125,     # iprocs=125
}


def get_scene_nprocs(scene_name: str, default: Optional[int] = None) -> Optional[int]:
    """按场景族名（最长前缀匹配）取默认 MPI 进程数。

    Args:
        scene_name: 场景名（如 ``"SNBOneCH_ml"``）。
        default: 未命中时的返回值（None = 不给默认值）。

    Returns:
        匹配到的核数，或 ``default``。
    """
    name = (scene_name or "").strip()
    best = ""
    for prefix in SCENE_NPROC_DEFAULTS:
        if name.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    if not best:
        return default
    return SCENE_NPROC_DEFAULTS[best]
