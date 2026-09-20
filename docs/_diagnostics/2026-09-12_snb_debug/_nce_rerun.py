"""NC-E 重跑 (修复 gr_hypreUseFloor 后): 上传修正 par → 复用 flash4 → ./flash4。

要点:
  - par 已在本地重新生成 (含 gr_hypreUseFloor=.false.)
  - flash4 二进制无需重编 (par 是运行时读取) → --skip-build 复用
  - 但单元包上传仍会把新 par 送到远端 deploy_dir, run.sh 再 cp 到 objdir
"""
import subprocess
import sys
import time
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
SCENE = (FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB"
         / "SNBOneCH_ml" / "SNBOneCH_ml.py")
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
LOG = FLASH_ROOT / "_nce_rerun.txt"

cmd = [PY, str(SCENE), "--mode", "hpc", "--account", "flash_ssh",
       "--tmax", "2.0e-10", "--nproc", "131", "--poll-timeout", "14400",
       "--skip-build"]

import os
env = {k: v for k, v in os.environ.items()
       if k in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
                "TEMP", "TMP", "SYSTEMROOT", "COMSPEC", "PATH")}
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONPATH"] = str(FLASH_ROOT)
env["PYTHONUNBUFFERED"] = "1"

t0 = time.time()
with open(LOG, "w", encoding="utf-8") as fh:
    fh.write(f"CMD: {' '.join(cmd)}\nT0: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    fh.write("=" * 70 + "\n")
    fh.flush()
    try:
        p = subprocess.run(cmd, cwd=str(FLASH_ROOT), env=env, bufsize=0,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=20000)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        fh.write("\n[TIMEOUT]\n")
        rc = 124
    fh.write("=" * 70 + f"\nRC={rc}\nWALL={time.time()-t0:.1f}s\n")
print(f"RC={rc} WALL={time.time()-t0:.1f}s")
