"""insitu_runner —— **已迁移，仅为兼容壳**

★ 2026-10-24（解耦计划 B1）：hpc-insitu 编排已迁至
``flash.flash_run.modes.hpc_insitu``（执行基础设施属于执行层，
放在场景层是层次倒置，也是 `modes → scenarios → modes` 循环的成因）。

保留本文件的原因（禁止删除）：
  * ``test/test_insitu_runner.py`` 直接 import 本模块的
    ``InsituSpec`` / ``collect_local`` / ``run_insitu``；
  * 少数场景脚本与文档按此路径引用。

本文件**只允许 re-export**，不得再放实现。
"""

from flash.flash_run.modes.hpc_insitu import (      # noqa: F401  (re-export)
    InsituSpec,
    collect_local,
    is_hpc_login_node,
    resolve_hpc_python,
    run_insitu,
)

__all__ = [
    "InsituSpec",
    "collect_local",
    "is_hpc_login_node",
    "resolve_hpc_python",
    "run_insitu",
]
