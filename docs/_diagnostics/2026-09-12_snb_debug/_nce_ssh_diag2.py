"""NC-E SSH 诊断 v2: 用真实凭据字段 ssh_username。"""
import subprocess

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_ssh_diag2.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys, time, traceback
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []

from flash._core.credentials import get_credential_manager
cm = get_credential_manager()
cred = cm.get("flash_ssh") or {}
user = cred.get("ssh_username")
pwd = cred.get("password")
lines.append(f"ssh_username={user}")
lines.append(f"active_route={cred.get('active_route')}")
lines.append(f"has_pwd={bool(pwd)}")

# 用项目自带 Remote 类测试 (走它自己的路由表)
try:
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession
    lines.append("RemoteSession import OK")
except Exception as e:
    lines.append("RemoteSession import err=" + repr(e))

try:
    import paramiko
    host, port = "ssh.cn-zhongwei-1.paracloud.com", 2222
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    t0 = time.time()
    cli.connect(hostname=host, port=port, username=user, password=pwd,
                timeout=20, banner_timeout=45, auth_timeout=45,
                allow_agent=False, look_for_keys=False)
    lines.append(f"paramiko CONNECT OK {(time.time()-t0):.1f}s")
    si, so, se = cli.exec_command("echo SSH_OK; hostname; whoami", timeout=25)
    lines.append("exec_out=" + so.read().decode(errors="replace").strip())
    err = se.read().decode(errors="replace").strip()
    if err:
        lines.append("exec_err=" + err[:300])
    cli.close()
except Exception as e:
    lines.append("paramiko_error=" + repr(e))
    lines.append(traceback.format_exc()[-1200:])

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=300)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
