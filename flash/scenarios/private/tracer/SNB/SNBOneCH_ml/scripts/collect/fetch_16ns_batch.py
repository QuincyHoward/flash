"""1.6ns 全量输出分批收集 (Plan C, 配额安全): 每批 ~50 文件 tar → 下载 → 校验
→ 本地解包 → 删远端批 tar。支持断点续传 (--resume)。

背景: 整包 tar.gz 3.9GB 处被杀 (疑似用户配额: 原始 12GB + tar 副本双倍)。
分批方案远端临时占用 ≤1GB。单流 SCP 实测 1.2MB/s → 12GB 约 3h。

用法:
  python fetch_16ns_batch.py                # 从头/续传
  python fetch_16ns_batch.py --workers 3    # 3 路并行下载 (若带宽可扩)
  python fetch_16ns_batch.py --finalize     # 全部批次完成后: 核对+清理远端
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
# 脚本位于 SNBOneCH_ml/scripts/collect/: 上溯 7 级 = 内层 flash, 8 级 = 外层根
_INNER = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", "..", ".."))
_ROOT = os.path.abspath(os.path.join(_INNER, ".."))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _ROOT)

SCEN_DIR = os.path.abspath(os.path.join(_HERE, "..", ".."))  # SNBOneCH_ml/

from remote_ssh_helper import (  # noqa: E402
    _resolve_route_and_credential, quick_run, scp_download)

OBJ = "~/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
BATCH_DIR = "~/SNB1CH_16ns_batches"
LOCAL_OUT = os.path.join(SCEN_DIR, "flash_output", "hpc_flash_ssh")
PROGRESS = os.path.join(SCEN_DIR, "flash_output", "_fetch_progress.txt")
BATCH_N = 50          # 每批文件数 (~500MB)
MANIFEST = ["snbonechug_*", "wsl_run_snbonech.log"]


def log(msg, tag="STEP"):
    print(f"[{datetime.now():%H:%M:%S}] [{tag}] {msg}", flush=True)


def md5_local(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_progress():
    done = set()
    if os.path.isfile(PROGRESS):
        with open(PROGRESS) as fh:
            done = {l.strip() for l in fh if l.strip()}
    return done


def mark_progress(batch):
    with open(PROGRESS, "a") as fh:
        fh.write(batch + "\n")


def make_batches(batch_n: int):
    """远端列全清单 → 本地分批。返回 [[name,...], ...]"""
    out, _, _ = quick_run(
        f"cd {OBJ} && ls snbonechug_* wsl_run_snbonech.log 2>/dev/null",
        credential_name="flash_ssh", timeout=120)
    names = [l.strip() for l in out.splitlines() if l.strip()]
    log(f"远端清单 {len(names)} 个文件 (batch_n={batch_n})")
    return [names[i:i + batch_n] for i in range(0, len(names), batch_n)]


def process_batch(route, idx, batch, batch_n: int):
    """单批: 远端 tar → 下载 → 校验 → 本地解包 → 删远端 tar。"""
    # tg 名带 batch_n 后缀: 不同批次大小空间不冲突
    remote_tg = f"{BATCH_DIR}/batch_{idx:03d}_s{batch_n}.tar.gz"
    local_tg = os.path.join(LOCAL_OUT, f"_batch_{idx:03d}_s{batch_n}.tar.gz")
    # 远端打包 (批次小, <1min)
    filelist = " ".join(batch)
    out, _, _ = quick_run(
        f"mkdir -p {BATCH_DIR} && cd {OBJ} && tar czf {remote_tg} {filelist} && "
        f"md5sum {remote_tg} | cut -d\" \" -f1",
        credential_name="flash_ssh", timeout=300)
    rmd5 = out.strip().splitlines()[-1] if out.strip() else ""
    if len(rmd5) != 32:
        log(f"batch {idx}: 远端 md5 缺失", "ERROR")
        return False
    # 下载 + 校验 (3 次)
    ok = False
    for attempt in (1, 2, 3):
        t1 = time.time()
        if scp_download(route, remote_tg, local_tg) and \
                os.path.isfile(local_tg) and md5_local(local_tg) == rmd5:
            sz = os.path.getsize(local_tg) / 1e6
            log(f"  batch {idx:03d}: {len(batch)} 文件 {sz:.0f}MB "
                f"{time.time()-t1:.0f}s ({sz/max(time.time()-t1,0.1)/1e3:.2f}MB/s)", "OK")
            ok = True
            break
        log(f"  batch {idx:03d} 第 {attempt} 次失败, 重试", "WARN")
    if not ok:
        return False
    # 解包
    r = subprocess.run(["tar", "xzf", local_tg, "-C", LOCAL_OUT],
                       capture_output=True)
    if r.returncode != 0:
        log(f"  batch {idx:03d} 解包失败: {r.stderr[:200]}", "ERROR")
        return False
    os.remove(local_tg)
    quick_run(f"rm -f {remote_tg}", credential_name="flash_ssh", timeout=30)
    mark_progress(f"batch_{idx:03d}_s{batch_n}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=50,
                    help="每批文件数 (默认 50; 网络差时用 10 小批)")
    ap.add_argument("--start-file", type=int, default=0,
                    help="从清单第 N 个文件开始 (跳过已收部分)")
    args = ap.parse_args()

    global PROGRESS
    PROGRESS = PROGRESS.replace(".txt", f"_s{args.batch_size}.txt")

    os.makedirs(LOCAL_OUT, exist_ok=True)
    t0 = time.time()
    # 首次连接 (网络抖动重试 10 次, 间隔 2 分钟)
    route = None
    for i in range(10):
        try:
            route = _resolve_route_and_credential("flash_ssh")
            break
        except Exception as exc:  # noqa: BLE001
            log(f"SSH 不可达 ({i+1}/10): {exc}", "WARN")
            time.sleep(120)
    if route is None:
        log("SSH 持续不可达, 退出 (重跑本脚本自动续传)", "ERROR")
        return 1
    batches = make_batches(args.batch_size)
    if args.start_file:
        offset = args.start_file // args.batch_size
        batches = batches[offset:]
        log(f"--start-file {args.start_file} → 跳过前 {offset} 批, 剩 {len(batches)} 批")
    done = load_progress()
    n_fail = 0
    for idx, batch in enumerate(batches, start=args.start_file // args.batch_size):
        key = f"batch_{idx:03d}_s{args.batch_size}"
        if key in done:
            log(f"  {key} 已完成 (跳过)")
            continue
        # 单批含网络容错: 失败整批重试 (含远端打包), 最多 6 轮
        ok = False
        for attempt in range(1, 7):
            try:
                ok = process_batch(route, idx, batch, args.batch_size)
            except Exception as exc:  # noqa: BLE001
                log(f"  {key} 第 {attempt} 轮异常: {exc}", "WARN")
                time.sleep(120)
                try:
                    route = _resolve_route_and_credential("flash_ssh")
                except Exception:  # noqa: BLE001
                    pass
            if ok:
                break
        if not ok:
            n_fail += 1
            log(f"{key} 6 轮均失败, 跳过 (汇总后可 --resume 重跑)", "ERROR")
    log(f"分批下载结束: {len(batches)} 批, 失败 {n_fail}, "
        f"耗时 {(time.time()-t0)/60:.1f} min", "OK")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
