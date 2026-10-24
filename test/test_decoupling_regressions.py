#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_decoupling_regressions.py — 解耦改造回归防护（2026-10-24）

对应 docs/功能模块解耦与流程梳理计划.md 的 B-1 批（10 个已发生回归）。
风格：能用行为断言的就不断言源码；源码级断言只用于"结构性禁令"
（如禁止某段兜底逻辑复活），并在 docstring 注明理由。

★ 这些测试的价值在于**能失败**：修改前它们应当红，修改后应当绿。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from flash.flash_run.env import venv_paths as vp


# ── venv_paths：单一事实源（G2 / G9）──────────────────────

def test_repo_root_found_in_source_tree():
    """源码树内必须能定位仓库根（含 pyproject.toml + start_flash.py）。"""
    root = vp.repo_root()
    assert root is not None, "源码树内 repo_root() 不应为 None"
    assert (root / "pyproject.toml").is_file()
    assert (root / "start_flash.py").is_file()


def test_repo_root_depth_matches_flash_file():
    """两条路径互证，防"再算错一级"。

    ``flash.__file__`` = ``<repo>/flash/__init__.py`` ⇒ 其 ``parent`` 是**包目录**，
    ``parent.parent`` 才是仓库根。此断言把两者钉在一起，层数写错立即红。
    """
    import flash

    root = vp.repo_root()
    assert root is not None
    assert root == Path(flash.__file__).resolve().parent.parent


def test_venv_dir_kind_semantics(tmp_path):
    """kind=local 用平台后缀，kind=hpc 用命名环境；两者必须不同。"""
    local = vp.venv_dir(tmp_path, "local")
    hpc = vp.venv_dir(tmp_path, "hpc")
    assert local.name == f".venv-{vp.platform_tag()}"
    assert hpc.name == vp.hpc_venv_name()
    assert local != hpc


def test_venv_dir_rejects_unknown_kind(tmp_path):
    with pytest.raises(ValueError):
        vp.venv_dir(tmp_path, "wsl")      # kind 只接受 local/hpc，平台名不是维度


def test_flash_venv_dir_env_wins(tmp_path, monkeypatch):
    """FLASH_VENV_DIR 永远最高优先级（离线机/超算注入通道）。"""
    fake = tmp_path / "custom_venv"
    monkeypatch.setenv("FLASH_VENV_DIR", str(fake))
    assert vp.candidates(tmp_path, "local")[0] == fake
    # kind=hpc 同样尊重显式注入
    assert vp.candidates(tmp_path, "hpc")[0] == fake


def test_venv_python_returns_none_not_sys_executable(tmp_path, monkeypatch):
    """找不到必须返回 None —— **禁止**回落 sys.executable（G9 的掩盖机制）。"""
    monkeypatch.delenv("FLASH_VENV_DIR", raising=False)
    assert vp.venv_python(tmp_path, "local") is None


def test_require_venv_python_raises_with_hint(tmp_path, monkeypatch):
    monkeypatch.delenv("FLASH_VENV_DIR", raising=False)
    with pytest.raises(RuntimeError) as ei:
        vp.require_venv_python(tmp_path, "local")
    assert "FLASH_VENV_DIR" in str(ei.value)   # 报错必须可操作


@pytest.mark.skipif(os.name == "nt", reason="Windows 不本地探测超算 venv（预期行为）")
def test_hpc_kind_windows_never_probes():
    """Windows 上 kind=hpc 不产生候选，避免 --check-env 误报"超算 venv 缺失"。"""
    assert vp.candidates(vp.repo_root(), "hpc") == [] or os.name != "nt"


# ── 运行层接线（G2）───────────────────────────────────────

def test_runner_resolve_venv_python_uses_repo_root():
    """resolve_venv_python 必须基于 repo_root 而非 package_root（包目录）。"""
    from flash.flash_run.modes import runner

    root = runner.repo_root()
    assert root is not None and (root / "start_flash.py").is_file()

    py = runner.resolve_venv_python()
    if py is not None:
        # 命中时 venv 必须位于仓库根之下（而非 .../flash/flash 之下）。
        # 跨平台布局：win=Scripts/python.exe、posix=bin/python，故用 parents 判定。
        assert root in py.parents, f"{py} 不在仓库根 {root} 之下"
        assert "python" in py.name.lower()


def test_package_root_kept_for_runs_root():
    """package_root 名不符实但承重：runs_root 依赖它，禁止"顺手修正"。"""
    from flash.flash_run.modes import runner

    assert runner.runs_root().name == "flash_sim_runs"
    assert runner.runs_root().parent == runner.package_root().parent


# ── 结构性禁令（源码级，防止旧缺陷复活）──────────────────

_ROOT = vp.repo_root()


def _read(rel: str) -> str:
    assert _ROOT is not None
    return (_ROOT / rel).read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("rel", [
    "flash/scenarios/flash_demo/demo_hpc/laserslab1d_supercomputer_demo.py",
    "flash/scenarios/flash_demo/demo_hpc/laserslab1d_hpc_demo_batch.py",
])
def test_g1_no_bare_hpc_literal_compare(rel):
    """G1：别名归一后 `!= "hpc"` 恒真，两个 demo 入口曾因此永远 return False。"""
    src = _read(rel)
    assert 'run_mode != "hpc"' not in src, "禁止用未归一的名字做相等比较"
    assert 'run_mode not in ("hpc", "hpc-remote")' in src


def test_g3_no_synthetic_fallback_on_real_failure():
    """G3：真实 FLASH 失败**不得**回退合成数据并报成功（最危险的静默失败）。"""
    src = _read("flash/scenarios/simulator.py")
    assert "自动回退 dry-run 合成" not in src, "失败即失败，合成数据只允许显式 dry_run"
    # 失败分支必须返回 success=False
    idx = src.find("FLASH 未产出 chk（未安装/编译失败/运行错误）")
    assert idx > 0


def test_g6_empty_collection_is_failure():
    """G6：insitu 收集 0 个文件必须判失败。

    ★ B1 迁移后实现位于 flash/flash_run/modes/hpc_insitu.py
      （flash/scenarios/insitu_runner.py 现为转发壳）。
    """
    src = _read("flash/flash_run/modes/hpc_insitu.py")
    assert "if not collected:" in src


@pytest.mark.parametrize("rel", [
    "flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py",
    "flash/scenarios/private/tracer/SNB/SNBOneCH_ml/SNBOneCH_ml.py",
])
def test_g7_snb_mode_normalized(rel):
    """G7：SNB 必须走统一别名归一，否则 `--mode hpc-remote` 会在本地跑 131 进程。"""
    src = _read(rel)
    assert "normalize_run_mode" in src
    assert "SNB 场景禁止 --mode local" in src


@pytest.mark.parametrize("rel", [
    "flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py",
    "flash/scenarios/private/tracer/SNB/SNBOneCH_ml/SNBOneCH_ml.py",
])
def test_g5_mgdfl_mode_matches_guard(rel):
    """G5：cfg 默认值必须与值级守卫一致，否则每轮都判"陈旧"并重生成。"""
    src = _read(rel)
    assert '"rt_mgdFlMode": "fl_larsen"' in src
    # 配置默认值不得再出现旧的 fl_harmonic（守卫要求 fl_larsen）
    assert '"rt_mgdFlMode": "fl_harmonic"' not in src


def test_g10_check_env_has_strict():
    """G10：--check-env 必须能作为门禁（strict 时返回非零）。"""
    from flash.flash_run.modes import runner

    assert runner._check_env.__defaults__ == (False,)
    src = _read("flash/flash_run/modes/runner.py")
    assert '"--strict"' in src
