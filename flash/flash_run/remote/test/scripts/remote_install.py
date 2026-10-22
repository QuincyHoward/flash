#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remote_install.py — Step 06: 超算命名环境离线安装 + 三套测试。

★ 环境（用户要求显式命名）: FLASH_VENV_DIR=.venv-hpc-nce
★ 离线安装: module load python/3.10.8 后用 start_flash.py --offline
  （--no-index 硬闸门 + wheelhouse 三道闸门 + 三套测试 + INSTALL_TEST_REPORT.txt）

执行策略（超算 SSH 限并发 ⇒ 全程单会话短连接轮询）：
  1. nohup 后台启动安装脚本（PYTHONUNBUFFERED=1，日志远端落盘）
  2. 每 30s 短连接轮询日志尾部 + 进程存活（sleep 在本地进行，对话中显示）
  3. 完成后回收 INSTALL_TEST_REPORT.txt 与远端日志到 results/

用法:
  python remote_install.py                 # 全新安装
  python remote_install.py --recover       # 逐项恢复模式：不删环境，续装+单包诊断
  python remote_install.py --profile runtime  # 磁盘不足时降档
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
LOG_DIR = TEST_DIR / "logs"
RESULTS_DIR = TEST_DIR / "results"

REMOTE_HOME = "/publicfs01/fs1-e/home/scfa2696"
TARGET_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim"
PKG_DIR_REMOTE = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
VENV_NAME = ".venv-hpc-nce"          # ★ 用户要求：超算环境显式命名
WHEELHOUSE_REMOTE = f"{PKG_DIR_REMOTE}/wheelhouse-linux"

POLL_INTERVAL = 30       # 秒
MAX_POLLS = 240          # 30s * 240 = 2h 上限


def install_script(profile: str, recover: bool) -> str:
    venv_dir = f"{TARGET_DIR}/{VENV_NAME}"
    recover_env = "FLASH_FORCE_CLEAN=0 " if recover else ""
    return f"""#!/bin/bash
set -uo pipefail
source /public1/soft/modules/module.sh 2>/dev/null || true
module load python/3.10.8
cd {TARGET_DIR}
export PYTHONUNBUFFERED=1
export FLASH_VENV_DIR={venv_dir}
export FLASH_PROFILE={profile}
{recover_env}exec python3 start_flash.py --offline --wheelhouse {WHEELHOUSE_REMOTE} --profile {profile}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="full", choices=["full", "runtime", "lite"])
    ap.add_argument("--recover", action="store_true",
                    help="逐项恢复：保留现有 venv 续跑（start_flash 健康检查自愈）")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"06_remote_install_{ts}.log"
    remote_log = f"/tmp/flash_install_{ts}.log"
    remote_sh = f"/tmp/flash_install_{ts}.sh"

    sys.path.insert(0, str(REPO_ROOT))
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    print(f"[06] 目标: {TARGET_DIR}")
    print(f"[06] 命名环境: FLASH_VENV_DIR={VENV_NAME}（用户要求显式命名）")
    print(f"[06] profile: {args.profile}  recover: {args.recover}")
    print(f"[06] 远端日志: {remote_log}")

    script = install_script(args.profile, args.recover)
    with open(LOG_DIR / f"06_install_cmd_{ts}.sh", "w", encoding="utf-8",
              newline="\n") as f:
        f.write(script)

    with RemoteSession("flash_ssh") as s:
        # ---- 启动 ----
        ok = s.upload(str(LOG_DIR / f"06_install_cmd_{ts}.sh"), remote_sh)
        if not ok:
            print("[FATAL] 上传安装脚本失败")
            return 1
        out, err, rc = s.run(
            f"chmod +x {remote_sh} && "
            f"nohup bash {remote_sh} > {remote_log} 2>&1 & echo PID=$!",
            timeout=60)
        pid = ""
        for line in (out or "").splitlines():
            if line.startswith("PID="):
                pid = line[4:].strip()
        print(f"[06] 已后台启动 PID={pid}（sleep 前，约 5~25 分钟）")

        # ---- 轮询（短连接，不占并发） ----
        n = 0
        last_tail = ""
        while n < MAX_POLLS:
            n += 1
            time.sleep(POLL_INTERVAL)
            est_min = n * POLL_INTERVAL // 60
            out, err, rc = s.run(
                f"tail -c 400 {remote_log} 2>/dev/null; echo '---'; "
                f"kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD",
                timeout=60)
            blob = (out or "")
            alive = "ALIVE" in blob
            tail = blob.split("---")[0].strip()[-200:]
            new_tail = tail[len(last_tail):] if tail.startswith(last_tail) else tail
            last_tail = tail
            print(f"  [poll {n:3d}] 已等 {est_min}min | 进程: {'运行中' if alive else '已结束'}"
                  f" | 尾部: {new_tail.strip()[-120:]!r}")
            if not alive:
                break
        else:
            print("[FATAL] 轮询超时（2h）—— 请查远端日志后用 --recover 续跑")
            return 1

        # ---- 判定 ----
        out, err, rc = s.run(f"wc -l {remote_log}; echo ===TAIL===; tail -40 {remote_log}",
                             timeout=120)
        full_tail = (out or "")
        (LOG_DIR / f"06_remote_log_tail_{ts}.txt").write_text(full_tail, encoding="utf-8")
        print(full_tail.split("===TAIL===")[-1][-2000:])

        venv_py = f"{TARGET_DIR}/{VENV_NAME}/bin/python"
        out, err, rc = s.run(
            f"{venv_py} -c \"import flash, numpy, h5py, pytest, yt; "
            f"import flash as f; print('IMPORT_OK', f.__file__)\"", timeout=300)
        import_ok = "IMPORT_OK" in (out or "")
        print(f"[06] 独立验证 import flash/yt: {'OK' if import_ok else 'FAIL'}")
        if not import_ok:
            print((out or "")[-400:], (err or "")[-600:])

        # ---- 回收报告 ----
        report_local = RESULTS_DIR / f"INSTALL_TEST_REPORT_hpc_{ts}.txt"
        ok_dl = s.download(f"{TARGET_DIR}/test/reports/INSTALL_TEST_REPORT.txt",
                           str(report_local))
        print(f"[06] 报告回收: {'OK' if ok_dl else 'FAIL'} -> {report_local}")
        if ok_dl:
            print(report_local.read_text(encoding="utf-8", errors="replace")[-1500:])

        verdict = "PASS" if (rc == 0 and import_ok and ok_dl) else "FAIL"
        print(f"[06] 远端 start_flash 退出码: {rc}")
        print(f"[06] 结论: {verdict}")
        return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
