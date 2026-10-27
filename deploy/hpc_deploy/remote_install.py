#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remote_install.py — Step 06: 超算命名环境离线安装 + 三套测试。

★ 环境（用户要求显式命名）: FLASH_VENV_DIR=.venv-hpc-nce
★ 离线安装: module load python/3.10.8 后用 start_flash.py --offline
  （--no-index 硬闸门 + wheelhouse 三道闸门 + 三套测试 + INSTALL_TEST_REPORT.txt）

执行策略（超算 SSH 限并发 + 动态路由会分到不同登录节点）：
  ★ 全部中间文件（脚本/日志/完成哨兵）放 **$HOME 并行盘**（flash_sim_pkg/），
    绝不用 /tmp —— /tmp 是登录节点本地盘，跨会话（不同节点）互相不可见
    （2026-10-22 实测：上传节点与轮询节点不同 ⇒ 脚本"消失"）。
  1. 上传安装脚本 → nohup bash -lc '...' 后台启动（登录 shell 保证 module 可用；
     系统裸 python3 是 3.6.8，必须先 module load python/3.10.8）
  2. 每 30s 短连接轮询：日志尾部 + **完成哨兵文件**（不依赖 kill -0 ——
     PID 判活也是节点本地的，跨节点恒 DEAD）
  3. 完成后回收 INSTALL_TEST_REPORT.txt 与远端日志到 results/

用法:
  python remote_install.py                 # 全新安装
  python remote_install.py --recover       # 逐项恢复：保留现有 venv 续跑
  python remote_install.py --profile runtime  # 磁盘不足时降档
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parents[1] / "artifacts"      # 根目录统一产物区
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"    # 兼容旧名: logs/packages/results 统一落 artifacts
REPO_ROOT = HERE.parents[1]
LOG_DIR = TEST_DIR / "logs"
RESULTS_DIR = TEST_DIR / "results"

import sys as _sys
_sys.path.insert(0, str(REPO_ROOT))
from flash._core.paths import hpc_target_dirs as _hpc_dirs
REMOTE_HOME, TARGET_DIR, PKG_DIR_REMOTE = _hpc_dirs()  # 运行期解析，绝不硬编码账号/家目录
VENV_NAME = ".venv-hpc-nce"          # ★ 用户要求：超算环境显式命名
WHEELHOUSE_REMOTE = f"{PKG_DIR_REMOTE}/wheelhouse-linux"

