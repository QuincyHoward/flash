# -*- coding: utf-8 -*-
"""hpc_job.py — 公开场景的**超算提交声明**（场景层唯一归属）
════════════════════════════════════════════════════════════════════════════

★ 为什么要有这个模块（2026-10-26）

  上一版把 sandwich 场景的超算提交逻辑放在 `deploy/hpc_deploy/submit_sandwich.py`，
  里面有：

    · 场景 → 目录/单元/par 的**映射表**（`SCENES`）
    · 每个场景的**额外 setup 参数**（`SETUP_EXTRA`）
    · 每个场景的**输入生成脚本路径**（`GEN_SCRIPT`）

  ⇒ 提交器里长出了**子场景知识**，而它本该只做"怎么提交"。

  ⇒ 现在拆成两半：

    · `flash.flash_run.remote.job_submit`：**通用提交服务**（渲染/落盘/sbatch）
      —— 不认识任何场景。
    · 本模块（场景层）：**场景声明** —— 场景叫什么、输入在哪、
      FLASH 单元叫什么、要传哪些 setup 参数。

★ 声明的最小信息集

    input_rel_dir   场景输入目录（相对仓库根）
    gen_script      输入生成脚本（相对仓库根）
    flash_unit      FLASH 场景单元名（可含 {run_id} 占位）
    par_file        par 文件名
    setup_extra     该场景额外的 setup 参数

★ 使用方式

    python -m flash.scenarios.cli submit grad_dens_sandwich --run-id 000002
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

__all__ = [
    "SceneHpcJob",
    "SCENE_HPC_JOBS",
    "get_scene_hpc_job",
    "list_scene_hpc_jobs",
]


#: FLASH `setup` 的公共参数（与各场景一致）。
#:
#: ★ 这是**FLASH 装置/求解器层面的通用参数**（1D + HDF5 + 多温 + 激光 + MGD），
#:   不是某个场景独有的 ⇒ 放这里作为公共基线，场景只声明**差异**。
SETUP_COMMON: Tuple[str, ...] = (
    "-1d", "+cartesian", "-nxb=16", "-maxblocks=2048",
    "+hdf5typeio", "species=cham,targ,poly",
    "+mtmmmt", "+laser", "+uhd3t", "+mgd", "mgd_meshgroups=10",
)


@dataclass(frozen=True)
class SceneHpcJob:
    """一个场景的超算提交声明。

    Attributes:
        name: 场景名。
        input_rel_dir: 场景输入目录（相对仓库根，如
            ``flash/scenarios/public/sandwich/grad_dens_sandwich/sim_input``）。
        gen_script: 输入生成脚本（相对仓库根）。
        flash_unit: FLASH 场景单元名；``{run_id}`` 会被替换。
        par_file: par 文件名。
        setup_extra: 该场景**额外**的 setup 参数（追加在公共基线之后）。
        ntasks: 默认 MPI rank 数（必须 ≤ nblockx）。
        time_limit: 默认墙钟上限。
    """

    name: str
    input_rel_dir: str
    gen_script: str
    flash_unit: str
    par_file: str
    setup_extra: Sequence[str] = ()
    ntasks: int = 4
    time_limit: str = "02:00:00"

    def unit_for(self, run_id: str = "") -> str:
        """展开单元名中的 ``{run_id}`` 占位。"""
        return self.flash_unit.format(run_id=run_id) if run_id else self.flash_unit

    def setup_args(self) -> Tuple[str, ...]:
        """完整 setup 参数（公共基线 + 场景差异）。"""
        return (*SETUP_COMMON, *self.setup_extra)


#: 公开场景的超算提交声明表。
SCENE_HPC_JOBS: Dict[str, SceneHpcJob] = {
    "grad_dens_sandwich": SceneHpcJob(
        name="grad_dens_sandwich",
        input_rel_dir="flash/scenarios/public/sandwich/grad_dens_sandwich/sim_input",
        gen_script="flash/scenarios/public/sandwich/grad_dens_sandwich/gen_flash_inputs.py",
        flash_unit="QC/grad_dens_sandwich_{run_id}",
        par_file="grid_rede.par",
        setup_extra=("ed_maxPulseSections=240",),
        ntasks=4,
    ),
    "thin_layer_sandwich_si": SceneHpcJob(
        name="thin_layer_sandwich_si",
        input_rel_dir="flash/scenarios/public/sandwich/thin_layer_sandwich/sim_input_si",
        gen_script="flash/scenarios/public/sandwich/thin_layer_sandwich/gen_flash_inputs.py",
        flash_unit="QC/grid_rede",
        par_file="grid_rede.par",
        setup_extra=(),
        ntasks=4,
    ),
}


def get_scene_hpc_job(name: str) -> SceneHpcJob:
    """取场景的超算提交声明（未知场景报 KeyError）。"""
    key = (name or "").strip()
    if key not in SCENE_HPC_JOBS:
        known = ", ".join(SCENE_HPC_JOBS)
        raise KeyError(f"场景 {name!r} 无超算提交声明；可用: {known}")
    return SCENE_HPC_JOBS[key]


def list_scene_hpc_jobs() -> Sequence[SceneHpcJob]:
    """列出全部超算提交声明。"""
    return tuple(SCENE_HPC_JOBS.values())
