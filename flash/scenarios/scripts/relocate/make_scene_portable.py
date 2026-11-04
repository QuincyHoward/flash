#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_scene_portable.py — 场景可移植化批量改造（场景收纳整理改造 P3 核心）
════════════════════════════════════════════════════════════════════════

三个子命令（均可重复执行 / 幂等）：

  manifests   把全部 scene*.json 的绝对绑定字段改写为相对形式：
              module/attr_module: "flash.scenarios.<场景包>.<尾>" → ".<尾>"
              script/hpc.input_rel_dir/hpc.gen_script:
                  "flash/scenarios/<场景目录>/<x>" → "./<x>"
              相对形式由 core/discovery 相对 manifest 物理位置解析 ——
              场景目录任意移动后自动跟随。

  parents     按规则表把已知的 ``Path(__file__).resolve().parents[N]``
              逃逸引用改写为位置无关形式（向上搜仓库根 / anchors 锚点）。

  initfiles   给场景目录及其中间目录补缺失的 ``__init__.py``
              （消除 PEP 420 命名空间包的不确定性 / find_packages 打包遗漏）。

用法::

    python make_scene_portable.py manifests            # 全部 manifest 改写
    python make_scene_portable.py parents              # parents[N] 规则替换
    python make_scene_portable.py initfiles            # 补 __init__.py
    python make_scene_portable.py manifests --dry-run
