# -*- coding: utf-8 -*-
"""batch.plans — 并行分配方案库（纯资源分配语义，场景无关）
════════════════════════════════════════════════════════════════════════════

★ 职责边界（2026-11-08 用户定版）：
  本模块只描述"怎么分配节点/核数/任务"（instances × ntasks、conc/seq、
  绑核策略、墙钟），**不携带任何场景的评分/速度**——每个场景的物理负载
  不同，实测节点价值（聚合吞吐等）由各场景自己的
  ``runs/pf_batch/leaderboard.json`` 沉淀，rank_plans 从榜单读取；
  未实测的方案无分（排序靠后），不做事先估值。

方案选择（两级回退）：
    显式 --plan <名>  →  内置默认 DEFAULT_PLAN_NAME（单节点单任务）。

绑核策略 pin：
    cumulative — 实例 i 独占 [累计前缀, 累计前缀+ntasks_i-1]（conc 并发必须）；
    shared     — 每实例复用 [0, ntasks_i-1]（seq 顺序执行不重叠，单任务独占整节点）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

# ────────────────────────────────────────────────────────────────────
# 方案模型（纯分配语义）
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanSpec:
    name: str                 # 方案名（--plan 选择的 key）
    instances: int            # 单节点内并发任务数
    ntasks_per: int           # 每任务 MPI rank 数（核数；多≠最优，标定后选）
    mode: str = "conc"        # conc 并发（&+wait）；seq 前台串行
    wall_clock: str = "04:00:00"
    note: str = ""            # 分配语义说明（不写场景速度）
    pin: str = "cumulative"   # cumulative | shared（见模块 docstring）


#: 候选方案库 —— 纯分配拓扑；各方案快慢由场景榜单实测决定
PLANS: tuple[PlanSpec, ...] = (
    # ── 打包拓扑（conc + cumulative，占满/半满节点）──
    PlanSpec("p24x2",    24, 2,  "conc", "04:00:00", "24 任务×2 核（极限密度）"),
    PlanSpec("p12x4",    12, 4,  "conc", "04:00:00", "12 任务×4 核"),
    PlanSpec("p6x8",      6, 8,  "conc", "04:00:00", "6 任务×8 核"),
    PlanSpec("p4x12",     4, 12, "conc", "04:00:00", "4 任务×12 核"),
    PlanSpec("p3x16",     3, 16, "conc", "04:00:00", "3 任务×16 核"),
    PlanSpec("p2x24",     2, 24, "conc", "04:00:00", "2 任务×24 核"),
    PlanSpec("p6x4_half", 6, 4,  "conc", "04:00:00", "半节点保守（6×4=24 核，预留共存）"),
    # ── 单节点单任务（seq + shared，每任务独占整节点、核数按标定选）──
    PlanSpec("p1x12", 1, 12, "seq", "01:00:00",
             "单任务×12 核（独占整节点，多任务 seq 复用）", pin="shared"),
    PlanSpec("p1x16", 1, 16, "seq", "01:00:00",
             "单任务×16 核（独占整节点）", pin="shared"),
    PlanSpec("p1x24", 1, 24, "seq", "01:00:00",
             "单任务×24 核（独占整节点）", pin="shared"),
    PlanSpec("p1x32", 1, 32, "seq", "01:00:00",
             "单任务×32 核（独占整节点）", pin="shared"),
    PlanSpec("p1x48", 1, 48, "seq", "01:00:00",
             "单任务×满核（独占整节点；标定显示常过载，慎用）", pin="shared"),
)

#: 内置默认（未显式 --plan 时）：单节点单任务
DEFAULT_PLAN_NAME = "p1x12"

#: 旧名 → 新名（2026-11-08 方案库去场景化重命名；读旧批次 manifest 兼容用）
_PLAN_ALIASES = {
    "p12x4_full": "p12x4",
    "p1x32_lowlat": "p1x32",
    "p1x12_lowlat": "p1x12",
}

_PLAN_BY_NAME = {p.name: p for p in PLANS}


# ────────────────────────────────────────────────────────────────────
# 节点价值与排序（只认场景榜单实测，不做估值）
# ────────────────────────────────────────────────────────────────────

def _entry_matches(entry: dict, plan: PlanSpec) -> bool:
    """leaderboard entry 与方案的匹配：plan 名优先（含旧名别名），
    config 串 "N inst × K rank" 兜底。"""
    if entry.get("plan") == plan.name:
        return True
    if _PLAN_ALIASES.get(entry.get("plan", "")) == plan.name:
        return True
    m = re.match(r"(\d+) inst × (\d+) rank", entry.get("config") or "")
    if m:
        return (int(m.group(1)) == plan.instances
                and int(m.group(2)) == plan.ntasks_per)
    return False


def plan_node_value(plan: PlanSpec,
                    leaderboard_entries: Sequence[dict]) -> Optional[float]:
    """方案在该场景榜单中的实测节点价值（聚合吞吐，步/s）。

    只回实测值；无实测 → None（调用方自行决定排序位置）。
    """
    best = None
    for e in leaderboard_entries:
        if _entry_matches(e, plan) and e.get("aggregate_steps_per_s"):
            v = float(e["aggregate_steps_per_s"])
            best = v if best is None else max(best, v)
    return best


def rank_plans(leaderboard_path=None, plans: Sequence[PlanSpec] = PLANS
               ) -> list[tuple[PlanSpec, Optional[float]]]:
    """按场景榜单实测节点价值降序返回 [(plan, value|None)]。

    实测过的方案排前（按吞吐降序）；未实测方案排后（保持库内声明序）。
    leaderboard 缺失/为空 → 全部未实测，保持声明序。
    """
    entries: list[dict] = []
    if leaderboard_path is not None:
        p = Path(leaderboard_path)
        if p.is_file():
            try:
                lb = json.loads(p.read_text(encoding="utf-8"))
                entries = lb.get("entries", [])
            except Exception:
                entries = []
    ranked = [(pl, plan_node_value(pl, entries)) for pl in plans]
    measured = sorted([t for t in ranked if t[1] is not None],
                      key=lambda t: -t[1])
    unmeasured = [t for t in ranked if t[1] is None]
    return measured + unmeasured


def choose_plan(leaderboard_path=None, plans: Sequence[PlanSpec] = PLANS) -> PlanSpec:
    """榜单实测最优方案；无任何实测时返回声明序第一个有实测的方案，
    全无实测 → 声明序第一个。"""
    ranked = rank_plans(leaderboard_path, plans)
    return ranked[0][0]


def resolve_plan(name: str = "", *, leaderboard_path=None) -> PlanSpec:
    """方案解析：显式名字 → 内置默认（单节点单任务）。

    默认不自动选榜单方案（场景快慢各异，选择权留给场景/用户）；
    榜单排序经 rank_plans/choose_plan 供标定分析与显式参考。
    """
    if name:
        key = _PLAN_ALIASES.get(name, name)
        plan = _PLAN_BY_NAME.get(key)
        if plan is None:
            raise KeyError(f"未知方案 {name!r}；可选: {sorted(_PLAN_BY_NAME)}")
        return plan
    return _PLAN_BY_NAME[DEFAULT_PLAN_NAME]


# ────────────────────────────────────────────────────────────────────
# calibration.json
# ────────────────────────────────────────────────────────────────────

def load_calibration(path) -> Optional[dict]:
    """读标定结果（calibrate 产出）；不存在返回 None。"""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def suggest_wall_clock(calibration: Optional[dict],
                       plan: PlanSpec) -> str:
    """标定建议墙钟（job_elapsed_hint×1.5）优先，否则方案内置值。"""
    if calibration:
        hint = calibration.get("suggested_wall_clock")
        if hint:
            return hint
    return plan.wall_clock
