# -*- coding: utf-8 -*-
"""batch.adapter — 场景适配器协议（flash_run 定义，子场景实现）
════════════════════════════════════════════════════════════════════════════

依赖倒置：本包（flash_run 层）不 import 任何场景模块；子场景实现本协议后
把实例对象传给 runner.run_batch / calibrate.calibrate。分层方向合法
（scenarios → flash_run）。

子场景最小实现（~40 行，见 SandwichTxN/scripts/batch_adapter.py）:

    from flash.flash_run.remote.batch import SceneBatchAdapter

    @dataclass
    class MyAdapter:
        scene = "MyScene"
        def render_par(self, overrides): ...     # {param 覆盖} → par 全文
        def par_basename(self, overrides): ...
        def static_inputs(self): ...             # {filename: bytes}
        def hpc_decl(self): return get_scene_hpc_job("MyScene")   # 只读
        def touch_files(self): return ()
        def batch_root(self): return HERE / "runs" / "batch"
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class SceneBatchAdapter(Protocol):
    """子场景批量适配器协议（结构化类型，无需显式继承）。"""

    #: 场景注册名（get_scene_hpc_job 用）
    scene: str

    def render_par(self, overrides: dict) -> str:
        """{param 覆盖} → par 文件全文。"""
        ...

    def par_basename(self, overrides: dict) -> str:
        """该 overrides 对应的 par 文件名（同内容覆盖组应同名去重）。"""
        ...

    def static_inputs(self) -> dict[str, bytes]:
        """静态输入（Config/Makefile/*.F90 + 数据表），{filename: bytes}。"""
        ...

    def hpc_decl(self):
        """场景 HPC 声明（只读 get_scene_hpc_job），供 unit/setup_args/
        env_profile/flash_home 取值。"""
        ...

    def touch_files(self) -> tuple[str, ...]:
        """每实例 run 目录需 touch 的空文件（场景差异）。"""
        ...

    def batch_root(self) -> Path:
        """批次数据落点（场景目录内，如 <scene>/runs/pf_batch）。"""
        ...
