"""验证修复后的 RemoteSession (paramiko 后端)。"""
import subprocess

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_session_test.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys, time, tempfile, os
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (
    RemoteSession, _use_paramiko, ssh_cmd, scp_upload, scp_download, _resolve_route_and_credential)
lines.append(f"use_paramiko={_use_paramiko()}")

t0 = time.time()
try:
    with RemoteSession("flash_ssh") as s:
        lines.append(f"RemoteSession OK in {time.time()-t0:.1f}s")
        out, err, rc = s.run("echo SESSION_TEST_OK; hostname; whoami")
        lines.append(f"run rc={rc} out={out.strip()!r}")

        # 上传/下载往返测试 (用临时文件)
        lf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        lf.write("roundtrip-probe\n"); lf.close()
        rp = "~/__probe_roundtrip__.txt"
        ok_up = s.upload(lf.name, rp)
        lines.append(f"upload={ok_up}")
        ld = lf.name + ".back"
        ok_dn = s.download(rp, ld)
        lines.append(f"download={ok_dn}")
        if ok_dn and os.path.exists(ld):
            lines.append("back_content=" + open(ld).read().strip())
        s.run(f"rm -f {rp}")
        for p in (lf.name, ld):
            try: os.unlink(p)
            except OSError: pass
except Exception as e:
    import traceback
    lines.append("RemoteSession FAILED: " + repr(e))
    lines.append(traceback.format_exc()[-800:])

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=400)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
