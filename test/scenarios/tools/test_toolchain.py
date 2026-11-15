# -*- coding: utf-8 -*-
"""收纳整理工具链测试：clone_scene（dry-run 模式）+ 门禁。
（场景收纳整理 2026-11-05 共享区整理 3/3；2026-11-11 收纳改造更新）

★ 2026-11-11：relocate_scene.py 已删除（场景移动 = 文件管理器直接剪切粘贴，
  位置信息随锚点表 v2 + scene.json hpc 节自动跟随）——TestRelocateScene 随之移除。
★ 场景目录夹具一律经 discovery ``resolve_scene_meta()`` 按名解析（位置无关），
  不再字面量拼接包路径——场景目录移动后测试自动跟随。

clone 的 dry-run 不落盘，可直接对真实仓库树断言行为；
门禁（audit/verify --strict）以子进程跑，断言退出码 0。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_PY = sys.executable
_RELOCATE = _REPO / "flash" / "scenarios" / "scripts" / "relocate"

if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _scene_dir(scene_key: str) -> Path:
    """经 discovery 按场景名/别名解析场景目录（位置无关，移动免疫）。"""
    from flash.scenarios.core.scene_reg.discovery import resolve_scene_meta
    meta = resolve_scene_meta(scene_key)
    assert meta is not None and meta.source, f"场景 {scene_key!r} 未被 discovery 发现"
    return Path(meta.source).parent


def _env() -> dict:
    """子进程注入仓库根到 PYTHONPATH 首位。

    ``python <脚本绝对路径>`` 启动时 sys.path[0] 是脚本所在目录，
    仓库根不在其中；若 site-packages 装了同名旧版 ``flash`` 包，
    ``import flash.scenarios.core`` 会命中旧包而报 ModuleNotFoundError。
    注入后测试自完备，不依赖外部 runner 是否设置过 PYTHONPATH。
    """
    env = os.environ.copy()
    sep = os.pathsep
    paths = [p for p in env.get("PYTHONPATH", "").split(sep) if p]
    if str(_REPO) not in paths:
        paths.insert(0, str(_REPO))
    env["PYTHONPATH"] = sep.join(paths)
    return env


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(_PY), str(script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_REPO), timeout=300, env=_env(),
    )


class TestCloneSceneDryRun:
    def test_dry_run_reports_and_writes_nothing(self):
        """dry-run：打印克隆计划但不产生目标目录（目标须在 scenarios 树内）。"""
        src = _scene_dir("ch_center_t")
        dst = src.parent / "_clone_probe_tmp"
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
        src = _scene_dir("ch_center_t")
        r = _run(_RELOCATE / "clone_scene.py", str(src), "whatever",
                 "--dst", str(tmp_path / "whatever"))
        assert r.returncode == 2

    def test_rejects_invalid_name(self):
        src = _scene_dir("ch_center_t")
        r = _run(_RELOCATE / "clone_scene.py", str(src), "9bad name")
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
            cwd=str(_REPO), timeout=300, env=_env(),
        )
        assert r.returncode == 0
        # 36 场景 + 表头 2 行
        assert len([l for l in r.stdout.splitlines() if l.strip()]) >= 30
