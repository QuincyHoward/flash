# -*- coding: utf-8 -*-
"""scene_ref.py — 跨场景模块**按名加载**器（场景收纳整理改造 P3）
════════════════════════════════════════════════════════════════════════

★ 定位：场景 A 需要复用场景 B 的模块级代码/常量（单一事实源模式，如
  SNB 族委托 SNBOneCH_ml、物理参数严格取自 OneCH_ml）时，
  **不得**硬编码 B 的层级包路径（``flash.scenarios.private.tracer.…``）
  —— 那会同时绑定两个场景的位置，任一方移动即断。

★ 正确用法（场景脚本内）::

    from flash.scenarios.common.scene_ref import scene_module

    ref = scene_module("SNBOneCH_ml")            # 委托参考场景
    cfg  = scene_module("OneCH_ml").config_constants   # 取共享物理常量

  解析规则：经 ``discovery`` 按场景**名**（scene.json 的 name）定位物理
  目录 → 文件级加载 ``<stem>.py``。两个场景各自**任意移动/重新归类**，
  只要场景名不变，引用自动跟随。

★ 语义与旧包路径 import 严格一致：
  - 模块顶层代码照常执行（与 import 等价）；
  - 同名模块进程内**单实例缓存**（重绑定委托依赖同一实例）；
  - 合成模块名 ``_scene_ref.<name>`` 不与包路径冲突；
  - ``__name__ != "__main__"``，与包导入行为一致。
"""
from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from types import ModuleType

__all__ = ["scene_module", "clear_scene_ref_cache"]

_lock = threading.Lock()
_cache: dict = {}


def scene_module(name: str, stem: str = "") -> ModuleType:
    """按场景名加载其主模块（进程内单实例缓存）。

    Args:
        name: 场景名（scene.json 的 ``name`` 字段，全局唯一）。
        stem: 主模块文件名（缺省 = 场景名，即 ``<name>.py``；
              ch_center 等主模块名与场景名不同的场景需显式给出）。

    Raises:
        ImportError: 场景名未注册 / 主模块文件不存在 / 执行失败。
    """
    modname = f"_scene_ref.{name}" + (f".{stem}" if stem and stem != name else "")
    with _lock:
        cached = _cache.get(modname)
        if cached is not None:
            return cached
    from flash.scenarios.core.scene_reg.discovery import iter_scene_manifests

    meta = next((m for m in iter_scene_manifests() if m.name == name), None)
    if meta is None:
        raise ImportError(
            f"scene_ref: 场景 {name!r} 未注册（无 scene.json）；"
            "跨场景引用请按 scene.json 的 name 解析")
    stem = stem or name
    path = Path(meta.source).parent / f"{stem}.py"
    if not path.is_file():
        raise ImportError(f"scene_ref: 场景 {name!r} 主模块不存在: {path}")
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"scene_ref: 无法为 {path} 构建 import spec")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod          # 先注册再执行（防递归自引）
    with _lock:
        _cache[modname] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        with _lock:
            _cache.pop(modname, None)
        sys.modules.pop(modname, None)
        raise
    return mod


def clear_scene_ref_cache() -> None:
    """清空缓存（测试用）。"""
    with _lock:
        _cache.clear()
