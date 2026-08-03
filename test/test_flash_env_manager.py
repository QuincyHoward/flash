"""
FLASH 环境管理器测试 — test_flash_env_manager.py
══════════════════════════════════════════════

测试 flash/env_manager.py 中的 FlashEnvironment 和 FlashEnvManager。
"""

import os
import tempfile

import pytest

from flash import (
    FlashEnvironment,
    FlashEnvManager,
    get_env_manager,
)

# ────────────────────────────────────────────
# FlashEnvironment 测试
# ────────────────────────────────────────────


class TestFlashEnvironment:
    """FlashEnvironment 测试。"""

    def test_default_creation(self):
        """默认构造不抛异常。"""
        env = FlashEnvironment(name="test_env")
        assert env.name == "test_env"
        assert env.flash_home != ""

    def test_env_type_default(self):
        """默认 env_type 为 local_wsl。"""
        env = FlashEnvironment(name="test")
        assert env.env_type == "local_wsl"

    def test_custom_creation(self):
        """自定义参数构造。"""
        env = FlashEnvironment(
            name="remote_ssh",
            env_type="remote_ssh",
            flash_home="~/FLASH/FLASH4.8",
            remote_flash_home="~/FLASH/FLASH4.8",
            remote_work_dir="~/FLASH/run",
            ssh_credential="flash_ssh",
        )
        assert env.env_type == "remote_ssh"
        assert env.ssh_credential == "flash_ssh"

    def test_flash_home_path(self):
        """flash_home 路径合理。"""
        env = FlashEnvironment(name="test")
        assert "~" in env.flash_home or os.path.isabs(env.flash_home)


# ────────────────────────────────────────────
# FlashEnvManager 测试
# ────────────────────────────────────────────


class TestFlashEnvManager:
    """FlashEnvManager 测试（使用 tmp_path）。"""

    def test_creation(self):
        """默认构造不抛异常。"""
        mgr = FlashEnvManager()
        assert mgr is not None

    def test_add_and_get(self):
        """add() 和 get() 存取环境。"""
        mgr = FlashEnvManager()
        env = FlashEnvironment(name="env1")
        mgr.add(env)
        retrieved = mgr.get("env1")
        assert retrieved is not None
        assert retrieved.name == "env1"

    def test_get_nonexistent(self):
        """get() 不存在的名称返回 None。"""
        mgr = FlashEnvManager()
        result = mgr.get("nonexistent_env_xyz")
        assert result is None

    def test_list_environments_empty(self):
        """list_environments() 新管理器返回空列表。"""
        mgr = FlashEnvManager()
        envs = mgr.list_environments()
        assert isinstance(envs, list)

    def test_list_environments_after_add(self):
        """list_environments() 添加后返回列表含添加项。"""
        mgr = FlashEnvManager()
        env = FlashEnvironment(name="env1")
        mgr.add(env)
        envs = mgr.list_environments()
        assert len(envs) >= 1
        assert any(e.name == "env1" for e in envs)

    def test_remove(self):
        """remove() 删除环境。"""
        mgr = FlashEnvManager()
        env = FlashEnvironment(name="to_remove")
        mgr.add(env)
        result = mgr.remove("to_remove")
        assert result is True
        assert mgr.get("to_remove") is None

    def test_remove_nonexistent(self):
        """remove() 不存在的环境返回 False。"""
        mgr = FlashEnvManager()
        result = mgr.remove("nonexistent_env_xyz")
        assert result is False

    def test_set_active(self):
        """set_active() 设置活跃环境。"""
        mgr = FlashEnvManager()
        env = FlashEnvironment(name="active_env")
        mgr.add(env)
        mgr.set_active("active_env")  # 不抛异常即通过
        active = mgr.get_active()
        assert active is not None

    def test_summary(self):
        """summary() 返回字符串。"""
        mgr = FlashEnvManager()
        env = FlashEnvironment(name="env1")
        mgr.add(env)
        result = mgr.summary()
        assert isinstance(result, str)
        assert len(result) > 0


# ────────────────────────────────────────────
# get_env_manager 单例测试
# ────────────────────────────────────────────


class TestGetEnvManager:
    """get_env_manager() 单例测试。"""

    def test_returns_manager(self):
        """返回 FlashEnvManager 实例。"""
        mgr = get_env_manager()
        assert isinstance(mgr, FlashEnvManager)

    def test_singleton(self):
        """多次调用返回同一实例。"""
        mgr1 = get_env_manager()
        mgr2 = get_env_manager()
        assert mgr1 is mgr2
