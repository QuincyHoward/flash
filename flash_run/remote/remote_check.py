"""
检查远程环境的详细信息

注意: 此脚本是用户临时调试脚本，不适用于其他用户。
      包含硬编码用户名路径，非通用发布代码。
"""
import sys
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


from flash._core.credentials import get_credential_manager, get_user_name
import paramiko

cm = get_credential_manager()
cred = cm.get('flash_ssh_2')
if __name__ == "__main__":
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cred['host'], port=22,
        username=cred['username'], password=cred['password'],
        timeout=30, allow_agent=False, look_for_keys=False, banner_timeout=15,
    )

    # 动态用户名: 优先 SSH 凭据 username, 回退 credentials 用户名 (勿硬编码)
    _SSH_USER = str(cred.get('username', '')).split('@')[0] if cred else ''
    USER_NAME = _SSH_USER or get_user_name()
    SUPER_PREFIX = f"/public1/wshome/ws173/{USER_NAME}"
    HPC_FLASH = f"{SUPER_PREFIX}/FLASH"
    HPC_PYTHON = f"{SUPER_PREFIX}/software-{USER_NAME}/anaconda3/bin/python3"

    def run(cmd, t=60):
        i, o, e = client.exec_command(cmd, timeout=t)
        return o.read().decode(errors='replace').strip(), e.read().decode(errors='replace').strip()

    checks = [
        ("FLASH目录", f'ls -la {HPC_FLASH}/ 2>/dev/null'),
        ("之前的作业日志", f'ls {HPC_FLASH}/*.out {HPC_FLASH}/*.err {HPC_FLASH}/*.log 2>/dev/null; cat {HPC_FLASH}/*.out 2>/dev/null | tail -30'),
        ("Par文件", f'find {HPC_FLASH}/ -name "*.par" 2>/dev/null'),
        ("CHK数据结构", f'{HPC_PYTHON} -c "import h5py; f=h5py.File(\'{HPC_FLASH}/FLASH4.8/object/lasslab_hdf5_chk_0000\',\'r\'); print(\"keys:\", list(f.keys())); print(\"attrs:\", dict(f.attrs)); f.close()" 2>&1'),
        ("PLT文件结构", f'{HPC_PYTHON} -c "import h5py; f=h5py.File(\'{HPC_FLASH}/FLASH4.8/object/lasslab_hdf5_plt_cnt_0000\',\'r\'); print(\"keys:\", list(f.keys())); print(\"attrs:\", dict(f.attrs)); f.close()" 2>&1'),
        ("磁盘空间", 'df -h /public1 2>/dev/null | tail -1'),
        ("当前作业", f'squeue -u {USER_NAME} 2>/dev/null'),
        ("上次作业日志", f'cat {HPC_FLASH}/FLASH4.8/object/flash*.log 2>/dev/null | tail -20 || echo NO_LOG'),
    ]

    for label, cmd in checks:
        print(f"\n{'='*50}")
        print(f"[{label}]")
        print(f"{'='*50}")
        out, err = run(cmd, 60)
        for line in out.split('\n'):
            print(f"  {line}")
        if err:
            print(f"  [STDERR] {err[:200]}")

    client.close()
    print("\nDone.")
