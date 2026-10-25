#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refresh_body_wheel.py — 只替换 wheelhouse 里的**本体 wheel**并重写 MANIFEST。

★ 为什么需要它（2026-10-26 实测踩坑）：
  `build_wheelhouse_linux.py` 每次都把 **整个 wheelhouse 删光重造**（含
  pip download 全部依赖）。但代码改动的绝大多数时候**依赖闭包没变**，
  只有本体 wheel（flash_sim-*.whl）需要更新 —— 重新下载 165 MB 既慢
  又可能因 PyPI 漂移引入版本变化（见下方 ★ 事故）。

★ 事故背景（记忆铁律的又一次印证）：
  - `pip download` 会用 PyPI 同名包**覆盖**本地 wheel（--find-links 不保证
    本地优先）⇒ 本体**绝不进 pip download 列表**，只单独拷贝 + 记指纹。
  - 造包后必核对 wheel 是 **MB 级**；GB 级 = exclude 漏了。
    本轮实测：modes_test/results/ 未排除 ⇒ wheel 达 **280 MB** ⇒ FAIL。

★ 本脚本的四道闸门（任一不过即中止，不留半成品）：
  1. 新本体 wheel 体积 ∈ [1, 20] MB（MB 级红线）；
  2. 新本体 wheel 条目数 ∈ [1000, 100000]（防残包/空包）；
  3. 写完 MANIFEST 后 `verify_manifest(deep=True)`（文件齐全 + 大小 +
     SHA256 三重校验）——★ 用**指纹**判定，不用体积（体积会被同名包骗）；
  4. `preflight()` 覆盖度 100% + `wheel_leak_audit.py` rc=0。

用法:
  python deploy/hpc_deploy/refresh_body_wheel.py \
      --body artifacts/dist_new/flash_sim-0.1.11-py3-none-any.whl \
      --house artifacts/logs/hpc_deploy/packages/wheelhouse-linux
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "deploy"))
import _wh_common as wh  # noqa: E402

# 与 build_wheelhouse_linux.py 同源的目标平台标记（超算 NC-E）
TARGET_PLATFORM = "linux"
TARGET_PYTHON_TAG = "3.10"
TARGET_PY_VERSION = "3.10.8"
TARGET_DESC = "NC-E scfa2696 python/3.10.8"
MANUAL_LINUX_EXTRAS = ["jeepney", "secretstorage",
                       "typing-extensions", "tomli", "exceptiongroup",
                       "importlib-metadata", "zipp", "backports.tarfile",
                       "pexpect", "ptyprocess"]


def die(msg: str) -> None:
    print(f"[FATAL] {msg}")
    raise SystemExit(1)


def wheel_entry_count(p: Path) -> int:
    import zipfile
    try:
        with zipfile.ZipFile(p) as z:
            return len(z.namelist())
    except Exception:  # noqa: BLE001
        return -1


