# -*- coding: utf-8 -*-
"""收纳整理工具链测试：clone_scene / relocate_scene（dry-run 模式）+ 门禁。
（场景收纳整理 2026-11-05 共享区整理 3/3）

clone/relocate 的 dry-run 不落盘，可直接对真实仓库树断言行为；
门禁（audit/verify --strict）以子进程跑，断言退出码 0。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_PY = sys.executable
_RELOCATE = _REPO / "flash" / "scenarios" / "scripts" / "relocate"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(_PY), str(script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_REPO), timeout=300,
    )


class TestCloneSceneDryRun:
    def test_dry_run_reports_and_writes_nothing(self):
        """dry-run：打印克隆计划但不产生目标目录（目标须在 scenarios 树内）。"""
        src = _REPO / "flash" / "scenarios" / "public" / "center_evolution" / "ch_center_t"
        dst = _REPO / "flash" / "scenarios" / "public" / "center_evolution" / "_clone_probe_tmp"
        try:
            r = _run(_RELOCATE / "clone_scene.py", str(src), "ch_center_probe",
                     "--dst", str(dst), "--dry-run")
            assert r.returncode == 0, r.stderr[-500:]
            assert not dst.exists(), "dry-run 不得落盘"
            assert "ch_center_probe" in r.stdout
        finally:
            if dst.exists():   # 防御：任何意外残留立即清除
                shutil.rmtree(dst, ignore_errors=True)

    def test_rejects_dst_outside_scenarios_tree(self, tmp_path):
        src = _REPO / "flash" / "scenarios" / "public" / "center_evolution" / "ch_center_t"
        r = _run(_RELOCATE / "clone_scene.py", str(src), "whatever",
                 "--dst", str(tmp_path / "whatever"))
        assert r.returncode == 2

    def test_rejects_invalid_name(self):
        src = _REPO / "flash" / "scenarios" / "public" / "center_evolution" / "ch_center_t"
        r = _run(_RELOCATE / "clone_scene.py", str(src), "9bad name")
        assert r.returncode == 2


class TestRelocateSceneDryRun:
    def test_dry_run_same_tree_guard(self, tmp_path):
        """目标在 scenarios 树外 → 拒绝（退出码 2）。"""
        src = _REPO / "flash" / "scenarios" / "public" / "center_evolution" / "ch_center_t"
        r = _run(_RELOCATE / "relocate_scene.py", str(src), str(tmp_path / "x"))
        assert r.returncode == 2

    def test_dry_run_missing_src(self, tmp_path):
        dst_inside = _REPO / "flash" / "scenarios" / "public" / "_probe_dst"
        r = _run(_RELOCATE / "relocate_scene.py",
                 str(_REPO / "flash" / "scenarios" / "public" / "_no_such_scene"),
                 str(dst_inside), "--dry-run")
        assert r.returncode == 2


class TestGates:
    """收纳整理门禁：整理前后必须全绿（audit ERROR=0 / verify 全过）。"""

    def test_audit_strict_exit_zero(self):
        r = _run(_RELOCATE / "audit_portable.py", "--strict")
        assert r.returncode == 0, r.stdout[-800:]

    def test_verify_all_strict_exit_zero(self):
        r = _run(_RELOCATE / "verify_all_scenes.py", "--strict")
        assert r.returncode == 0, r.stdout[-800:]

    def test_cli_list_nonempty(self):
        r = subprocess.run(
            [str(_PY), "-m", "flash.scenarios.core.entry.cli", "list"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_REPO), timeout=300,
        )
        assert r.returncode == 0
        # 36 场景 + 表头 2 行
        assert len([l for l in r.stdout.splitlines() if l.strip()]) >= 30
