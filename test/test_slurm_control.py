"""
test_slurm_control.py — SLURM 作业控制薄层单测（2026-10-22）
════════════════════════════════════════════════════════════════

FakeExecutor: canned 命令→输出映射，覆盖 sacct 状态序列、sbatch 提交解析、
哨兵 grep、sinfo 分区探测。全部离线，不碰真 slurm。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

import pytest

from flash.flash_run.remote.slurm_control import (
    LocalExecutor,
    SlurmJobSpec,
    cores_per_node,
    detect_partition,
    render_sbatch,
    run_job_chain,
    submit,
    wait_for_job,
)


class FakeExecutor:
    """canned 命令匹配执行器: 精确匹配 → 指定输出；否则 (含子串) 回落。"""

    def __init__(self, responses=None, state_sequence=None):
        # responses: {substring: (out, err, rc)}；state_sequence: sacct 依次弹出
        self.responses = dict(responses or {})
        self.state_sequence = list(state_sequence or [])
        self.commands: list = []

    def run(self, cmd: str, timeout: int = 120):
        self.commands.append(cmd)
        if "sacct" in cmd and "--format=State" in cmd:
            state = self.state_sequence.pop(0) if self.state_sequence else "COMPLETED"
            return f"{state}\n", "", 0
        for key, val in self.responses.items():
            if key in cmd:
                return val
        return "", "", 0


# ── submit ───────────────────────────────────────────────

def test_submit_parses_job_id():
    exe = FakeExecutor({"sbatch": ("Submitted batch job 4917041\n", "", 0)})
    assert submit(exe, "/wk/run.sh", workdir="/wk") == "4917041"


def test_submit_failure_raises():
    exe = FakeExecutor({"sbatch": ("sbatch: error: bad partition", "", 1)})
    with pytest.raises(RuntimeError):
        submit(exe, "/wk/run.sh", workdir="/wk")


# ── wait_for_job ─────────────────────────────────────────

def test_wait_completed_with_marker():
    exe = FakeExecutor(
        responses={"grep -l 'BUILD_OK'": ("/wk/build_1.out\nBUILD_OK", "", 0)},
        state_sequence=["PENDING", "RUNNING", "COMPLETED"])
    assert wait_for_job(exe, "1", marker="BUILD_OK",
                        out_glob="/wk/build_*.out", timeout=60, poll=0.05) is True


def test_wait_failed_returns_false_and_tails():
    exe = FakeExecutor(responses={"tail -25": ("ERR line", "", 0)},
                       state_sequence=["RUNNING", "FAILED"])
    assert wait_for_job(exe, "9", out_glob="/wk/run_*.out",
                        timeout=60, poll=0.05) is False


def test_wait_completed_without_marker_warns_but_true():
    # COMPLETED 但 marker 未命中 → 告警并返回 True（SNB 原版语义）
    exe = FakeExecutor(responses={}, state_sequence=["COMPLETED"])
    assert wait_for_job(exe, "2", marker="NOPE", out_glob="/wk/*",
                        timeout=30, poll=0.05) is True


def test_wait_timeout_returns_false():
    exe = FakeExecutor(state_sequence=["PENDING"] * 100)
    assert wait_for_job(exe, "3", timeout=0.2, poll=0.05) is False


# ── 分区/核数探测 ────────────────────────────────────────

def test_detect_partition_prefers_known_up():
    sinfo = "v5_192* up 48\nv6_384 up 96\nall inact 0\n"
    exe = FakeExecutor({"sinfo -s": (sinfo, "", 0)})
    assert detect_partition(exe, {"flash_ssh": "v5_192"}, "flash_ssh") == "v5_192"


def test_detect_partition_falls_back_to_first_up():
    sinfo = "v6_384 up 96\nall inact 0\n"
    exe = FakeExecutor({"sinfo -s": (sinfo, "", 0)})
    assert detect_partition(exe, {"flash_ssh": "v5_192"}, "flash_ssh") == "v6_384"


def test_detect_partition_fallback_default():
    exe = FakeExecutor()  # sinfo 输出空 → known 缺失 → v5_192 兜底
    assert detect_partition(exe, {}, "other") == "v5_192"


def test_cores_per_node():
    exe = FakeExecutor({'"%c"': ("48\n", "", 0)})
    assert cores_per_node(exe, "v5_192") == 48
    exe2 = FakeExecutor()  # 无输出 → default 兜底
    assert cores_per_node(exe2, "bad", default=96) == 96


# ── render_sbatch ────────────────────────────────────────

def test_render_sbatch_header_and_marker():
    spec = SlurmJobSpec(name="build", script="echo hi", partition="v5_192",
                        nodes=3, ntasks=131, env_block="module load mpich",
                        marker="BUILD_OK")
    txt = render_sbatch(spec, "/wk")
    assert txt.startswith("#!/bin/bash")
    assert "#SBATCH -p v5_192" in txt
    assert "#SBATCH -N 3" in txt
    assert "#SBATCH --ntasks=131" in txt
    assert "#SBATCH -o /wk/build_%j.out" in txt
    assert "cd /wk" in txt
    assert "module load mpich" in txt
    assert "echo BUILD_OK" in txt
    assert "\r" not in txt                          # LF 行尾


def test_render_sbatch_no_partition():
    txt = render_sbatch(SlurmJobSpec(name="j", script="true"), "/wk")
    assert "#SBATCH -p" not in txt


# ── run_job_chain ────────────────────────────────────────

def test_job_chain_build_then_run():
    exe = FakeExecutor(
        responses={
            "grep -l 'BUILD_OK'": ("BUILD_OK", "", 0),
            "grep -l 'RUN_DONE'": ("RUN_DONE", "", 0),
            "sbatch": ("Submitted batch job 1000", "", 0),  # 键=命令子串
        },
        state_sequence=["PENDING", "COMPLETED", "RUNNING", "COMPLETED"])
    build = SlurmJobSpec(name="build", script="make", marker="BUILD_OK", poll=0.05)
    run = SlurmJobSpec(name="run", script="mpiexec ./flash4", marker="RUN_DONE",
                       poll=0.05)
    assert run_job_chain(exe, [build, run], "/wk") is True
    submitted = [c for c in exe.commands if "sbatch" in c]
    assert len(submitted) == 2
    assert "sbatch /wk/build.sh" in submitted[0]
    assert "sbatch /wk/run.sh" in submitted[1]


def test_job_chain_gate_blocks_run():
    exe = FakeExecutor({"sbatch": ("Submitted batch job 1", "", 0)},
                       state_sequence=["COMPLETED"])
    gate_calls = []

    def bad_gate(exe):
        gate_calls.append(1)
        return False

    jobs = [SlurmJobSpec(name="build", script="make"),
            SlurmJobSpec(name="run", script="mpiexec")]
    assert run_job_chain(exe, jobs, "/wk",
                         gates={"run": bad_gate}) is False
    assert gate_calls == [1]
    # build 已提交、run 被闸门拦截
    assert len([c for c in exe.commands if "sbatch" in c]) == 1


def test_job_chain_skip_first_if():
    exe = FakeExecutor(
        responses={"sbatch": ("Submitted batch job 7", "", 0),
                   "grep -l 'RUN_DONE'": ("RUN_DONE", "", 0)},
        state_sequence=["COMPLETED"])
    jobs = [SlurmJobSpec(name="build", script="make"),
            SlurmJobSpec(name="run", script="mpiexec", marker="RUN_DONE")]
    assert run_job_chain(exe, jobs, "/wk", skip_first_if=lambda e: True) is True
    assert len([c for c in exe.commands if "sbatch" in c]) == 1


# ── LocalExecutor 冒烟（无 slurm 环境也能跑的纯 bash 命令）──

def test_local_executor_basic():
    exe = LocalExecutor()
    out, err, rc = exe.run("echo HELLO_LOCAL")
    assert rc == 0 and "HELLO_LOCAL" in out
