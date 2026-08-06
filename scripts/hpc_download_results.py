"""从超算下载 HDF5 结果到本地"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
import paramiko

from flash._core.credentials._core import load_ssh_credentials

OUT_DIR = Path(
    r"D:\PhySimX\PhySimX\sim\flash\scenarios\flash_demo\hello_flash\outputfiles\hdf5filesfrom_ssh1\laserslab1d"
)


def main():
    cred = load_ssh_credentials("flash_ssh")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        cred["host"],
        port=int(cred["port"]),
        username=cred["username"],
        password=cred["password"],
        timeout=30,
        banner_timeout=60,
        auth_timeout=60,
    )
    print("SSH 连接成功")

    # 用户名: 优先 SSH 凭据 username, 回退 credentials/默认 (勿硬编码用户名)
    _sim_user = str(cred.get("username", "")).split("@")[0] or "hello"

    # 打包 HDF5 (压缩传输更快)
    stdin, stdout, stderr = client.exec_command(
        f'export FLASH_SIM_USER_DIR="{_sim_user}"; '
        "cd ~/$FLASH_SIM_USER_DIR/FLASH/run_laserslab_hpc_test && tar czf /tmp/laserslab_hpc.tar.gz lasslab_hdf5_chk_0001 lasslab_hdf5_chk_0005 lasslab_hdf5_chk_0010 lasslab_hdf5_chk_0020 lasslab_hdf5_chk_0030 lasslab_hdf5_chk_0039 && ls -lh /tmp/laserslab_hpc.tar.gz",
        timeout=120,
    )
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err.strip():
        print("STDERR:", err[:300])

    # 下载
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sftp = client.open_sftp()
    local_tar = Path(r"D:\PhySimX\PhySimX\sim\flash\scenarios\flash_demo\hello_flash\wsl_tmp\laserslab_hpc.tar.gz")
    local_tar.parent.mkdir(parents=True, exist_ok=True)
    sftp.get("/tmp/laserslab_hpc.tar.gz", str(local_tar))
    sftp.close()
    print("已下载:", local_tar, local_tar.stat().st_size, "bytes")

    # 解压到目标目录
    import tarfile

    with tarfile.open(local_tar) as tf:
        for member in tf.getmembers():
            member.name = Path(member.name).name  # 去除路径
            tf.extract(member, OUT_DIR)
    print(f"解压完成: {len(list(OUT_DIR.glob('*')))} 个文件 → {OUT_DIR}")
    for f in sorted(OUT_DIR.glob("*"))[:8]:
        print("  ", f.name, f.stat().st_size, "bytes")

    client.close()


if __name__ == "__main__":
    main()
