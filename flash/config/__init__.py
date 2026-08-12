"""
FLASH 仿真基本配置
═════════════════════

管理 FLASH 仿真的运行配置，包括：
  - 本地运行 vs 超算 SSH 运行
  - 超算硬件配置（节点数、CPU/GPU、内存）
  - FLASH 可执行文件路径
  - 编译选项

用法示例：
  from flash.config import FlashConfig, get_default_config

  config = get_default_config()
  config.mode = "ssh"  # 切换到超算模式
  config.ssh.host = "ssh.cn-zhongwei-1.paracloud.com"
  config.save()
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json


DEFAULT_CONFIG_PATH = Path.home() / ".physimx" / "flash_config.json"


class FlashConfig:
    """FLASH 运行配置。"""

    def __init__(
        self,
        mode: str = "local",
        flash_exe_path: Optional[str] = None,
        ssh_host: Optional[str] = None,
        ssh_port: int = 22,
        ssh_username: Optional[str] = None,
        ssh_password: Optional[str] = None,
        nodes: int = 1,
        ppn: int = 32,
        walltime: str = "01:00:00",
    ):
        self.mode = mode  # "local" | "ssh"
        self.flash_exe_path = flash_exe_path
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.nodes = nodes
        self.ppn = ppn
        self.walltime = walltime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "flash_exe_path": self.flash_exe_path,
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "ssh_username": self.ssh_username,
            "ssh_password": self.ssh_password,
            "nodes": self.nodes,
            "ppn": self.ppn,
            "walltime": self.walltime,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlashConfig":
        return cls(**d)

    def save(self, path: Optional[Path] = None):
        """保存配置到 ~/.physimx/flash_config.json。"""
        path = path or DEFAULT_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"[配置] 已保存: {path}")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "FlashConfig":
        """从文件加载配置。"""
        path = path or DEFAULT_CONFIG_PATH
        if not path.exists():
            return cls()  # 返回默认配置
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)

    def __repr__(self) -> str:
        return (
            f"FlashConfig(mode={self.mode!r}, "
            f"ssh={self.ssh_host if self.ssh_host else 'N/A'})"
        )


def get_default_config() -> FlashConfig:
    """获取默认配置（优先从文件加载）。"""
    return FlashConfig.load()


if __name__ == "__main__":
    config = get_default_config()
    print("当前配置:", config)
    config.mode = "local"
    config.save()
    print("配置已保存到:", DEFAULT_CONFIG_PATH)
