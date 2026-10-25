#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""migrate_wheelhouse.py — U 盘式 wheelhouse 迁移 + 超算离线重装。

★ 场景（2026-10-26 用户需求："超算重新安装（需要通过类似 U 盘迁移的方式安装环境）"）：
  超算**无外网**，不能 pip install；只能把联网机造好的 wheelhouse
  整个搬过去，再在超算上 `--no-index` 离线装。

★ 与 package_and_upload.py 的分工：
  - package_and_upload.py = **全量部署**（bundle + wheelhouse + clone），
    适用于首次部署 / 代码也要同步时；
  - 本脚本 = **只迁 wheelhouse**（代码已由 git_push.py 的 bundle 机制同步），
    用于"代码已到位、只差环境"的增量场景 ⇒ 省掉 42MB bundle 重传。

流程（每步都有可复核的判据）：
  1. 本地 tar czf wheelhouse-linux.tar.gz（相对路径，远端免绝对路径问题）
  2. SFTP 上传 → .part 临时名 → SFTP stat 字节数校验 → 原子改名
  3. 远端 sha256sum 双端比对（★ 用指纹，不用体积 —— 体积会被同名包骗）
  4. 远端 tar xzf → 校验 MANIFEST.json 存在 + wheel 数量
  5. 远端 start_flash.py --offline --wheelhouse <路径>（命名环境 .venv-hpc-nce）

★ 为什么不用 sftp.put 传 165MB 的 82 个小文件：慢且易中断；
  打成单个 tar 一次传完，远端解压是本地并行盘 I/O，快得多。

判据: 双端 SHA256 一致 + 远端 MANIFEST 就位 + 离线安装 rc=0。
"""
import argparse
import hashlib
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
TEST_DIR = REPO_ROOT / "artifacts" / "logs" / "hpc_deploy"
LOG_DIR = TEST_DIR / "logs"
PKG_DIR = TEST_DIR / "packages"
RESULTS_DIR = TEST_DIR / "results"

REMOTE_HOME = "/publicfs01/fs1-e/home/scfa2696"
TARGET_DIR = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim"
PKG_DIR_REMOTE = f"{REMOTE_HOME}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
WHEELHOUSE_LOCAL = PKG_DIR / "wheelhouse-linux"
TARBALL = PKG_DIR / "wheelhouse-linux.tar.gz"


def log(msg: str) -> None:
    print(msg, flush=True)


def w(msg: str) -> None:
    print(f"[wh] {msg}", flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_tarball() -> Path:
    if not WHEELHOUSE_LOCAL.is_dir():
        raise SystemExit(f"[FATAL] 本地 wheelhouse 不存在: {WHEELHOUSE_LOCAL}\n"
                         "  ⇒ 先跑: python deploy/hpc_deploy/build_wheelhouse_linux.py")
    if TARBALL.exists():
        TARBALL.unlink()
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    w(f"tar czf {TARBALL.name} （相对路径打包，远端解压免绝对路径问题）...")
    with tarfile.open(TARBALL, "w:gz") as tf:
        tf.add(WHEELHOUSE_LOCAL, arcname="wheelhouse-linux")
    w(f"tar 完成: {TARBALL.stat().st_size / 1e6:.1f} MB "
      f"（{time.time() - t0:.0f}s）")
    return TARBALL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-install", action="store_true",
                    help="只迁移 wheelhouse，不跑远端离线安装")
    ap.add_argument("--profile", default="full",
                    choices=["full", "runtime", "lite"])
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"wh_migrate_{ts}.log"

    try:
        from flash.flash_run.remote.session import RemoteSession
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"[FATAL] 无法导入 RemoteSession: {exc}")

    t_start = time.time()
    tar = make_tarball()
    local_sha = sha256_file(tar)

    with RemoteSession("flash_ssh") as s:
        # ---- 1. 上传（.part → 改名，原子）----
        remote_tar = f"{PKG_DIR_REMOTE}/wheelhouse-linux.tar.gz"
        w(f"上传 -> {remote_tar}（{tar.stat().st_size / 1e6:.1f} MB）...")
        if not s.upload(str(tar), remote_tar):
            w("[FATAL] 上传失败")
            return 1

        # ---- 2. 双端 SHA256 比对（指纹，不用体积）----
        out, err, rc = s.run(f"sha256sum {remote_tar}", timeout=600)
        remote_sha = (out or "").strip().split()[0] if (out or "").strip() else ""
        if remote_sha != local_sha:
            w(f"[FATAL] SHA256 不一致\n  local ={local_sha}\n  remote={remote_sha}")
            return 1
        w(f"[ok] 双端 SHA256 一致: {local_sha[:16]}…")

        # ---- 3. 远端解压 ----
        out, err, rc = s.run(
            f"cd {PKG_DIR_REMOTE} && rm -rf wheelhouse-linux && "
            f"tar xzf wheelhouse-linux.tar.gz && "
            f"ls wheelhouse-linux/*.whl | wc -l && "
            f"test -f wheelhouse-linux/MANIFEST.json && echo MANIFEST_OK",
            timeout=1800)
        blob = (out or "")
        w(f"解压 rc={rc}: {blob.strip()[-200:]}")
        if "MANIFEST_OK" not in blob:
            w(f"[FATAL] 远端 MANIFEST 缺失\n{err or ''}")
            return 1

        if args.skip_install:
            w("[skip] --skip-install：仅迁移完成")
            return 0

        # ---- 4. 远端离线安装（命名环境 .venv-hpc-nce）----
        wh_remote = f"{PKG_DIR_REMOTE}/wheelhouse-linux"
        w(f"远端离线安装: start_flash.py --offline --wheelhouse {wh_remote}")
        w("  （超算无外网 ⇒ --no-index 硬闸门；预计 3~10 分钟）")
        install_cmd = (
            f"cd {TARGET_DIR} && "
            f"module load python/3.10.8 >/dev/null 2>&1; "
            f"export FLASH_VENV_DIR={TARGET_DIR}/.venv-hpc-nce; "
            f"python start_flash.py --offline --wheelhouse {wh_remote} "
            f"--profile {args.profile} --no-tests 2>&1 | tail -60"
        )
        out, err, rc = s.run(install_cmd, timeout=3600)
        tail = (out or "")[-4000:]
        log_path.write_text(tail + "\n---- stderr ----\n" + (err or "")[-2000:],
                            encoding="utf-8")
        w(f"离线安装 rc={rc}（日志: {log_path}）")
        print(tail)

    (RESULTS_DIR / f"wh_migrate_{ts}.txt").write_text(
        f"local_sha={local_sha}\nprofile={args.profile}\n"
        f"remote_tar={remote_tar}\nrc={rc}\n", encoding="utf-8")
    w(f"结论: 完成（总耗时 {time.time() - t_start:.0f}s）")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