def find_body_wheel(explicit: str | None) -> Path:
    """定位本体 wheel（显式指定优先；否则找 artifacts/dist* 与 dist/）。"""
    if explicit:
        p = Path(explicit).resolve()
        if not p.is_file():
            die(f"指定的本体 wheel 不存在: {p}")
        return p
    cands: list[Path] = []
    for d in (REPO_ROOT / "artifacts" / "dist_new",
              REPO_ROOT / "artifacts" / "dist",
              REPO_ROOT / "dist"):
        if d.is_dir():
            cands.extend(d.glob("flash_sim-*.whl"))
    if not cands:
        die("未找到 flash_sim-*.whl —— 先构建: "
            "python -m build --wheel --no-isolation -o artifacts/dist_new")
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0]


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", default=None, help="本体 wheel 路径（默认自动找最新）")
    ap.add_argument("--house", default=None, help="wheelhouse 目录")
    ap.add_argument("--profile", default="full")
    args = ap.parse_args()

    house_dir = Path(args.house).resolve() if args.house else (
        REPO_ROOT / "artifacts" / "logs" / "hpc_deploy" / "packages"
        / "wheelhouse-linux")
    if not house_dir.is_dir():
        die(f"wheelhouse 目录不存在: {house_dir}\n"
            "  ⇒ 首次造包请跑: python deploy/hpc_deploy/build_wheelhouse_linux.py")

    body = find_body_wheel(args.body)
    print(f"[refresh] wheelhouse : {house_dir}")
    print(f"[refresh] 本体 wheel : {body.name} "
          f"({wh.human_size(body.stat().st_size)})")

    # ---- 闸门 1/2：体积与条目数 ----
    size = body.stat().st_size
    entries = wheel_entry_count(body)
    print(f"[refresh]   size={size} bytes  entries={entries}")
    if not (1_000_000 <= size <= 20_000_000):
        die(f"本体 wheel 体积 {wh.human_size(size)} 越界 [1, 20] MB —— "
            "疑似 exclude 漏了（查 modes_test/results/ 等产物目录）或残包")
    if not (1000 <= entries <= 100000):
        die(f"本体 wheel 条目数异常: {entries}")

    # ---- 换本体：删旧版本 wheel（同名不同版本会共存 → pip 装错版本）----
    old_manifest = wh.WheelHouse(house_dir).read_manifest() or {}
    old_body_names = {e["file"] for e in old_manifest.get("entries", [])
                      if "flash" in e.get("name", "").lower()}
    for old in old_body_names:
        op = house_dir / old
        if op.is_file() and op.name != body.name:
            print(f"[refresh]   移除旧本体 wheel: {old}")
            op.unlink()

    dest = house_dir / body.name
    shutil.copy2(body, dest)
    print(f"[refresh]   已拷入: {dest.name}")

    # ---- 重写 MANIFEST ----
    house = wh.WheelHouse(house_dir)
    import platform as _plat
    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "profile": args.profile,
        "profile_desc": wh.PROFILES[args.profile]["desc"],
        "project_dist": wh.PROJECT_DIST,
        "git_sha": "N/A",
        "python_version": f"cross-build target {TARGET_PY_VERSION}",
        "platform": f"cross:{_plat.system()}-{_plat.machine()} -> linux x86_64",
        "platform_tag": TARGET_PLATFORM,
        "python_tag": TARGET_PYTHON_TAG,
        "platform_extra_pkgs": MANUAL_LINUX_EXTRAS,
        "platform_diff_note": ("交叉造包: Windows 联网机 pip download "
                               "--platform manylinux2014_x86_64 --python-version 3.10 "
                               "（目标: NC-E python/3.10.8）"),
        "pip_flags": ["--no-index"],
        "target": TARGET_DESC,
        "refreshed_note": ("2026-10-26 仅刷新本体 wheel，依赖闭包沿用"
                           "build_wheelhouse_linux.py 的交叉造包结果"),
    }
    mp = house.write_manifest(meta)
    man = house.read_manifest() or {}
    print(f"[refresh] MANIFEST: {len(man.get('entries', []))} 条目 -> {mp.name}")

    # ---- 闸门 3：MANIFEST 深校验（齐全 + 大小 + SHA256）----
    problems, notes = house.verify_manifest(deep=True)
    for n in notes:
        print(f"[refresh]   {n}")
    if problems:
        for p in problems[:20]:
            print(f"    - {p}")
        die(f"MANIFEST 校验失败 {len(problems)} 项")
    print("[refresh]   MANIFEST 深校验 OK（齐全 + 大小 + SHA256）")

    # ---- 闸门 4：覆盖度 + 泄漏审计 ----
    missing, present = house.preflight(REPO_ROOT / "pyproject.toml", args.profile)
    print(f"[refresh]   覆盖度: {len(present)}/{len(present) + len(missing)}")
    if missing:
        die(f"预检缺直接依赖: {missing}")

    audit = REPO_ROOT / "deploy" / "wheel_leak_audit.py"
    r = subprocess.run([sys.executable, str(audit), str(house_dir)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    print((r.stdout or "")[-1500:])
    if r.returncode != 0:
        print((r.stderr or "")[-800:])
        die(f"泄漏审计未通过 rc={r.returncode}")

    total = sum(p.stat().st_size for p in house_dir.iterdir() if p.is_file())
    n_wheel = len(list(house_dir.glob("*.whl")))
    print(f"[refresh] 完成: {n_wheel} wheel, 总体积 {wh.human_size(total)}, "
          f"耗时 {time.time() - t0:.0f}s")
    print("[refresh] 结论: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
