"""flash-sim 场景包 — 物理专题 + 场景两层组织

scenarios/
├── __init__.py     ← 本文件：**惰性**预热注册所有场景包
├── base.py         ← SimulationScenario 数据类
├── registry.py     ← 声明式场景注册表（引擎用）
├── catalog.py      ← 可执行场景目录（CLI 用，2026-10-24 新增）
├── cli.py          ← 统一入口 python -m flash.scenarios.core.cli
├── runner.py       ← 兼容壳（转发 flash.flash_run.modes.runner）
├── public/         ← 公开示例（随发布包分发）
├── flash_demo/     ← 演示场景
└── private/        ← 私有场景（tracer 系列，不随包分发）

★ 2026-10-24（解耦计划 B0/C4）：原实现在 **import 时**就 `__import__` 三个
  子包（public/flash_demo/private），导致 `python -m flash.scenarios.core.cli list`
  启动即全量导入所有场景（含 private 告警、h5py/yt 依赖）。
  现改为 `warm_registry()` 显式预热，由 `registry.get_scenario()` /
  `list_scenarios()` 首次调用时自动触发 ⇒ 语义不变，但 CLI 快得多。
"""

from __future__ import annotations

_SHIPPED_PACKAGES = ("public", "flash_demo")   # 随发布包分发：缺失即打包缺陷
_OPTIONAL_PACKAGES = ("private",)              # 私有分区：克隆/发布环境可缺

_LOADED = False
_LOADING = False
_registered_packages: tuple = ()


def warm_registry() -> tuple:
    """扫描 ``scene.json`` 发现场景（幂等、可重入安全，2026-10-27 去注册化）。

    ★ 旧实现在此 ``__import__`` 三个子包（import 副作用链 → 各场景
      ``__init__`` 底部 ``register(...)``）。现在场景发现改为**纯文件
      扫描**（``discovery.iter_scene_manifests``）—— 新增场景 = 落一份
      ``scene.json``，零注册代码、零 import 副作用。
      ``registry._ensure_loaded()`` 直接调用发现器，本函数仅保留为
      兼容 API（返回已发现的分区名）。

    ★ 重入保护保留（历史调用方仍可能在 import 期间触达本函数）。
    """
    global _LOADED, _LOADING, _registered_packages
    if _LOADED or _LOADING:
        return _registered_packages

    _LOADING = True
    loaded = []
    try:
        from flash.scenarios.core.discovery import scenario_base, iter_scene_manifests

        base = scenario_base()
        iter_scene_manifests()   # 非法 manifest 在此显式暴露（不吞）
        for _pkg in (*_SHIPPED_PACKAGES, *_OPTIONAL_PACKAGES):
            if (base / _pkg).is_dir():
                loaded.append(_pkg)
            # 随发布包分区缺失：发现器不 import，交给 CLI --check-env 报告
    except Exception:
        _LOADING = False
        raise
    _registered_packages = tuple(loaded)
    _LOADED = True
    return _registered_packages


def registered_packages() -> tuple:
    """已加载的场景包名（供 `--check-env` 报告"已注册场景数"）。"""
    return _registered_packages


#: 旧根级核心模块名 → core/ 子模块（2026-10-27 目录整洁化兼容层）
_LEGACY_CORE_ATTRS = ("base", "registry", "runner", "simulator", "catalog",
                      "cli", "hints", "discovery", "launcher", "policies",
                      "hpc_job", "device_defaults", "submit_cli",
                      "insitu_runner", "interpolator")


def __getattr__(name):
    """兼容旧行为：`flash.scenarios.<旧模块名>` → core 子模块。

    旧代码依赖 `import flash.scenarios` 的**副作用**（注册表已填充）。
    现改为：首次访问旧模块名时预热一次再转发 core。
    """
    if name in _LEGACY_CORE_ATTRS:
        warm_registry()
        from importlib import import_module

        return import_module(f"flash.scenarios.core.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
