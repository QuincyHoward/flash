"""诊断构建脚本校验失败: 直接跑 chmod/bash -n 看 stdout/stderr/rc。"""
import subprocess

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_build_check.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession, ssh_cmd

with RemoteSession("flash_ssh", verbose=False) as s:
    route = s._route
    d = "~/SNBOneCH_ml_deploy"
    cmds = [
        f"ls -la {d}/",
        f"test -f {d}/build.sh && echo FILE_OK || echo FILE_MISSING",
        f"head -3 {d}/build.sh",
        f"chmod +x {d}/build.sh; echo CHMOD_RC=$?",
        f"bash -n {d}/build.sh; echo BASHN_RC=$?",
        f"chmod +x {d}/build.sh && bash -n {d}/build.sh && echo SCRIPT_OK; echo COMBINED_RC=$?",
    ]
    for c in cmds:
        out, err, rc = s.run(c, timeout=60)
        lines.append(f"CMD: {c}")
        lines.append(f"  rc={rc} out={out.strip()[:300]!r}")
        lines.append(f"  err={err.strip()[:300]!r}")

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=400)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
