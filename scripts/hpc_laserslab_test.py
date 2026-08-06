"""超算 (NC-E) LaserSlab 1D 仿真测试 — 远程执行器

流程:
  1. 远程编译 FLASH (LaserSlab 1D) — 已有 Makefile.h, 缓存避免重复编译
  2. 准备运行目录 (EOS 表 + .par)
  3. mpirun 运行仿真
  4. 检查 HDF5 输出并报告
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import paramiko

from flash._core.credentials._core import load_ssh_credentials

# 远程脚本用户名: 环境变量 FLASH_SIM_USER_DIR → 默认 hello (勿硬编码用户名)
REMOTE_SCRIPT = r"""
#!/bin/bash
set -e
SIM_USER_DIR="${FLASH_SIM_USER_DIR:-hello}"
FLASH_HOME=$HOME/$SIM_USER_DIR/FLASH/FLASH4.8
MPI=/public1/soft/mpich/3.2
export PATH=$MPI/bin:$PATH
export LD_LIBRARY_PATH=/public1/soft/hdf5/1.8.18/lib:$HOME/$SIM_USER_DIR/FLASH/local/hypre/lib:$LD_LIBRARY_PATH

echo "=== [1/4] 检查/编译 FLASH (LaserSlab 1D) ==="
BIN=$FLASH_HOME/object/flash4
if [ -f "$BIN" ]; then
    echo "flash4 已存在, 跳过编译"
else
    cd $FLASH_HOME
    rm -rf object
    echo "--- setup ---"
    ./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio \
        species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=object -parfile=example1d.par 2>&1 | tail -5
    echo "--- make ---"
    cd object
    make -j8 2>&1 | tail -5
    ls -la flash4 && echo "COMPILE_OK"
fi

echo ""
echo "=== [2/4] 准备运行目录 ==="
RUN_DIR=$HOME/$\{SIM_USER_DIR}/FLASH/run_laserslab_hpc_test
rm -rf $RUN_DIR
mkdir -p $RUN_DIR
cd $RUN_DIR
SRC=$FLASH_HOME/source/Simulation/SimulationMain/LaserSlab
cp $SRC/al-imx-003.cn4 $RUN_DIR/ 2>/dev/null || true
cp $SRC/he-imx-005.cn4  $RUN_DIR/ 2>/dev/null || true
cp $SRC/example1d.par $RUN_DIR/flash.par
echo "运行目录: $RUN_DIR"
ls -la $RUN_DIR

echo ""
echo "=== [3/4] 运行仿真 (mpirun -np 4) ==="
mpirun -np 4 $FLASH_HOME/object/flash4 2>&1 | tail -20

echo ""
echo "=== [4/4] 检查输出 ==="
CHK=$(ls $RUN_DIR/*hdf5_chk_* 2>/dev/null | wc -l)
PLT=$(ls $RUN_DIR/*hdf5_plt_cnt_* 2>/dev/null | wc -l)
echo "checkpoint 文件: $CHK"
echo "plot 文件: $PLT"
echo "--- 文件列表 ---"
ls -lh $RUN_DIR/ | head -20
echo "RUN_DONE"
"""


def main():
    cred = load_ssh_credentials("flash_ssh")
    if not cred:
        print("找不到 flash_ssh 凭据")
        sys.exit(1)

    host, port = cred["host"], int(cred["port"])
    user, pwd = cred["username"], cred["password"]
    print(f"连接 {host}:{port} ({user}) ...")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=user, password=pwd,
                   timeout=30, banner_timeout=60, auth_timeout=60)
    print("SSH 连接成功\n")

    # 上传脚本到超算
    sftp = client.open_sftp()
    remote_script = f"/tmp/flash_laserslab_test_{int(time.time())}.sh"
    with sftp.file(remote_script, "w") as f:
        f.write(REMOTE_SCRIPT)
    sftp.close()
    print(f"脚本已上传: {remote_script}\n")

    # 执行
    cmd = f"bash {remote_script}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=1800, get_pty=True)
    # 实时输出
    for line in iter(stdout.readline, ""):
        print(line, end="")
    exit_code = stdout.channel.recv_exit_status()
    err = stderr.read().decode()
    if err.strip():
        print("STDERR:", err[-500:])
    print(f"\n退出码: {exit_code}")

    # 清理远程脚本
    client.exec_command(f"rm -f {remote_script}")
    client.close()


if __name__ == "__main__":
    main()
