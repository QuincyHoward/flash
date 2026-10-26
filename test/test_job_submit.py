# -*- coding: utf-8 -*-
"""test_job_submit.py — 通用超算提交服务（`flash.flash_run.remote.job_submit`）
════════════════════════════════════════════════════════════════════════════

★ 覆盖

  · `JobRequest` → `render_job()`：完整 sbatch 脚本文本（离线，可测）
  · `submit_job()`：落盘 → sbatch → 解析 JobID（用假 executor）
  · 失败路径：落盘失败 / sbatch 未解析出 JobID ⇒ **ok=False**（不报假成功）
  · `dry_run`：只渲染，不落盘不提交

★ 与场景无关：这里的用例**不出现任何场景名** ——
  场景声明在 `flash.scenarios.hpc_job`（另见 test_scenarios_modes.py）。
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

from flash.flash_run.remote.job_layout import JobLayout, ResourceSpec
from flash.flash_run.remote.job_submit import JobRequest, render_job, submit_job


# ── 夹具 ────────────────────────────────────────────────────────────

def _request(**kw) -> JobRequest:
    base = dict(
        name="flash_test",
        flash_home="/home/u/QC/FLASH/FLASH4.8",
        unit="QC/myunit",
        setup_args=("-1d", "+cartesian"),
        par_file="my.par",
        source_dir="/shared/sim_input",
        layout=JobLayout(
            scratch_root="/tmp",
            shared_root="/shared",
            scratch_prefix="flash_${SLURM_JOB_ID:-$$}",
            build_dir="obj",
            run_dir="run",
            output_dir="out",
            log_dir="logs",
        ),
        resource=ResourceSpec(nodes=1, ntasks=4, time_limit="02:00:00"),
        ntasks=4,
    )
    base.update(kw)
    return JobRequest(**base)


class FakeExecutor:
    """记录命令、返回预设输出的假执行器。"""

    def __init__(self, write_rc=0, submit_out="Submitted batch job 123456", submit_rc=0):
        self.commands: list[str] = []
        self.write_rc = write_rc
        self.submit_out = submit_out
        self.submit_rc = submit_rc

    def run(self, cmd: str, timeout: int = 120):
        self.commands.append(cmd)
        if "cat >" in cmd:          # ① 落盘命令
            return "", "write failed", self.write_rc
        return self.submit_out, "", self.submit_rc


# ── 渲染 ────────────────────────────────────────────────────────────

def test_render_job_contains_sbatch_and_body():
    r = render_job(_request())
    txt = r.script_text
    assert txt.startswith("#!/bin/bash")
    assert "#SBATCH --ntasks=4" in txt
    assert "#SBATCH --time=02:00:00" in txt
    # 作业体四步齐全
    assert "stage：shared → scratch" in txt
    assert "build：编译" in txt
    assert "run：运行" in txt
    assert "归档：scratch → shared" in txt
    # 目录变量
    assert 'export FL_SHARED_ROOT="/shared"' in txt
    assert "/shared/out" in txt


def test_render_job_scratch_is_separate_from_shared():
    """★ 编译/运行目录必须在 scratch（节点本地），产物在 shared。"""
    txt = render_job(_request()).script_text
    assert 'export FL_BUILD_DIR="${FL_SCRATCH_ROOT}/obj"' in txt
    assert 'export FL_RUN_DIR="${FL_SCRATCH_ROOT}/run"' in txt
    assert 'export FL_OUTPUT_DIR="/shared/out"' in txt


def test_render_job_setup_is_non_interactive():
    """★ setup 必须非交互（否则批处理里 stdin 为空 ⇒ EOFError）。"""
    txt = render_job(_request()).script_text
    assert "printf '%s\\n' 'Y' | ./setup" in txt
    assert "-parfile=my.par" in txt


def test_render_job_paths_are_reported():
    r = render_job(_request())
    assert r.script_path == "/shared/logs/flash_test.sh"
    assert r.output_dir == "/shared/out"
    assert r.log_dir == "/shared/logs"


# ── 提交 ────────────────────────────────────────────────────────────

def test_submit_job_returns_job_id():
    exe = FakeExecutor()
    res = submit_job(_request(), executor=exe)
    assert res["ok"] is True
    assert res["job_id"] == "123456"
    assert res["reason"] == ""
    # 返回值键集固定（调用方按 key 取用 ⇒ 缺键会 KeyError）
    assert set(res) == {"ok", "job_id", "job_name", "script_path", "log_dir",
                        "output_dir", "reason"}
    assert res["job_name"] == "flash_test"
    # 落盘 + 提交两步都发生了
    assert len(exe.commands) == 2
    assert "cat >" in exe.commands[0]
    assert "sbatch" in exe.commands[1]


def test_submit_job_failure_paths_keep_same_keys():
    """★ 失败路径也必须返回同一套键（否则调用方 KeyError）。"""
    for exe in (FakeExecutor(write_rc=1), FakeExecutor(submit_out="err")):
        res = submit_job(_request(), executor=exe)
        assert res["ok"] is False
        assert set(res) == {"ok", "job_id", "job_name", "script_path",
                            "log_dir", "output_dir", "reason"}


def test_submit_job_write_failure_is_not_success():
    """★ 落盘失败必须 ok=False（不得报假成功）。"""
    res = submit_job(_request(), executor=FakeExecutor(write_rc=1))
    assert res["ok"] is False
    assert "落盘失败" in res["reason"]


def test_submit_job_without_jobid_is_not_success():
    """★ sbatch 没解析出 JobID ⇒ 失败（"命令返回 0" ≠ "作业已入队"）。"""
    res = submit_job(_request(), executor=FakeExecutor(submit_out="sbatch: error"))
    assert res["ok"] is False
    assert res["job_id"] == ""
    assert "未解析出 JobID" in res["reason"]


def test_submit_job_dry_run_does_not_execute():
    exe = FakeExecutor()
    res = submit_job(_request(), executor=exe, dry_run=True)
    assert res["ok"] is True
    assert res["reason"] == "dry-run"
    assert exe.commands == [], "dry-run 不得执行任何命令"


def test_submit_job_writes_lf_line_endings():
    """★ 落盘时必须剥离 CRLF（否则 sbatch 报 `\\r: command not found`）。"""
    exe = FakeExecutor()
    submit_job(_request(), executor=exe)
    assert "sed -i 's/\\r$//'" in exe.commands[0]


# ── 边界：执行层不认识任何场景 ─────────────────────────────────────

def test_job_request_has_no_scene_field():
    """★ 通用请求里**不得**有场景字段（场景声明在场景层）。"""
    fields = set(JobRequest.__dataclass_fields__)
    for banned in ("scene", "scene_name", "scenario"):
        assert banned not in fields
