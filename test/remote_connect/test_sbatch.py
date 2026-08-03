"""
SBATCH 提交测试 — 验证 sbatch 脚本生成和提交函数
══════════════════════════════════════════════════

使用 mock SSH 测试 sbatch 相关功能，不需要真实 SSH 连接。
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path


@pytest.fixture
def mock_deploy():
    """创建 mock FlashRemoteDeploy 实例（不连接 SSH）。"""
    with patch("flash.flash_run.remote.remote_deploy.load_ssh_credentials") as mock_creds, \
         patch("flash.flash_run.remote.route_tester.test_and_select_best_route") as mock_route, \
         patch("paramiko.SSHClient") as mock_ssh:
        
        mock_creds.return_value = {
            "ssh_username": "test_user",
            "password": "test_pass",
            "active_route": 0,
        }
        mock_route.return_value = {
            "host": "mock.host", "port": 22,
            "username": "test_user", "latency_ms": 5.0,
        }
        mock_client = MagicMock()
        # exec_command 返回 (stdin, stdout, stderr)
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"/home/test_user\n"
        mock_stdout.channel = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        mock_ssh.return_value = mock_client

        from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy
        deploy = FlashRemoteDeploy(credential_name="test_mock", verbose=False)
        deploy.connect()
        yield deploy


class TestSbatchScript:
    """sbatch 脚本生成测试。"""

    def test_env_manager_build_sbatch(self):
        """测试 FlashEnvironment.build_sbatch_script 可以生成脚本。"""
        from flash.flash_run.env.env_manager import FlashEnvironment

        env = FlashEnvironment(
            name="test_env",
            env_type="ssh_slurm",
            flash_home="/home/test/flash",
            slurm_partition="test_queue",
            slurm_account="test_account",
            default_nproc=4,
        )
        script = env.build_sbatch_script(
            job_name="test_job",
            par_file="test.par",
            flash_exe="flash4",
        )
        assert script is not None
        assert isinstance(script, str)
        assert "#SBATCH" in script
        assert "test_job" in script
        assert "flash4" in script

    def test_env_manager_sbatch_params(self):
        """验证 sbatch 脚本包含关键参数。"""
        from flash.flash_run.env.env_manager import FlashEnvironment

        env = FlashEnvironment(
            name="test_env",
            env_type="ssh_slurm",
            flash_home="/home/test/flash",
            slurm_partition="v5_192",
            slurm_account="flash_test",
            default_nproc=8,
        )
        script = env.build_sbatch_script(
            job_name="test_physics",
            par_file="laserslab.par",
            flash_exe="flash4",
        )
        assert "mpirun" in script or "srun" in script
        assert "#SBATCH" in script


class TestSubmitJob:
    """sbatch 作业提交测试（mock SSH）。"""

    def _mock_exec_success(self, mock_deploy, stdout_text, exit_code=0):
        """辅助：设置 mock 的 exec_command 返回值。"""
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = stdout_text.encode()
        mock_stdout.channel = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = exit_code
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_deploy._client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

    def test_submit_job_success(self, mock_deploy):
        """模拟 sbatch 提交成功。"""
        self._mock_exec_success(mock_deploy, "Submitted batch job 12345\n")

        job_id = mock_deploy.submit_job(
            par_file="laserslab.par",
            flash_exe="flash4",
            nprocs=4,
            job_name="test_job",
        )
        assert job_id == "12345"

    def test_submit_job_failure(self, mock_deploy):
        """模拟 sbatch 提交失败。"""
        self._mock_exec_success(mock_deploy, "sbatch: error: Invalid partition\n", exit_code=1)

        with pytest.raises(Exception):
            mock_deploy.submit_job(
                par_file="laserslab.par",
                flash_exe="flash4",
                nprocs=4,
                job_name="test_job",
            )
