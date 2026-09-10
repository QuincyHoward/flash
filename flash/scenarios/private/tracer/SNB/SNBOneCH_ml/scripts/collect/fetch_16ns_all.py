"""1.6ns 全量输出收集: 远端 tar 分卷 → 逐卷下载 → 本地校验合并解包。

数据量 ~12 GB (1088 chk + 219 plt + dat + log), 单流 SCP 实测 ~1.2 MB/s,
逐文件连接开销不可接受 → 打包后按 700MB 分卷流式传输 (抗断线, 可续传)。

流程:
  [远端] objdir 内 tar czf → split -b 700m → md5sum
  [本地] 逐卷下载 → cat 合并 → md5 校验 → tar tzf 校验 → 解包
  [远端] 本地校验通过后才删除原始输出与分卷 (用后即转)

用法:
  python fetch_16ns_all.py                 # 全流程 (打包+下载+解包+清理)
  python fetch_16ns_all.py --no-clean      # 保留远端原始文件
  python fetch_16ns_all.py --skip-tar      # 跳过打包 (分卷已存在, 断点续传)
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 双层 flash 结构: 上溯 5 级 = 内层 flash, 6 级 = 外层根 (含 flash 包)
_INNER = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "..", "..", ".."))
ROOT = os.path.abspath(os.path.join(_INNER, ".."))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, ROOT)

SCEN_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))  # SNBOneCH_ml/
sys.path.insert(0, ROOT)

from remote_ssh_helper import (  # noqa: E402
    _resolve_route_and_credential, quick_run, scp_download)

OBJDIR = "~/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
REMOTE_TAR = "~/SNB1CH_16ns_all.tar.gz"
REMOTE_DIR = "~/SNB1CH_16ns_vols"
LOCAL_OUT = os.path.join(SCEN_DIR, "flash_output", "hpc_flash_ssh")
LOCAL_TAR = os.path.join(SCEN_DIR, "flash_output", "SNB1CH_16ns_all.tar.gz")
VOL_SIZE = "700m"


def log(msg: str, tag: str = "STEP") -> None:
    print(f"[{datetime.now():%H:%M:%S}] [{tag}] {msg}", flush=True)


def md5_local(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-clean", action="store_true", help="保留远端原始输出")
    ap.add_argument("--skip-tar", action="store_true", help="分卷已存在, 跳过打包")
    args = ap.parse_args()
    t0 = time.time()

    # [1] 远端打包 + 分卷 + md5
    if not args.skip_tar:
        log("远端 tar czf 打包 (12GB, 需数分钟)...")
        out, _, _ = quick_run(
            f"cd {OBJDIR} && tar czf {REMOTE_TAR} snbonechug_* wsl_run_snbonech.log "
            f"&& ls -l {REMOTE_TAR} | awk '{{print $5}}'",
            credential_name="flash_ssh", timeout=1800)
        log(f"tar 完成, 大小 {out.strip().splitlines()[-1]} bytes", "OK")
        quick_run(
            f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR} && "
            f"cd ~ && split -b {VOL_SIZE} {REMOTE_TAR} {REMOTE_DIR}/vol_ && "
            f"cd {REMOTE_DIR} && md5sum vol_* > MD5SUMS && ls vol_* | wc -l",
            credential_name="flash_ssh", timeout=900)
        out, _, _ = quick_run(
            f"cat {REMOTE_DIR}/MD5SUMS", credential_name="flash_ssh", timeout=60)
        remote_md5 = {}
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                remote_md5[os.path.basename(parts[1])] = parts[0]
        log(f"分卷 {len(remote_md5)} 个, MD5 已记录", "OK")
        out, _, _ = quick_run(
            f"md5sum {REMOTE_TAR} | cut -d' ' -f1",
            credential_name="flash_ssh", timeout=600)
        tar_md5_remote = out.strip().splitlines()[-1]
    else:
        out, _, _ = quick_run(
            f"cat {REMOTE_DIR}/MD5SUMS 2>/dev/null && echo === && "
            f"md5sum {REMOTE_TAR} | cut -d' ' -f1",
            credential_name="flash_ssh", timeout=120)
        remote_md5, tar_md5_remote = {}, ""
        for line in out.strip().splitlines():
            p = line.split()
            if len(p) == 2 and p[1].startswith("vol_"):
                remote_md5[os.path.basename(p[1])] = p[0]
            elif len(p) == 1 and len(p[0]) == 32:
                tar_md5_remote = p[0]
        log(f"续传: 分卷 {len(remote_md5)} 个", "OK")

    # [2] 逐卷下载 + 校验
    route = _resolve_route_and_credential("flash_ssh")
    os.makedirs(os.path.dirname(LOCAL_TAR), exist_ok=True)
    for name in sorted(remote_md5):
        local_vol = os.path.join(os.path.dirname(LOCAL_TAR), name)
        need = True
        if os.path.isfile(local_vol):
            if md5_local(local_vol) == remote_md5[name]:
                log(f"  = {name} 已存在且校验通过 (跳过)", "OK")
                need = False
            else:
                log(f"  ! {name} 本地副本损坏, 重下", "WARN")
        if need:
            for attempt in (1, 2, 3):
                t1 = time.time()
                ok = scp_download(route, f"{REMOTE_DIR}/{name}", local_vol)
                if ok and os.path.isfile(local_vol) and \
                        md5_local(local_vol) == remote_md5[name]:
                    sz = os.path.getsize(local_vol) / 1e6
                    log(f"  ✓ {name} ({sz:.0f}MB, {time.time()-t1:.0f}s, "
                        f"{sz/max(time.time()-t1,0.1)/1e3:.2f}MB/s)", "OK")
                    break
                log(f"  ✗ {name} 第 {attempt} 次下载/校验失败, 重试", "WARN")
            else:
                log(f"{name} 3 次均失败, 中止", "ERROR")
                return 1

    # [3] 合并 + 总校验 + 解包
    log("合并分卷 → tar.gz ...")
    vols = sorted(p for p in os.listdir(os.path.dirname(LOCAL_TAR))
                  if p.startswith("vol_"))
    with open(LOCAL_TAR, "wb") as fout:
        for v in vols:
            with open(os.path.join(os.path.dirname(LOCAL_TAR), v), "rb") as fin:
                while True:
                    chunk = fin.read(1 << 22)
                    if not chunk:
                        break
                    fout.write(chunk)
    tar_md5_local = md5_local(LOCAL_TAR)
    log(f"合并完成 {os.path.getsize(LOCAL_TAR)/1e9:.2f}GB, "
        f"md5 {'一致' if tar_md5_local == tar_md5_remote else '不一致!'}", "OK")
    if tar_md5_local != tar_md5_remote:
        log("tar 总校验失败, 中止 (远端未清理)", "ERROR")
        return 1

    log("tar tzf 完整性校验 (可能数分钟)...")
    r = subprocess.run(["tar", "tzf", LOCAL_TAR], capture_output=True)
    if r.returncode != 0:
        log(f"tar 校验失败: {r.stderr[:300]}", "ERROR")
        return 1
    n_files = len(r.stdout.splitlines())
    log(f"tar 完整, 含 {n_files} 个文件", "OK")

    os.makedirs(LOCAL_OUT, exist_ok=True)
    log(f"解包 → {LOCAL_OUT} ...")
    r = subprocess.run(["tar", "xzf", LOCAL_TAR, "-C", LOCAL_OUT],
                       capture_output=True)
    if r.returncode != 0:
        log(f"解包失败: {r.stderr[:300]}", "ERROR")
        return 1
    n_local = len([p for p in os.listdir(LOCAL_OUT) if p.startswith("snbonechug")])
    log(f"解包完成, 本地 {n_local} 个 snbonechug* 文件", "OK")

    # [4] 清理 (本地校验全部通过后才动远端)
    if not args.no_clean:
        log("清理远端 (原始输出 + 分卷 + tar)...")
        quick_run(
            f"cd {OBJDIR} && rm -f snbonechug_* wsl_run_snbonech.log _t_start _t_end && "
            f"rm -rf {REMOTE_DIR} {REMOTE_TAR} ~/SNB1CH_speedtest && echo REMOTE_CLEANED",
            credential_name="flash_ssh", timeout=600)
        for v in vols:
            os.remove(os.path.join(os.path.dirname(LOCAL_TAR), v))
        os.remove(LOCAL_TAR)
        log("本地分卷/合并包已清理", "OK")

    log(f"全部完成, 总耗时 {(time.time()-t0)/60:.1f} min", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
