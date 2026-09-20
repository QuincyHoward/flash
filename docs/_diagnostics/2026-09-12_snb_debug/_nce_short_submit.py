"""NC-E 短时测试提交 (tmax=2.0e-10, 131 核)。

按用户指定的顺序执行: 上传单元包 → setup+make → ./flash4。
本脚本用绝对部署路径 ~/<SIM_USER_DIR>/SNBOneCH_ml_deploy (paramiko SFTP 不展开 ~)。
"""
import subprocess
import sys
import time
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
SCENE = (FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB"
         / "SNBOneCH_ml" / "SNBOneCH_ml.py")
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
LOG = FLASH_ROOT / "_nce_short_run.txt"

cmd = [PY, str(SCENE), "--mode", "hpc", "--account", "flash_ssh",
       "--tmax", "2.0e-10", "--nproc", "131", "--poll-timeout", "14400"]

env = {"PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(FLASH_ROOT),
       "PATH": r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts;"
               r"C:\Windows\System32;C:\Windows"}
try:
    import os
    env.update({k: v for k, v in os.environ.items()
                if k in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA",
                         "LOCALAPPDATA", "TEMP", "TMP", "SYSTEMROOT", "COMSPEC")})
except Exception:
    pass

t0 = time.time()
with open(LOG, "w", encoding="utf-8") as fh:
    fh.write(f"CMD: {' '.join(cmd)}\nT0: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    fh.write("=" * 70 + "\n")
    fh.flush()
    try:
        p = subprocess.run(cmd, cwd=str(FLASH_ROOT), env=env,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=20000)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        fh.write("\n[TIMEOUT] subprocess 20000s 超时\n")
        rc = 124
    fh.write("=" * 70 + f"\nRC={rc}\nWALL={time.time()-t0:.1f}s\n")
print(f"RC={rc} WALL={time.time()-t0:.1f}s LOG={LOG}")
