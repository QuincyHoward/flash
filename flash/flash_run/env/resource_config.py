"""
FLASH 仿真资源配置管理器
═══════════════════════════════════════════════════════════

按「装置类型 × 仿真维度」自动管理 CPU/并行数资源配置，
并持久化到控制文件 ``~/.physimx/flash_resource/resource_config.json``，
供 flash 包 (``flash.flash_run.env.resource_config``) 读取使用。

装置分类 (按总核数自动判别):
  total_cpus < 10          → laptop   (笔记本)
  10 <= total_cpus < 30    → desktop  (台式机)
  total_cpus >= 30         → hpc      (超算/集群节点)

每装置每维度的默认配置 (统一 80% CPU):

  device    1D              2D              3D
  --------  --------------  --------------  --------------
  laptop    80% / 1 并行    80% / 1 并行    80% / 1 并行
  desktop   80% / 2 并行    80% / 1 并行    80% / 1 并行
  hpc       80% / 3 并行    80% / 2 并行    80% / 1 并行

每个仿真作业的 MPI 进程数:
  nproc = max(1, int(total_cpus * max_cpu_percent / 100) // max_parallel)

其中 total_cpus 为装置总核数, max_cpu_percent 为 CPU 占用百分比,
max_parallel 为该维度可并行运行的仿真数量。

用法:
    from flash.flash_run.env.resource_config import (
        FlashResourceConfig, get_resource_config, classify_device
    )

    config = FlashResourceConfig()
    cfg_1d = config.get_device_config(device="desktop", dimension=1)
    nproc  = config.get_effective_nproc(dimension=1, total_cpus=16)   # 自动分类装置
"""

import json
import os
import platform
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List


# ── 存储位置 ──────────────────────────────────────
CONFIG_DIR = Path.home() / ".physimx" / "flash_resource"
CONFIG_FILE = CONFIG_DIR / "resource_config.json"

# ── 装置分类阈值 ──────────────────────────────────
# total_cpus < 10 → laptop; < 30 → desktop; >= 30 → hpc
DEVICE_THRESHOLDS: Dict[str, int] = {
    "laptop": 10,
    "desktop": 30,
}

# 默认 CPU 占用百分比 (所有装置统一)
DEFAULT_CPU_PERCENT = 80

# 合法装置名
VALID_DEVICES = ("laptop", "desktop", "hpc")


def classify_device(total_cpus: Optional[int] = None) -> str:
    """按总核数自动判别装置类型。

    Args:
        total_cpus: 装置总核数 (None = 自动探测 os.cpu_count())

    Returns:
        "laptop" | "desktop" | "hpc"
    """
    if total_cpus is None:
        total_cpus = os.cpu_count() or 8
    if total_cpus < DEVICE_THRESHOLDS["laptop"]:
        return "laptop"
    if total_cpus < DEVICE_THRESHOLDS["desktop"]:
        return "desktop"
    return "hpc"


@dataclass
class DeviceDimensionConfig:
    """单装置单维度资源配置。

    Attributes:
        max_cpu_percent: 最大 CPU 占用百分比 (1-100)
        max_parallel: 该维度可并行运行的 FLASH 仿真数量
            (nproc = int(total_cpus * max_cpu_percent/100) // max_parallel)
        description: 维度描述
    """
    max_cpu_percent: int = DEFAULT_CPU_PERCENT
    max_parallel: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DeviceDimensionConfig":
        return cls(
            max_cpu_percent=int(d.get("max_cpu_percent", DEFAULT_CPU_PERCENT)),
            max_parallel=int(d.get("max_parallel", 1)),
            description=d.get("description", ""),
        )


@dataclass
class LocalDimensionConfig:
    """本地 WSL 单维度资源配置 (旧 schema, 向后兼容)。

    Attributes:
        max_cpu_percent: 最大 CPU 占用百分比 (1-100)
        max_parallel: 最大可并行运行的 FLASH 仿真数量
        description: 维度描述
    """
    max_cpu_percent: int = 80
    max_parallel: int = 3
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LocalDimensionConfig":
        return cls(
            max_cpu_percent=d.get("max_cpu_percent", 80),
            max_parallel=d.get("max_parallel", 3),
            description=d.get("description", ""),
        )


