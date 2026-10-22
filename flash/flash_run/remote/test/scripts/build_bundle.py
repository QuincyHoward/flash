#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_bundle.py — Step 04: 制作并校验 git bundle（整库含全部提交历史）。

用法: python build_wheelhouse_linux.py 同目录运行本脚本
  python build_bundle.py [--output packages/flash_sim_all.bundle]

流程:
  1. 检查工作区状态（★ 只打包已提交内容；禁用 git add -A —— E: 盘间歇
     不可见会让 add -A 静默提交删除，见 §R 事故）。若有未提交变更，
     默认中止并提示先单独提交（--allow-dirty 跳过检查，风险自负）。
  2. git bundle create <out> --all
  3. git bundle verify <out>（rc=0 判据）
  4. 体积 sanity check（预期 15~40MB；超 200MB 报警）
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
LOG_DIR = TEST_DIR / "logs"
PKG_DIR = TEST_DIR / "packages"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(f"[FATAL] git {' '.join(args)} 失败 rc={r.returncode}\n"
              f"{r.stdout[-500:]}\n{r.stderr[-500:]}")
        raise SystemExit(1)
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=None)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="工作区有未提交变更时仍继续（bundle 只含已提交内容）")
    args = ap.parse_args()

    out = Path(args.output) if args.output else PKG_DIR / "flash_sim_all.bundle"
    PKG_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 1. 工作区状态 ----
    status = git("status", "--porcelain").stdout
    # ★ 只看**已跟踪文件**的变更（?? 未跟踪产物目录不进 bundle，不阻断）；
    #   git add -A 禁用（E: 盘间歇不可见会静默提交删除，见工作记忆 §R）。
    tracked_dirty = [ln for ln in status.splitlines()
                     if ln.strip() and not ln.startswith("??")]
    if tracked_dirty and not args.allow_dirty:
        print("[FATAL] 工作区有未提交变更（bundle 只包含已提交内容）：")
        for line in tracked_dirty[:20]:
            print(f"  {line}")
        print("  ⇒ 请先单独提交这些变更（逐条显式路径 git add）"
              "或用 --allow-dirty 跳过。")
        return 1
    head = git("rev-parse", "HEAD").stdout.strip()
    print(f"[04] HEAD: {head[:12]}")
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    print(f"[04] branch: {branch}")

    # ---- 2. bundle create ----
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[04] git bundle create {out.name} --all ...")
    t0 = datetime.now()
    r = git("bundle", "create", str(out), "--all")
    print(f"[04] create rc={r.returncode}，耗时 {(datetime.now() - t0).seconds}s")

    # ---- 3. verify ----
    r = git("bundle", "verify", str(out))
    print(f"[04] verify rc={r.returncode}")
    if r.returncode != 0:
        print(r.stderr[-500:])
        return 1
    print(r.stdout.strip()[:400])

    size = out.stat().st_size
    print(f"[04] 体积: {size / 1e6:.1f} MB")
    if size > 200_000_000:
        print("[warn] bundle 超过 200MB —— 检查是否误打包了大文件")
    if size < 5_000_000:
        print("[warn] bundle 小于 5MB —— 检查仓库是否完整")

    # ---- 4. 记录清单头（供远端 clone 后比对 HEAD） ----
    (PKG_DIR / "bundle_head.txt").write_text(f"{head}\n{branch}\n", encoding="utf-8")
    print(f"[04] HEAD 已记录到 {PKG_DIR / 'bundle_head.txt'}")
    print("[04] 结论: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
