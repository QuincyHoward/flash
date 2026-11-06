# -*- coding: utf-8 -*-
"""sync_workbuddy_skills — 将仓库级 skills/ 镜像到 WorkBuddy 项目级 .workbuddy/skills/。

背景
----
仓库级 skills/ 是随 git 分发的单一事实源；WorkBuddy 只从项目级
.workbuddy/skills/ 自动加载技能。本脚本做单向幂等镜像：

    <repo>/skills/<name>/  →  <repo>/.workbuddy/skills/<name>/

行为
----
* 清点 ``skills/*/``（跳过 skills/README.md 等散文件，只镜像子目录）；
* 逐文件复制（源有变化或目标缺失时覆写）；
* 删除目标中源里已不存在的 skill 目录（保持精确镜像）；
* 输出变更清单。

用法
----
    python scripts/sync_workbuddy_skills.py             # 全量镜像
    python scripts/sync_workbuddy_skills.py --dry-run   # 只打印计划，不落盘
    python scripts/sync_workbuddy_skills.py --check     # 只校验一致性（退出码 0/1，可挂 CI）

注意：.workbuddy/ 已在 .gitignore，属本地生成物，不入 git。
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "skills"
DST = REPO / ".workbuddy" / "skills"


def list_source_skills() -> list[Path]:
    """源侧 skill 目录清单（skills/ 下的子目录）。"""
    if not SRC.is_dir():
        return []
    return sorted(p for p in SRC.iterdir() if p.is_dir())


def _files_under(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def plan_sync() -> tuple[list[str], list[str], list[Path]]:
    """返回 (复制计划描述, 删除计划描述, 源目录列表)。"""
    copies: list[str] = []
    src_skills = list_source_skills()
    src_names = {p.name for p in src_skills}

    for skill in src_skills:
        dst_skill = DST / skill.name
        if not dst_skill.is_dir():
            for rel in sorted(_files_under(skill)):
                copies.append(f"+ {skill.name}/{rel.as_posix()}")
            continue
        src_files = _files_under(skill)
        dst_files = _files_under(dst_skill)
        for rel in sorted(src_files):
            s, d = skill / rel, dst_skill / rel
            if not d.exists() or not filecmp.cmp(s, d, shallow=False):
                copies.append(f"U {skill.name}/{rel.as_posix()}")
        for rel in sorted(dst_files - src_files):
            copies.append(f"- {skill.name}/{rel.as_posix()}")

    deletes: list[str] = []
    if DST.is_dir():
        for item in sorted(DST.iterdir()):
            if item.name not in src_names:
                deletes.append(f"D .workbuddy/skills/{item.name}")
    return copies, deletes, src_skills


def do_sync(dry_run: bool) -> int:
    copies, deletes, src_skills = plan_sync()
    if not src_skills:
        print(f"[X] 源目录无 skill: {SRC}")
        return 2

    if not copies and not deletes:
        print(f"[ok] 已一致 · {len(src_skills)} 个 skill 镜像无变更")
        return 0

    for line in copies + deletes:
        print(f"  {line}")

    if dry_run:
        print(f"[dry-run] {len(copies)} 处复制/更新, {len(deletes)} 处删除 · 未落盘")
        return 0

    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    for skill in src_skills:
        shutil.copytree(skill, DST / skill.name)
    print(f"[ok] 已镜像 {len(src_skills)} 个 skill → {DST}")
    return 0


def check() -> int:
    copies, deletes, _ = plan_sync()
    if copies or deletes:
        print(f"[X] 不一致 · {len(copies)} 处差异, {len(deletes)} 处多余目标")
        for line in (copies + deletes)[:20]:
            print(f"  {line}")
        return 1
    print("[ok] 一致")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="skills/ → .workbuddy/skills/ 镜像同步")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="只打印计划，不落盘")
    g.add_argument("--check", action="store_true", help="只校验一致性（CI 用）")
    a = ap.parse_args()
    if a.check:
        return check()
    return do_sync(dry_run=a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