@dataclass
class HPCDimensionConfig:
    """超算单维度资源配置 (旧 schema, 向后兼容)。

    Attributes:
        max_cpu_percent: 最大 CPU 占用百分比 (1-100)
        max_parallel: 最大可并行运行的 FLASH 仿真数量
            (每个仿真独占一个节点，不同节点可并发)
        mem_per_job_auto: 是否自动计算每个作业的内存
            = (总内存 * max_cpu_percent / 100) / max_parallel
        mem_per_job_gb: 手动指定的每个作业内存 (GB), 仅当
            mem_per_job_auto=False 时生效
        mem_total_gb: 节点总内存 (GB), 用于自动计算
        description: 维度描述
    """
    max_cpu_percent: int = 95
    max_parallel: int = 4
    mem_per_job_auto: bool = True
    mem_per_job_gb: float = 0.0
    mem_total_gb: float = 0.0  # 0.0 = 自动探测
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HPCDimensionConfig":
        return cls(
            max_cpu_percent=d.get("max_cpu_percent", 95),
            max_parallel=d.get("max_parallel", 4),
            mem_per_job_auto=d.get("mem_per_job_auto", True),
            mem_per_job_gb=d.get("mem_per_job_gb", 0.0),
            mem_total_gb=d.get("mem_total_gb", 0.0),
            description=d.get("description", ""),
        )

    def get_mem_per_job_gb(self, detected_total_gb: Optional[float] = None) -> float:
        """获取每个作业的内存大小 (GB)。

        Args:
            detected_total_gb: 从系统探测到的总内存 (可选)

        Returns:
            每个作业的内存大小 (GB)
        """
        if not self.mem_per_job_auto:
            return self.mem_per_job_gb

        total_gb = self.mem_total_gb if self.mem_total_gb > 0 else (detected_total_gb or 0.0)
        if total_gb <= 0:
            return 0.0  # 无法计算
        return (total_gb * self.max_cpu_percent / 100.0) / self.max_parallel


