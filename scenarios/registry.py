"""场景注册表 — 按名称加载仿真场景

用法::

    from flash.scenarios.registry import get_scenario, list_scenarios

    for name, desc in list_scenarios():
        print(f"  {name}: {desc}")

    scenario = get_scenario("thin_layer_sandwich_si")
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flash.scenarios.base import SimulationScenario

# 懒加载注册表: 名称 → 导入函数
_SCENARIO_REGISTRY: Dict[str, tuple] = {}


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
    if name not in _SCENARIO_REGISTRY:
        raise KeyError(
            f"未知场景: '{name}'. 可用: {', '.join(sorted(_SCENARIO_REGISTRY))}"
        )
    module_path, attr = _SCENARIO_REGISTRY[name]
    return _lazy_import(module_path, attr)


def list_scenarios() -> List[Tuple[str, str]]:
    """列出所有已注册场景 (名称, 描述)"""
    results = []
    for name in sorted(_SCENARIO_REGISTRY):
        try:
            sc = get_scenario(name)
            results.append((name, sc.description))
        except Exception:
            results.append((name, "(加载失败)"))
    return results
