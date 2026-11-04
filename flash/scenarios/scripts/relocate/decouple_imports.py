#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""decouple_imports.py — 跨场景 import 解耦迁移（场景收纳整理改造 P3，可重复执行）
════════════════════════════════════════════════════════════════════════

把"硬编码层级包路径"的跨场景 import 改写为位置无关形式：

  R1  flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper
        → flash.flash_run.remote.session          （唯一实现本就在框架层）
  R2  from …tracer.SNB.SNBOneCH_ml import SNBOneCH_ml as <别名>
        → scene_module("SNBOneCH_ml")             （按场景名经 discovery 解析）
  R3  from …tracer.OneCH_ml.OneCH_ml import config_constants as <别名>
        → scene_module("OneCH_ml").config_constants
  R4  from …tracer.OneCH_ml.OneCH_ml import (SPECIES_LIST, build_species_defs)
        → scene_module("OneCH_ml") 属性提取
  R5  from …public.sandwich.thin_layer_sandwich.interpolator import <名> as <别名>
        → scene_module("thin_layer_sandwich_si", stem="interpolator").<名>
  R6  _gen_module_name(): return "flash.scenarios.…gen_flash_inputs"
        → return f"{__package__}.gen_flash_inputs"

幂等：改写后的文本不再匹配任何规则的原模式。排除 flash_input/ 等产物目录。

用法::

    python decouple_imports.py            # 执行迁移并打印逐文件改动
    python decouple_imports.py --dry-run  # 只报告不写盘
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_HERE = Path(__file__).resolve()
for _c in (_HERE, *_HERE.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        REPO = _c
        break
else:
    raise SystemExit("[X] 无法定位仓库根")

SCEN = REPO / "flash" / "scenarios"
EXCLUDE_PARTS = {"__pycache__", "flash_output", "sim_output", "flash_input",
                 "sim_input", "sim_input_si", "logs_archive", "database"}

#: (规则名, 编译型正则, 替换函数或模板)
_R = re

#: ``(`` 后允许空白/一行 # 注释再换行（``import (  # noqa: E402`` 形态）
_OPEN = r"\(\s*(?:#[^\n]*\n)?\s*"


def _r2_repl(m: re.Match) -> str:
    ind, alias = m.group(1), m.group(2)
    return (f"{ind}from flash.scenarios.common.scene_ref import "
            f"scene_module as _scene_ref_load\n"
            f'{ind}{alias} = _scene_ref_load("SNBOneCH_ml")')


RULES = [
    ("R1_remote_session",
     _R.compile(r"flash\.scenarios\.flash_demo\.demo_hpc\.remote_ssh_helper"),
     "flash.flash_run.remote.session"),

    ("R2_snbonech_ml_ref",
     _R.compile(
         r"^([ \t]*)from flash\.scenarios\.private\.tracer\.SNB\.SNBOneCH_ml import "
         r"(?:" + _OPEN + r")?SNBOneCH_ml as (\w+),?[ \t]*\)?[ \t]*(?:#[^\n]*)?"
         r"(?:\n[ \t]*\)[ \t]*)?",
         _R.M),
     _r2_repl),

    ("R3_onech_cfg",
     _R.compile(
         r"^([ \t]*)from flash\.scenarios\.private\.tracer\.OneCH_ml\.OneCH_ml import "
         r"(?:" + _OPEN + r")?config_constants as (\w+),?[ \t]*\)?[ \t]*(?:#[^\n]*)?"
         r"(?:\n[ \t]*\)[ \t]*)?",
         _R.M),
     lambda m: (f"{m.group(1)}from flash.scenarios.common.scene_ref import "
                f'scene_module as _scene_ref_load\n'
                f'{m.group(1)}{m.group(2)} = '
                f'_scene_ref_load("OneCH_ml").config_constants')),

    ("R4_onech_species",
     _R.compile(
         r"^([ \t]*)from flash\.scenarios\.private\.tracer\.OneCH_ml\.OneCH_ml import "
         + _OPEN + r"SPECIES_LIST,\s*\n[ \t]*build_species_defs,?\s*\n[ \t]*\)[ \t]*$",
         _R.M),
     lambda m: (f"{m.group(1)}from flash.scenarios.common.scene_ref import "
                f'scene_module as _scene_ref_load\n'
                f'{m.group(1)}_onech_ml = _scene_ref_load("OneCH_ml")\n'
                f"{m.group(1)}SPECIES_LIST = _onech_ml.SPECIES_LIST\n"
                f"{m.group(1)}build_species_defs = _onech_ml.build_species_defs")),

    ("R5_thin_interp",
     _R.compile(
         r"^([ \t]*)from flash\.scenarios\.public\.sandwich\.thin_layer_sandwich\.interpolator "
         r"import " + _OPEN + r"(\w+)(?:[ \t]+as[ \t]+(\w+))?,?[ \t]*\)?[ \t]*$"
         r"(?:\n[ \t]*\)[ \t]*)?",
         _R.M),
     lambda m: (f"{m.group(1)}from flash.scenarios.common.scene_ref import "
                f'scene_module as _scene_ref_load\n'
                f'{m.group(1)}{m.group(3) or m.group(2)} = _scene_ref_load('
                f'"thin_layer_sandwich_si", stem="interpolator").{m.group(2)}')),

    ("R6_gen_module_name",
     _R.compile(r'(return )["\']flash\.scenarios\.[\w.]+\.gen_flash_inputs["\']'),
     r'\1f"{__package__}.gen_flash_inputs"'),
]


def _iter_pys():
    for p in sorted(SCEN.rglob("*.py")):
        rel = p.relative_to(SCEN)
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        if rel.parts[:2] == ("scripts", "relocate"):
            continue          # 迁移工具自身不改写（规则文本含模式字符串）
        yield p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    total = 0
    for p in _iter_pys():
        src = p.read_text(encoding="utf-8", errors="replace")
        new = src
        hits = []
        for name, pat, repl in RULES:
            new2, n = pat.subn(repl, new)
            if n:
                hits.append(f"{name}×{n}")
                new = new2
        if hits:
            rel = p.relative_to(REPO)
            print(f"[{'+'.join(hits)}] {rel}")
            total += len(hits)
            if not args.dry_run:
                p.write_text(new, encoding="utf-8", newline="")
    print(f"\n[{'DRY-RUN' if args.dry_run else 'ok'}] 改动文件数: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