class FlashResourceConfig:
    """FLASH 仿真资源配置管理器。

    管理不同装置 (laptop/desktop/hpc) 和维度 (1d/2d/3d) 的
    CPU/并行数配置，持久化到 ~/.physimx/flash_resource/resource_config.json。

    控制文件 schema (version 2):
        {
          "version": 2,
          "device_classification": {thresholds, formula, ...},
          "devices": {
              "laptop": {"1d": {...}, "2d": {...}, "3d": {...}},
              "desktop": {...}, "hpc": {...}
          },
          "detected": {total_cores, device, generated_at, ...},
          "local"/"hpc": {...}   # 旧 schema, 向后兼容
        }
    """

    # 维度关键字映射
    DIM_KEYS = {1: "1d", 2: "2d", 3: "3d"}

    def __init__(self):
        # 装置 × 维度配置 (新 schema, 主配置)
        self._devices: Dict[str, Dict[str, DeviceDimensionConfig]] = {}
        # 本地 WSL 配置 (旧 schema, 按维度, 向后兼容)
        self._local: Dict[str, LocalDimensionConfig] = {}
        # 超算配置 (旧 schema, 按维度, 向后兼容)
        self._hpc: Dict[str, HPCDimensionConfig] = {}

        self._load()

    # ── 初始化默认值 ──────────────────────────────────

    def _init_defaults(self) -> None:
        """初始化默认资源配置 (装置感知, 用户规格: 统一 80% CPU)。"""
        # 新 schema: 装置 × 维度
        self._devices = {
            "laptop": {
                "1d": DeviceDimensionConfig(80, 1, "laptop 1D: 80% CPU, 1 parallel (no parallel)"),
                "2d": DeviceDimensionConfig(80, 1, "laptop 2D: 80% CPU, 1 parallel (no parallel)"),
                "3d": DeviceDimensionConfig(80, 1, "laptop 3D: 80% CPU, 1 parallel (no parallel)"),
            },
            "desktop": {
                "1d": DeviceDimensionConfig(80, 2, "desktop 1D: 80% CPU, 2 parallel"),
                "2d": DeviceDimensionConfig(80, 1, "desktop 2D: 80% CPU, 1 parallel (no parallel)"),
                "3d": DeviceDimensionConfig(80, 1, "desktop 3D: 80% CPU, 1 parallel (no parallel)"),
            },
            "hpc": {
                "1d": DeviceDimensionConfig(80, 3, "hpc 1D: 80% CPU, 3 parallel"),
                "2d": DeviceDimensionConfig(80, 2, "hpc 2D: 80% CPU, 2 parallel"),
                "3d": DeviceDimensionConfig(80, 1, "hpc 3D: 80% CPU, 1 parallel (no parallel)"),
            },
        }

        # 旧 schema (向后兼容, 保持原默认值)
        self._local = {
            "1d": LocalDimensionConfig(80, 3, "Local WSL 1D: 80% CPU, 3 parallel"),
            "2d": LocalDimensionConfig(80, 2, "Local WSL 2D: 80% CPU, 2 parallel"),
            "3d": LocalDimensionConfig(80, 1, "Local WSL 3D: 80% CPU, 1 parallel"),
        }
        self._hpc = {
            "1d": HPCDimensionConfig(95, 4, True, 0.0, 0.0, "HPC 1D: 95% CPU, 4 parallel, auto-memory"),
            "2d": HPCDimensionConfig(95, 3, True, 0.0, 0.0, "HPC 2D: 95% CPU, 3 parallel, auto-memory"),
            "3d": HPCDimensionConfig(95, 2, True, 0.0, 0.0, "HPC 3D: 95% CPU, 2 parallel, auto-memory"),
        }

    # ── 持久化 ──────────────────────────────────────

    def _load(self) -> None:
        """从磁盘加载配置。"""
        if not CONFIG_FILE.exists():
            self._init_defaults()
            self._save()
            return

        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)

            # 新 schema: devices (优先)
            dev_data = data.get("devices", {})
            if dev_data:
                for dev in VALID_DEVICES:
                    dblock = dev_data.get(dev, {})
                    self._devices[dev] = {
                        dim: DeviceDimensionConfig.from_dict(dblock.get(dim, {}))
                        for dim in ["1d", "2d", "3d"]
                    }
            else:
                self._init_devices_defaults_only()

            # 旧 schema: local / hpc (向后兼容)
            for dim_key in ["1d", "2d", "3d"]:
                ldata = data.get("local", {}).get(dim_key, {})
                self._local[dim_key] = LocalDimensionConfig.from_dict(ldata)

            for dim_key in ["1d", "2d", "3d"]:
                hdata = data.get("hpc", {}).get(dim_key, {})
                self._hpc[dim_key] = HPCDimensionConfig.from_dict(hdata)

        except (json.JSONDecodeError, KeyError):
            self._init_defaults()
            self._save()

    def _init_devices_defaults_only(self) -> None:
        """仅初始化新 schema 装置默认值 (旧 schema 文件加载时调用)。"""
        self._devices = {
            "laptop": {
                "1d": DeviceDimensionConfig(80, 1, "laptop 1D: 80% CPU, 1 parallel (no parallel)"),
                "2d": DeviceDimensionConfig(80, 1, "laptop 2D: 80% CPU, 1 parallel (no parallel)"),
                "3d": DeviceDimensionConfig(80, 1, "laptop 3D: 80% CPU, 1 parallel (no parallel)"),
            },
            "desktop": {
                "1d": DeviceDimensionConfig(80, 2, "desktop 1D: 80% CPU, 2 parallel"),
                "2d": DeviceDimensionConfig(80, 1, "desktop 2D: 80% CPU, 1 parallel (no parallel)"),
                "3d": DeviceDimensionConfig(80, 1, "desktop 3D: 80% CPU, 1 parallel (no parallel)"),
            },
            "hpc": {
                "1d": DeviceDimensionConfig(80, 3, "hpc 1D: 80% CPU, 3 parallel"),
                "2d": DeviceDimensionConfig(80, 2, "hpc 2D: 80% CPU, 2 parallel"),
                "3d": DeviceDimensionConfig(80, 1, "hpc 3D: 80% CPU, 1 parallel (no parallel)"),
            },
        }

    def _save(self) -> None:
        """持久化存储到磁盘。"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        tmp = CONFIG_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(CONFIG_FILE)

    def to_dict(self) -> Dict[str, Any]:
        """导出完整配置字典 (控制文件内容)。"""
        return {
            "version": 2,
            "device_classification": {
                "method": "total_cores",
                "thresholds": DEVICE_THRESHOLDS,
                "formula": "nproc = max(1, int(total_cpus * max_cpu_percent / 100) // max_parallel)",
                "note": (
                    "total_cpus < 10 → laptop; 10 ≤ total_cpus < 30 → desktop; "
                    "total_cpus ≥ 30 → hpc"
                ),
            },
            "devices": {
                dev: {k: v.to_dict() for k, v in self._devices.get(dev, {}).items()}
                for dev in VALID_DEVICES
            },
            "detected": {
                "total_cores": os.cpu_count() or 8,
                "device": classify_device(),
                "generated_at": "",
            },
            "local": {k: v.to_dict() for k, v in self._local.items()},
            "hpc": {k: v.to_dict() for k, v in self._hpc.items()},
        }

    # ── 公开 API — 装置配置 (新) ─────────────────────

    def get_device_config(self, device: str, dimension: int) -> DeviceDimensionConfig:
        """获取指定装置、指定维度的资源配置。

        Args:
            device: "laptop" | "desktop" | "hpc"
            dimension: 仿真维度 (1, 2, 3)

        Returns:
            DeviceDimensionConfig 实例 (总是返回副本)
        """
        device = device if device in VALID_DEVICES else classify_device()
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        src = self._devices.get(device, {}).get(dim_key, DeviceDimensionConfig())
        return DeviceDimensionConfig(
            max_cpu_percent=src.max_cpu_percent,
            max_parallel=src.max_parallel,
            description=src.description,
        )

    def set_device_config(
        self,
        device: str,
        dimension: int,
        max_cpu_percent: Optional[int] = None,
        max_parallel: Optional[int] = None,
        description: Optional[str] = None,
    ) -> None:
        """修改指定装置、指定维度的资源配置。

        Args:
            device: "laptop" | "desktop" | "hpc"
            dimension: 仿真维度 (1, 2, 3)
            max_cpu_percent: 最大 CPU 占用百分比
            max_parallel: 最大可并行运行数量
            description: 描述
        """
        device = device if device in VALID_DEVICES else classify_device()
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        cfg = self._devices.setdefault(device, {}).setdefault(
            dim_key, DeviceDimensionConfig()
        )
        if max_cpu_percent is not None:
            cfg.max_cpu_percent = max_cpu_percent
        if max_parallel is not None:
            cfg.max_parallel = max_parallel
        if description is not None:
            cfg.description = description
        self._save()

    def list_device_config(self) -> Dict[str, Dict[str, DeviceDimensionConfig]]:
        """列出所有装置 × 维度资源配置。"""
        return {
            dev: dict(self._devices.get(dev, {})) for dev in VALID_DEVICES
        }

    # --- 本地 WSL 配置 (旧 schema, 向后兼容) ---

    def get_local_config(self, dimension: int) -> LocalDimensionConfig:
        """获取本地 WSL 指定维度的资源配置。"""
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        src = self._local.get(dim_key, self._local["1d"])
        return LocalDimensionConfig(
            max_cpu_percent=src.max_cpu_percent,
            max_parallel=src.max_parallel,
            description=src.description,
        )

    def set_local_config(
        self,
        dimension: int,
        max_cpu_percent: Optional[int] = None,
        max_parallel: Optional[int] = None,
        description: Optional[str] = None,
    ) -> None:
        """修改本地 WSL 指定维度的资源配置 (旧 schema, 向后兼容)。"""
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        cfg = self._local.setdefault(dim_key, LocalDimensionConfig())
        if max_cpu_percent is not None:
            cfg.max_cpu_percent = max_cpu_percent
        if max_parallel is not None:
            cfg.max_parallel = max_parallel
        if description is not None:
            cfg.description = description
        self._save()

    def list_local_config(self) -> Dict[str, LocalDimensionConfig]:
        """列出所有本地 WSL 资源配置。"""
        return dict(self._local)

    # --- 超算配置 (旧 schema, 向后兼容) ---

    def get_hpc_config(self, dimension: int) -> HPCDimensionConfig:
        """获取超算指定维度的资源配置。"""
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        src = self._hpc.get(dim_key, self._hpc["1d"])
        return HPCDimensionConfig(
            max_cpu_percent=src.max_cpu_percent,
            max_parallel=src.max_parallel,
            mem_per_job_auto=src.mem_per_job_auto,
            mem_per_job_gb=src.mem_per_job_gb,
            mem_total_gb=src.mem_total_gb,
            description=src.description,
        )

    def set_hpc_config(
        self,
        dimension: int,
        max_cpu_percent: Optional[int] = None,
        max_parallel: Optional[int] = None,
        mem_per_job_auto: Optional[bool] = None,
        mem_per_job_gb: Optional[float] = None,
        mem_total_gb: Optional[float] = None,
        description: Optional[str] = None,
    ) -> None:
        """修改超算指定维度的资源配置 (旧 schema, 向后兼容)。"""
        dim_key = self.DIM_KEYS.get(dimension, "1d")
        cfg = self._hpc.setdefault(dim_key, HPCDimensionConfig())
        if max_cpu_percent is not None:
            cfg.max_cpu_percent = max_cpu_percent
        if max_parallel is not None:
            cfg.max_parallel = max_parallel
        if mem_per_job_auto is not None:
            cfg.mem_per_job_auto = mem_per_job_auto
        if mem_per_job_gb is not None:
            cfg.mem_per_job_gb = mem_per_job_gb
        if mem_total_gb is not None:
            cfg.mem_total_gb = mem_total_gb
        if description is not None:
            cfg.description = description
        self._save()

    def list_hpc_config(self) -> Dict[str, HPCDimensionConfig]:
        """列出所有超算资源配置。"""
        return dict(self._hpc)

    # --- 实用方法 ---

    def get_effective_nproc(
        self,
        dimension: int,
        is_hpc: bool = False,
        device: Optional[str] = None,
        total_cpus: Optional[int] = None,
    ) -> int:
        """计算有效的 MPI 进程数 (每仿真作业)。

        装置判定优先级:
          1. device 参数 (显式指定)
          2. is_hpc=True → "hpc"
          3. 否则按 total_cpus 自动分类 (laptop/desktop/hpc)

        公式 (所有装置统一):
          nproc = max(1, int(total_cpus * max_cpu_percent / 100) // max_parallel)

        Args:
            dimension: 仿真维度 (1, 2, 3)
            is_hpc: 是否为超算模式 (旧调用兼容; device 参数优先)
            device: 装置类型 "laptop"/"desktop"/"hpc" (None = 自动判别)
            total_cpus: 总 CPU 核心数 (None = 自动探测)

        Returns:
            每个作业建议使用的 MPI 进程数
        """
        if total_cpus is None:
            total_cpus = os.cpu_count() or 8

        if device is None:
            device = "hpc" if is_hpc else classify_device(total_cpus)

        cfg = self.get_device_config(device=device, dimension=dimension)
        available = int(total_cpus * cfg.max_cpu_percent / 100)
        return max(1, available // cfg.max_parallel)

    def summary(self) -> str:
        """生成配置摘要文本。"""
        lines = [
            "FLASH 仿真资源配置 (装置感知)",
            "=" * 60,
            "",
            "  装置分类: 总核数 < 10 → 笔记本; < 30 → 台式机; ≥ 30 → 超算",
            "  nproc = max(1, int(总核数 × CPU% / 100) ÷ 并行数)",
            "",
        ]

        for dev in VALID_DEVICES:
            lines.append(f"  [{dev}]")
            for dim_key in ["1d", "2d", "3d"]:
                cfg = self._devices.get(dev, {}).get(dim_key)
                if cfg:
                    parallel_txt = f"{cfg.max_parallel} 个" if cfg.max_parallel > 1 else "不支持并行"
                    lines.append(
                        f"    {dim_key.upper()}: CPU {cfg.max_cpu_percent}%, "
                        f"并行 {parallel_txt}"
                    )
            lines.append("")

        tc = os.cpu_count() or 8
        dev = classify_device(tc)
        lines.append(f"  本机探测: 总核数 {tc} → {dev}")
        lines.append("  控制文件: " + str(CONFIG_FILE))
        lines.append("  生成脚本: scripts/01_env_diagnose/gen_resource_config.py")
        return "\n".join(lines)

    def reset_to_defaults(self) -> None:
        """重置为默认配置。"""
        self._init_defaults()
        self._save()


# ── 全局单例 ──────────────────────────────────────

_config_instance: Optional[FlashResourceConfig] = None


def get_resource_config() -> FlashResourceConfig:
    """获取全局 FlashResourceConfig 单例。"""
    global _config_instance
    if _config_instance is None:
        _config_instance = FlashResourceConfig()
    return _config_instance


# ── CLI 入口 ──────────────────────────────────────

def main():
    """命令行入口: python -m flash.flash_run.env.resource_config"""
    import sys as _sys

    config = get_resource_config()

    if len(_sys.argv) > 1:
        cmd = _sys.argv[1].lower()

        if cmd == "detect":
            tc = int(_sys.argv[2]) if len(_sys.argv) > 2 else (os.cpu_count() or 8)
            dev = classify_device(tc)
            print(f"  总核数: {tc}")
            print(f"  装置类型: {dev}")
            for dim in (1, 2, 3):
                n = config.get_effective_nproc(dimension=dim, total_cpus=tc)
                cfg = config.get_device_config(device=dev, dimension=dim)
                par_txt = f"{cfg.max_parallel} 个并行" if cfg.max_parallel > 1 else "不支持并行"
                print(f"  {dim}D: nproc={n} (CPU {cfg.max_cpu_percent}%, {par_txt})")

        elif cmd in ("device", "dev"):
            dev = _sys.argv[2] if len(_sys.argv) > 2 else None
            dim = int(_sys.argv[3]) if len(_sys.argv) > 3 else 1
            cpu = int(_sys.argv[4]) if len(_sys.argv) > 4 else None
            par = int(_sys.argv[5]) if len(_sys.argv) > 5 else None
            if dev is None:
                print("用法: ... device <laptop|desktop|hpc> <dim> [cpu%] [parallel]")
                return
            if cpu is not None:
                config.set_device_config(dev, dim, max_cpu_percent=cpu, max_parallel=par)
                print(f"  [OK] {dev} {dim}D: CPU={cpu}%, 并行={par}")
            else:
                cfg = config.get_device_config(dev, dim)
                print(f"  {dev} {dim}D: CPU={cfg.max_cpu_percent}%, 并行={cfg.max_parallel}")

        elif cmd == "local":
            dim = int(_sys.argv[2]) if len(_sys.argv) > 2 else 1
            cpu = int(_sys.argv[3]) if len(_sys.argv) > 3 else None
            par = int(_sys.argv[4]) if len(_sys.argv) > 4 else None
            if cpu is not None:
                config.set_local_config(dim, max_cpu_percent=cpu, max_parallel=par)
                print(f"  [OK] 本地 {dim}D: CPU={cpu}%, 并行={par}")
            else:
                cfg = config.get_local_config(dim)
                print(f"  本地 {dim}D: CPU={cfg.max_cpu_percent}%, 并行={cfg.max_parallel}")

        elif cmd == "hpc":
            dim = int(_sys.argv[2]) if len(_sys.argv) > 2 else 1
            cpu = int(_sys.argv[3]) if len(_sys.argv) > 3 else None
            par = int(_sys.argv[4]) if len(_sys.argv) > 4 else None
            if cpu is not None:
                config.set_hpc_config(dim, max_cpu_percent=cpu, max_parallel=par)
                print(f"  [OK] 超算 {dim}D: CPU={cpu}%, 并行={par}")
            else:
                cfg = config.get_hpc_config(dim)
                print(f"  超算 {dim}D: CPU={cfg.max_cpu_percent}%, 并行={cfg.max_parallel}")

        elif cmd in ("show", "list", "summary"):
            print(config.summary())

        elif cmd == "reset":
            config.reset_to_defaults()
            print("  [OK] 已重置为默认配置")

        else:
            print("用法:")
            print("  python -m ...resource_config show        显示当前配置")
            print("  python -m ...resource_config detect [核数]   探测并计算 nproc")
            print("  python -m ...resource_config device <装置> <dim> [cpu%] [parallel]")
            print("  python -m ...resource_config local <dim> [cpu%] [parallel]")
            print("  python -m ...resource_config hpc <dim> [cpu%] [parallel]")
            print("  python -m ...resource_config reset      重置为默认")
    else:
        print(config.summary())


if __name__ == "__main__":
    main()
