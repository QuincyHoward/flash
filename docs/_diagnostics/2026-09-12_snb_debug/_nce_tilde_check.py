"""验证 ~ 在 paramiko SFTP 下不被展开的假设。"""
import subprocess

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_tilde_check.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

with RemoteSession("flash_ssh", verbose=False) as s:
    # 字面 ~ 目录是否存在?
    for c in [
        "pwd; echo HOME=$HOME",
        "ls -la './~' 2>/dev/null | head -10 || echo NO_LITERAL_TILDE_DIR",
        "ls -la '/publicfs01/fs1-e/home/scfa2696/~/SNBOneCH_ml_deploy' 2>/dev/null | head -10 || echo NO_ABS_TILDE",
        "find /publicfs01/fs1-e/home/scfa2696 -maxdepth 3 -name 'build.sh' 2>/dev/null | head -10",
        "find /publicfs01/fs1-e/home/scfa2696 -maxdepth 3 -name 'unit.tar.gz' 2>/dev/null | head -10",
        "ls -la /publicfs01/fs1-e/home/scfa2696/SNBOneCH_ml_deploy/ | head",
    ]:
        out, err, rc = s.run(c, timeout=90)
        lines.append(f"CMD: {c}")
        lines.append(f"  rc={rc}\n  out={out.strip()[:500]}")
        if err.strip():
            lines.append(f"  err={err.strip()[:300]}")

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=600)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
