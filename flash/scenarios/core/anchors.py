# -*- coding: utf-8 -*-
"""anchors.py — 跨场景**数据文件**逻辑锚点（场景收纳整理改造 P1，2026-11-11 v2）
════════════════════════════════════════════════════════════════════════

★ 定位：锚点表只解决"场景 A 需要读场景 B 目录下的**数据/资源文件**"
  （如 SNB 场景共用 t001 的 source_patches）。**Python 代码级复用不走
  锚点** —— 一律抽到 ``flash/scenarios/common/`` 共享包（位置固定），
  场景之间保持零 import（子场景独立性原则，2026-11-04）。

★ 锚点表：``flash/scenarios/_scene_anchors.json``，值两种格式::

    v2（首选）  "<场景名或别名>::<场景目录内 POSIX 相对路径>"
                如 "tracer.VTi": "VTi1::."        （VTi 目录本身）
                   "SNB.ref":    "SNBtest::Test/x" （SNBtest 场景内子目录）
    legacy      "相对 scenarios 根的 POSIX 路径"
                如 "SNB.t001": "private/SNB/SNBtest/Test/t001"

  ★ v2 经 discovery 按**场景名**解析 scene_dir ⇒ 场景目录被**直接移动/
    收纳后锚点自动跟随**，无需任何手工同步（2026-11-11 收纳改造）。
  ★ legacy 值在解析时**自动迁移**：遍历 manifests 取最长 scene_dir 前缀
    匹配 → 原子回写为 v2（只读/无仓库环境静默降级为内存解析）。
    无法归属到任何场景的 legacy 条目（如 SNB 资源目录）保留原样 + WARN。

用法::

    from flash.scenarios.core.anchors import anchor, try_anchor, resolve_anchor

    d = anchor("SNB.t001")        # 未登记/场景名不可解析 → KeyError（显式失败）
    d = try_anchor("SNB.x")       # 未登记或不可解析 → None
    p, warn = resolve_anchor("SNB.t001")   # 统一解析入口（verify/门禁复用）
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

__all__ = ["anchor", "try_anchor", "resolve_anchor", "anchors_table", "anchors_file"]

_anchors_file: Optional[Path] = None
_migrate_attempted: set = set()   # legacy 自动迁移只尝试一次（per key）


def anchors_file() -> Path:
    """锚点表文件路径（scenarios 根下）。"""
    global _anchors_file
    if _anchors_file is None:
        from flash.scenarios.core.scene_paths import scenarios_root
        _anchors_file = scenarios_root() / "_scene_anchors.json"
    return _anchors_file


def anchors_table() -> dict:
    """读锚点表（缺文件 → 空表）。"""
    f = anchors_file()
    if not f.is_file():
        return {}
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _scene_dir_by_name(scene_key: str) -> Optional[Path]:
    """按场景名/别名解析 scene_dir（discovery 位置无关寻址）。"""
    from flash.scenarios.core.scene_reg.discovery import resolve_scene_meta
    meta = resolve_scene_meta(scene_key)
    if meta is None or not meta.source:
        return None
    return Path(meta.source).parent


def resolve_anchor(key: str) -> tuple[Optional[Path], Optional[str]]:
    """统一解析入口 → ``(路径, 警告)``。

    - 未登记 → KeyError（显式失败，防路径漂移成谜题）。
    - v2 值：场景名不可解析 → KeyError；解析成功但目录不存在 → 返回
      (路径, WARN)（部分锚点描述超算远端布局，本地缺失属正常）。
    - legacy 值：返回 (scenarios 根相对路径, WARN) 并触发自动迁移。
    """
    val = anchors_table().get(key)
    if val is None:
        known = ", ".join(sorted(k for k in anchors_table() if not k.startswith("_")))
        raise KeyError(f"未知场景锚点: {key!r}；请在 _scene_anchors.json 登记。可用: {known or '（空）'}")
    val = str(val).replace("\\", "/").rstrip("/")
    if not val:
        raise KeyError(f"场景锚点 {key!r} 值为空")

    if "::" in val:                                    # ── v2 ──
        scene_key, _, rel = val.partition("::")
        scene_dir = _scene_dir_by_name(scene_key.strip())
        if scene_dir is None:
            raise KeyError(
                f"场景锚点 {key!r} 的场景名 {scene_key!r} 未经 discovery 解析到场景"
                f"（场景已删除/改名？请更新 _scene_anchors.json）")
        rel = rel.strip()
        p = scene_dir if rel in (".", "") else scene_dir / rel
        warn = None if p.is_dir() else f"锚点 {key} → {p} 本地不存在（远端布局锚点属正常）"
        return p, warn

    # ── legacy：scenarios 根相对 + 自动迁移 ──
    from flash.scenarios.core.scene_paths import scenarios_root
    p = scenarios_root() / val
    _try_migrate_legacy(key, val)
    return p, f"锚点 {key} 仍为 legacy 路径值（已尝试自动迁移）"


def try_anchor(key: str) -> Optional[Path]:
    """按逻辑名解析锚点目录；未登记或不可解析返回 None。"""
    try:
        p, _ = resolve_anchor(key)
        return p
    except KeyError:
        return None


def anchor(key: str) -> Path:
    """按逻辑名解析锚点目录；未登记/不可解析显式报错（防路径漂移成谜题）。"""
    p, _ = resolve_anchor(key)
    return p


def _try_migrate_legacy(key: str, legacy_val: str) -> None:
    """legacy 值 → v2 自动迁移：最长 scene_dir 前缀匹配，原子回写。

    ★ 失败全部静默（只读 fs / wheel 模式 / 无仓库环境）—— 内存解析照常。
    """
    if key in _migrate_attempted:
        return
    _migrate_attempted.add(key)
    try:
        from flash.scenarios.core.scene_reg.discovery import iter_scene_manifests
        target = (anchors_file().parent / legacy_val).resolve()
        best_name, best_dir, best_rel = None, None, None
        for meta in iter_scene_manifests():
            if not meta.source:
                continue
            scene_dir = Path(meta.source).parent.resolve()
            if target == scene_dir:
                cand_rel = "."
            else:
                try:
                    cand_rel = target.relative_to(scene_dir).as_posix()
                except ValueError:
                    continue
            # 最长 scene_dir 优先；同长取字典序首个 meta.name（确定性）
            depth = len(scene_dir.parts)
            if best_dir is None or depth > len(best_dir.parts) or \
                    (depth == len(best_dir.parts) and meta.name < best_name):
                best_name, best_dir, best_rel = meta.name, scene_dir, cand_rel
        if best_name is None:
            return                                     # 无场景可归属（SNB 组）→ 保留 legacy
        v2 = f"{best_name}::{best_rel}"
        tbl = anchors_table()
        if tbl.get(key) == v2:
            return
        tbl[key] = v2
        f = anchors_file()
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(tbl, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        os.replace(tmp, f)                             # 原子回写
    except OSError:
        pass                                           # 只读/wheel 环境：静默降级
    except Exception:
        pass                                           # discovery 不可用等：保留 legacy
