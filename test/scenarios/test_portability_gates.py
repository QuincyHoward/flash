# -*- coding: utf-8 -*-
"""test_portability_gates.py — 场景可移植性门禁（2026-11-11 收纳改造）
════════════════════════════════════════════════════════════════════════

目标工作流：**场景文件夹在文件管理器里直接剪切粘贴即可移动**，零脚本零配置。
本文件把"位置无关"从口号变成 pytest 红灯：

  ① 锚点表全解析 —— v2 条目（``<场景名>::<相对路径>``）经 discovery 按名
     解析必须成功（场景被删/改名即红灯）；目录本地缺失仅 WARN（远端布局
     锚点属正常）；legacy 条目（SNB 组，目标无 scene.json 无法按名寻址）
     断言本地目录存在 —— 被移走即红灯，提醒 manifest 化。
  ② hpc 提交声明路径有效性 —— list_scene_hpc_jobs() 每条 input_rel_dir /
     gen_script 相对仓库根必须存在（scene.json hpc 节 ``./`` 相对形式 +
     discovery 解析，移动自动跟随；此断言防回归到硬编码字面量）。
  ③ hpc 别名回退 —— 消费方可用 scene.json 显式 name/别名键查询
     （thin_layer_sandwich_si → 生效名 thin_layer_sandwich）；未知名 KeyError。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


# ── ① 锚点表 ──────────────────────────────────────────────

def test_anchors_v2_resolve_by_scene_name():
    """v2 条目经 discovery 按名解析成功（位置无关的核心保证）。"""
    from flash.scenarios.core.anchors import anchors_table, resolve_anchor

    v2_keys = [k for k, v in anchors_table().items()
               if not k.startswith("_") and "::" in str(v)]
    assert v2_keys, "锚点表中无 v2 条目（迁移丢失？）"
    for k in v2_keys:
        p, warn = resolve_anchor(k)          # 场景名不可解析 → KeyError → 红灯
        assert p is not None
        print(f"  [v2] {k} -> {p}" + (f"  (WARN: {warn})" if warn else ""))


def test_anchors_legacy_targets_exist_locally():
    """legacy 条目（SNB 组）目标本地必须存在。

    legacy = 无法按场景名寻址的历史遗留（private/SNB 全树无 scene.json）。
    目录被移走 → 本用例红灯，提醒把 SNB 资源目录 manifest 化或同步改表。
    """
    from flash.scenarios.core.anchors import anchors_table, resolve_anchor

    legacy_keys = [k for k, v in anchors_table().items()
                   if not k.startswith("_") and "::" not in str(v)]
    assert legacy_keys, "SNB legacy 锚点缺失（已全部 manifest 化？可更新本用例）"
    for k in legacy_keys:
        p, _ = resolve_anchor(k)
        assert p.is_dir(), (
            f"legacy 锚点 {k} → {p} 不存在：该目录被移动/删除。"
            f"legacy 值不会随移动自动跟随，请把目标 manifest 化（scene.json）"
            f"或同步更新 _scene_anchors.json")
        print(f"  [legacy] {k} -> {p}")


# ── ② hpc 提交声明路径有效性 ──────────────────────────────

def test_hpc_job_paths_exist_relative_to_repo():
    """每条超算提交声明的 input_rel_dir / gen_script 相对仓库根必须存在。

    声明唯一事实源 = scene.json ``hpc`` 节（``./`` 相对形式经 discovery
    解析为仓库根相对路径）→ 场景目录移动后此断言自动跟随；
    若有人回退为硬编码字面量，移动场景后本用例即红灯。
    """
    from flash.scenarios.core.hpc.hpc_job import list_scene_hpc_jobs

    jobs = list_scene_hpc_jobs()
    assert jobs, "无任何超算提交声明（manifest hpc 节全部丢失？）"
    for j in jobs:
        input_dir = _REPO / j.input_rel_dir
        gen = _REPO / j.gen_script
        assert input_dir.is_dir(), (
            f"{j.name}: input_rel_dir 不存在: {j.input_rel_dir}（声明路径与场景"
            f"实际位置脱钩？检查 scene.json hpc 节是否为 './' 相对形式）")
        assert gen.is_file(), f"{j.name}: gen_script 不存在: {j.gen_script}"
        print(f"  [hpc] {j.name}: {j.input_rel_dir}")


# ── ③ hpc 别名回退 ────────────────────────────────────────

def test_hpc_job_alias_fallback():
    """别名键查询命中（thin_layer_sandwich_si → 生效名 thin_layer_sandwich）。

    断言不变量：声明路径 == 场景 discovery **实时位置**下的对应子路径
    （目录移动/改名后自动跟随，不写死目录名）。
    """
    from pathlib import Path

    from flash.scenarios.core.hpc.hpc_job import get_scene_hpc_job
    from flash.scenarios.core.scene_reg.discovery import resolve_scene_meta

    j = get_scene_hpc_job("thin_layer_sandwich_si")
    meta = resolve_scene_meta("thin_layer_sandwich_si")
    # 生效 name = 目录名派生（discovery 位置优先）：目录被改名后随之变化，
    # 但别名键必须始终解析到同一场景 ⇒ 只断言与 discovery 一致。
    assert j.name == meta.name
    live = Path(meta.source).parent
    assert (Path(_REPO) / j.input_rel_dir) == live / "sim_input_si"
    j2 = get_scene_hpc_job("grad_dens")           # scene.json aliases 键
    assert j2.name == "grad_dens_sandwich"
    print(f"  [alias] thin_layer_sandwich_si -> {j.name}; "
          f"grad_dens -> {j2.name}")


def test_hpc_job_unknown_name_raises():
    """未知名仍显式 KeyError（防静默兜底成谜题）。"""
    from flash.scenarios.core.hpc.hpc_job import get_scene_hpc_job

    with pytest.raises(KeyError):
        get_scene_hpc_job("no_such_scene_zzz")
