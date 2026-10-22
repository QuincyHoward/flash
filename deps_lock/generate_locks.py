#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_locks.py — 从 deploy/env_spec.py 生成三平台 requirements 锁定文件
═══════════════════════════════════════════════════════════

用法:
    python deps_lock/generate_locks.py           # 生成/覆盖三份 lock
    python deps_lock/generate_locks.py --check   # 只校验现有 lock 与 env_spec 一致

产出:
    deps_lock/requirements-win.txt
    deps_lock/requirements-wsl.txt
    deps_lock/requirements-hpc.txt

铁律:
  * lock 文件**由本脚本生成**，禁止手改（手改会在下次生成时被覆盖/被 --check 拦下）；
  * 平台差异只允许来自 deploy/env_spec.py 的 PLATFORM_OVERRIDES。
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "deploy"))

import env_spec  # noqa: E402  (deploy/env_spec.py)

FILES = {
    "win": HERE / "requirements-win.txt",
    "wsl": HERE / "requirements-wsl.txt",
    "hpc": HERE / "requirements-hpc.txt",
}


def render(platform: str) -> str:
    versions = env_spec.resolve(platform, profile="full")
    lines = [
        f"# requirements-{platform}.txt — 由 deps_lock/generate_locks.py 自动生成，禁止手改",
        f"# 平台说明: {env_spec.PLATFORM_NOTES[platform]}",
        f"# 基线策略: 三平台交集版本；差异仅来自 deploy/env_spec.py::PLATFORM_OVERRIDES",
        "# 安装: pip install --no-index --find-links=<wheelhouse> -r requirements-"
        f"{platform}.txt",
        "",
    ]
    overrides = env_spec.PLATFORM_OVERRIDES.get(platform, {})
    for pkg in sorted(versions):
        v = versions[pkg]
        if pkg in overrides and overrides[pkg] != env_spec.BASELINE[pkg]:
            lines.append(f"{pkg}=={v}  # 平台差异（基线 {env_spec.BASELINE[pkg]}）")
        else:
            lines.append(f"{pkg}=={v}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写入")
    args = ap.parse_args()

    problems = []
    for platform, path in FILES.items():
        want = render(platform)
        if args.check:
            got = path.read_text(encoding="utf-8") if path.exists() else ""
            if got != want:
                problems.append(f"{path.name}: 与 env_spec 不一致（需重新生成）")
            else:
                print(f"[OK] {path.name} 一致")
        else:
            path.write_text(want, encoding="utf-8")
            print(f"[OK] 已生成 {path}")
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print("→ 修复: python deps_lock/generate_locks.py （重新生成）")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
