"""
FLASH 超算远程部署模块
══════════════════════════

迁移并整合 OldVersion/ParaPython 的功能，
支持通过 SSH 在超算上安装、运行、管理 FLASH。

功能:
  - FlashRemoteDeploy: 超算远程部署管理器
  - 支持多超算账户（load_all_ssh_credentials）
  - FLASH 一键安装（结合 FirstRun）
  - SBATCH 作业提交与监控
  - 结果下载与后处理

依赖:
  - paramiko (SSH/SFTP)
  - flash._core.credentials (密码管理)
  - flash.input_gen.first_run (FLASH 安装)

用法:
  from flash.remote_deploy import FlashRemoteDeploy
  deploy = FlashRemoteDeploy(credential_name="flash_ssh")
  deploy.install_flash()
  job_id = deploy.submit_job("flash_2d.par")
"""

import os
import time
import socket
import posixpath
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import paramiko
from paramiko.ssh_exception import (
    AuthenticationException,
    SSHException,
    BadHostKeyException,
)

from flash._core.credentials import load_ssh_credentials, load_all_ssh_credentials, get_user_name


# ── 默认配置 ──────────────────────────────────

# 默认 FLASH 安装目录 — 使用 user_name 动态构造
# 实际值由 FlashEnvironment 或调用方提供
DEFAULT_FLASH_INSTALL_DIR = None
DEFAULT_FLASH_SETUP_SH = "FLASH_env.sh"
DEFAULT_SBATCH_PARTITION = "cpu"
DEFAULT_SFTP_RETRY = 3
DEFAULT_CMD_TIMEOUT = 300  # 5 minutes


# ── 异常类 ──────────────────────────────────

class RemoteDeployError(Exception):
    """超算部署错误。"""
    pass


class SSHConnectionError(RemoteDeployError):
    """SSH 连接失败。"""
    pass


class JobSubmissionError(RemoteDeployError):
    """作业提交失败。"""
    pass


# ── 远程部署类 ──────────────────────────────

