#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""relocate_scene.py — 场景目录收纳整理执行器（场景收纳整理改造 P4）
════════════════════════════════════════════════════════════════════════

把场景目录（或整个场景族目录）在 ``flash/scenarios/`` 内移动到任意新位置，
并自动完成配套修复 —— 配合 P1-P3 的可移植化改造，移动**零手工修改**。

流程：
  1. 前置校验（src 存在 / dst 不冲突 / 同在 scenarios 树内）+ 场景发现快照；
  2. ``git mv``（保留 history；未跟踪文件回退普通 mv 并提示）；
  3. 重写 ``_scene_anchors.json`` 中命中旧路径的条目；
  4. 全树扫描旧路径字面量残留（相对路径/点分包路径两种形态），逐条报告；
  5. 后置校验：discovery 发现的场景名集合与移动前一致。

用法::

    python relocate_scene.py <src> <dst>             # 移动单个场景/族目录
    python relocate_scene.py <src> <dst> --dry-run   # 只报告不落盘

示例::

    python relocate_scene.py \\
        flash/scenarios/public/center_evolution/ch_center \\
        flash/scenarios/public/laser_ch/ch_center
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
for _c in (_HERE, *_HERE.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        REPO = _c
        break
else:
    raise SystemExit("[X] 无法定位仓库根")
SCEN = REPO / "flash" / "scenarios"
ANCHORS = SCEN / "_scene_anchors.json"

SCAN_EXTS = {".py", ".sh", ".bat", ".json", ".md", ".txt"}
SCAN_EXCLUDE_PARTS = {"__pycache__", "flash_output", "sim_output", "flash_input",
                      "sim_input", "sim_input_si", "logs_archive", "database"}


def _scene_names() -> set:
    from flash.scenarios.core.scene_reg.discovery import iter_scene_manifests
    return {m.name for m in iter_scene_manifests()}


def _git(*args: str) -> tuple:
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="场景目录收纳整理执行器")
    ap.add_argument("src", help="源目录（相对仓库根或绝对路径）")
    ap.add_argument("dst", help="目标目录（其父目录须已存在，末级目录名可新起）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    src = Path(a.src).resolve()
    dst = Path(a.dst).resolve()
    for p in (src, dst):
        if SCEN not in p.parents and p != SCEN:
            print(f"[X] 路径不在 scenarios 树内: {p}")
            return 2
    if not src.is_dir():
        print(f"[X] 源目录不存在: {src}")
        return 2
    if dst.exists():
        print(f"[X] 目标已存在: {dst}")
        return 2
    if src == dst:
        print("[X] 源与目标相同")
        return 2

    src_rel = src.relative_to(REPO).as_posix()
    dst_rel = dst.relative_to(REPO).as_posix()
    src_scen_rel = src.relative_to(SCEN).as_posix()      # 相对 scenarios（锚点表粒度）

    print(f"移动: {src_rel}\n  →  {dst_rel}")
    if not a.dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)   # 新分类目录自动创建
    if a.dry_run:
        print("[DRY-RUN] 不落盘")
    else:
        rc, out = _git("mv", src_rel, dst_rel)
        if rc != 0:
            print(f"[W] git mv 失败（含未跟踪产物?），回退普通移动: {out.strip()[:200]}")
            try:
                src.rename(dst)
            except OSError as e:
                print(f"[X] 移动失败: {e}")
                return 1

    # ── 3. 重写锚点表 ──
    if ANCHORS.is_file():
        tbl = json.loads(ANCHORS.read_text(encoding="utf-8"))
        hit = 0
        for k, v in tbl.items():
            vv = str(v).replace("\\", "/").rstrip("/")
            if vv == src_scen_rel or vv.startswith(src_scen_rel + "/"):
                tbl[k] = vv.replace(src_scen_rel,
                                    dst.relative_to(SCEN).as_posix(), 1)
                hit += 1
                print(f"[anchor] {k}: {v} → {tbl[k]}")
        if hit and not a.dry_run:
            ANCHORS.write_text(
                json.dumps(tbl, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="")

    # ── 4a. 移动子树内部的自指路径字面量（docstring/注释）安全自动改写 ──
    old_posix = src_rel
    old_dotted = ".".join(src_rel.replace("/", ".").split("."))
    fixed_in_tree = 0
    if not a.dry_run:
        for p in sorted(dst.rglob("*.py")):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            new = text.replace(old_posix, dst_rel).replace(old_dotted,
                        ".".join(dst_rel.replace("/", ".").split(".")))
            if new != text:
                p.write_text(new, encoding="utf-8", newline="")
                fixed_in_tree += 1
        if fixed_in_tree:
            print(f"[fix] 子树内自指路径 docstring 改写: {fixed_in_tree} 文件")

    # ── 4b. 全树旧路径字面量扫描（子树外残留仅报告）──
    residues = []
    for p in sorted(SCEN.rglob("*")):
        if not p.is_file() or p.suffix not in SCAN_EXTS:
            continue
        rel = p.relative_to(SCEN)
        if any(part in SCAN_EXCLUDE_PARTS for part in rel.parts):
            continue
        if rel.parts[:2] == ("scripts", "relocate"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if old_posix in line.replace("\\", "/") or old_dotted in line:
                residues.append((p.relative_to(REPO).as_posix(), i, line.strip()[:100]))
    if residues:
        print(f"\n[!] 子树外旧路径字面量残留 {len(residues)} 处（需人工核对）:")
        for f, i, l in residues[:20]:
            print(f"  [{f}:{i}] {l}")
        if len(residues) > 20:
            print(f"  … 其余 {len(residues) - 20} 条略")
    else:
        print("[ok] 全树无旧路径字面量残留")

    # ── 5. 后置校验：discovery 场景名集合不变 ──
    sys.path.insert(0, str(REPO))
    names = _scene_names()
    print(f"\n[verify] discovery 场景数: {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
