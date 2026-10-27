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

    python -m flash.scenarios.core.cli submit grad_dens_sandwich --run-id 000002
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

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
        setup_common: 公共 setup 基线（None = ``SETUP_COMMON``）。
            ★ 特殊装置（如 FLASHSNB +ug 均匀网格）的参数集与公共基线
            完全不同 ⇒ 场景整组自声明（场景层唯一归属）。
        flash_home_default: FLASH 根默认值（含 $HOME，提交前解析）。
        launcher: 运行期启动器（``srun`` 走 SLURM PMI；``mpiexec`` 走
            自带 bootstrap —— FLASHSNB/NC-E 实测铁律，见 SNBOneCH_ml）。
        nodes: 默认节点数（ntasks 超单节点核数时必须 >1）。
        archive_patterns: 归档回共享盘的文件名 glob。
        gen_mode: 输入生成方式：
            ``"remote"``       = 登录节点跑 gen_script（公开场景，树自包含）；
            ``"local_upload"`` = 本地生成 + SFTP 上传（SNB 覆盖 F90 不入库
              ⇒ 远端树缺 ``snb_package`` 镜像，只有本地能完整生成）。
        gen_args: 传给 gen_script 的参数（默认 ``("--force",)``）。
        pre_build_targets: make -j 之前先单独烘的目标（竞态修复，
            2026-09 实测 hy_slopeLimiters 并行竞态）。
        make_jobs_max: make 并行度上限（0 = 不限）。
        env_profile: 运行期环境块模板（见 submit_cli.build_env_block）。
    """

    name: str
    input_rel_dir: str
    gen_script: str
    flash_unit: str
    par_file: str
    setup_extra: Sequence[str] = ()
    ntasks: int = 4
    time_limit: str = "02:00:00"
    setup_common: Optional[Sequence[str]] = None
    flash_home_default: str = "$HOME/QC/FLASH/FLASH4.8"
    launcher: str = "srun"
    nodes: int = 1
    archive_patterns: Sequence[str] = ("*chk*",)
    gen_mode: str = "remote"
    gen_args: Sequence[str] = ("--force",)
    pre_build_targets: Sequence[str] = ()
    make_jobs_max: int = 0
    env_profile: str = "nce_qc_flash_sim"

    def unit_for(self, run_id: str = "") -> str:
        """展开单元名中的 ``{run_id}`` 占位。"""
        return self.flash_unit.format(run_id=run_id) if run_id else self.flash_unit

    def setup_args(self) -> Tuple[str, ...]:
        """完整 setup 参数（公共基线 + 场景差异）。"""
        common = SETUP_COMMON if self.setup_common is None else tuple(self.setup_common)
        return (*common, *self.setup_extra)


#: 公开场景的超算提交声明表。
#:
#: ★ 2026-10-27 去注册化：SNBVTi{1,2,3}um / SNBVTi{1,2,3}umx 的提交声明
#:   已迁至各自场景目录 ``scene.json`` 的 ``hpc`` 节（含 SNB_UG_SETUP_COMMON
#:   全量 setup 参数、ntasks=125/175、nodes=3/4、gen_mode=local_upload 等），
#:   由 ``_merge_manifest_hpc_jobs()`` 并入本表 —— **本模块不再保留副本**，
#:   新增超算场景 = 写 scene.json，不改这里。
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
    _merge_manifest_hpc_jobs()   # 幂等：manifest 声明并入内置表（去注册化）
    key = (name or "").strip()
    if key not in SCENE_HPC_JOBS:
        known = ", ".join(SCENE_HPC_JOBS)
        raise KeyError(f"场景 {name!r} 无超算提交声明；可用: {known}")
    return SCENE_HPC_JOBS[key]


def list_scene_hpc_jobs() -> Sequence[SceneHpcJob]:
    """列出全部超算提交声明。"""
    _merge_manifest_hpc_jobs()
    return tuple(SCENE_HPC_JOBS.values())


#: manifest ``hpc`` 节 → SceneHpcJob 字段白名单
_HPC_MANIFEST_FIELDS = (
    "input_rel_dir", "gen_script", "flash_unit", "par_file", "setup_extra",
    "ntasks", "time_limit", "setup_common", "flash_home_default", "launcher",
    "nodes", "archive_patterns", "gen_mode", "gen_args", "pre_build_targets",
    "make_jobs_max", "env_profile",
)

_merged = False


def _merge_manifest_hpc_jobs() -> None:
    """把 ``scene.json`` 的 ``hpc`` 节并入声明表（2026-10-27 去注册化）。

    ★ 新增超算场景 = 场景目录 ``scene.json`` 里写 ``"hpc": {...}``
      （字段白名单见 ``_HPC_MANIFEST_FIELDS``），**不改本模块**。
    ★ 内置表优先：同名时 manifest 不覆盖（存量场景声明仍是唯一事实源）。
    """
    global _merged
    if _merged:
        return
    _merged = True
    try:
        from flash.scenarios.core.discovery import iter_scene_manifests
    except Exception:
        return   # discovery 不可用时退回纯内置表（与旧行为一致）
    for meta in iter_scene_manifests():
        hpc = meta.extra.get("hpc")
        if not isinstance(hpc, dict) or meta.name in SCENE_HPC_JOBS:
            continue
        kwargs = {k: (tuple(v) if isinstance(v, list) else v)
                  for k, v in hpc.items() if k in _HPC_MANIFEST_FIELDS}
        SCENE_HPC_JOBS[meta.name] = SceneHpcJob(name=meta.name, **kwargs)