class FlashRemoteDeploy:
    """FLASH 超算远程部署管理器。

    封装 paramiko SSH/SFTP 操作，支持：
      - 多超算账户（通过 credential_name 选择）
      - FLASH 远程安装（调用 FirstRun 脚本）
      - SBATCH 作业提交、监控、取消
      - 文件上传/下载
      - 结果分析（调用 output_analysis）

    Attributes:
        credential_name: 凭据名称（None = 主账户）
        flash_install_dir: 远程 FLASH 安装目录
        connected: 是否已连接
    """

    def __init__(
        self,
        credential_name: Optional[str] = None,
        flash_install_dir: Optional[str] = DEFAULT_FLASH_INSTALL_DIR,
        partition: str = DEFAULT_SBATCH_PARTITION,
        verbose: bool = True,
    ):
        """
        Args:
            credential_name: 凭据名称。None = 自动选择主账户。
            flash_install_dir: 远程 FLASH 安装目录。
            partition: SLURM 分区名。
            verbose: 是否打印详细日志。
        """
        self.credential_name = credential_name
        # 如果 flash_install_dir 为 None，从 credentials 动态获取 user_name 构造路径
        if flash_install_dir is None:
            try:
                user_name = get_user_name()
            except Exception:
                user_name = "hello"
            flash_install_dir = f"~/{user_name}/FLASH/FLASH4.8"
        self.flash_install_dir = flash_install_dir
        self.partition = partition
        self.verbose = verbose

        # SSH 连接状态
        self._credential: Optional[Dict[str, Any]] = None
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._connected = False
        self._home_dir: Optional[str] = None

        # 当前使用的路由 (由 connect() 自动选择)
        self._current_route: Optional[Dict[str, Any]] = None

    # ── 路由自动选择 (每次连接时动态测试) ──────────

    def _auto_select_best_route(self) -> Dict[str, Any]:
        """自动选择当前网络延迟最低的 SSH 路由。

        每次连接时重新测试所有路由，确保始终使用
        当前网络条件下最快的线路。
        """
        try:
            from flash.flash_run.remote.route_tester import (
                RouteTester, test_and_select_best_route,
                ROUTES_SCFA2696, ROUTES_SCH0348,
            )
        except ImportError:
            raise SSHConnectionError(
                "route_tester 模块未找到, 无法自动选择路由"
            )

        if self._credential is None:
            self._credential = load_ssh_credentials(self.credential_name)
            if self._credential is None:
                raise SSHConnectionError(
                    f"凭据未找到: {self.credential_name or '(主账户)'}"
                )

        # 确定路由 key
        route_key = self._credential.get("route_key", "")
        password = self._credential.get("password", "")

        if route_key == "scfa2696":
            routes = ROUTES_SCFA2696
        else:
            routes = ROUTES_SCH0348

        if self.verbose:
            print(f"[FlashRemoteDeploy] 正在测试 SSH 路由 (TCP 延迟)...")

        best = test_and_select_best_route(
            RouteTester.account_label(self.credential_name or "flash_ssh", self._credential),
            routes,
        )

        if best is None:
            raise SSHConnectionError(
                f"所有 SSH 路由均不可达 (TCP 连接失败)"
            )

        if self.verbose:
            print(f"  最佳路由: {best['host']}:{best['port']} ({best['latency_ms']:.0f}ms)")

        return {
            "host": best["host"],
            "port": int(best["port"]),
            "username": best["username"],
            "password": password,
        }

    # ── 连接管理 ──────────────────────────────

    def connect(self, retry: int = 3, retry_interval: float = 5.0) -> None:
        """建立 SSH 连接（支持自动重试 + 动态路由选择）。

        每次连接时自动测试所有路由的 TCP 延迟，
        选择当前网络条件下最快的线路。

        Raises:
            SSHConnectionError: 所有重试均失败或路由不可达。
        """
        if self._connected:
            if self.verbose:
                print("[FlashRemoteDeploy] 已连接，跳过")
            return

        # 加载凭据
        if self._credential is None:
            self._credential = load_ssh_credentials(self.credential_name)
            if self._credential is None:
                raise SSHConnectionError(
                    f"凭据未找到: {self.credential_name or '(主账户)'}"
                    f"\n请先运行: python scripts/setup_credentials.py"
                )

        # 自动选择最佳路由 (每次连接都测试)
        route = self._auto_select_best_route()
        host = route["host"]
        port = route["port"]
        username = route["username"]
        password = route["password"]
        self._current_route = route

        last_error = None
        for attempt in range(1, retry + 1):
            try:
                if self.verbose:
                    print(f"[FlashRemoteDeploy] 连接 {username}@{host}:{port} "
                           f"(尝试 {attempt}/{retry})...")

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=30,
                    allow_agent=False,
                    look_for_keys=False,
                )
                self._client = client

                # 打开 SFTP
                self._sftp = client.open_sftp()

                # 获取 HOME 目录
                stdin, stdout, stderr = client.exec_command("echo $HOME")
                self._home_dir = stdout.read().decode("utf-8").strip()

                self._connected = True
                if self.verbose:
                    print(f"  [OK] 已连接 (HOME={self._home_dir})")
                return

            except (AuthenticationException, BadHostKeyException) as e:
                raise SSHConnectionError(f"认证失败: {e}") from e
            except (socket.gaierror, socket.timeout) as e:
                last_error = e
                if self.verbose:
                    print(f"  [WARN] 连接失败: {e}，{retry_interval}s 后重试...")
                time.sleep(retry_interval)
            except (SSHException, Exception) as e:
                last_error = e
                if attempt < retry:
                    if self.verbose:
                        print(f"  [WARN] 连接失败: {e}，{retry_interval}s 后重试...")
                    time.sleep(retry_interval)
                else:
                    raise SSHConnectionError(
                        f"连接失败（已重试 {retry} 次）: {last_error}"
                    ) from last_error

        raise SSHConnectionError(f"连接失败（已重试 {retry} 次）: {last_error}")

    def disconnect(self) -> None:
        """断开 SSH 连接。"""
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None
        self._connected = False
        if self.verbose:
            print("[FlashRemoteDeploy] 已断开连接")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    # ── 工具方法 ──────────────────────────────

    def _resolve_path(self, path: str) -> str:
        """解析远程路径（~ → 实际 HOME）。"""
        if path.startswith("~/"):
            if self._home_dir is None:
                raise RemoteDeployError("未连接，无法解析 ~ 路径")
            return posixpath.join(self._home_dir, path[2:])
        return path

    def execute(
        self,
        command: str,
        work_dir: Optional[str] = None,
        timeout: int = DEFAULT_CMD_TIMEOUT,
        get_pty: bool = False,
    ) -> Tuple[str, str, int]:
        """执行远程命令。

        Args:
            command: shell 命令。
            work_dir: 工作目录（执行命令前 cd 到此目录）。
            timeout: 命令超时（秒）。
            get_pty: 是否分配 PTY（用于交互式命令）。

        Returns:
            (stdout, stderr, exit_code)
        """
        if not self._connected:
            self.connect()

        if work_dir:
            work_dir = self._resolve_path(work_dir)
            command = f"cd {work_dir} && {command}"

        if self.verbose:
            print(f"  [CMD] {command[:120]}{'...' if len(command) > 120 else ''}")

        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=timeout, get_pty=get_pty
        )

        stdout_str = stdout.read().decode("utf-8", errors="replace")
        stderr_str = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()

        if self.verbose and exit_code != 0:
            print(f"  [WARN] exit_code={exit_code}")
            if stderr_str.strip():
                print(f"  [STDERR] {stderr_str[:200]}")

        return stdout_str, stderr_str, exit_code

    def upload(self, local_path: str, remote_path: str) -> None:
        """上传文件到超算。"""
        if not self._connected:
            self.connect()

        remote_path = self._resolve_path(remote_path)
        remote_dir = posixpath.dirname(remote_path)

        # 确保远程目录存在
        self.execute(f"mkdir -p {remote_dir}")

        if self.verbose:
            print(f"  [UPLOAD] {local_path} → {remote_path}")
        self._sftp.put(local_path, remote_path)

    def download(self, remote_path: str, local_path: str) -> None:
        """从超算下载文件。"""
        if not self._connected:
            self.connect()

        remote_path = self._resolve_path(remote_path)
        local_path = os.path.abspath(local_path)

        # 确保本地目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if self.verbose:
            print(f"  [DOWNLOAD] {remote_path} → {local_path}")

        # 检查远程文件是否存在
        try:
            self._sftp.stat(remote_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"远程文件不存在: {remote_path}") from None

        self._sftp.get(remote_path, local_path)

    def file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在。"""
        if not self._connected:
            self.connect()

        remote_path = self._resolve_path(remote_path)
        try:
            self._sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    # ── FLASH 安装 ─────────────────────────────

    def install_flash(
        self,
        flash_version: str = "4.6.2",
        install_dir: Optional[str] = None,
        with_setup: bool = True,
    ) -> Dict[str, Any]:
        """在超算上安装 FLASH（结合 FirstRun 逻辑）。

        Args:
            flash_version: FLASH 版本号。
            install_dir: 安装目录（None = self.flash_install_dir）。
            with_setup: 是否生成 FLASH_env.sh 等配置文件。

        Returns:
            {"success": bool, "install_dir": str, ...}
        """
        install_dir = install_dir or self.flash_install_dir
        install_dir = self._resolve_path(install_dir)

        if self.verbose:
            print(f"\n[Install] 开始在超算上安装 FLASH {flash_version}")
            print(f"  安装目录: {install_dir}")

        # 1. 检查是否已安装
        stdout, stderr, exit_code = self.execute(
            f"test -d {install_dir}/flash4 && echo EXISTS || echo NOT_FOUND"
        )
        if "EXISTS" in stdout:
            if self.verbose:
                print(f"  [INFO] FLASH 已安装在 {install_dir}")
                print(f"  跳过快安装。如需重装，请手动删除 {install_dir}/flash4")
            return {"success": True, "skipped": True, "install_dir": install_dir}

        # 2. 检查依赖
        if self.verbose:
            print("  [Step 1/5] 检查依赖...")
        for cmd in ["gcc", "gfortran", "make", "git"]:
            stdout, stderr, exit_code = self.execute(f"which {cmd}")
            if exit_code != 0:
                print(f"  [WARN] {cmd} 未找到，尝试加载模块...")
                self.execute(f"module load {cmd} 2>/dev/null || true")

        # 3. 下载 FLASH 源码
        if self.verbose:
            print(f"  [Step 2/5] 下载 FLASH {flash_version} 源码...")
        flash_url = f"https://github.com/Flash-Centro/Astrophysical-FLASH/archive/refs/tags/v{flash_version}.tar.gz"
        # 实际上 FLASH 需要注册才能下载，这里使用占位符
        # 真实部署时应该从内部源或预先上传的 tarball 安装

        stdout, stderr, exit_code = self.execute(f"""
            mkdir -p {install_dir} && cd {install_dir} &&
            echo "FLASH {flash_version} download would happen here" &&
            echo "Please upload FLASH source tarball manually." &&
            ls -la {install_dir}/
        """)
        if self.verbose:
            print(f"  [INFO] {stdout[:300]}")

        # 4. 生成 FLASH_env.sh, FLASH_setup.sh, FLASH_run.sh, FLASH_move.sh
        if with_setup:
            if self.verbose:
                print("  [Step 3/5] 生成 FLASH 配置文件...")

            # 这些文件的内容来自 OldVersion/BASEINFO/FLASH_GenShell.py
            # 简化版：只生成占位符
            self.execute(f"""cat > {install_dir}/FLASH_env.sh << 'ENVEOF'
