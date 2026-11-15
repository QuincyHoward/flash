# -*- coding: utf-8 -*-
"""flash_run.remote.batch — 单节点批量仿真提速包（场景无关）
════════════════════════════════════════════════════════════════════════════

三层职责（scenarios → flash_run，本包位于 flash_run 层，零场景知识）：

    scripts.py    批量作业体渲染（build 一次 + N 实例 + 累计绑核 + 内联归档）
    control.py    提交/轮询/探针/取消/收集 + 解析 + 排序榜持久化
    plans.py      并行分配方案库（纯分配拓扑 + 场景榜单实测排序 + 两级回退）
    adapter.py    SceneBatchAdapter 协议（子场景实现后传入——依赖倒置）
    runner.py     run_batch 一键链（plan→upload→submit→poll→collect）
    calibrate.py  批量优化前标定驱动（E1 核数扫描 / E2 打包扫描 / 余量档）

子场景接入成本：实现一个 SceneBatchAdapter（~40 行）+ 薄壳 CLI。
"""
from __future__ import annotations

__all__ = [
    "BatchInstance", "BatchGroupSpec", "render_batch_job_body",
    "render_batch_sbatch",
    "save_json", "load_json", "parse_slurm_time", "parse_batch_stats",
    "upload_batch_inputs", "submit_batch", "poll_batch", "probe_batch",
    "cancel_batch", "collect_batch", "merge_leaderboard",
    "stats_to_leaderboard_entry",
    "PlanSpec", "PLANS", "DEFAULT_PLAN_NAME", "plan_node_value",
    "rank_plans", "choose_plan", "resolve_plan", "load_calibration",
    "SceneBatchAdapter",
    "plan_batch", "run_batch",
    "calibrate",
]


def __getattr__(name: str):
    if name in ("BatchInstance", "BatchGroupSpec", "render_batch_job_body",
                "render_batch_sbatch"):
        from . import scripts as _m
        return getattr(_m, name)
    if name in ("save_json", "load_json", "parse_slurm_time",
                "parse_batch_stats", "upload_batch_inputs", "submit_batch",
                "poll_batch", "probe_batch", "cancel_batch", "collect_batch",
                "merge_leaderboard", "stats_to_leaderboard_entry"):
        from . import control as _m
        return getattr(_m, name)
    if name in ("PlanSpec", "PLANS", "DEFAULT_PLAN_NAME", "plan_node_value",
                "rank_plans", "choose_plan", "resolve_plan",
                "load_calibration"):
        from . import plans as _m
        return getattr(_m, name)
    if name == "SceneBatchAdapter":
        from .adapter import SceneBatchAdapter
        return SceneBatchAdapter
    if name in ("plan_batch", "run_batch"):
        from . import runner as _m
        return getattr(_m, name)
    if name == "calibrate":
        from . import calibrate as _m
        return _m.calibrate
    raise AttributeError(f"flash_run.remote.batch: no attribute {name!r}")
