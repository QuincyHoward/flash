#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_incremental.py — 轻量增量同步：只传 bundle，不重传 wheelhouse。

背景（实测教训）：
  * `package_and_upload.py` 每次都把 `flash_sim_all.bundle`（42MB）+ 
    `wheelhouse-linux/`（165MB）打成 deploy.tar.gz（212MB）再上传。
    但 **wheelhouse 只有在 Python/EOS/不透明度表版本变化时才需要重传**；
    代码改动（如 patch_job.py、run_public_tests.py）只需同步 git 历史。
  * ⇒ 增量路径：只上传 bundle（42MB）→ 远端 `git fetch bundle` + `merge --ff-only`。
    体积从 212MB 降到 42MB，耗时从分钟级降到秒级。

流程：
  1. 校验本地 bundle 存在 + 读 bundle_head.txt（期望 HEAD）
  2. 连远端，查当前部署目录 HEAD
     - 相同 → 跳过（幂等）
     - 不同 → 上传 bundle 到 PKG_DIR_REMOTE/flash_sim_all.bundle（.part 临时名 + 改名）
  3. 远端 `git fetch <bundle> refs/heads/master:refs/heads/bundle-sync`
     + `git merge --ff-only bundle-sync` + 删临时分支
  4. 校验远端 HEAD == 期望 HEAD

铁律：
  * 远端 git 1.8.3.1 —— **不支持 `git -C`**，必须 `cd dir && git ...`。
  * 目标目录必须存在（增量路径不负责 clone；全新安装走 package_and_upload.py）。
  * 上传用 .part 临时名，避免远端读到半截文件。
  * 失败重试前先查 HEAD，避免"失败≠未执行"导致重复 fetch。
"""
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ARTIFACTS = REPO_ROOT / "artifacts"
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"
PKG_DIR = TEST_DIR / "packages"
LOG_DIR = TEST_DIR / "logs"

REMOTE_HOME = "/publicfs01/fs1-e/home/scfa2696"
PKG_DIR_REMOTE = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
TARGET_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim"

BUNDLE = PKG_DIR / "flash_sim_all.bundle"
HEAD_FILE = PKG_DIR / "bundle_head.txt"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not BUNDLE.is_file():
        print(f"[FATAL] 缺少 {BUNDLE} —— 先跑 build_bundle.py")
        return 1
    if not HEAD_FILE.is_file():
        print(f"[FATAL] 缺少 {HEAD_FILE} —— 先跑 build_bundle.py")
        return 1

    head_expect = HEAD_FILE.read_text(encoding="utf-8").split()[0]
    local_sha = sha256_file(BUNDLE)
    size_mb = BUNDLE.stat().st_size / 1e6
    print(f"[SYNC] 本地 bundle: {size_mb:.1f} MB  HEAD={head_expect[:12]}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_f = open(LOG_DIR / f"sync_incremental_{ts}.log", "w",
                 encoding="utf-8", errors="replace")

    def w(msg: str) -> None:
        print(msg)
        log_f.write(msg + "\n")
        log_f.flush()

    sys.path.insert(0, str(REPO_ROOT))
    from flash.flash_run.remote.session import RemoteSession

    try:
        with RemoteSession("flash_ssh") as s:
            # ---- 1. 查远端现状 ----
            out, err, rc = s.run(
                f"if [ -d {TARGET_DIR}/.git ]; then "
                f"  cd {TARGET_DIR} && git rev-parse HEAD; echo CLONE_EXISTS; "
                f"else echo CLONE_ABSENT; fi", timeout=120)
            blob = (out or "")
            if "CLONE_EXISTS" not in blob:
                w("[FATAL] 远端部署目录不存在 —— 全新安装请走 package_and_upload.py")
                return 1
            head_remote = blob.strip().splitlines()[0].strip()
            w(f"[SYNC] 远端 HEAD = {head_remote[:12]}")
            if head_remote == head_expect:
                w("[SYNC] [ok] 远端已是目标 HEAD，无需同步")
                w("[SYNC] 结论: PASS（幂等跳过）")
                return 0

            # ---- 2. 上传 bundle（只传 bundle，不传 wheelhouse） ----
            remote_bundle = f"{PKG_DIR_REMOTE}/flash_sim_all.bundle"
            out, err, rc = s.run(
                f"sha256sum {remote_bundle} 2>/dev/null || echo ABSENT", timeout=300)
            line = (out or "").strip()
            remote_sha = line.split(" ", 1)[0] if line else ""
            if remote_sha == local_sha:
                w("[SYNC] [skip] 远端 bundle SHA256 已一致，跳过上传")
            else:
                w(f"[SYNC] 上传 bundle -> {remote_bundle}（{size_mb:.1f} MB）...")
                t0 = time.time()
                if not s.upload(str(BUNDLE), remote_bundle):
                    w("[FATAL] 上传失败")
                    return 1
                w(f"[SYNC] 上传完成，耗时 {time.time() - t0:.0f}s")
                out, err, rc = s.run(f"sha256sum {remote_bundle}", timeout=600)
                line = (out or "").strip()
                remote_sha = line.split(" ", 1)[0] if line else ""
                if remote_sha != local_sha:
                    w(f"[FATAL] 双端 SHA256 不一致（远端 {remote_sha[:12]}）")
                    return 1
                w("[SYNC] [ok] 双端 SHA256 一致")

            # ---- 3. 增量 fetch + ff-merge（git 1.8.3 兼容，禁 git -C） ----
            head_after = ""
            for attempt in range(1, 4):
                try:
                    out, err, rc = s.run(
                        f"cd {TARGET_DIR} && "
                        f"git fetch {remote_bundle} "
                        f"'refs/heads/master:refs/heads/bundle-sync' 2>&1 | tail -2 && "
                        f"git merge --ff-only bundle-sync 2>&1 | tail -2 && "
                        f"git branch -d bundle-sync 2>/dev/null; git rev-parse HEAD",
                        timeout=900)
                except Exception as e:  # noqa: BLE001
                    out, err, rc = "", f"{type(e).__name__}: {e}", -1
                lines = (out or "").strip().splitlines()
                head_after = lines[-1].strip() if lines else ""
                if head_after == head_expect:
                    break
                w(f"[SYNC] 同步第 {attempt}/3 次: rc={rc}, "
                  f"HEAD={head_after[:12] or '(空)'} — 20s 后重试")
                time.sleep(20)
            if head_after != head_expect:
                w(f"[FATAL] 同步后 HEAD 不一致（{head_after[:12]} != "
                  f"{head_expect[:12]}）")
                return 1
            w(f"[SYNC] 同步完成: HEAD={head_after[:12]}")
        # ★ 日志文件必须在最后一次 w() 之后关闭（放 finally 里会先关闭再写 ⇒ ValueError）
        w("[SYNC] 结论: PASS")
    except Exception as e:  # noqa: BLE001
        w(f"[FATAL] 未捕获异常: {type(e).__name__}: {e}")
        raise
    finally:
        log_f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
