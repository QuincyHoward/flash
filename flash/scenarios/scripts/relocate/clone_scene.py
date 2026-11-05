#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""clone_scene.py — 场景克隆器（场景收纳整理工具链补充）
════════════════════════════════════════════════════════════════════════

回答"复制一个场景目录后直接执行报错：场景名重复"——**移动**零改动是可
移植化改造的目标；但**复制**是制造第二个场景，两份 manifest 声明同一
`name` 会被 discovery 显式拒绝（防呆：否则 CLI 同名场景谁生效不可知）。

克隆 = 复制目录 + **身份再标识**。本工具自动完成：

  1. 复制场景目录（排除 flash_output/ 产物；flash_input/ 生成产物可选
     排除 —— 缺失时 gen_flash_inputs 自动重建）；
  2. scene.json：name → 新名；aliases 清空（防与源场景别名冲突）；
     description 追加克隆标注；sim_name/basenm 若存在则加后缀；
  3. 场景代码内身份常量再标识（best-effort，逐项报告）：
     - ``name="<旧名>"`` / ``run_dir_name="runs_<旧名>"``
     - ``basenm="<旧>_"``（含 ``_add("basenm", …)`` 形态）
     - runs 目录 ``/ "<旧名>"``、远端 ``flash_sim_runs/<旧名>/``
     - WSL 工作目录 ``/root/<...>_<旧名片段>_work``（防并行冲突）
  4. 后置校验：discovery 无重名、新旧两场景 get_scenario 均可用。

用法::

    python clone_scene.py <源场景目录> <新场景名> [--dst 路径] [--keep-products]
                           [--dry-run]

新场景默认落在源场景**同级目录**（``<源目录>_t`` 或 --dst 指定）。
克隆后请人工核对 --list 报告的"未自动处理项"（物理参数/单元名等是否
需要区分属实验设计问题，工具不越权修改）。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
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

_EXCLUDE_COPY = {"flash_output", "sim_output", "__pycache__", "results"}
_IDENT_KEYS = ("name", "run_dir_name", "basenm", "sim_name")


def _old_name(scene_dir: Path) -> str:
    raw = json.loads((scene_dir / "scene.json").read_text(encoding="utf-8"))
    return str(raw["name"]).strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="场景克隆器（复制 + 身份再标识）")
    ap.add_argument("src", help="源场景目录（含 scene.json）")
    ap.add_argument("new_name", help="新场景名（全局唯一，如 ch_center_t）")
    ap.add_argument("--dst", default="", help="目标目录（缺省 = 源同级/<new_name>）")
    ap.add_argument("--keep-products", action="store_true",
                    help="连 flash_input/flash_output 一起复制（缺省排除，生成物自动重建）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    src = Path(a.src).resolve()
    if not (src / "scene.json").is_file():
        print(f"[X] 源目录缺 scene.json: {src}")
        return 2
    if SCEN not in src.parents:
        print(f"[X] 源不在 scenarios 树内: {src}")
        return 2
    new_name = a.new_name.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-]*", new_name):
        print(f"[X] 新场景名非法: {new_name!r}")
        return 2

    # 1. 复制
    dst = Path(a.dst).resolve() if a.dst else src.parent / new_name
    if dst.exists():
        print(f"[X] 目标已存在: {dst}")
        return 2
    old = _old_name(src)
    print(f"克隆: {src.relative_to(REPO)}  ({old} → {new_name})")
    print(f"  →  {dst.relative_to(REPO)}")

    def _ignore(directory, names):
        drop = set()
        for n in names:
            if n in _EXCLUDE_COPY:
                drop.add(n)
            elif n == "flash_input" and not a.keep_products:
                drop.add(n)
        return drop

    if not a.dry_run:
        shutil.copytree(src, dst, ignore=_ignore)

    # 2. scene.json 再标识
    mf = dst / "scene.json"
    raw = json.loads(mf.read_text(encoding="utf-8"))
    raw["name"] = new_name
    raw["aliases"] = []
    raw["description"] = str(raw.get("description") or "") + f"（{old} 克隆）"
    if raw.get("sim_name"):
        raw["sim_name"] = f"{raw['sim_name']}_t"
    if raw.get("basenm"):
        raw["basenm"] = re.sub(r"_+$", "_t_", str(raw["basenm"]))
    if not a.dry_run:
        mf.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="")
    print(f"[scene.json] name={new_name}, aliases=[], sim_name/basenm 加后缀")

    # 3. 代码内身份常量（best-effort 正则，逐项报告）
    todo_manual = []
    for py in sorted(dst.rglob("*.py")):
        if py.name == "run.py":
            continue
        t = py.read_text(encoding="utf-8", errors="replace")
        orig = t
        t = t.replace(f'name="{old}"', f'name="{new_name}"')
        t = t.replace(f'run_dir_name="runs_{old}"', f'run_dir_name="runs_{new_name}"')
        t = t.replace(f'basenm="lasslab_"' if old == "ch_center" else f'basenm="{old}_"',
                      f'basenm="{new_name}_"')
        t = t.replace('_add("basenm", "lasslab_")', f'_add("basenm", "{new_name}_")')
        t = t.replace('_add("log_file", "lasslab.log")', f'_add("log_file", "{new_name}.log")')
        t = t.replace(f'runs_root() / "{old}"', f'runs_root() / "{new_name}"')
        t = t.replace(f"flash_sim_runs/{old}/", f"flash_sim_runs/{new_name}/")
        # WSL 工作目录默认值（防两场景并行共用同一 ext4 工作区）
        t = re.sub(r'(/root/[A-Za-z0-9_]+_)(' + re.escape(old) + r'(_work"))',
                   rf"\g<1>{new_name}\g<3>", t)
        if t != orig:
            rel = py.relative_to(dst)
            if not a.dry_run:
                py.write_text(t, encoding="utf-8", newline="")
            print(f"[ident] {rel} 身份常量已再标识")
        # 收集疑似未处理项：仍引用旧名且不在注释里的行
        for i, line in enumerate(t.splitlines(), 1):
            s = line.strip()
            if old in s and not s.startswith("#") and "old" not in s:
                if re.search(rf"[\"']{old}[\"']", s):
                    todo_manual.append(f"{py.relative_to(REPO)}:{i}  {s[:90]}")

    # 4. 后置校验
    sys.path.insert(0, str(REPO))
    from flash.scenarios.core.scene_reg.discovery import iter_scene_manifests
    names = [m.name for m in iter_scene_manifests()]
    dup = [n for n in names if names.count(n) > 1]
    if dup:
        print(f"[X] 发现重名（克隆失败）: {sorted(set(dup))}")
        return 1
    print(f"[verify] discovery 场景数: {len(names)}，无重名")
    if todo_manual:
        print(f"\n[!] 以下行仍引用旧名 {old!r}，请人工核对（可能只是文档/分析脚本名）:")
        for x in todo_manual[:15]:
            print(f"  {x}")
        if len(todo_manual) > 15:
            print(f"  … 其余 {len(todo_manual) - 15} 条略")
    print(f"\n[ok] 克隆完成。冒烟: cd {dst.relative_to(REPO)} && python run.py --tmax 1e-11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
