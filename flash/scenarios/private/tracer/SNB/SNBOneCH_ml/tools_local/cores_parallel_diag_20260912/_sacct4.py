# -*- coding: utf-8 -*-
"""_sacct4.py — 定位"真正开始积分"的时刻: 用 chk 文件/plt 的 mtime 与 log 首行步表时刻"""
import sys
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
DEPLOY = "/publicfs01/fs1-e/home/scfa2696/QC/SNBOneCH_ml_deploy"

with M._HpcRemote(ACCOUNT) as remote:
    for n, jid in (("131", "4864482"), ("192", "4864483"), ("256", "4864484")):
        obj = f"SNBOneCH_ml_ug_obj_n{n}"
        print("=" * 105)
        print(f"### n{n}  job {jid}  objdir {obj}")
        # 关键: chk 文件 mtime 数列出，可推 RUN 开始与节流
        out, _, _ = remote.run(
            f"ls -la --time-style=full-iso {DEPLOY}/{obj}/snbonechug_hdf5_chk_* "
            f"{DEPLOY}/{obj}/snbonechug_hdf5_plt_* {DEPLOY}/{obj}/snbonechug.log 2>&1", timeout=90)
        print(out)
    # SBATCH 脚本内容（看是否有 timing 记录）
    print("=" * 105)
    o, _, _ = remote.run(f"cat {DEPLOY}/coretest_131.sh", timeout=90)
    print(o)
