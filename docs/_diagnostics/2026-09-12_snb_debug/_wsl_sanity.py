"""WSL 快速健全性检查: 用低核数 (iProcs=4, 同参考单元) 极小 tmax 验证 dt_Diff 是否正常。

★ 注意: 此检查只用 4 核/低分辨率, 目的是验证 **物理初态** 是否不再溢出,
   不验证 0.03um 网格精度 (那必须上超算)。+ug 下 mpiexec -n 必须 == iProcs。
"""
import subprocess
import sys
import time
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
SCENE = (FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB"
         / "SNBOneCH_ml" / "SNBOneCH_ml.py")
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
LOG = FLASH_ROOT / "_wsl_sanity.txt"

cmd = [PY, str(SCENE), "--mode", "wsl", "--tmax", "1.0e-12",
       "--nproc", "4", "--skip-build"]

import os
env = {k: v for k, v in os.environ.items()
       if k in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
                "TEMP", "TMP", "SYSTEMROOT", "COMSPEC", "PATH")}
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUNBUFFERED"] = "1"

t0 = time.time()
with open(LOG, "w", encoding="utf-8") as fh:
    fh.write(f"CMD: {' '.join(cmd)}\nT0: {time.strftime('%H:%M:%S')}\n" + "=" * 70 + "\n")
    fh.flush()
    try:
        p = subprocess.run(cmd, cwd=str(FLASH_ROOT), env=env, bufsize=0,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=3000)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        fh.write("\n[TIMEOUT 3000s]\n")
        rc = 124
    fh.write("=" * 70 + f"\nRC={rc}\nWALL={time.time()-t0:.1f}s\n")
print(f"RC={rc} WALL={time.time()-t0:.1f}s")
