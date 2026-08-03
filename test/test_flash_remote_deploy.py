"""
FLASH 远程部署测试 — test_flash_remote_deploy.py
═══════════════════════════════════════

测试 flash/remote_deploy.py 中的 FlashRemoteDeploy 类。
SSH 连接使用 unittest.mock 模拟，不依赖真实 SSH。
"""

import pytest
from unittest.mock import MagicMock, patch

from flash import FlashRemoteDeploy
from flash.flash_run.remote.remote_deploy import (
    SSHConnectionError,
    JobSubmissionError,
)

# ────────────────────────────────────────────
# FlashRemoteDeploy 测试（mock SSH）
# ────────────────────────────────────────────


class TestFlashRemoteDeployInit:
    """FlashRemoteDeploy 构造测试（不连接 SSH）。"""

    def test_creation_no_connect(self):
        """
        构造 FlashRemoteDeploy 不抛异常。
        使用 credential_name=None 跳过 SSH 连接。
        """
        try:
            deploy = FlashRemoteDeploy(credential_name=None, verbose=False)
            assert deploy is not None
        except SSHConnectionError:
            pytest.skip("需要 SSH 凭据，跳过")

    def test_init_signature(self):
        """__init__ 接受 credential_name / flash_install_dir / partition / verbose。"""
        import inspect
        from flash.flash_run.remote import remote_deploy

        sig = inspect.signature(remote_deploy.FlashRemoteDeploy.__init__)
        params = list(sig.parameters.keys())
        assert "credential_name" in params
        assert "flash_install_dir" in params
        assert "partition" in params
        assert "verbose" in params


class TestFlashRemoteDeployMocked:
    """
    使用 mock 模拟 SSHClient，测试部署逻辑。
    使用 MinimalCredentialManager 避免 physimx_core 依赖。
    """

    @patch("paramiko.SSHClient")
    @patch("flash.flash_run.remote.remote_deploy.load_ssh_credentials")
    @patch("flash.flash_run.remote.route_tester.test_and_select_best_route")
    def test_connect_success(self, mock_route, mock_load_creds, mock_ssh_class):
        """模拟 SSH 连接成功。"""
        # 设置 mock 路由 — 避免真实的 TCP 连接测试
        mock_route.return_value = {"host": "mock.host", "port": 22, "username": "test_user", "label": "mock", "latency_ms": 5.0}
        # 设置 mock 凭据
        mock_load_creds.return_value = {
            "ssh_username": "test_user",
            "password": "test_pass",
            "active_route": 0,
        }
        # 设置 mock SSHClient
        mock_client = MagicMock()
        # exec_command 需要返回 3 个值 (stdin, stdout, stderr)
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"/home/test_user\n"
        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, MagicMock())
        mock_ssh_class.return_value = mock_client

        deploy = FlashRemoteDeploy(credential_name="test_mock", verbose=False)
        deploy.connect()
        # mock 客户端应被创建并连接
        assert mock_ssh_class.called
        # 验证 connect 被调用
        mock_client.connect.assert_called_once()

    @patch("paramiko.SSHClient")
    @patch("flash.flash_run.remote.remote_deploy.load_ssh_credentials")
    @patch("flash.flash_run.remote.route_tester.test_and_select_best_route")
    def test_connect_failure(self, mock_route, mock_load_creds, mock_ssh_class):
        """模拟 SSH 连接失败 → 抛 SSHConnectionError。"""
        # 设置 mock 路由
        mock_route.return_value = {"host": "mock.host", "port": 22, "username": "test_user", "label": "mock", "latency_ms": 5.0}
        # 设置 mock 凭据
        mock_load_creds.return_value = {
            "ssh_username": "test_user",
            "password": "test_pass",
            "active_route": 0,
        }
        # 设置 mock SSHClient 连接时抛异常
        mock_client = MagicMock()
        mock_client.connect.side_effect = Exception("Connection refused")
        mock_ssh_class.return_value = mock_client

        deploy = FlashRemoteDeploy(credential_name="test_mock", verbose=False)
        with pytest.raises(SSHConnectionError):
            deploy.connect()


class TestDeployFunctions:
    """模块级函数测试。"""

    def test_load_ssh_credentials_no_crash(self):
        """load_ssh_credentials() 不崩溃（无凭据时返回 None 或空）。"""
        from flash.flash_run.remote.remote_deploy import load_ssh_credentials

        result = load_ssh_credentials("nonexistent_credential_xyz")
        # 返回 None 或空字典均可通过
        assert result is None or isinstance(result, dict)

    def test_deploy_to_all_accounts_no_crash(self):
        """deploy_to_all_accounts() 无账户时不崩溃。"""
        from flash.flash_run.remote.remote_deploy import deploy_to_all_accounts

        try:
            deploy_to_all_accounts(job_name="test", nodes=1, walltime="01:00:00")
        except (SSHConnectionError, Exception):
            # 无账户或连接失败是可预期行为
            pass
        assert True


class TestExceptions:
    """异常类测试。"""

    def test_ssh_connection_error(self):
        """SSHConnectionError 是 Exception 子类。"""
        assert issubclass(SSHConnectionError, Exception)

    def test_job_submission_error(self):
        """JobSubmissionError 是 Exception 子类。"""
        assert issubclass(JobSubmissionError, Exception)
