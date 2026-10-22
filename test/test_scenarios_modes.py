"""
test_scenarios_modes.py — 三模式体系单测（runner.py，2026-10-22）
════════════════════════════════════════════════════════════════

覆盖:
  * normalize/resolve 优先级（explicit > FLASH_RUN_MODE > default）
  * 别名兼容（hpc→hpc-remote 永续；local/remote/slurm 老别名不破坏）
  * detect_native_linux / bash_launcher 平台分叉
  * runs_root 环境变量覆盖与默认兄弟目录
  * resolve_venv_python 平台解析
"""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

import pytest

from flash.scenarios.runner import (
    RUN_MODES,
    bash_launcher,
    detect_native_linux,
    normalize_run_mode,
    resolve_venv_python,
    resolve_run_mode,
    runs_root,
)


# ── normalize / resolve ──────────────────────────────────

def test_run_modes_canonical():
    assert RUN_MODES == ("wsl", "hpc-remote", "hpc-insitu")


def test_normalize_aliases():
    assert normalize_run_mode("hpc") == "hpc-remote"          # 老别名永续
    assert normalize_run_mode("local") == "wsl"
    assert normalize_run_mode("remote") == "hpc-remote"
    assert normalize_run_mode("slurm") == "hpc-remote"
    assert normalize_run_mode("insitu") == "hpc-insitu"
    assert normalize_run_mode("in-situ") == "hpc-insitu"
    assert normalize_run_mode("hpc-in-situ") == "hpc-insitu"
    assert normalize_run_mode("HPC") == "hpc-remote"          # 大小写不敏感
    for m in RUN_MODES:
        assert normalize_run_mode(m) == m


def test_normalize_unknown_raises():
    with pytest.raises(ValueError):
        normalize_run_mode("quantum")


def test_resolve_priority_explicit_beats_env(monkeypatch):
    monkeypatch.setenv("FLASH_RUN_MODE", "hpc")
    assert resolve_run_mode("wsl") == "hpc-remote"            # env 优先于 default
    assert resolve_run_mode("wsl", explicit="wsl") == "wsl"   # explicit 最高


def test_resolve_default_without_env(monkeypatch):
    monkeypatch.delenv("FLASH_RUN_MODE", raising=False)
    assert resolve_run_mode("wsl") == "wsl"
    assert resolve_run_mode("hpc") == "hpc-remote"
    assert resolve_run_mode("hpc-insitu") == "hpc-insitu"


# ── 平台检测 ─────────────────────────────────────────────

def test_detect_native_linux_matches_os_name():
    assert detect_native_linux() == (os.name != "nt")


def test_bash_launcher_platform():
    launcher = bash_launcher()
    if os.name == "nt":
        assert launcher == ["wsl", "bash", "-c"]
    else:
        assert launcher == ["bash", "-c"]


# ── 目录契约 ─────────────────────────────────────────────

def test_runs_root_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASH_RUNS_DIR", str(tmp_path / "my_runs"))
    assert runs_root() == tmp_path / "my_runs"


def test_runs_root_default_sibling(monkeypatch):
    monkeypatch.delenv("FLASH_RUNS_DIR", raising=False)
    rr = runs_root()
    assert rr.name == "flash_sim_runs"
    # 兄弟目录: 与包根同父
    from flash.scenarios.runner import package_root
    assert rr.parent == package_root().parent


def test_resolve_venv_python_returns_path_or_none():
    py = resolve_venv_python()
    if py is not None:
        assert py.is_file()
        assert "python" in py.name.lower()