"""
from __future__ import annotations

import argparse
import json
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

# ═══════════════════════ manifests ═══════════════════════

def _to_rel_pkg(abs_pkg: str, scene_pkg: str) -> str | None:
    """绝对包路径 → 相对形式；不属于本场景包则 None。"""
    prefix = scene_pkg + "."
    if abs_pkg == scene_pkg:
        return "."
    if abs_pkg.startswith(prefix):
        return "." + abs_pkg[len(prefix):]
    return None


def _to_rel_repo(repo_rel: str, scene_dir_rel: str) -> str | None:
    """仓库根相对路径 → './…'（相对 manifest 目录）；不在场景目录下则 None。"""
    r = repo_rel.replace("\\", "/")
    prefix = "flash/scenarios/" + scene_dir_rel + "/"
    if r.startswith(prefix):
        return "./" + r[len(prefix):]
    return None


def cmd_manifests(dry: bool) -> int:
    n_conv = 0
    for mf in sorted(SCEN.rglob("scene*.json")):
        rel_parts = mf.parent.relative_to(SCEN).parts
        scene_pkg = ".".join(("flash.scenarios", *rel_parts))
        scene_dir_rel = "/".join(rel_parts)
        raw = json.loads(mf.read_text(encoding="utf-8"))
        orig = json.dumps(raw, ensure_ascii=False, indent=2)
        changed = []

        for key in ("module", "attr_module"):
            v = str(raw.get(key) or "")
            if v.startswith("flash/scenarios/"):
                # 斜杠形式 "flash/scenarios/private/tracer/CHTi.CHTi1" → 点分
                v = "flash.scenarios." + v[len("flash/scenarios/"):].replace("/", ".")
            if v.startswith("flash.scenarios."):
                rel = _to_rel_pkg(v, scene_pkg)
                if rel is not None:
                    raw[key] = rel
                    changed.append(f"{key}→{rel}")
        for key in ("script",):
            v = str(raw.get(key) or "")
            if v.startswith("flash/scenarios/"):
                rel = _to_rel_repo(v, scene_dir_rel)
                if rel is not None:
                    raw[key] = rel
                    changed.append(f"{key}→{rel}")
        hpc = raw.get("hpc")
        if isinstance(hpc, dict):
            for key in ("input_rel_dir", "gen_script"):
                v = str(hpc.get(key) or "")
                if v.startswith("flash/scenarios/"):
                    rel = _to_rel_repo(v, scene_dir_rel)
                    if rel is not None:
                        hpc[key] = rel
                        changed.append(f"hpc.{key}→{rel}")

        if changed:
            out = json.dumps(raw, ensure_ascii=False, indent=2)
            if orig != out and not orig.endswith("\n"):
                pass
            rel = mf.relative_to(REPO)
            print(f"[{'; '.join(changed)}] {rel}")
            n_conv += 1
            if not dry:
                mf.write_text(out + "\n", encoding="utf-8", newline="")
    print(f"\n[{'DRY-RUN' if dry else 'ok'}] 改写 manifest 数: {n_conv}")
    return 0


# ═══════════════════════ parents[N] 规则表 ═══════════════════════

#: 向上搜仓库根的统一 bootstrap（缩进占位 {I}）
_BOOTSTRAP = """_REPO_ROOT = Path(__file__).resolve()
for _c in (_REPO_ROOT, *_REPO_ROOT.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        _REPO_ROOT = _c
        break
else:
    raise RuntimeError("无法定位仓库根（需含 pyproject.toml + start_flash.py）")"""

_BOOTSTRAP_PKG = """_FLASH_PKG = Path(__file__).resolve()
for _c in (_FLASH_PKG, *_FLASH_PKG.parents):
    if (_c / "pyproject.toml").is_file() and (_c / "start_flash.py").is_file():
        _FLASH_PKG = _c / "flash"
        break
else:
    raise RuntimeError("无法定位仓库根（需含 pyproject.toml + start_flash.py）")"""

PARENT_RULES = [
    # P1: _ROOT = Path(__file__).resolve().parents[N]  → 向上搜仓库根
    ("P1_repo_root",
     re.compile(r"^_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*(?:#.*)?$", re.M),
     lambda m: _BOOTSTRAP),

    # P2: _FLASH_PKG = Path(__file__).resolve().parents[N] / 'flash' → 搜根后 /flash
    ("P2_flash_pkg",
     re.compile(r"^_FLASH_PKG = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t]*['\"]flash['\"]"
                r"[ \t]*(?:#.*)?$", re.M),
     lambda m: _BOOTSTRAP_PKG),

    # P3: SNBVTi* 跨资源目录 parents[3] → 锚点
    ("P3_t001",
     re.compile(r"^_T001_DIR = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t]*\"SNB/SNBtest/Test/t001\"[ \t]*(?:#[^\n]*)?$", re.M),
     lambda m: ('from flash.scenarios.core.anchors import anchor as _anchor\n'
                '_T001_DIR = _anchor("SNB.t001")')),
    ("P3_snb_pkg",
     re.compile(r"^_SNB_PKG_DIR = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t]*\"SNB/SNB/source/snb_package\"[ \t]*(?:#[^\n]*)?$", re.M),
     lambda m: ('from flash.scenarios.core.anchors import anchor as _anchor\n'
                '_SNB_PKG_DIR = _anchor("SNB.snb_package")')),
    ("P3_variants",
     re.compile(r"^_SNB_VARIANTS_DIR = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t]*\"SNB/SNB/variants\"[ \t]*(?:#[^\n]*)?$", re.M),
     lambda m: ('from flash.scenarios.core.anchors import anchor as _anchor\n'
                '_SNB_VARIANTS_DIR = _anchor("SNB.variants")')),

    # P4: _longrun_lib REPO_ROOT = SCEN_DIR.parents[4]
    ("P4_longrun_repo",
     re.compile(r"^REPO_ROOT = SCEN_DIR\.parents\[\d+\][ \t]*(?:#.*)?$", re.M),
     lambda m: _BOOTSTRAP.replace("_REPO_ROOT", "REPO_ROOT", 1)
                          .replace("Path(__file__).resolve()", "SCEN_DIR", 1)
                          .replace("(_c, *_c.parents)", "(SCEN_DIR, *SCEN_DIR.parents)", 1)),

    # P5: t005 _FLASH_PKG = Path(__file__).resolve().parents[8] / 'flash'
    ("P5_flash_pkg_quote",
     re.compile(r"^_FLASH_PKG = Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t*]*'flash'.*$", re.M),
     lambda m: _BOOTSTRAP_PKG),

    # P6: VCH_ml OUR = ... parents[7] / "flash" / ...
    ("P6_our_flash",
     re.compile(r"^OUR = str\(Path\(__file__\)\.resolve\(\)\.parents\[\d+\][ \t]*/[ \t]*\"flash\"[ \t]*/$", re.M),
     lambda m: ("_REPO_ROOT = Path(__file__).resolve()\n"
                "for _c in (_REPO_ROOT, *_REPO_ROOT.parents):\n"
                "    if (_c / \"pyproject.toml\").is_file() and (_c / \"start_flash.py\").is_file():\n"
                "        _REPO_ROOT = _c\n"
                "        break\n"
                "else:\n"
                "    raise RuntimeError(\"无法定位仓库根\")\n"
                "OUR = str(_REPO_ROOT / \"flash\" /")),
]


def cmd_parents(dry: bool) -> int:
    n_files = 0
    for p in sorted(SCEN.rglob("*.py")):
        rel = p.relative_to(SCEN)
        if any(part in {"__pycache__", "flash_input", "flash_output"} for part in rel.parts):
            continue
        if rel.parts[:2] == ("scripts", "relocate"):
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        new, hits = src, []
        for name, pat, repl in PARENT_RULES:
            new2, n = pat.subn(repl, new)
            if n:
                hits.append(f"{name}×{n}")
                new = new2
        if hits:
            print(f"[{'+'.join(hits)}] {rel}")
            n_files += 1
            if not dry:
                p.write_text(new, encoding="utf-8", newline="")
    print(f"\n[{'DRY-RUN' if dry else 'ok'}] 改写文件数: {n_files}")
    return 0


# ═══════════════════════ __init__.py 补齐 ═══════════════════════

_INIT_DOC = '# -*- coding: utf-8 -*-\n# ★ 场景收纳整理改造（2026-11-04）自动补齐：保证包导入/打包行为确定。\n# 场景发现由 core/discovery.py 纯文件扫描完成，本文件无需登记任何场景。\n'


def cmd_initfiles(dry: bool) -> int:
    need: list[Path] = []
    for mf in sorted(SCEN.rglob("scene*.json")):
        d = mf.parent
        if not (d / "__init__.py").is_file():
            need.append(d)
        # 场景目录上溯到 scenarios 根的中间段
        for anc in d.parents:
            if anc == SCEN:
                break
            if not (anc / "__init__.py").is_file():
                need.append(anc)
    need = sorted(set(need))
    for d in need:
        print(f"[+__init__.py] {d.relative_to(SCEN)}")
    if not dry and need:
        for d in need:
            (d / "__init__.py").write_text(_INIT_DOC, encoding="utf-8", newline="")
    print(f"\n[{'DRY-RUN' if dry else 'ok'}] 补齐 __init__.py 数: {len(need)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="场景可移植化批量改造")
    ap.add_argument("cmd", choices=["manifests", "parents", "initfiles"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return {"manifests": cmd_manifests, "parents": cmd_parents,
            "initfiles": cmd_initfiles}[a.cmd](a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
