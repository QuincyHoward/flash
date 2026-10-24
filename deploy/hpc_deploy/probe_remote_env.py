#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_remote_env.py — Step 02: 超算远端只读环境探测（scfa2696 / NC-E）。

只读操作，不改远端任何文件。所有命令走**单条** RemoteSession 串行执行
（超算 SSH 限并发，绝不并行开连接）。

探测项与判据：
  1. module avail python/3.10.8     → 可用（用户已确认，复核）
  2. python/3.10.8 下 venv/ensurepip 可用性
  3. df -h $HOME                    → 剩余空间 ≥ 1.5 GB（wheelhouse+venv+源码≈850MB）
  4. FLASH 树存在性: ~/QC/FLASH/FLASH4.8 与 ~/QC/FLASH/FLASHSNB/FLASH4.8
  5. git --version
  6. 部署目标目录 ~/PhySimX/.../flash_sim 当前状态（是否已存在）

输出: logs/02_probe_<ts>.log；判据汇总 PASS/FAIL。
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parents[1] / "artifacts"      # 根目录统一产物区
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"    # 兼容旧名: logs/packages/results 统一落 artifacts
REPO_ROOT = HERE.parents[1]
LOG_DIR = TEST_DIR / "logs"

REMOTE_HOME = "/publicfs01/fs1-e/home/scfa2696"
TARGET_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim"
PKG_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"

CHECKS = [
    ("module_python310",
     "bash -lc 'module avail python/3.10.8 2>&1 | grep -c \"python/3.10.8\" || true'",
     lambda out, rc: int(out.strip() or "0") >= 1, "module python/3.10.8 可用"),
    ("module_load_venv",
     "bash -lc 'module load python/3.10.8 && python3 -c \"import venv, ensurepip; print(\\\"venv+ensurepip OK\\\")\"'",
     lambda out, rc: "venv+ensurepip OK" in out, "python/3.10.8 venv+ensurepip 可用"),
    ("python310_version",
     "bash -lc 'module load python/3.10.8 && python3 --version'",
     lambda out, rc: "3.10" in out, "python/3.10.8 版本确认"),
    ("disk_free",
     f"df -m {REMOTE_HOME} | tail -1 | awk '{{print $4}}'",
     lambda out, rc: int(out.strip() or "0") >= 1500, "HOME 剩余空间 ≥1500MB"),
    ("flash_trees",
     f"ls -d {REMOTE_HOME}/QC/FLASH/FLASH4.8 {REMOTE_HOME}/QC/FLASH/FLASHSNB/FLASH4.8 2>/dev/null | wc -l",
     lambda out, rc: int(out.strip() or "0") >= 1, "超算 FLASH/SNB 树存在（≥1）"),
    ("git_version",
     "git --version 2>/dev/null || echo NO_GIT",
     lambda out, rc: "git version" in out, "远端 git 可用"),
    ("target_dir_state",
     f"if [ -d {TARGET_DIR} ]; then ls {TARGET_DIR} | head -5; echo DIR_EXISTS; else echo DIR_ABSENT; fi",
     lambda out, rc: ("DIR_EXISTS" in out) or ("DIR_ABSENT" in out), "部署目标目录状态"),
    ("pkg_dir_state",
     f"if [ -d {PKG_DIR} ]; then echo PKG_DIR_EXISTS; else echo PKG_DIR_ABSENT; fi",
     lambda out, rc: ("PKG_DIR_EXISTS" in out) or ("PKG_DIR_ABSENT" in out), "pkg 暂存目录状态"),
    ("sbatch_available",
     "bash -lc 'which sbatch srun 2>/dev/null | wc -l'",
     lambda out, rc: int(out.strip() or "0") >= 1, "SLURM sbatch/srun 可用"),
]


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"02_probe_{ts}.log"

    # 复用包内 RemoteSession（Windows 默认 paramiko，自动建父目录、3 次重试）
    sys.path.insert(0, str(REPO_ROOT))
    from flash.flash_run.remote.session import RemoteSession

    results = []
    with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
        def w(msg: str) -> None:
            print(msg)
            lf.write(msg + "\n")

        w(f"[02] 远端探测 log: {log_path}")
        w(f"[02] RemoteSession('flash_ssh') 单会话串行，共 {len(CHECKS)} 项")
        with RemoteSession("flash_ssh") as s:
            for name, cmd, judge, desc in CHECKS:
                try:
                    out, err, rc = s.run(cmd, timeout=120)
                except Exception as e:  # noqa: BLE001
                    out, err, rc = "", f"{type(e).__name__}: {e}", -1
                blob = out or ""
                ok = False
                try:
                    ok = bool(judge(blob, rc))
                except Exception:  # noqa: BLE001
                    pass
                results.append((name, ok, desc))
                w(f"[{'ok' if ok else 'FAIL'}] {name}: {desc}"
                  f"  | rc={rc} out={blob.strip()[:120]!r}"
                  + (f" err={err.strip()[:120]!r}" if err.strip() else ""))

    n_ok = sum(1 for _, ok, _ in results if ok)
    print(f"[02] 判据: {n_ok}/{len(results)} 通过")
    for name, ok, desc in results:
        if not ok:
            print(f"  !! 未通过: {name} — {desc}")
    # 阻断性判据: module/venv/disk/sbatch；FLASH 树缺失只影响 smoke 步骤
    blocking = ["module_python310", "module_load_venv", "disk_free", "sbatch_available"]
    ok_all = all(ok for name, ok, _ in results if name in blocking)
    print(f"[02] 结论: {'PASS' if ok_all else 'FAIL'}（阻断项全过={ok_all}）")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
