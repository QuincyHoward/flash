#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_snb_assets.py — SNB 场景资产同步（本机 → 超算部署树，一次/按需执行）。

背景（2026-10-22 in-situ 冒烟实测）：EOS/opacity 表 (*.cn4) 与
Driver_evolveFlash.F90 因 FLASH License §3 被 .gitignore 排除——hpc-remote
模式由单元包从本地上传补齐，**hpc-insitu 模式缺这一环**（超算源码树上没有）。

本脚本把本地 flash_input/ 全部文件打成 tar → SFTP 上传 → 远端解压覆盖到
部署树的同路径 flash_input/（untracked, git status 不受影响；idempotent，
文件少体积小 ~15MB）。同步完成后超算侧 generate_input_files / 辐射核验
即可自足。
"""
import sys
import tarfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
sys.path.insert(0, str(REPO_ROOT))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402

LOCAL_INPUT = REPO_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB" \
    / "SNBOneCH_m" / "flash_input"
REMOTE_INPUT = (f"{_RH}/PhySimX/PhySimX/simulation"
                "/flash/flash_sim/flash/scenarios/private/tracer/SNB/"
                "SNBOneCH_m/flash_input")
PKG = (f"{_RH}/PhySimX/PhySimX/simulation/flash"
       "/flash_sim_pkg")


def main() -> int:
    if not LOCAL_INPUT.is_dir():
        print(f"[FATAL] 本地 flash_input 不存在: {LOCAL_INPUT}")
        return 1
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tar_local = TEST_DIR / "packages" / f"snb_assets_{ts}.tar.gz"
    tar_local.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in LOCAL_INPUT.iterdir() if p.is_file())
    with tarfile.open(tar_local, "w:gz") as tf:
        for p in files:
            tf.add(p, arcname=p.name)
    print(f"[assets] 打包 {len(files)} 文件 → {tar_local.name} "
          f"({tar_local.stat().st_size/1e6:.1f} MB)")

    with RemoteSession("flash_ssh") as s:
        remote_tar = f"{PKG}/snb_assets.tar.gz"
        if not s.upload(str(tar_local), remote_tar):
            print("[FATAL] 上传失败")
            return 1
        out, err, rc = s.run(
            f"mkdir -p {REMOTE_INPUT} && cd {REMOTE_INPUT} && "
            f"tar xzf {remote_tar} && ls | wc -l", timeout=300)
        print(f"[assets] 远端解压 rc={rc}, 现有文件数: {(out or '').strip()}")
        s.run(f"rm -f {remote_tar}", timeout=30)
    tar_local.unlink(missing_ok=True)
    print("[assets] 同步完成 (idempotent, 可重复执行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