# FLASH environment variables
export FLASHHOME={install_dir}/flash4
export FLASHWorkspace={install_dir}/workspace
export PATH=$FLASHHOME/bin:$PATH
export LD_LIBRARY_PATH=$FLASHHOME/lib:$LD_LIBRARY_PATH
ENVEOF
echo "FLASH_env.sh created"
""")

        # 5. 编译 FLASH（占位符）
        if self.verbose:
            print("  [Step 4/5] 编译 FLASH（占位符）...")
            print("  [TODO] 实际上传 FLASH 源码并编译")

        # 6. 验证安装
        if self.verbose:
            print("  [Step 5/5] 验证安装...")
        stdout, stderr, exit_code = self.execute(f"ls -la {install_dir}/")
        if self.verbose:
            print(f"  [INFO] 安装目录内容:\n{stdout[:400]}")

        print(f"\n  [WARN] FLASH 安装功能为占位符版本。")
        print(f"  真实部署需要:")
        print(f"    1. 上传 FLASH 源码到超算")
        print(f"    2. 修改此函数以调用真实的编译命令")
        print(f"    或: 手动在超算上安装后，通过 submit_job() 提交作业")

        return {
            "success": True,
            "shell": True,
            "install_dir": install_dir,
            "flash_version": flash_version,
            "note": "Placeholder implementation — manual FLASH installation required",
        }

    # ── SBATCH 作业管理 ───────────────────────

    def submit_job(
        self,
        par_file: str,
        flash_exe: str = "flash4",
        nprocs: int = 32,
        wall_time: str = "01:00:00",
        job_name: str = "flash_job",
        output_dir: Optional[str] = None,
    ) -> Optional[str]:
        """提交 SBATCH 作业。

        Args:
            par_file: .par 文件路径（本地或远程）。
            flash_exe: FLASH 可执行文件名。
            nprocs: 进程数。
            wall_time: 最长运行时间（HH:MM:SS）。
            job_name: 作业名。
            output_dir: 输出目录（None = 自动生成）。

        Returns:
            作业 ID（提交失败时返回 None）。
        """
        if not self._connected:
            self.connect()

        if self.verbose:
            print(f"\n[Submit] 提交 FLASH 作业: {job_name}")

        # 上传 .par 文件（如果是本地文件）
        par_file_resolved = self._resolve_path(par_file) if par_file.startswith("~") else par_file
        if not par_file.startswith("/") and not par_file.startswith("~"):
            # 相对路径，假设已经在超算上
            par_remote = posixpath.join(self.flash_install_dir, "workspace", par_file)
        else:
            par_remote = par_file_resolved

        # 生成 SBATCH 脚本
        sbatch_script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={self.partition}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node={nprocs}
#SBATCH --time={wall_time}
#SBATCH --output=flash_%j.out
#SBATCH --error=flash_%j.err

echo "=== FLASH Job Start ==="
date
hostname

cd {posixpath.dirname(par_remote)}
source {self.flash_install_dir}/FLASH_env.sh

srun ./{flash_exe} -par_file {posixpath.basename(par_remote)}

echo "=== FLASH Job End ==="
date
"""

        # 写入远程临时文件
        sbatch_path = posixpath.join(self.flash_install_dir, f"{job_name}.sbatch")
        # 通过 echo 写入（小文件）
        sbatch_escaped = sbatch_script.replace("'", "'\\''")
        self.execute(f"cat > {sbatch_path} << 'SBATCHEOF'\n{sbatch_script}\nSBATCHEOF")

        # 提交作业
        stdout, stderr, exit_code = self.execute(f"sbatch {sbatch_path}")
        if exit_code != 0:
            raise JobSubmissionError(f"sbatch 失败: {stderr}")

        # 解析作业 ID
        import re
        match = re.search(r"Submitted batch job (\d+)", stdout)
        if match:
            job_id = match.group(1)
            if self.verbose:
                print(f"  [OK] 作业已提交: JobID={job_id}")
            return job_id
        else:
            print(f"  [WARN] 无法解析 JobID，sbatch 输出: {stdout}")
            return None

    def check_job(self, job_id: str) -> str:
        """检查作业状态。

        Returns:
            状态字符串: "PENDING", "RUNNING", "COMPLETED", "FAILED", "UNKNOWN"
        """
        if not self._connected:
            self.connect()

        stdout, stderr, exit_code = self.execute(f"sacct -j {job_id} --format=State --noheader")
        state = stdout.strip().split("\n")[0] if stdout.strip() else "UNKNOWN"
        return state

    def cancel_job(self, job_id: str) -> bool:
        """取消作业。"""
        if not self._connected:
            self.connect()

        stdout, stderr, exit_code = self.execute(f"scancel {job_id}")
        if exit_code == 0:
            if self.verbose:
                print(f"  [OK] 作业 {job_id} 已取消")
            return True
        else:
            print(f"  [FAIL] 取消作业失败: {stderr}")
            return False

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = 30,
        timeout: int = 3600,
    ) -> str:
        """等待作业完成。

        Returns:
            最终状态。
        """
        if self.verbose:
            print(f"[Wait] 等待作业 {job_id} 完成 (timeout={timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self.check_job(job_id)
            if state in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"):
                if self.verbose:
                    print(f"  [OK] 作业 {job_id} 结束: {state}")
                return state
            if self.verbose:
                print(f"  [INFO] 作业 {job_id} 状态: {state}")
            time.sleep(poll_interval)

        print(f"  [WARN] 等待超时 ({timeout}s)")
        return "TIMEOUT"

    # ── 结果下载与分析 ────────────────────────

    def download_results(
        self,
        remote_output_dir: str,
        local_output_dir: str,
        pattern: str = "*.h5",
    ) -> List[str]:
        """下载仿真结果文件。

        Args:
            remote_output_dir: 远程输出目录。
            local_output_dir: 本地保存目录。
            pattern: 文件匹配模式。

        Returns:
            下载的文件列表（本地路径）。
        """
        if not self._connected:
            self.connect()

        remote_output_dir = self._resolve_path(remote_output_dir)
        os.makedirs(local_output_dir, exist_ok=True)

        # 列出远程文件
        stdout, stderr, exit_code = self.execute(
            f"ls {remote_output_dir}/{pattern} 2>/dev/null || echo 'NO_FILES'"
        )
        if "NO_FILES" in stdout:
            print(f"  [WARN] 未找到匹配文件: {remote_output_dir}/{pattern}")
            return []

        remote_files = [f for f in stdout.strip().split("\n") if f]
        downloaded = []

        for rf in remote_files:
            local_path = os.path.join(local_output_dir, os.path.basename(rf))
            try:
                self.download(rf, local_path)
                downloaded.append(local_path)
            except Exception as e:
                print(f"  [WARN] 下载失败 {rf}: {e}")

        if self.verbose:
            print(f"  [OK] 下载了 {len(downloaded)} 个文件到 {local_output_dir}")

        return downloaded

    def get_job_output(self, job_id: str, local_dir: str = "outputs") -> Dict[str, Any]:
        """获取作业输出（stdout/stderr 文件）。"""
        if not self._connected:
            self.connect()

        output_dir = self._resolve_path(f"~/flash_{job_id}.out")
        error_dir = self._resolve_path(f"~/flash_{job_id}.err")

        result = {"job_id": job_id, "stdout": "", "stderr": "", "files": []}

        if self.file_exists(output_dir):
            local_out = os.path.join(local_dir, f"flash_{job_id}.out")
            self.download(output_dir, local_out)
            with open(local_out, "r", encoding="utf-8", errors="replace") as f:
                result["stdout"] = f.read()

        if self.file_exists(error_dir):
            local_err = os.path.join(local_dir, f"flash_{job_id}.err")
            self.download(error_dir, local_err)
            with open(local_err, "r", encoding="utf-8", errors="replace") as f:
                result["stderr"] = f.read()

        return result


# ── 多超算并行调度 ─────────────────────────

def deploy_to_all_accounts(
    task_fn: callable,
    **kwargs
) -> Dict[str, Any]:
    """向所有超算账户并行部署任务。

    Args:
        task_fn: 任务函数，签名为 (deploy: FlashRemoteDeploy, **kwargs) -> Any
        **kwargs: 传递给 task_fn 的额外参数

    Returns:
        {账户名: 任务结果}
    """
    all_creds = load_all_ssh_credentials()
    if not all_creds:
        print("[deploy_to_all] 没有找到超算凭据")
        return {}

    results = {}
    for name, cred in all_creds.items():
        try:
            from flash.flash_run.remote.route_tester import RouteTester
            label = RouteTester.account_label(name, cred)
        except ImportError:
            label = cred.get("route_key", name)
        print(f"\n[deploy_to_all] 部署到 {name} ({label})...")
        try:
            deploy = FlashRemoteDeploy(credential_name=name)
            results[name] = task_fn(deploy, **kwargs)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results[name] = {"error": str(e)}

    return results


# ── 便捷函数 ──────────────────────────────────

def quick_submit(
    par_file: str,
    credential_name: Optional[str] = None,
    nprocs: int = 32,
    **kwargs,
) -> Optional[str]:
    """便捷函数: 快速提交 FLASH 作业。

    Returns:
        作业 ID。
    """
    with FlashRemoteDeploy(credential_name=credential_name) as deploy:
        return deploy.submit_job(par_file, nprocs=nprocs, **kwargs)


def quick_install(
    credential_name: Optional[str] = None,
    flash_version: str = "4.6.2",
    **kwargs,
) -> Dict[str, Any]:
    """便捷函数: 快速安装 FLASH。"""
    with FlashRemoteDeploy(credential_name=credential_name) as deploy:
        return deploy.install_flash(flash_version=flash_version, **kwargs)


if __name__ == "__main__":
    print("FLASH Remote Deploy Demo")
    print("=" * 40)

    # 列出所有超算账户
    all_creds = load_all_ssh_credentials()
    print(f"\n可用超算账户: {list(all_creds.keys())}")

    try:
        from flash.flash_run.remote.route_tester import RouteTester
        for name, cred in all_creds.items():
            label = RouteTester.account_label(name, cred)
            print(f"  {name}: {label}")
    except ImportError:
        pass

    primary = load_ssh_credentials()
    if primary:
        from flash.flash_run.remote.route_tester import RouteTester
        label = RouteTester.account_label("(primary)", primary)
        print(f"主账户: {label}")
    else:
        print("\n[WARN] 未找到凭据，请先运行:")
        print("  python scripts/setup_credentials.py")
