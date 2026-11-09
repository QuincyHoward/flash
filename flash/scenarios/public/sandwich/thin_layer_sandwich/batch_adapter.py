# -*- coding: utf-8 -*-
"""batch_adapter — thin_layer_sandwich(si) 批量适配器（flash_run.remote.batch 协议实现）
════════════════════════════════════════════════════════════════════════════

依赖倒置：flash_run 定义 SceneBatchAdapter 协议，本文件只做物理构建
（par 渲染/静态输入/HPC 声明），并行方案选择由 runner CLI --plan 或
缺省（单节点单任务）完成。

用法（skill / CLI）:
    python -m flash.flash_run.remote.batch.runner \\
        --adapter flash.scenarios.public.sandwich.thin_layer_sandwich.batch_adapter:ADAPTER \\
        run --overrides-json '[{"power_factor":1.0}]'

功率因子 PF: 激光峰值功率乘子（默认 1.0 → 5e14 W/cm²，defaults_si 基准）。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

_HERE = Path(__file__).resolve().parent            # 场景目录
_REPO = _HERE
for _ in range(12):
    if (_REPO / "pyproject.toml").is_file():
        break
    _REPO = _REPO.parent
else:
    raise RuntimeError("batch_adapter: cannot locate repo root")
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_HERE))   # par_builder 需要 import defaults（本目录）

from flash.scenarios.public.sandwich.thin_layer_sandwich import scenario_si


@dataclass
class ThinLayerAdapter:
    """thin_layer_sandwich(si) 批量适配器（SceneBatchAdapter 协议实现）。"""
    scene: str = "thin_layer_sandwich_si"   # scene.json 注册名

    # ── 物理构建 ──

    def render_par(self, overrides: dict) -> str:
        """{param 覆盖} → par 全文。

        power_factor 语义：缩放激光脉冲峰值功率（基准 5e14 W/cm²）；
        tmax 直接透传（build_par 闭包内 fit_time_controls 自动收缩 dtinit/dtmax）。
        """
        params = dict(scenario_si.default_params)
        pf = overrides.pop("power_factor", None) if isinstance(overrides, dict) else None
        if pf is not None:
            pf = float(pf)
            params["laser_powers"] = [p * pf for p in params["laser_powers"]]
        params.update(overrides)
        return scenario_si.build_par(params)

    def par_basename(self, overrides: dict) -> str:
        pf = overrides.get("power_factor")
        return f"thin_layer_pf{pf}.par" if pf is not None else \
            "thin_layer_custom.par"

    def static_inputs(self) -> dict[str, bytes]:
        """Config/Makefile/*.F90 + cn4 数据表（sim_input_si 生成物，只读收集）。"""
        out: dict[str, bytes] = {}
        for f in sorted(_HERE.glob("sim_input_si/*")):
            if f.suffix in (".par", ".png") or f.suffix in (".sh", ".bat"):
                continue          # par 由 render_par 逐实例渲染；脚本/图非运行所需
            if f.is_file():
                out[f.name] = f.read_bytes()
        return out

    # ── HPC 声明（只读） ──

    def hpc_decl(self):
        from flash.scenarios.core.hpc.hpc_job import get_scene_hpc_job
        decl = get_scene_hpc_job(self.scene)
        # ★ 内置表 thin_layer 条目 setup_extra=() 为历史遗留——场景
        #   THIN_LAYER_SETUP 明确需要 ed_maxPulseSections=240（5 段脉冲）。
        if "ed_maxPulseSections=240" not in decl.setup_extra:
            decl = replace(decl, setup_extra=("ed_maxPulseSections=240",))
        return decl

    def touch_files(self) -> tuple[str, ...]:
        return ("lasslab.dat",)

    def batch_root(self) -> Path:
        return _HERE / "runs" / "pf_batch"


ADAPTER = ThinLayerAdapter()
