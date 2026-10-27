#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remote_clean.py — Step 00: 超算安装目录安全清理（2026-10-22 新增）

用途
  重装前把 ``<base>/flash_sim``（安装目录）腾空，让 05 步重新 clone、
  06 步全新离线安装，避免旧 venv/旧代码污染。

安全策略（★ 默认不删，两道闸门）
  1. **默认 dry-run**：只列出将清理的条目 + 体积 + 活跃作业检查，不动任何文件；
  2. ``--yes`` 才执行，且执行方式是 **同盘改名归档**（``mv`` 秒级、可回滚），
     归档目录 ``flash_sim.bak-<时间戳>``；确认新装成功后再 ``--purge`` 删归档。
     ⇒ 误删风险归零，且 Lustre 上删除 1.8G 目录远比改名慢。

用法
  python remote_clean.py                 # dry-run（只报告）
  python remote_clean.py --yes           # 归档腾空（可回滚）
  python remote_clean.py --purge         # 连带删除历史归档
  python remote_clean.py --yes --keep-pkg   # 连同 flash_sim_pkg 一起归档（默认保留 pkg）

铁律
  * 中间文件一律落 $HOME 并行盘，不用 /tmp（跨登录节点不可见，2026-10-22 实测）；
  * 有活跃作业时拒绝执行（防打断别人/自己的仿真）。
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parents[1] / "artifacts"
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"
LOG_DIR = TEST_DIR / "logs"
RESULTS_DIR = TEST_DIR / "results"
REPO_ROOT = HERE.parents[1]

import sys as _sys
_sys.path.insert(0, str(REPO_ROOT))
from flash._core.paths import hpc_target_dirs as _hpc_dirs
REMOTE_HOME, TARGET_DIR, PKG_DIR_REMOTE = _hpc_dirs()  # 运行期解析，绝不硬编码账号/家目录
BASE = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash"


def _ssh():
    sys.path.insert(0, str(REPO_ROOT))
    from flash.flash_run.remote.session import RemoteSession
    return RemoteSession("flash_ssh")


def survey(s, targets: list[str]) -> tuple[str, int, str]:
    """返回 (清单文本, 活跃作业数, 总体积)。只读。"""
    cmd = (
        f"cd {BASE} 2>/dev/null || exit 1; "
        f"for d in {' '.join(targets)}; do "
        f"  if [ -e \"$d\" ]; then echo \"### $d\"; ls -A \"$d\" | head -40; "
        f"    echo \"### size: $(du -sh \"$d\" 2>/dev/null | cut -f1)\"; "
        f"  else echo \"### $d (不存在)\"; fi; "
        f"done; echo '### JOBS'; squeue -u $USER -h -o '%i|%j|%T|%M' 2>/dev/null | head -20"
    )
    out, _, rc = s.run(cmd, timeout=300)
    return (out or ""), (out or "").count("|"), ""


def main() -> int:
    ap = argparse.ArgumentParser(description="超算安装目录安全清理（默认 dry-run）")
    ap.add_argument("--yes", action="store_true", help="真正执行（归档腾空）")
    ap.add_argument("--purge", action="store_true", help="删除历史归档 flash_sim.bak-*")
    ap.add_argument("--keep-pkg", action="store_true", default=True,
                    help="保留 flash_sim_pkg（默认保留：wheelhouse/bundle 在此）")
    ap.add_argument("--include-pkg", action="store_true",
                    help="连同 flash_sim_pkg 一起归档（重造 wheelhouse 时用）")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    targets = [TARGET_DIR] + ([f"{BASE}/flash_sim_pkg"] if args.include_pkg else [])
    archive = f"{BASE}/flash_sim.bak-{ts}"

    with _ssh() as s:
        # ---------- purge 分支 ----------
        if args.purge:
            out, _, rc = s.run(f"cd {BASE} && ls -d flash_sim.bak-* 2>/dev/null | wc -l", timeout=120)
            n = (out or "0").strip()
            print(f"[00] 历史归档数量: {n}")
            if n == "0":
                print("[00] 无归档可删")
                return 0
            if not args.yes:
                print("[00] dry-run: 加 --yes 才真正删除")
                return 0
            print(f"[00] 删除归档（Lustre 大目录删除较慢，耐心等待）...")
            t0 = time.time()
            out, err, rc = s.run(f"cd {BASE} && rm -rf flash_sim.bak-* && echo PURGED", timeout=3600)
            ok = "PURGED" in (out or "")
            print(f"[00] purge {'OK' if ok else 'FAIL'}（{time.time() - t0:.0f}s）")
            return 0 if ok else 1

        # ---------- 体检 ----------
        listing, n_jobs, _ = survey(s, targets)
        (LOG_DIR / f"00_survey_{ts}.txt").write_text(listing, encoding="utf-8")
        print("[00] ==== 清理前体检 ====")
        print(listing)
        print(f"[00] 活跃作业行数: {n_jobs}")
        if n_jobs:
            print("[FATAL] 存在活跃作业，拒绝清理（先 scancel 或等其结束）")
            return 2

        if not args.yes:
            print("[00] dry-run：未做任何改动。确认无误后加 --yes 执行归档腾空。")
            print(f"[00] 将归档: {archive}")
            return 0

        # ---------- 执行：同盘改名归档 ----------
        print(f"[00] 归档腾空 → {archive}")
        t0 = time.time()
        mv = " && ".join([f"mv {d} {archive}" if i == 0 else f"mv {d} {archive}/{d.split('/')[-1]}"
                          for i, d in enumerate(targets)])
        out, err, rc = s.run(
            f"cd {BASE} && mkdir -p {archive} && {mv} && ls -A {archive} "
            f"&& echo ARCHIVED", timeout=1800)
        ok = "ARCHIVED" in (out or "")
        if not ok:
            print(f"[FATAL] 归档失败 rc={rc}: {(err or out or '')[-400:]}")
            return 1
        print(f"[00] 归档完成（{time.time() - t0:.0f}s）:\n{(out or '').strip()[-500:]}")

        # 重建**空**的安装目录（★ 只能空！
        #   git clone 要求目标目录不存在或为空 —— 若在此处预建
        #   artifacts/dist 等子目录，05 步的 clone 会报
        #   "destination path already exists and is not an empty directory"。
        #   生成目录的补偿放在 05 步 clone 之后做。）
        out, err, rc = s.run(
            f"rm -rf {TARGET_DIR} && mkdir -p {TARGET_DIR} && "
            f"ls -A {TARGET_DIR} | wc -l && echo READY", timeout=1800)
        ready = "READY" in (out or "")
        print(f"[00] 空目录就绪: {'OK' if ready else 'FAIL'}"
              f"（条目数 {(out or '').splitlines()[0].strip() if out else '?'}）")
        (RESULTS_DIR / f"00_clean_{ts}.txt").write_text(
            f"archive={archive}\nlisting:\n{listing}\n", encoding="utf-8")
        print("[00] 回滚方法: mv <archive>/flash_sim flash_sim（原样恢复）")
        print("[00] 确认新装成功后可执行: python remote_clean.py --purge --yes")
        return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())