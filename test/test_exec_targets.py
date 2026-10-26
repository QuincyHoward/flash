"""test_exec_targets.py — 平台自适应判定表 + 场景策略约束（解耦计划 B2/B4）

覆盖：
  · 判定表 6 条判据的顺序与命中条件（mock `shutil.which` / `os.name`）
  · `auto` → 与场景 `allowed` 求交，**交集为空必定报错**（SNB 禁本地）
  · 核数约束 `NprocRule.exact` 不可被改写
  · `mode_is_remote()` 修复 G1 那类字面量比较回归
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

from flash.flash_run.execution import (
    EXEC_TARGETS,
    ExecutionPolicy,
    ExecutionTargetError,
    ExecOptions,
    NprocRule,
    SceneSpec,
    mode_is_local,
    mode_is_remote,
    normalize_target,
    resolve_target,
    run_scene,
)
# ★ 场景族策略在**场景层**（执行层不含任何场景信息）——
#   见 flash.scenarios.policies。
from flash.scenarios.policies import SNB_POLICY


# ── 词汇表 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("hpc", "hpc-remote"),
    ("HPC-REMOTE", "hpc-remote"),
    ("slurm", "hpc-remote"),
    ("insitu", "hpc-insitu"),
    ("hpc-insitu", "hpc-insitu"),
    ("local", "local"),
    ("wsl", "wsl"),
    ("", "auto"),
    ("AUTO", "auto"),
])
def test_normalize_target(raw, expected):
    assert normalize_target(raw) == expected


def test_mode_is_remote_covers_both_hpc_modes():
    """G1 根因：改名 hpc→hpc-remote 后 `!= "hpc"` 恒真。

    `mode_is_remote` 是唯一正确写法，两种超算模式都返回 True。
    """
    assert mode_is_remote("hpc")
    assert mode_is_remote("hpc-remote")
    assert mode_is_remote("hpc-insitu")
    assert not mode_is_remote("wsl")
    assert mode_is_local("wsl") and mode_is_local("local")


# ── 判定表 ────────────────────────────────────────────────────────

def _force_no_slurm(monkeypatch, available=()):
    """把 which() 限定为 available 集合。"""
    import flash.flash_run.execution as ex

    monkeypatch.setattr(ex, "_has_cmd", lambda name: name in available)


def test_judgement1_explicit_mode_wins(monkeypatch):
    target, trace = resolve_target("hpc-remote", ExecutionPolicy())
    assert target == "hpc-remote"
    assert any("判据 1" in t for t in trace)


def test_judgement2_env_var(monkeypatch):
    monkeypatch.delenv("FLASH_RUN_MODE", raising=False)
    target, trace = resolve_target("auto", ExecutionPolicy(),
                                   env={"FLASH_RUN_MODE": "hpc-insitu"})
    assert target == "hpc-insitu"
    assert any("判据 2" in t for t in trace)


def test_judgement4_insitu_requires_slurm(monkeypatch):
    import flash.flash_run.execution as ex

    monkeypatch.setattr(ex.os, "name", "posix")
    monkeypatch.setattr(ex, "_probe_slurm_healthy", lambda *a, **k: (True, "sinfo 返回 2 个分区"))
    target, trace = resolve_target("auto", ExecutionPolicy(), env={})
    assert target == "hpc-insitu"
    assert any("判据 4 命中" in t for t in trace)


def test_judgement4_miss_falls_back_to_local(monkeypatch):
    import flash.flash_run.execution as ex

    monkeypatch.setattr(ex.os, "name", "posix")
    monkeypatch.setattr(ex, "_probe_slurm_healthy", lambda *a, **k: (False, "缺少命令 sbatch"))
    target, trace = resolve_target("auto", ExecutionPolicy(), env={})
    assert target == "local"
    assert any("判据 4 未命中" in t for t in trace)


def test_windows_never_judged_insitu(monkeypatch):
    """★ Windows 上即使装了 slurm 客户端也**绝不允许**判 insitu
    （计划风险 R1：登录节点误判会直接在登录节点跑 FLASH）。"""
    import flash.flash_run.execution as ex

    monkeypatch.setattr(ex.os, "name", "nt")
    monkeypatch.setattr(ex, "_probe_slurm_healthy", lambda *a, **k: (True, "假装可用"))
    monkeypatch.setattr(ex, "_probe_wsl", lambda: (True, "发行版 Ubuntu-22.04"))
    target, _trace = resolve_target("auto", ExecutionPolicy(), env={})
    assert target == "wsl"


def test_no_platform_at_all_raises(monkeypatch):
    import flash.flash_run.execution as ex

    monkeypatch.setattr(ex.os, "name", "nt")
    monkeypatch.setattr(ex, "_probe_wsl", lambda: (False, "wsl 不存在"))
    with pytest.raises(ExecutionTargetError) as ei:
        resolve_target("auto", ExecutionPolicy(), env={})
    assert "wsl --install" in str(ei.value)


# ── 策略约束（B4：SNB 禁本地）─────────────────────────────────────

def test_snb_policy_rejects_local(monkeypatch):
    with pytest.raises(ExecutionTargetError) as ei:
        resolve_target("local", SNB_POLICY, env={})
    msg = str(ei.value)
    assert "只允许 hpc-remote, hpc-insitu" in msg
    assert "dx=0.02" in msg, "必须给出物理原因，否则用户只会去找绕过办法"


def test_snb_policy_accepts_remote():
    target, _ = resolve_target("hpc-remote", SNB_POLICY, env={})
    assert target == "hpc-remote"


def test_run_scene_refuses_and_never_returns_fake_success(monkeypatch):
    """被策略拒绝时 run_scene 必须 ok=False（不得吞错报成功）。"""
    scene = SceneSpec(name="snb", policy=SNB_POLICY, runner=lambda o: {"ok": True})
    result = run_scene(scene, ExecOptions(mode="local"))
    assert result.ok is False
    assert "只允许" in result.reason


def test_nproc_exact_cannot_be_rewritten():
    rule = NprocRule(mode="exact", value=131, note="网络定义")
    assert rule.validate(131) is None
    assert rule.validate(24) is not None


def test_run_scene_enforces_nproc_before_anything(monkeypatch):
    policy = ExecutionPolicy(nproc=NprocRule(mode="exact", value=131))
    called = {"n": 0}
    scene = SceneSpec(name="x", policy=policy, runner=lambda o: called.__setitem__("n", 1))
    result = run_scene(scene, ExecOptions(mode="hpc-remote", nproc=4))
    assert result.ok is False
    assert called["n"] == 0, "核数不合法时不得进入执行"


def test_exec_targets_are_canonical():
    assert EXEC_TARGETS == ("local", "wsl", "hpc-remote", "hpc-insitu")


def test_run_modes_unchanged_for_backward_compat():
    """`RUN_MODES` 三元组**不动**（test_scenarios_modes.py:39 断言零改动）。"""
    from flash.flash_run.modes.runner import RUN_MODES

    assert RUN_MODES == ("wsl", "hpc-remote", "hpc-insitu")
