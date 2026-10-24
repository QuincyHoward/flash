"""FLASH remote deployment and environment management.

This package provides remote deployment and environment management
tools for FLASH simulations.

★ 2026-10-24（解耦计划 B0）改为 **PEP 562 惰性导出**。
原实现顶层 `from .remote.remote_deploy import FlashRemoteDeploy`，而
`remote_deploy.py` 模块级 `import paramiko` ⇒ 任何
`from flash.flash_run.<轻量模块> import ...`（哪怕只要一个 dataclass）
都会强制拉起 paramiko + cryptography + `flash._core.credentials`。
场景层要求零重依赖，故下沉到 `__getattr__`。

用法不变：``from flash.flash_run import FlashRemoteDeploy`` 仍可用，
首次访问属性时才真正 import。
"""

from typing import Any

#: 惰性导出表：名字 → (子模块, 属性名)
_LAZY = {
    "FlashRemoteDeploy": (".remote.remote_deploy", "FlashRemoteDeploy"),
    "FlashEnvManager": (".env.env_manager", "FlashEnvManager"),
    "FlashEnvironment": (".env.env_manager", "FlashEnvironment"),
    "FlashResourceConfig": (".env.resource_config", "FlashResourceConfig"),
    "get_resource_config": (".env.resource_config", "get_resource_config"),
    "RouteTester": (".remote.route_tester", "RouteTester"),
    "test_and_select_best_route": (".remote.route_tester", "test_and_select_best_route"),
    "ROUTES_SCFA2696": (".remote.route_tester", "ROUTES_SCFA2696"),
    "ROUTES_SCH0348": (".remote.route_tester", "ROUTES_SCH0348"),
}

__all__ = list(_LAZY)


def __getattr__(name: str) -> Any:
    """PEP 562：按需导入子模块属性。"""
    try:
        mod_name, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module

    value = getattr(import_module(mod_name, __name__), attr)
    globals()[name] = value          # 缓存，后续访问零成本
    return value


def __dir__() -> list:
    return sorted(__all__)
