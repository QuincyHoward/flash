"""
test_insitu_runner.py — hpc-insitu 编排单测（2026-10-22）
════════════════════════════════════════════════════════════

全部离线：sbatch_available / run_job_chain 打 mock；collect_local 用 tmp_path
构造 chk/plt/日志文件验证 fetch_policy chk-only 过滤与就地移动。
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

import pytest

import flash.flash_run.modes.hpc_insitu as ir   # 实现模块（monkeypatch 目标）
from flash.flash_run.remote.slurm_control import SlurmJobSpec
# ★ 兼容性断言：旧路径 flash.scenarios.insitu_runner 仍须可用（B1 迁移后为转发壳）。
#   公开 API 故意从旧路径导入，确保 shim 不断链。
from flash.scenarios.insitu_runner import (
    InsituSpec,
    collect_local,
    resolve_hpc_python,
    run_insitu,
)


# ── collect_local ────────────────────────────────────────

@pytest.fixture
def fake_objdir(tmp_path):
    obj = tmp_path / "SNB_obj"
    obj.mkdir()
    for n in ("snbonechmug_hdf5_chk_0000", "snbonechmug_hdf5_chk_0001",
              "snbonechmug_hdf5_plt_0000", "snbonechmug_LaserEnergyProfile.dat",
              "wsl_run_snbonech_m.log"):
        (obj / n).write_bytes(b"x" * 64)
    return obj


def test_collect_local_chk_only_moves(fake_objdir, tmp_path):
    out = tmp_path / "out"
    collected, stats = collect_local(str(fake_objdir), out, basenm="snbonechmug",
                                     with_plt=False, move=True)
    names = sorted(p.name for p in out.iterdir())
    # chk 2 个 + fixed 2 个（dat/log）；plt 被 chk-only 策略跳过
    assert names == ["snbonechmug_LaserEnergyProfile.dat",
                     "snbonechmug_hdf5_chk_0000",
                     "snbonechmug_hdf5_chk_0001",
                     "wsl_run_snbonech_m.log"]
    assert stats["plt_skipped"] == 1 and stats["n_chk"] == 2
    # move=True: 源文件已删（plt 除外——未被 picked）
    assert not (fake_objdir / "snbonechmug_hdf5_chk_0000").exists()
    assert (fake_objdir / "snbonechmug_hdf5_plt_0000").exists()


def test_collect_local_with_plt_copies(fake_objdir, tmp_path):
    out = tmp_path / "out"
    collected, stats = collect_local(str(fake_objdir), out, basenm="snbonechmug",
                                     with_plt=True, move=False)
    assert stats["plt_skipped"] == 0
    assert (out / "snbonechmug_hdf5_plt_0000").exists()
    # move=False: 源保留
    assert (fake_objdir / "snbonechmug_hdf5_chk_0000").exists()


def test_collect_local_missing_objdir(tmp_path):
    collected, stats = collect_local(str(tmp_path / "nope"), tmp_path / "out",
                                     basenm="x")
    assert collected == [] and stats["n_chk"] == 0


# ── resolve_hpc_python ───────────────────────────────────

def test_resolve_hpc_python_falls_back_to_sys(monkeypatch, tmp_path):
    monkeypatch.delenv("FLASH_VENV_DIR", raising=False)
    # 无 .venv-hpc-nce 的环境 → sys.executable 兜底
    monkeypatch.setattr(ir, "__file__", str(tmp_path / "x" / "insitu_runner.py"))
    assert ir.resolve_hpc_python() == sys.executable


# ── run_insitu（mock 作业链）────────────────────────────

@pytest.fixture
def spec(tmp_path):
    input_dir = tmp_path / "flash_input"
    input_dir.mkdir()
    (input_dir / "Config").write_text("unit test")
    (input_dir / "grid.par").write_text("par")
    obj = tmp_path / "FLASH4.8" / "SNB_obj"     # ★ objdir 必须在 flash_home 下
    obj.mkdir(parents=True)
    (obj / "snbonechmug_hdf5_chk_0000").write_bytes(b"chk")
    (obj / "wsl_run_snbonech_m.log").write_bytes(b"log")
    return InsituSpec(
        name="SNBOneCH_m",
        input_dir=input_dir,
        runs_dir=tmp_path / "runs" / "SNBOneCH_m",
        flash_home=str(tmp_path / "FLASH4.8"),
        objdir="SNB_obj",
        basenm="snbonechmug",
        jobs=[SlurmJobSpec(name="build", script="make", marker="BUILD_OK",
                           poll=0.05),
              SlurmJobSpec(name="run", script="mpiexec", marker="RUN_DONE",
                           poll=0.05)],
        log_names=("wsl_run_snbonech_m.log",),
    )


def test_run_insitu_happy_path(spec, tmp_path, monkeypatch):
    monkeypatch.setattr(ir, "sbatch_available", lambda exe: True)
    monkeypatch.setattr(ir, "run_job_chain", lambda exe, jobs, wd, **kw: True)
    assert run_insitu(spec, cfg={"collect_move": True}) is True

    run_dirs = list(spec.runs_dir.iterdir())
    assert len(run_dirs) == 1
    rd = run_dirs[0]
    assert (rd / "input" / "Config").exists()           # 输入快照
    assert (rd / "output" / "snbonechmug_hdf5_chk_0000").exists()
    assert (rd / "output" / "wsl_run_snbonech_m.log").exists()
    state = json.loads((rd / "state.json").read_text(encoding="utf-8"))
    assert state["ok"] is True and state["mode"] == "hpc-insitu"
    assert state["run_id"] == 1


def test_run_insitu_job_chain_failure(spec, tmp_path, monkeypatch):
    monkeypatch.setattr(ir, "sbatch_available", lambda exe: True)
    monkeypatch.setattr(ir, "run_job_chain", lambda exe, jobs, wd, **kw: False)
    assert run_insitu(spec) is False
    rd = list(spec.runs_dir.iterdir())[0]
    state = json.loads((rd / "state.json").read_text(encoding="utf-8"))
    assert state["ok"] is False and "作业链失败" in state["note"]


def test_run_insitu_without_slurm_fails_fast(spec, monkeypatch):
    monkeypatch.setattr(ir, "sbatch_available", lambda exe: False)
    assert run_insitu(spec) is False
    assert not spec.runs_dir.exists() or not list(spec.runs_dir.iterdir())


def test_run_insitu_run_id_increments(spec, tmp_path, monkeypatch):
    monkeypatch.setattr(ir, "sbatch_available", lambda exe: True)

    def _fake_chain(exe, jobs, wd, **kw):
        # ★ 2026-10-24：G6 起"收集 0 文件"判失败。旧测试靠"产物已被上一轮
        #   collect_move 移走、第二轮空收集仍返回 True"通过，等于把缺陷当契约。
        #   真实 FLASH 每轮都会重写 chk ⇒ 此处模拟重产出，保持严格判据。
        obj = tmp_path / "FLASH4.8" / "SNB_obj"
        obj.mkdir(parents=True, exist_ok=True)
        (obj / "snbonechmug_hdf5_chk_0000").write_bytes(b"chk")
        (obj / "wsl_run_snbonech_m.log").write_bytes(b"log")
        return True

    monkeypatch.setattr(ir, "run_job_chain", _fake_chain)
    assert run_insitu(spec) is True
    assert run_insitu(spec) is True
    ids = sorted(p.name for p in spec.runs_dir.iterdir())
    assert ids == ["run_000001", "run_000002"]
