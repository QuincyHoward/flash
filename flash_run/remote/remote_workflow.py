"""
FLASH 超算完整工作流脚本

注意: 此脚本是用户临时调试脚本，不适用于其他用户。
      包含硬编码用户名路径，非通用发布代码。
"""
import sys, os, time, re
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

# 动态用户名: 优先 SSH 凭据 username, 回退 credentials 用户名
_SSH_USER = str(cred.get('username', '')).split('@')[0] if cred else ''
USER_NAME = _SSH_USER or get_user_name()
# 超算路径前缀 (从用户名动态构造, 无硬编码)
SUPER_PREFIX = f"/public1/wshome/ws173/{USER_NAME}"
HPC_FLASH = f"{SUPER_PREFIX}/FLASH"
HPC_PYTHON = f"{SUPER_PREFIX}/software-{USER_NAME}/anaconda3/bin/python3"

print("="*60)
print(f"连接超算: {USER_NAME}@BSCC-T6")
print("="*60)

if __name__ == "__main__":
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cred['host'], port=22,
        username=cred['username'], password=cred['password'],
        timeout=30, allow_agent=False, look_for_keys=False, banner_timeout=15,
    )
    print("[OK] 连接成功\n")

    def run_cmd(cmd, timeout=60):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors='replace').strip()
        err = stderr.read().decode(errors='replace').strip()
        return out, err

    # Step 1: Create AI directory
    print("[Step 1/5] 创建 AI 工作目录...")
    out, err = run_cmd(f'mkdir -p {HPC_FLASH}/AI && echo OK')
    print(f"  {out}\n")

    # Step 2: Check if FLASH object is compiled and ready
    print("[Step 2/5] 检查 FLASH 编译状态...")
    out, err = run_cmd(f'ls -la {HPC_FLASH}/FLASH4.8/object/flash4 2>/dev/null && echo "FLASH_EXISTS" || echo "NO_FLASH4"')
    if 'FLASH_EXISTS' in out:
        print("  FLASH 已编译完成")
    else:
        print("  需要先编译 FLASH...")
        # Need to setup and compile
        out, err = run_cmd(f"""
    cd {HPC_FLASH}/FLASH4.8 && \
    module load hdf5/1.8.18 && module load mpich/3.2-gcc9.3 && \
    ./setup -auto LaserSlab -2d +cylindrical -nxb=16 -nyb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=6 -parfile=example.par 2>&1 | tail -5
    """, timeout=120)
        print(f"  Setup: {out[:200]}")
        out, err = run_cmd(f"""
    cd {HPC_FLASH}/FLASH4.8/object && \
    module load hdf5/1.8.18 && module load mpich/3.2-gcc9.3 && \
    make -j8 2>&1 | tail -10
    """, timeout=600)
        print(f"  Make: {out[:300]}")

    # Step 3: Check if a simulation was already run (has chk files)
    print("[Step 3/5] 检查已有仿真结果...")
    out, err = run_cmd(f'ls {HPC_FLASH}/FLASH4.8/object/*chk* 2>/dev/null')
    chk_files = [f for f in out.split('\n') if f and 'chk' in f]
    print(f"  找到 {len(chk_files)} 个 chk 文件")

    # Step 4: Create sbatch job to run simulation
    print("[Step 4/5] 创建并提交仿真作业...")

    SBATCH_SCRIPT = f"""#!/bin/bash
    #SBATCH -p v6_384
    #SBATCH -N 1
    #SBATCH -n 90
    #SBATCH -J FLASH_LaserSlab
    #SBATCH -o FLASH_%%j.out
    #SBATCH -e FLASH_%%j.err
    #SBATCH --time=02:00:00

    source /public1/soft/modules/module.sh
    module load hdf5/1.8.18
    module load mpich/3.2-gcc9.3

    export HYPRE_HOME={HPC_FLASH}/local/hypre
    export LD_LIBRARY_PATH=$HYPRE_HOME/lib:$LD_LIBRARY_PATH
    export C_INCLUDE_PATH=$HYPRE_HOME/include:$C_INCLUDE_PATH

    export FLASHHome={HPC_FLASH}/FLASH4.8
    cd $FLASHHome/object

    echo "Starting FLASH simulation at $(date)"
    mpirun -np 90 ./flash4
    echo "FLASH finished at $(date)"
    """

    # Write the sbatch script to remote
    sbatch_cmds = f"""cat > {HPC_FLASH}/AI/submit_flash.sbatch << 'SCRIPT_EOF'
    {SBATCH_SCRIPT}
    SCRIPT_EOF
    echo "SBATCH_SCRIPT_WRITTEN"
    """
    out, err = run_cmd(sbatch_cmds)
    print(f"  Script write: {out[:100]}")

    # Submit the job
    out, err = run_cmd(f'cd {HPC_FLASH}/AI && sbatch submit_flash.sbatch 2>&1')
    print(f"  Submit output: {out}")
    print(f"  Submit stderr: {err[:200] if err else ''}")

    # Extract job ID
    job_id = None
    m = re.search(r'(\d+)', out)
    if m:
        job_id = m.group(1)
        print(f"  作业 ID: {job_id}")
    else:
        print("  无法解析作业 ID，尝试手动提交")
        job_id = 'check_later'

    client.close()
    print("\nDone. Job submission complete.")
