# -*- coding: utf-8 -*-
"""policies.py — 场景族级执行策略（**场景层**唯一归属）
════════════════════════════════════════════════════════════════════════════

★ 为什么从 `flash.flash_run.execution` 移到这里（2026-10-26）

  `flash_run` 是**执行服务**：它只提供"策略机制"（`ExecutionPolicy` /
  `NprocRule` / `resolve_target`），**不该知道任何一个场景族**。
  上一版把 `SNB_POLICY`（SNB 族的"仅超算 + 核数即网格"约束）直接写在
  `flash/flash_run/execution.py` ⇒ 执行层里出现了子场景信息。

  ⇒ 现在：`flash_run` 只剩**通用机制**；
    具体的场景族策略在本模块（场景层）声明。

★ 分层方向（禁止反向）

    scenarios/  →  flash_run/  →  flash/_core/

  本模块 `import flash.flash_run.execution` 是**合法方向**（场景 → 执行）。
"""
from __future__ import annotations

from flash.flash_run.execution import ExecutionPolicy, NprocRule

__all__ = ["SNB_POLICY", "PUBLIC_SCENE_POLICY"]


#: SNB 族（非局方热传导算例族）：**仅超算**，且 nproc 是网格定义的一部分。
#:
#: ★ 为什么禁本地：``iProcs × nxb = const`` ⇒ `dx = 0.02 µm`，
#:   改核数就等于改网格（FLASH 直接 SystemExit）；
#:   且 125/131 进程远超本机核数 ⇒ 本机必然超订卡死。
SNB_POLICY = ExecutionPolicy(
    allowed=("hpc-remote", "hpc-insitu"),
    requires_slurm=True,
    forbid_reason=("nproc 是本场景网格定义的一部分（iProcs×nxb=const ⇒ dx=0.02 µm），"
                   "且 125/131 进程远超本机核数"),
    nproc=NprocRule(mode="exact", value=None,
                    note="请用场景自带的 --nproc（默认即超算配置）"),
)


#: 公开场景策略：允许本机两种执行目标（Windows→WSL / Linux→本地）。
#:
#: ⚠ 与 `DEFAULT_POLICY` 的区别在 **preferred**：引擎型场景在超算登录节点上
#:   auto 会判到 hpc-insitu（判据 4：slurm 健康），而引擎不承接超算 ⇒
#:   显式把 allowed 收窄到 (local, wsl)，让 auto 在超算上**明确报错**
#:   而不是跑到引擎才给一句模糊提示。
PUBLIC_SCENE_POLICY = ExecutionPolicy(
    allowed=("local", "wsl"),
    preferred="auto",
    forbid_reason=("公开场景的引擎执行体只承接本机（local/wsl）；"
                   "在超算上请用 `python -m flash.scenarios.core.cli submit <场景>`"),
)