POLL_INTERVAL = 30       # 秒
MAX_POLLS = 360          # 30s * 360 = 3h 上限


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="full", choices=["full", "runtime", "lite"])
    ap.add_argument("--recover", action="store_true",
                    help="逐项恢复：保留现有 venv 续跑（start_flash 健康检查自愈）")
    ap.add_argument("--clean", action="store_true",
                    help="FLASH_FORCE_CLEAN=1 强制删 venv 重建（venv 半损坏时用，"
                         "如 sympy dist-info OSError）")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"06_remote_install_{ts}.log"
    # ★ 并行盘路径（跨登录节点共享），绝不用 /tmp
    remote_log = f"{PKG_DIR_REMOTE}/install_{ts}.log"
    remote_sentinel = f"{PKG_DIR_REMOTE}/install_{ts}.done"
    local_sh = LOG_DIR / f"06_install_cmd_{ts}.sh"
    remote_sh = f"{PKG_DIR_REMOTE}/install_{ts}.sh"

    venv_dir = f"{TARGET_DIR}/{VENV_NAME}"
    clean_env_var = "FLASH_FORCE_CLEAN=1 " if args.clean else ""
    venv_pip = f"{venv_dir}/bin/pip"
    resume_target = ("flash_sim[full,dev] scipy paramiko" if args.profile == "full"
                     else "flash_sim[full] scipy paramiko" if args.profile == "runtime"
                     else "flash_sim scipy paramiko")
    # ★ Lustre 断点续装：全量安装 96 包时并行盘会随机瞬时 ENOENT（dist-info
    #   METADATA 读写竞态，2026-10-22 实测 sympy/fonttools 先后中招，单包安装
    #   均正常）。pip 事务失败不删 venv，重复 install —— 已装的自动跳过，
    #   每轮推进剩余部分，直至 rc=0。
    resume_loop = (
        f"for i in 1 2 3 4 5 6; do\n"
        f"  {venv_pip} install --no-index --find-links {WHEELHOUSE_REMOTE} "
        f"{resume_target} && break\n"
        f"  echo \"[resume] 第 $i 轮续装失败，30s 后重试...\"\n"
        f"  sleep 30\n"
        f"done"
    )
    inner = (
        f"cd {TARGET_DIR} && "
        f"module load python/3.10.8 && "
        f"export PYTHONUNBUFFERED=1 "
        f"{clean_env_var}"
        f"FLASH_VENV_DIR={venv_dir} "
        f"FLASH_PROFILE={args.profile} && "
        f"python3 start_flash.py --offline --wheelhouse {WHEELHOUSE_REMOTE} "
        f"--profile {args.profile}; "
        f"rc1=$?; "
        f"if [ $rc1 -ne 0 ]; then echo '[resume] start_flash 首轮失败，进入续装循环'; {resume_loop}; fi; "
        f"python3 start_flash.py --offline --wheelhouse {WHEELHOUSE_REMOTE} "
        f"--profile {args.profile}"
    )
    script = (
        f"#!/bin/bash\n"
        f"{inner}\n"
        f"echo $? > {remote_sentinel}\n"
    )
    local_sh.write_text(script, encoding="utf-8", newline="\n")

    sys.path.insert(0, str(REPO_ROOT))
    from flash.flash_run.remote.session import RemoteSession

    print(f"[06] 目标: {TARGET_DIR}")
    print(f"[06] 命名环境: FLASH_VENV_DIR={VENV_NAME}（用户要求显式命名）")
    print(f"[06] profile: {args.profile}  recover: {args.recover}")
    print(f"[06] 安装日志（并行盘）: {remote_log}")

    with RemoteSession("flash_ssh") as s:
        # ---- 清理旧哨兵 + 上传脚本 + 启动（★ 启动 exec 加 3 次重试，
        #      应对 paramiko exec_command 瞬时失败）----
        s.run(f"rm -f {remote_sentinel}", timeout=60)
        ok = s.upload(str(local_sh), remote_sh)
        if not ok:
            print("[FATAL] 上传安装脚本失败")
            return 1
        launched = False
        # ★★ 启动确认铁律：paramiko exec 的 `nohup ... & echo LAUNCHED` 常常
        #   拿不到回显（★ exec 失败 ≠ 未执行！老铁律），而此时作业**其实已经
        #   在跑**（实测：日志已写完、哨兵已生成，脚本却报"启动 3 次均失败"）。
        #   ⇒ 判据改为「日志已出现 或 哨兵已生成」，二者其一即视为已启动。
        for attempt in range(1, 4):
            try:
                out, err, rc = s.run(
                    f"chmod +x {remote_sh} && cd {PKG_DIR_REMOTE} && "
                    f"nohup bash {remote_sh} > {remote_log} 2>&1 & echo LAUNCHED",
                    timeout=60)
                if "LAUNCHED" in (out or ""):
                    launched = True
                    break
            except Exception as e:  # noqa: BLE001
                print(f"  [launch] 第 {attempt} 次启动异常: {type(e).__name__}: {e}")
            # 回显没拿到 → 查实际状态：日志已出现 / 哨兵已生成 ⇒ 已启动
            out2, _, _ = s.run(
                f"if [ -s {remote_log} ] || [ -f {remote_sentinel} ]; "
                f"echo ACTUALLY_STARTED; else echo NOT_STARTED; fi",
                timeout=60)
            if "ACTUALLY_STARTED" in (out2 or ""):
                print("  [launch] 未拿到 LAUNCHED 回显，但日志/哨兵已出现 ⇒ 判定已启动")
                launched = True
                break
            print(f"  [launch] 第 {attempt}/3 次启动未确认，20s 后重试...")
            time.sleep(20)
        if not launched:
            print("[FATAL] 启动 3 次均失败（且日志/哨兵均未出现）")
            return 1
        print(f"[06] 已后台启动（bash -lc 登录 shell，module load python/3.10.8）")
        print(f"[06] 预计 5~25 分钟（WSL 预演实测 432s），每 {POLL_INTERVAL}s 轮询一次")

        # ---- 哨兵轮询（短连接，不占并发；跨节点只认并行盘文件） ----
        n = 0
        done_rc = None
        while n < MAX_POLLS:
            n += 1
            time.sleep(POLL_INTERVAL)
            est_min = n * POLL_INTERVAL // 60
            out, err, rc = s.run(
                f"tail -c 300 {remote_log} 2>/dev/null | tr '\\n' ' ' | tail -c 150; "
                f"echo '||'; cat {remote_sentinel} 2>/dev/null || echo NORC",
                timeout=60)
            blob = (out or "")
            tail, _, rcv = blob.partition("||")
            done = rcv.strip() not in ("", "NORC")
            print(f"  [poll {n:3d}] 已等 {est_min:3d}min | "
                  f"{'完成 rc=' + rcv.strip() if done else '运行中'} | "
                  f"尾部: ...{tail.strip()[-110:]!r}")
            if done:
                done_rc = int(rcv.strip())
                break
        else:
            print("[FATAL] 轮询超时（3h）—— 查远端日志后用 --recover 续跑")
            return 1

        # ---- 判定 ----
        out, err, rc = s.run(f"echo ===TAIL===; tail -50 {remote_log}", timeout=120)
        full_tail = (out or "")
        (LOG_DIR / f"06_remote_log_tail_{ts}.txt").write_text(full_tail, encoding="utf-8")
        print(full_tail.split("===TAIL===")[-1][-2200:])

        venv_py = f"{venv_dir}/bin/python"
        out, err, rc = s.run(
            f"{venv_py} -c \"import flash, numpy, h5py, pytest, yt; "
            f"import flash as f; print('IMPORT_OK', f.__file__)\"", timeout=300)
        import_ok = "IMPORT_OK" in (out or "")
        print(f"[06] 独立验证 import flash/yt: {'OK' if import_ok else 'FAIL'}")
        if not import_ok:
            print((out or "")[-400:], (err or "")[-600:])

        # ---- 回收报告与日志 ----
        report_local = RESULTS_DIR / f"INSTALL_TEST_REPORT_hpc_{ts}.txt"
        ok_dl = s.download(f"{TARGET_DIR}/test/reports/INSTALL_TEST_REPORT.txt",
                           str(report_local))
        print(f"[06] 报告回收: {'OK' if ok_dl else 'FAIL'} -> {report_local}")
        if ok_dl:
            print(report_local.read_text(encoding="utf-8", errors="replace")[-1500:])
        s.download(remote_log, str(RESULTS_DIR / f"remote_install_log_{ts}.txt"))

        verdict = "PASS" if (done_rc == 0 and import_ok and ok_dl) else "FAIL"
        print(f"[06] 远端 start_flash 退出码: {done_rc}")
        print(f"[06] 结论: {verdict}")
        return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
