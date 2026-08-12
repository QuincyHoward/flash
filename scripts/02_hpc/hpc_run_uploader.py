"""上传并执行超算运行脚本"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
import paramiko

from flash._core.credentials._core import load_ssh_credentials

LOCAL_SCRIPT = Path(__file__).parent / "hpc_run_laserslab.sh"


def main():
    cred = load_ssh_credentials("flash_ssh")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(cred["host"], port=int(cred["port"]),
                   username=cred["username"], password=cred["password"],
                   timeout=30, banner_timeout=60, auth_timeout=60)
    print("SSH 连接成功")

    sftp = client.open_sftp()
    remote = "/tmp/hpc_run_laserslab.sh"
    sftp.put(str(LOCAL_SCRIPT), remote)
    sftp.close()
    print("脚本已上传:", remote)

    stdin, stdout, stderr = client.exec_command(f"bash {remote}", timeout=1200, get_pty=True)
    for line in iter(stdout.readline, ""):
        print(line, end="")
    client.close()
    print("\n完成")


if __name__ == "__main__":
    main()
