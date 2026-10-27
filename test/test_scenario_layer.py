# -*- coding: utf-8 -*-
"""test_scenario_layer.py — 场景层的**专属**内容（与执行层对称）
════════════════════════════════════════════════════════════════════════════

★ 分层约定

    scenarios/  →  flash_run/  →  _core/        （禁止反向）

  执行层只提供**通用机制**；下列三类内容必须落在**场景层**：

    · 场景族执行策略      → `flash.scenarios.policies`
    · 场景专属核数默认值  → `flash.scenarios.device_defaults`
    · 场景超算提交声明    → `flash.scenarios.hpc_job`

  护栏 `R-LAYER-03` 机械校验执行层不含场景名（见 test_arch_guards.py）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

import pytest


# ── 场景族策略在场景层 ─────────────────────────────────────────────

def test_snb_policy_lives_in_scenarios_layer():
    """★ `SNB_POLICY` 不得再从 `flash.flash_run.execution` 导入。"""
    import flash.flash_run.execution as ex

    assert not hasattr(ex, "SNB_POLICY"), "执行层不得含场景族策略"

    from flash.scenarios.policies import SNB_POLICY
    assert SNB_POLICY.allowed == ("hpc-remote", "hpc-insitu")
    assert SNB_POLICY.requires_slurm is True


def test_public_scene_policy_lives_in_scenarios_layer():
    import flash.scenarios.policies as pol
    from flash.scenarios.catalog import PUBLIC_SCENE_POLICY

    assert pol.PUBLIC_SCENE_POLICY is PUBLIC_SCENE_POLICY
    assert PUBLIC_SCENE_POLICY.allowed == ("local", "wsl")


# ── 场景专属核数默认值在场景层 ─────────────────────────────────────

def test_scene_nprocs_in_scenarios_layer():
    import flash.flash_run.env.resource_config as rc

    assert not hasattr(rc, "SCENE_DEVICE_DEFAULTS"), "执行层不得含场景键表"
    assert not hasattr(rc, "get_scene_device_default"), "执行层不得含场景查表函数"

    from flash.scenarios.device_defaults import get_scene_nprocs
    assert get_scene_nprocs("SNBOneCH_ml") == 131
    # 2026-10-27 去注册化：SNBVTi 核数默认值在各自 scene.json 的
    # nproc_default 节（精确名匹配），内置表只剩前缀族 SNBOneCH
    assert get_scene_nprocs("SNBVTi2um") == 125
    assert get_scene_nprocs("SNBVTi2umx") == 175
    assert get_scene_nprocs("unrelated_scene") is None
    assert get_scene_nprocs("unrelated_scene", default=4) == 4


# ── 装置默认值在执行层（与场景无关）────────────────────────────────

def test_device_defaults_are_scene_agnostic():
    from flash.flash_run.env.devices import DEVICE_DEFAULTS, device_default

    assert "account" in DEVICE_DEFAULTS
    assert "insitu_venv" in DEVICE_DEFAULTS
    # 键里不得出现场景名
    for k in DEVICE_DEFAULTS:
        assert not any(s in k.lower() for s in ("snb", "ch_center", "sandwich"))


def test_slurm_account_is_not_credential_name():
    """★★ SLURM 计费账户 ≠ SSH 凭据名（超算实测：混用即被拒）。

    实测：`#SBATCH --account=flash_ssh` ⇒
    "sbatch: error: Batch job submission failed: Invalid account or
    account/partition combination specified"。
    ⇒ `account` 取 `sacct -X --format=Account` 的值（nc-e），
      凭据名（flash_ssh）只用于选 SSH 路由。
    """
    from flash.flash_run.env.devices import credential_name, device_default

    account = device_default("account")
    cred = credential_name()
    assert account, "必须提供 SLURM 计费账户"
    assert account != cred, "计费账户与凭据名不得相同（否则就是混淆了）"
    # 凭据名默认值保持不变（历史约定）
    assert cred == "flash_ssh"


# ── 场景超算提交声明 ───────────────────────────────────────────────

def test_scene_hpc_job_declarations():
    from flash.scenarios.hpc_job import get_scene_hpc_job, list_scene_hpc_jobs

    grad = get_scene_hpc_job("grad_dens_sandwich")
    assert grad.input_rel_dir.endswith("grad_dens_sandwich/sim_input")
    assert grad.flash_unit == "QC/grad_dens_sandwich_{run_id}"
    assert grad.unit_for("000002") == "QC/grad_dens_sandwich_000002"
    assert grad.par_file == "grid_rede.par"

    si = get_scene_hpc_job("thin_layer_sandwich_si")
    assert si.input_rel_dir.endswith("thin_layer_sandwich/sim_input_si")
    assert si.flash_unit == "QC/grid_rede"
    assert si.unit_for("000002") == "QC/grid_rede"

    with pytest.raises(KeyError):
        get_scene_hpc_job("no_such_scene")


def test_scene_hpc_job_setup_args_include_common_baseline():
    from flash.scenarios.hpc_job import SETUP_COMMON, get_scene_hpc_job

    args = get_scene_hpc_job("grad_dens_sandwich").setup_args()
    for token in SETUP_COMMON:
        assert token in args
    assert "ed_maxPulseSections=240" in args


def test_scene_hpc_job_gen_script_exists():
    """★ 声明的生成脚本必须真实存在（否则提交时才炸）。"""
    from flash.scenarios.hpc_job import list_scene_hpc_jobs

    root = Path(__file__).resolve().parent.parent
    for decl in list_scene_hpc_jobs():
        assert (root / decl.gen_script).is_file(), decl.gen_script
        assert (root / decl.input_rel_dir).is_dir(), decl.input_rel_dir
