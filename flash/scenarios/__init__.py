"""flash-sim 场景包 — 物理专题 + 场景两层组织

scenarios/
├── __init__.py     ← 本文件：**惰性**预热注册所有场景包
├── base.py         ← SimulationScenario 数据类
├── registry.py     ← 声明式场景注册表（引擎用）
├── catalog.py      ← 可执行场景目录（CLI 用，2026-10-24 新增）
├── cli.py          ← 统一入口 python -m flash.scenarios.cli
├── runner.py       ← 兼容壳（转发 flash.flash_run.modes.runner）
├── public/         ← 公开示例（随发布包分发）
├── flash_demo/     ← 演示场景
└── private/        ← 私有场景（tracer 系列，不随包分发）

★ 2026-10-24（解耦计划 B0/C4）：原实现在 **import 时**就 `__import__` 三个
  子包（public/flash_demo/private），导致 `python -m flash.scenarios.cli list`
  启动即全量导入所有场景（含 private 告警、h5py/yt 依赖）。
  现改为 `warm_registry()` 显式预热，由 `registry.get_scenario()` /
  `list_scenarios()` 首次调用时自动触发 ⇒ 语义不变，但 CLI 快得多。
"""

from __future__ import annotations

import warnings

_SHIPPED_PACKAGES = ("public", "flash_demo")   # 随发布包分发：缺失即打包缺陷
_OPTIONAL_PACKAGES = ("private",)              # 私有分区：克隆/发布环境可缺

_LOADED = False
_LOADING = False
_registered_packages: tuple = ()


def warm_registry() -> tuple:
    """导入并注册所有场景包（幂等、可重入安全）。

    ★ 重入保护是必需的：`warm_registry()` 里 import 的子包可能反过来
      `from flash.scenarios.registry import get_scenario`，而
      `get_scenario()` 又会调用本函数 —— 没有 `_LOADING` 会无限递归。
    """
    global _LOADED, _LOADING, _registered_packages
    if _LOADED or _LOADING:
        return _registered_packages

    _LOADING = True
    loaded = []
    try:
        for _pkg in (*_SHIPPED_PACKAGES, *_OPTIONAL_PACKAGES):
            try:
                __import__(f"flash.scenarios.{_pkg}")
                loaded.append(_pkg)
            except ImportError as _e:
                _missing = (getattr(_e, "name", "") or "")
                if _pkg in _SHIPPED_PACKAGES and _missing.startswith("flash."):
                    raise ImportError(
                        f"场景包 flash.scenarios.{_pkg} 缺失或不完整：{_e}\n"
                        f"  这通常表示发布物打包不完整（wheel/sdist 缺文件），"
                        f"请重装或更新 flash-sim。"
                    ) from _e
                warnings.warn(
                    f"场景包 {_pkg} 加载失败（可选依赖或私有分区缺失，已跳过）: {_e}",
                    stacklevel=2,
                )
    finally:
        _LOADING = False
    _registered_packages = tuple(loaded)
    _LOADED = True
    return _registered_packages


def registered_packages() -> tuple:
    """已加载的场景包名（供 `--check-env` 报告"已注册场景数"）。"""
    return _registered_packages


def __getattr__(name):
    """兼容旧行为：访问 `flash.scenarios.<attr>` 前确保已预热。

    旧代码依赖 `import flash.scenarios` 的**副作用**（注册表已填充）。
    现改为：首次访问任何未知属性时预热一次。
    """
    if name in ("base", "registry", "runner", "simulator", "catalog", "cli", "hints"):
        warm_registry()
        from importlib import import_module

        return import_module(f"flash.scenarios.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
