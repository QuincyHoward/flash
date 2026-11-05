#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_all_scenes.py — 全场景批量验证（场景收纳整理改造 P5）
════════════════════════════════════════════════════════════════════════

对 CATALOG 全部场景做**静态可运行性验证**（零仿真执行，秒级完成）：

  1. discovery 发现 & manifest 解析（module/script/hpc 路径有效）；
  2. main/engine 型：场景模块可导入、（engine）scenario 实例可获取；
  3. script 型：脚本文件存在；
  4. anchors 锚点表全部指向真实存在的目录。

用法::

    python verify_all_scenes.py                  # 打印摘要
    python verify_all_scenes.py --json out.json  # 机器可读报告
    python verify_all_scenes.py --strict         # 有失败退出码 1

动态冒烟（真实极短运行）请按场景单独执行:
    python -m flash.scenarios.core.entry.cli run <场景> --tmax 1e-11
"""
from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve()
for _c in (_HERE, *_HERE.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        REPO = _c
        break
else:
    raise SystemExit("[X] 无法定位仓库根")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out", default="")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)

    from flash.scenarios.core.scene_reg.discovery import iter_scene_manifests
    from flash.scenarios.core.scene_reg.catalog import CATALOG
    from flash.scenarios.core.anchors import anchors_table

    results = []
    metas = {m.name: m for m in iter_scene_manifests()}

    for entry in CATALOG:
        name = entry.name
        meta = metas.get(name)
        row = {"name": name, "kind": entry.runner_kind, "ok": True, "checks": []}
        if meta is None:
            row["ok"] = False
            row["checks"].append("manifest 不在 discovery 结果中")
            results.append(row)
            continue
        # 1) 路径有效性
        if entry.runner_kind == "script":
            p = REPO / meta.script
            if not p.is_file():
                row["ok"] = False
                row["checks"].append(f"脚本不存在: {meta.script}")
        else:
            try:
                mod = importlib.import_module(meta.module)
                row["checks"].append(f"import ok: {meta.module}")
            except Exception as e:
                row["ok"] = False
                row["checks"].append(f"import FAIL: {meta.module}: {e}")
        results.append(row)

    # 2) engine 型 scenario 实例
    for name in [r["name"] for r in results if r["kind"] == "engine" and r["ok"]]:
        try:
            from flash.scenarios.core.scene_reg.registry import get_scenario
            get_scenario(name)
        except Exception as e:
            for r in results:
                if r["name"] == name:
                    r["ok"] = False
                    r["checks"].append(f"scenario 实例 FAIL: {e}")

    # 3) anchors（存在性仅 WARN —— 部分锚点描述超算远端布局, 本地可不存在）
    from flash.scenarios.core.scene_paths import scenarios_root
    warns = []
    for k, v in anchors_table().items():
        if k.startswith("_"):
            continue
        if not (scenarios_root() / str(v).replace("\\", "/")).is_dir():
            warns.append(f"[anchor:{k}] 本地不存在（远端布局锚点?）: {v}")
    for w in warns:
        results.append({"name": w.split(":")[1].split("]")[0], "kind": "anchor-warn",
                        "ok": True, "checks": [w]})

    n_fail = sum(1 for r in results if not r["ok"])
    print(f"{'=' * 66}")
    print(f"全场景静态验证  {datetime.now():%Y-%m-%d %H:%M:%S}  "
          f"通过 {len(results) - n_fail}/{len(results)}")
    print(f"{'=' * 66}")
    for r in results:
        mark = "OK " if r["ok"] else "X  "
        extra = "" if r["ok"] else "  ← " + "; ".join(r["checks"])
        print(f"  [{mark}] {r['name']:24s} {r['kind']}{extra}")
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(
            {"summary": f"{len(results) - n_fail}/{len(results)}",
             "results": results}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\n[ok] JSON → {a.json_out}")
    return 1 if (a.strict and n_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())
