"""
FLASH超算工作流: 连接→检查→分析→绘图→下载

注意: 此脚本是用户临时调试脚本，不适用于其他用户。
      包含硬编码用户名路径，非通用发布代码。
"""
import sys, os, time
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


from flash._core.credentials import get_credential_manager, get_user_name
import paramiko

cm = get_credential_manager()
cred = cm.get('flash_ssh_2')

# 动态用户名: 优先 SSH 凭据 username, 回退 credentials 用户名
_SSH_USER = str(cred.get('username', '')).split('@')[0] if cred else ''
USER_NAME = _SSH_USER or get_user_name()
HPC_FLASH = f"/public1/wshome/ws173/{USER_NAME}/FLASH"
HPC_HOME = f"/public1/wshome/ws173/{USER_NAME}"

print("="*60)
print("连接超算: {USER_NAME}@BSCC-T6")
print("="*60)

if __name__ == "__main__":
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cred['host'],
        port=22,  # Use port 22
        username=cred['username'],
        password=cred['password'],
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
        banner_timeout=15,
    )
    print("[OK] 连接成功\n")

    def run_cmd(cmd, timeout=30):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors='replace').strip()
        err = stderr.read().decode(errors='replace').strip()
        return out, err

    # 1. Check all chk files
    print("[1/5] 检查所有 chk 文件...")
    out, err = run_cmd(f'ls -la {HPC_FLASH}/FLASH4.8/object/*chk* 2>/dev/null || echo NO_CHK')
    print(out)
    print()

    # 2. Check for flash Par files
    out, err = run_cmd(f'ls {HPC_FLASH}/FLASH4.8/*.par 2>/dev/null && ls {HPC_FLASH}/FLASH4.8/object/*.par 2>/dev/null || echo NO_PAR')
    print(f"Par files:\n{out}\n")

    # 3. Check disk space
    out, err = run_cmd(f'df -h {HPC_HOME}/ 2>/dev/null | tail -1')
    print(f"Disk space: {out}\n")

    # 4. Check available Python
    out, err = run_cmd('which python3 && python3 --version || echo NO_PYTHON3')
    print(f"Python: {out}\n")

    # 5. Check h5py availability
    out, err = run_cmd('python3 -c "import h5py; print(h5py.__version__)" 2>/dev/null || echo NO_H5PY')
    print(f"h5py: {out}\n")

    # 6. Check matplotlib
    out, err = run_cmd('python3 -c "import matplotlib; print(matplotlib.__version__)" 2>/dev/null || echo NO_MATPLOTLIB')
    print(f"matplotlib: {out}\n")

    # 7. Check numpy
    out, err = run_cmd('python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo NO_NUMPY')
    print(f"numpy: {out}\n")

    # 8. List chk file sizes
    out, err = run_cmd(f'ls -lh {HPC_FLASH}/FLASH4.8/object/*chk* 2>/dev/null')
    print(f"CHK file details:\n{out}\n")

    # 9. Check number of chk files
    out, err = run_cmd(f'ls {HPC_FLASH}/FLASH4.8/object/*chk* 2>/dev/null | wc -l')
    print(f"Number of chk files: {out}\n")

    # 10. Check if there are plt files too
    out, err = run_cmd(f'ls {HPC_FLASH}/FLASH4.8/object/*plt* 2>/dev/null | head -5 || echo NO_PLT')
    print(f"PLT files:\n{out}\n")

    # 11. Get HOME directory listing
    out, err = run_cmd(f'ls {HPC_FLASH}/ 2>/dev/null || echo NO_FLASH_DIR')
    print(f"FLASH dir:\n{out}\n")

    client.close()
    print("Done.")
