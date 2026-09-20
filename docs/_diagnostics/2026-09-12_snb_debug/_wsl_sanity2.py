"""WSL 健全性测试 第2轮: 复用 objdir (--skip-setup --skip-make), 只换 par 运行。

目的: 验证 (a) CH-BADGER 表可被找到; (b) dt_Diff 是否从 2.8e86 恢复正常。
"""
import subprocess
import sys
import time
import os
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
SCENE = (FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB"
         / "SNBOneCH_ml" / "SNBOneCH_ml.py")
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
LOG = FLASH_ROOT / "_wsl_sanity2.txt"

cmd = [PY, str(SCENE), "--mode", "wsl", "--tmax", "1.0e-12", "--nproc", "4",
       "--distro", "Ubuntu-22.04"]

env = {"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "PATH": os.environ.get("PATH", "")}
for k in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
          "TEMP", "TMP", "SYSTEMROOT", "COMSPEC"):
    if k in os.environ:
        env[k] = os.environ[k]

t0 = time.time()
with open(LOG, "w", encoding="utf-8") as fh:
    fh.write(f"CMD: {' '.join(cmd)}\nT0: {time.strftime('%H:%M:%S')}\n" + "=" * 70 + "\n")
    fh.flush()
    try:
        p = subprocess.run(cmd, cwd=str(FLASH_ROOT), env=env, bufsize=0,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=5400)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        fh.write("\n[TIMEOUT 5400s]\n")
        rc = 124
    fh.write("=" * 70 + f"\nRC={rc}\nWALL={time.time()-t0:.1f}s\n")
print(f"RC={rc} WALL={time.time()-t0:.1f}s")
