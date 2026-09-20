"""验证假设: SSH CLI + ASKPASS 在 Windows 下失效, 而 paramiko 正常。

分别测试:
  (a) 当前项目方式: subprocess ssh + SSH_ASKPASS .bat
  (b) 纯 ssh CLI 不带 askpass (应立即要求密码 -> 非交互下失败并快速返回)
  (c) paramiko 直连 (已知成功)
"""
import subprocess, os, tempfile

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_ssh_verify.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys, os, subprocess, tempfile, time, platform
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = [f"platform={platform.system()} {platform.release()}"]

from flash._core.credentials import get_credential_manager
cred = get_credential_manager().get("flash_ssh") or {}
user = cred["ssh_username"]; pwd = cred["password"]
host, port = "ssh.cn-zhongwei-1.paracloud.com", 2222

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import _find_ssh
exe = _find_ssh()
lines.append(f"ssh_exe={exe}")
lines.append(f"ssh_exe_exists={os.path.isfile(exe) if exe else None}")

# (a) 项目方式: ssh + ASKPASS .bat
bat = tempfile.NamedTemporaryFile(mode="w", suffix=".bat", delete=False, newline="\r\n")
bat.write("@echo off\n"); bat.write(f"echo {pwd}\n"); bat.close()
args = [exe, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
        "-o", "BatchMode=no", "-o", "NumberOfPasswordPrompts=1",
        "-p", str(port), f"{user}@{host}", "echo ASKPASS_OK"]
env = os.environ.copy(); env["SSH_ASKPASS"] = bat.name; env["DISPLAY"] = ":0"
t0 = time.time()
try:
    r = subprocess.run(args, capture_output=True, text=True, errors="replace",
                       timeout=40, env=env)
    lines.append(f"(a) ASKPASS rc={r.returncode} t={time.time()-t0:.1f}s")
    lines.append(f"    out={r.stdout.strip()[:200]!r}")
    lines.append(f"    err={r.stderr.strip()[:300]!r}")
except subprocess.TimeoutExpired:
    lines.append(f"(a) ASKPASS TIMEOUT after {time.time()-t0:.1f}s  <-- 超时")
except Exception as e:
    lines.append(f"(a) ASKPASS EXC {e!r}")
finally:
    try: os.unlink(bat.name)
    except OSError: pass

# (b) 无 askpass, 强制非交互 -> 应快速失败
args2 = [exe, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
         "-o", "BatchMode=yes", "-o", "NumberOfPasswordPrompts=0",
         "-p", str(port), f"{user}@{host}", "echo NOASK_OK"]
env2 = os.environ.copy(); env2.pop("SSH_ASKPASS", None)
t0 = time.time()
try:
    r = subprocess.run(args2, capture_output=True, text=True, errors="replace",
                       timeout=40, env=env2, stdin=subprocess.DEVNULL)
    lines.append(f"(b) NOASK rc={r.returncode} t={time.time()-t0:.1f}s")
    lines.append(f"    err={r.stderr.strip()[:200]!r}")
except subprocess.TimeoutExpired:
    lines.append(f"(b) NOASK TIMEOUT after {time.time()-t0:.1f}s")
except Exception as e:
    lines.append(f"(b) NOASK EXC {e!r}")

# (c) paramiko
try:
    import paramiko
    cli = paramiko.SSHClient(); cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    t0 = time.time()
    cli.connect(hostname=host, port=port, username=user, password=pwd,
                timeout=20, banner_timeout=45, auth_timeout=45,
                allow_agent=False, look_for_keys=False)
    si, so, se = cli.exec_command("echo PARAMIKO_OK", timeout=20)
    lines.append(f"(c) paramiko rc=0 t={time.time()-t0:.1f}s out={so.read().decode().strip()!r}")
    cli.close()
except Exception as e:
    lines.append(f"(c) paramiko EXC {e!r}")

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=400)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
