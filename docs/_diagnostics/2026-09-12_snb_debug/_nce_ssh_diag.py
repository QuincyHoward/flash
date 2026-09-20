"""NC-E SSH 独立诊断: 绕过项目栈, 直接测试 paramiko + ssh CLI。"""
import subprocess, sys

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_ssh_diag.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys, socket, time, traceback
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []

# 1) 纯 TCP 连通性 (多端口/多主机)
targets = [
    ("ssh.cn-zhongwei-1.paracloud.com", 2222),
    ("ssh.cn-zhongwei-1.paracloud.com", 22),
    ("ssh.paracloud.com", 2222),
]
for host, port in targets:
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=10)
        s.close()
        lines.append(f"TCP {host}:{port} OK {(time.time()-t0)*1000:.0f}ms")
    except Exception as e:
        lines.append(f"TCP {host}:{port} FAIL {e!r}")

# 2) 凭据读取 (不打印明文)
try:
    from flash._core.credentials import get_credential_manager
    cm = get_credential_manager()
    cred = cm.get("flash_ssh")
    if cred:
        lines.append("cred.flash_ssh keys=" + ",".join(sorted(k for k in cred.keys() if not any(
            s in k.lower() for s in ("pass", "token", "secret", "key")))))
        lines.append("user=" + str(cred.get("user") or cred.get("username"))[:24])
        lines.append("has_password=" + str(bool(cred.get("password"))))
        lines.append("has_private_key=" + str(bool(cred.get("private_key") or cred.get("key"))))
    else:
        lines.append("cred.flash_ssh = None")
except Exception as e:
    lines.append("cred_error=" + repr(e))

# 3) paramiko 直连测试
try:
    import paramiko
    lines.append("paramiko=" + paramiko.__version__)
    from flash._core.credentials import get_credential_manager
    cm = get_credential_manager()
    cred = cm.get("flash_ssh") or {}
    user = cred.get("user") or cred.get("username")
    pwd = cred.get("password")
    host, port = "ssh.cn-zhongwei-1.paracloud.com", 2222
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    t0 = time.time()
    cli.connect(hostname=host, port=port, username=user, password=pwd,
                timeout=20, banner_timeout=30, auth_timeout=30,
                allow_agent=False, look_for_keys=False)
    lines.append(f"paramiko CONNECT OK {(time.time()-t0):.1f}s")
    si, so, se = cli.exec_command("echo SSH_OK; hostname", timeout=20)
    lines.append("exec_out=" + so.read().decode(errors="replace").strip())
    cli.close()
except Exception as e:
    lines.append("paramiko_error=" + repr(e))
    lines.append(traceback.format_exc()[-900:])

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=300)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
