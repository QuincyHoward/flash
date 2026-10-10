# -*- coding: utf-8 -*-
"""bench_sftp.py — NC-E SFTP 单流吞吐基准 (临时, 用完即弃).

对比三种读取方式:
  A. sftp.get()                (paramiko 内置, 自带 prefetch)
  B. sftp.open + prefetch      (显式 prefetch + 32KB 读)
  C. sftp.open(prefetch) + 大包 max_packet_size + 1MB 读块
"""
import os
import sys
import time

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
sys.path.insert(0, REPO)

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (  # noqa: E402
    _resolve_route_and_credential,
)
import paramiko  # noqa: E402

route = _resolve_route_and_credential("flash_ssh")
HOST, PORT, USER, PWD = route["host"], int(route["port"]), route["username"], route["password"]

REMOTE = ("/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASHSNB/FLASH4.8"
          "/SNBVTi1um_ug_obj/snbvti1umug_hdf5_chk_0100")
TMP = os.path.join(REPO, "_bench_sftp.bin")

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
t0 = time.time()
cli.connect(hostname=HOST, port=PORT, username=USER, password=PWD,
            timeout=30, banner_timeout=45, auth_timeout=45)
print(f"connect: {time.time()-t0:.1f}s ({HOST}:{PORT})")
sftp = cli.open_sftp()
size = sftp.stat(REMOTE).st_size
print(f"file size: {size/1e6:.1f} MB")


def timed(tag, fn):
    t = time.time()
    n = fn()
    dt = time.time() - t
    print(f"{tag}: {dt:.1f}s  {n/1e6/dt:.2f} MB/s")
    return dt


# A: sftp.get
timed("A sftp.get", lambda: (sftp.get(REMOTE, TMP), os.path.getsize(TMP))[1])

# B: open + prefetch + 64KB read
def _b():
    with sftp.open(REMOTE, "rb") as fr:
        fr.prefetch(size)
        n = 0
        while True:
            buf = fr.read(65536)
            if not buf:
                break
            n += len(buf)
    return n

timed("B open+prefetch 64KB", _b)

# C: open + prefetch + 1MB read, 大 max_packet_size
def _c():
    with sftp.open(REMOTE, "rb", max_packet_size=1 << 20) as fr:
        fr.prefetch(size)
        n = 0
        while True:
            buf = fr.read(1 << 20)
            if not buf:
                break
            n += len(buf)
    return n

timed("C open+prefetch 1MB+maxpkt1M", _c)

sftp.close()
cli.close()
try:
    os.remove(TMP)
except OSError:
    pass
