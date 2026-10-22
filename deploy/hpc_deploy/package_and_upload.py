#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""package_and_upload.py — Step 05: 打包上传与远端展开 clone。

流程（★ 上传用单会话；远端命令串行执行）：
  1. 本地 tar czf packages/deploy.tar.gz -C packages flash_sim_all.bundle wheelhouse-linux
     （相对路径打包，远端解压免绝对路径问题）
  2. RemoteSession("flash_ssh") 上传到 ~/PhySimX/PhySimX/simulation/flash/flash_sim_pkg/
     - .part 临时名写入 → SFTP stat 字节数校验 → 原子改名
     - set_keepalive(20)、长超时
  3. 远端串行执行:
     a. sha256sum 双端比对
     b. tar xzf
     c. git clone flash_sim_all.bundle -> $HOME/PhySimX/PhySimX/simulation/flash/flash_sim
        （已存在则先比对 HEAD，同为 bundle HEAD 时跳过；否则报错由人工裁决）
     d. git remote set-url origin https://gitee.com/physimx/flash.git
     e. mkdir -p dist offline_pkg test/reports（fresh-clone 生成目录补偿）
判据: 双端 SHA256 一致 + 远端 start_flash.py / deploy/_wh_common.py 存在。
"""
import hashlib
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parents[1] / "artifacts"      # 根目录统一产物区
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"    # 兼容旧名: logs/packages/results 统一落 artifacts
REPO_ROOT = HERE.parents[1]
LOG_DIR = TEST_DIR / "logs"
PKG_DIR = TEST_DIR / "packages"

REMOTE_HOME = "/publicfs01/fs1-e/home/scfa2696"
PKG_DIR_REMOTE = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
TARGET_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim"
GITEE_URL = "https://gitee.com/physimx/flash.git"

BUNDLE = PKG_DIR / "flash_sim_all.bundle"
WHEELHOUSE = PKG_DIR / "wheelhouse-linux"
TARBALL = PKG_DIR / "deploy.tar.gz"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_tarball() -> None:
    if not BUNDLE.is_file():
        raise SystemExit("[FATAL] 缺少 flash_sim_all.bundle —— 先跑 build_bundle.py")
    if not WHEELHOUSE.is_dir():
        raise SystemExit("[FATAL] 缺少 wheelhouse-linux —— 先跑 build_wheelhouse_linux.py")
    if TARBALL.is_file():
        TARBALL.unlink()
    print("[05] tar czf deploy.tar.gz （wheelhouse ~165MB，压缩约 1-3 分钟）...")
    with tarfile.open(TARBALL, "w:gz") as tf:
        tf.add(BUNDLE, arcname="flash_sim_all.bundle")
        tf.add(WHEELHOUSE, arcname="wheelhouse-linux")
    print(f"[05] tar 完成: {TARBALL.stat().st_size / 1e6:.1f} MB")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"05_upload_{ts}.log"
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")

    def w(msg: str) -> None:
        print(msg)
        log_f.write(msg + "\n")
        log_f.flush()

    sys.path.insert(0, str(REPO_ROOT))
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    local_sha = ""
    t_start = time.time()
    with RemoteSession("flash_ssh") as s:
        # ---- 1-2. 打包 + 上传（幂等：远端已有同 SHA 的 tar 则跳过上传） ----
        make_tarball()
        local_sha = sha256_file(TARBALL)
        w(f"[05] 本地 SHA256: {local_sha}")

        remote_tar = f"{PKG_DIR_REMOTE}/deploy.tar.gz"
        out, err, rc = s.run(f"sha256sum {remote_tar} 2>/dev/null || echo ABSENT",
                             timeout=300)
        remote_line = (out or "").strip()
        remote_sha = remote_line.split(" ", 1)[0] if remote_line else ""
        if remote_sha == local_sha:
            w("[05] [skip] 远端已有同 SHA256 的 deploy.tar.gz，跳过上传")
        else:
            w(f"[05] 上传 -> {remote_tar}（约 230MB，视线路 2~15 分钟）...")
            t0 = time.time()
            # RemoteSession.upload = paramiko put（3 次重试，自动建父目录）
            ok = s.upload(str(TARBALL), remote_tar)
            if not ok:
                w("[FATAL] 上传失败（RemoteSession.upload 返回 False）")
                return 1
            w(f"[05] 上传完成，耗时 {time.time() - t0:.0f}s")

            # ---- 3a. 远端 SHA256 比对 ----
            out, err, rc = s.run(f"sha256sum {remote_tar}", timeout=300)
            remote_line = (out or "").strip()
            remote_sha = remote_line.split(" ", 1)[0] if remote_line else ""
            w(f"[05] 远端 SHA256: {remote_sha}")
            if remote_sha != local_sha:
                w("[FATAL] 双端 SHA256 不一致 —— 传输损坏，删除远端文件后重跑本脚本")
                s.run(f"rm -f {remote_tar}", timeout=60)
                return 1
            w("[05] [ok] 双端 SHA256 一致")

        # ---- 3b. 解压 ----
        out, err, rc = s.run(f"cd {PKG_DIR_REMOTE} && tar xzf deploy.tar.gz && ls -la", timeout=900)
        w(f"[05] 解压 rc={rc}")
        if rc != 0:
            w((err or "")[-600:])
            return 1
        w((out or "")[-800:])

        # ---- 3c. git clone（幂等：已存在且 HEAD 一致则跳过） ----
        head_expect = (PKG_DIR / "bundle_head.txt").read_text().split()[0]
        # ★ 远端 git 1.8.3.1 不支持 `git -C`（1.8.5 引入）—— 必须用 `cd dir && git`
        out, err, rc = s.run(
            f"if [ -d {TARGET_DIR}/.git ]; then "
            f"  cd {TARGET_DIR} && git rev-parse HEAD; echo CLONE_EXISTS; "
            f"else echo CLONE_ABSENT; fi", timeout=120)
        blob = (out or "")
        head_remote = ""
        if "CLONE_EXISTS" in blob:
            head_remote = blob.strip().splitlines()[0]
            if head_remote == head_expect:
                w(f"[05] [ok] 部署目录已存在且 HEAD 一致（{head_remote[:12]}），跳过 clone")
            else:
                # ---- 增量同步：从新 bundle fetch + fast-forward（git 1.8.3 兼容）----
                w(f"[05] 远端 HEAD {head_remote[:12]} != bundle HEAD {head_expect[:12]}"
                  f" → 增量同步 (fetch bundle + ff-merge) ...")
                # ★ paramiko exec 瞬时失败重试（历史实测：失败≠未执行，故每次
                #   重试前检查 HEAD 是否已到位，避免重复 fetch）
                head_after = ""
                for attempt in range(1, 4):
                    try:
                        out, err, rc = s.run(
                            f"cd {TARGET_DIR} && git rev-parse HEAD; "
                            f"git fetch {PKG_DIR_REMOTE}/flash_sim_all.bundle "
                            f"'refs/heads/master:refs/heads/bundle-sync' 2>&1 | tail -2 && "
                            f"git merge --ff-only bundle-sync 2>&1 | tail -2 && "
                            f"git branch -d bundle-sync 2>/dev/null; git rev-parse HEAD",
                            timeout=600)
                    except Exception as e:  # noqa: BLE001
                        out, err, rc = "", f"{type(e).__name__}: {e}", -1
                    lines = (out or "").strip().splitlines()
                    head_after = lines[-1].strip() if lines else ""
                    if head_after == head_expect:
                        break
                    w(f"[05] 增量同步第 {attempt}/3 次: rc={rc}, "
                      f"HEAD={head_after[:12] or '(空)'} — 30s 后重试")
                    time.sleep(30)
                if head_after != head_expect:
                    w(f"[FATAL] 增量同步后 HEAD 不一致 ({head_after[:12]} != "
                      f"{head_expect[:12]}) —— 需人工裁决")
                    return 1
                w(f"[05] 增量同步完成: HEAD={head_after[:12]}")
        else:
            w(f"[05] git clone bundle -> {TARGET_DIR} ...")
            out, err, rc = s.run(
                f"git clone {PKG_DIR_REMOTE}/flash_sim_all.bundle {TARGET_DIR} 2>&1 "
                f"| tail -3", timeout=600)
            w(f"[05] clone rc={rc}: {(out or '').strip()[-300:]}")
            if rc != 0:
                return 1

        # ---- 3d/3e. remote 预留 + 生成目录补偿（同样规避 git -C） ----
        s.run(f"cd {TARGET_DIR} && git remote set-url origin {GITEE_URL} "
              f"&& git remote -v | head -2", timeout=120)
        out, err, rc = s.run(
            f"mkdir -p {TARGET_DIR}/dist {TARGET_DIR}/offline_pkg {TARGET_DIR}/test/reports "
            f"&& cd {TARGET_DIR} && git rev-parse HEAD "
            f"&& test -f {TARGET_DIR}/start_flash.py && echo START_FLASH_OK "
            f"&& test -f {TARGET_DIR}/deploy/_wh_common.py && echo WH_COMMON_OK",
            timeout=120)
        blob = (out or "")
        w(f"[05] 远端校验: {blob.strip()[-200:]}")
        if "START_FLASH_OK" not in blob or "WH_COMMON_OK" not in blob:
            w("[FATAL] 远端部署目录缺关键文件")
            return 1

    # 回收远端 HEAD 记录
    (TEST_DIR / "results").mkdir(exist_ok=True)
    (TEST_DIR / "results" / f"remote_clone_head_{ts}.txt").write_text(
        f"bundle_head={head_expect}\nsha256={local_sha}\ntarget={TARGET_DIR}\n", encoding="utf-8")
    w(f"[05] 结论: PASS（总耗时 {time.time() - t_start:.0f}s）")
    log_f.close()   # ★ 必须在最后一次 w() 之后关闭（上一版提前 close 触发 ValueError）
    return 0


if __name__ == "__main__":
    sys.exit(main())
