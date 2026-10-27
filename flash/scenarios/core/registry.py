"""场景注册表 — 按名称加载仿真场景

用法::

    from flash.scenarios.core.registry import get_scenario, list_scenarios

    for name, desc in list_scenarios():
        print(f"  {name}: {desc}")

    scenario = get_scenario("thin_layer_sandwich_si")
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flash.scenarios.core.base import SimulationScenario

# 懒加载注册表: 名称 → 导入函数
_SCENARIO_REGISTRY: Dict[str, tuple] = {}


def _ensure_loaded() -> None:
    """首次访问时扫 ``scene.json`` 填表（2026-10-27 去注册化）。

    ★ 场景发现改为**纯文件扫描**（``discovery.iter_scene_manifests``），
      不再依赖 import 副作用链（warm_registry → 父包 → 场景 __init__
      → register）。``register()`` 保留为运行时扩展点（测试注入假
      场景、第三方插件），场景代码**不再调用它**。

    ★ manifest 非法时 ``iter_scene_manifests`` 会抛 —— 这里**不吞**，
      因为"注册表空着"会导致 get_scenario 报"未知场景"——
      正是 G8 要消灭的那种误导性错误。
    """
    from flash.scenarios.core.discovery import iter_scene_manifests

    for meta in iter_scene_manifests():
        if meta.kind == "script":
            continue   # script 型无可声明式场景对象，只属于 catalog
        if not (meta.module and meta.attr):
            continue   # main 型未声明场景对象（只有 main()）
        _SCENARIO_REGISTRY.setdefault(
            meta.name, (meta.attr_module or meta.module, meta.attr))


def _lazy_import(module_path: str, attr: str):
    """延迟导入场景模块"""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


def register(name: str, module_path: str, attr: str = "scenario"):
    """注册场景

    Args:
        name:        场景名称 (如 "thin_layer_sandwich_si")
        module_path: Python 模块路径 (如 "flash.scenarios.collision_compression.thin_layer_sandwich")
        attr:        模块内的变量名, 指向 SimulationScenario 实例 (默认 "scenario")
    """
    _SCENARIO_REGISTRY[name] = (module_path, attr)


def get_scenario(name: str) -> SimulationScenario:
    """按名称获取场景实例"""
    _ensure_loaded()
    if name not in _SCENARIO_REGISTRY:
        raise KeyError(
            f"未知场景: '{name}'. 可用: {', '.join(sorted(_SCENARIO_REGISTRY))}"
        )
    module_path, attr = _SCENARIO_REGISTRY[name]
    return _lazy_import(module_path, attr)


def list_scenarios() -> List[Tuple[str, str]]:
    """列出所有已注册场景 (名称, 描述)"""
    _ensure_loaded()
    results = []
    for name in sorted(_SCENARIO_REGISTRY):
        try:
            sc = get_scenario(name)
            results.append((name, sc.description))
        except Exception:
            results.append((name, "(加载失败)"))
    return results
