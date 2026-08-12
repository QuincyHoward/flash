"""
FLASH 仿真环境管理器
═══════════════════════════════════════════════════════════

管理不同计算环境下 FLASH 的位置和执行命令：
  - 本地 WSL: 直接运行 mpirun
  - 超算 SSH: SBATCH/SLURM 提交
  - 多环境切换: 按名称选择环境

用法:
    from flash.env_manager import FlashEnvManager, FlashEnvironment

    mgr = FlashEnvManager()

    # 列出可用环境
    envs = mgr.list_environments()

    # 获取当前活跃环境
    env = mgr.get_active()

    # 切换环境
    mgr.set_active("supercomputer_nc_e")

    # 生成运行命令
    cmd = env.build_run_command(par_file="flash.par", nproc=4)

    # 生成 SBATCH 脚本
    script = env.build_sbatch_script(par_file="flash.par", job_name="LaserSlab1D")
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from flash._core.credentials import get_user_name


# ── 配置存储位置 ──────────────────────────────────────
ENV_CONFIG_DIR = Path.home() / ".physimx" / "flash_envs"
ENV_CONFIG_FILE = ENV_CONFIG_DIR / "environments.json"


class FlashEnvironment:
    """单个 FLASH 运行环境的完整配置。

    Attributes:
        name: 环境名称 (唯一标识)
        env_type: 环境类型 ("local_wsl" | "ssh_slurm")
        description: 环境描述
        user_name: 用户名称（用于构造路径前缀，如 ~/hello/FLASH/...）
                     默认为 None，从 credentials 系统动态读取
                     如读取失败则使用 "hello"

        # 本地 WSL 配置
        wsl_distro: WSL 发行版名称 (默认 Ubuntu)
        flash_home: FLASH 安装路径 (远程/WSL 上的路径)
                     默认: ~/{user_name}/FLASH/FLASH4.8 (user_name 构造)
        mpi_path: MPI 安装路径
        hdf5_path: HDF5 安装路径
        hypre_path: HYPRE 安装路径

        # SSH/SLURM 配置
        ssh_credential: 凭据名称 (如 "flash_ssh")
        remote_flash_home: 超算上 FLASH 安装路径
                           默认: ~/{user_name}/FLASH/FLASH4.8 (user_name 构造)
        remote_work_dir: 超算上工作目录
                           默认: ~/{user_name}/FLASH/run (user_name 构造)
        slurm_partition: SLURM 分区名
        slurm_account: SLURM 账户名

        # 通用配置
        default_nproc: 默认进程数
        default_walltime: 默认墙钟时间
    """

    def __init__(
        self,
        name: str = "local_wsl",
        env_type: str = "local_wsl",
        description: str = "",
        # 用户名称（用于构造路径前缀 ~/{user_name}/...）
        user_name: Optional[str] = None,
        # 本地 WSL
        wsl_distro: str = "Ubuntu",
        flash_home: Optional[str] = None,  # None = 用 user_name 自动构造
        mpi_path: str = "/usr/local/mpich",
        hdf5_path: str = "/usr/local/hdf5",
        hypre_path: str = "/usr/local/hypre",
        # SSH/SLURM
        ssh_credential: str = "flash_ssh",
        remote_flash_home: Optional[str] = None,  # None = 用 user_name 自动构造
        remote_work_dir: Optional[str] = None,    # None = 用 user_name 自动构造
        slurm_partition: str = "",
        slurm_account: str = "",
        # 通用
        default_nproc: int = 4,
        default_walltime: str = "01:00:00",
        # 输入文件打包
        bundle_input_files: bool = True,
    ):
        self.name = name
        self.env_type = env_type  # "local_wsl" | "ssh_slurm"
        self.description = description

        # 从 credentials 动态获取 user_name（为 None 时自动读取）
        if user_name is None:
            try:
                user_name = get_user_name()
            except Exception:
                user_name = "hello"
        self.user_name = user_name

        # 本地 WSL
        self.wsl_distro = wsl_distro
        self.flash_home = flash_home if flash_home is not None else f"~/{user_name}/FLASH/FLASH4.8"
        self.mpi_path = mpi_path
        self.hdf5_path = hdf5_path
        self.hypre_path = hypre_path

        # SSH/SLURM
        self.ssh_credential = ssh_credential
        self.remote_flash_home = remote_flash_home if remote_flash_home is not None else f"~/{user_name}/FLASH/FLASH4.8"
        self.remote_work_dir = remote_work_dir if remote_work_dir is not None else f"~/{user_name}/FLASH/run"
        self.slurm_partition = slurm_partition
        self.slurm_account = slurm_account

        # 通用
        self.default_nproc = default_nproc
        self.default_walltime = default_walltime
        self.bundle_input_files = bundle_input_files
        self._resource_config = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "env_type": self.env_type,
            "description": self.description,
            "user_name": self.user_name,
            "wsl_distro": self.wsl_distro,
            "flash_home": self.flash_home,
            "mpi_path": self.mpi_path,
            "hdf5_path": self.hdf5_path,
            "hypre_path": self.hypre_path,
            "ssh_credential": self.ssh_credential,
            "remote_flash_home": self.remote_flash_home,
            "remote_work_dir": self.remote_work_dir,
            "slurm_partition": self.slurm_partition,
            "slurm_account": self.slurm_account,
            "default_nproc": self.default_nproc,
            "default_walltime": self.default_walltime,
            "bundle_input_files": self.bundle_input_files,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlashEnvironment":
        return cls(**{k: v for k, v in d.items() if k in cls.__init__.__code__.co_varnames})

    def is_local(self) -> bool:
        return self.env_type == "local_wsl"

    def is_remote(self) -> bool:
        return self.env_type == "ssh_slurm"

    def build_run_command(
        self,
        par_file: str = "flash.par",
        nproc: Optional[int] = None,
        flash_exe: str = "flash4",
    ) -> str:
        """构建运行命令。

        本地 WSL: wsl -d {distro} -- bash -c "cd {work_dir} && {mpi}/bin/mpirun -np {n} ./flash4"
        超算: 由 build_sbatch_script 生成
        """
        nproc = nproc or self.default_nproc

        if self.is_local():
            mpi_run = f"{self.mpi_path}/bin/mpirun -np {nproc}"
            return (
                f'wsl -d {self.wsl_distro} -- bash -c "'
                f"source {self.flash_home}/FLASH_env.sh 2>/dev/null; "
                f"cd $(dirname {par_file}) && {mpi_run} ./{flash_exe} 2>&1"
                f'"'
            )
        else:
            # 超算模式: 返回 sbatch 提交命令
            return f"sbatch {par_file.replace('.par', '_job.sh')}"

    def build_sbatch_script(
        self,
        par_file: str = "flash.par",
        job_name: str = "FLASH",
        nproc: Optional[int] = None,
        nodes: Optional[int] = None,
        ppn: int = 32,
        walltime: Optional[str] = None,
        flash_exe: str = "flash4",
    ) -> str:
        """生成 SLURM/SBATCH 提交脚本内容。

        仅适用于 ssh_slurm 类型环境。
        """
        if self.is_local():
            return "# 本地环境无需 SBATCH 脚本，请直接使用 build_run_command()"

        nproc = nproc or self.default_nproc
        walltime = walltime or self.default_walltime
        nodes = nodes or max(1, nproc // ppn)

        # 构建 FLASH 环境变量脚本
        env_script = f"""#!/bin/bash
# FLASH environment
export FLASH_HOME={self.remote_flash_home}
export MPI_HOME={self.mpi_path}
export HDF5_HOME={self.hdf5_path}
export HYPRE_HOME={self.hypre_path}
export PATH=$MPI_HOME/bin:$HDF5_HOME/bin:$PATH
export LD_LIBRARY_PATH=$MPI_HOME/lib:$HDF5_HOME/lib:$HYPRE_HOME/lib:$LD_LIBRARY_PATH
"""

        sbatch_header = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node={ppn}
#SBATCH --time={walltime}"""

        if self.slurm_partition:
            sbatch_header += f"\n#SBATCH --partition={self.slurm_partition}"
        if self.slurm_account:
            sbatch_header += f"\n#SBATCH --account={self.slurm_account}"

        run_script = f"""
# Source FLASH environment
source {self.remote_flash_home}/FLASH_env.sh 2>/dev/null || echo "FLASH_env.sh not found, using defaults"

# Run FLASH
cd {self.remote_work_dir}
{self.mpi_path}/bin/mpirun -np {nproc} {self.remote_flash_home}/object/{flash_exe}
"""

        return sbatch_header + run_script

    def __repr__(self) -> str:
        type_str = "LOCAL(WSL)" if self.is_local() else f"SSH({self.ssh_credential})"
        return f"FlashEnvironment({self.name!r}, {type_str})"

# ── 资源配置集成 ──────────────────────────────────

    def get_resource_config(self):
        """获取资源配置管理器 (懒加载)。"""
        if self._resource_config is None:
            try:
                from flash.flash_run.env.resource_config import get_resource_config
                self._resource_config = get_resource_config()
            except ImportError:
                self._resource_config = None
        return self._resource_config

    def get_effective_nproc(self, dimension: int = 1, total_cpus: Optional[int] = None) -> int:
        """根据资源配置计算有效的进程数。

        Args:
            dimension: 仿真维度 (1, 2, 3)
            total_cpus: 总 CPU 核心数 (None = 自动探测)

        Returns:
            每个作业建议使用的进程数
        """
        rc = self.get_resource_config()
        if rc is not None:
            return rc.get_effective_nproc(
                dimension=dimension,
                is_hpc=self.is_remote(),
                total_cpus=total_cpus,
            )
        # 回退: 使用默认值
        return self.default_nproc

    def get_mem_per_job_gb(self, dimension: int = 1, detected_total_gb: Optional[float] = None) -> float:
        """根据资源配置计算每个作业的内存 (GB)。

        仅对超算模式有效:
            mem_per_job = (总内存 * max_cpu_percent / 100) / max_parallel

        Args:
            dimension: 仿真维度 (1, 2, 3)
            detected_total_gb: 从系统探测到的总内存

        Returns:
            每个作业内存 (GB)，本地模式返回 0
        """
        if self.is_local():
            return 0.0

        rc = self.get_resource_config()
        if rc is not None:
            cfg = rc.get_hpc_config(dimension)
            return cfg.get_mem_per_job_gb(detected_total_gb)

        return 0.0


# ── FlashEnvironment end ──


class FlashEnvManager:
    """FLASH 运行环境管理器。

    管理 FlashEnvironment 实例，支持:
      - 多环境注册/删除/切换
      - 活跃环境标记
      - 从凭据自动创建环境
      - 环境持久化存储
    """

    def __init__(self):
        self._envs: Dict[str, FlashEnvironment] = {}
        self._active: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """从磁盘加载环境配置。"""
        if not ENV_CONFIG_FILE.exists():
            self._init_defaults()
            self._save()
            return

        try:
            with open(ENV_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)

            for name, env_data in data.get("environments", {}).items():
                self._envs[name] = FlashEnvironment.from_dict(env_data)

            self._active = data.get("active")

            # 确保 active 指向有效环境
            if self._active and self._active not in self._envs:
                self._active = None
            if not self._active and self._envs:
                self._active = next(iter(self._envs))

        except (json.JSONDecodeError, KeyError):
            self._init_defaults()
            self._save()

        # 从凭据系统同步 user_name
        self._sync_user_name()

    def _sync_user_name(self) -> None:
        """从凭据系统同步 user_name。"""
        try:
            from flash._core.credentials import get_user_name
            cred_user = get_user_name()
            # 同步到所有环境
            changed = False
            for env in self._envs.values():
                if env.user_name != cred_user:
                    env.user_name = cred_user
                    changed = True
            if changed:
                self._save()
        except ImportError:
            pass

    def _save(self) -> None:
        """持久化存储到磁盘。"""
        ENV_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "active": self._active,
            "environments": {
                name: env.to_dict() for name, env in self._envs.items()
            },
        }
        tmp = ENV_CONFIG_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(ENV_CONFIG_FILE)

    def _init_defaults(self) -> None:
        """初始化默认环境配置。"""
        # 本地 WSL 环境（flash_home 自动从 user_name 构造，默认从 credentials 读取）
        self._envs["local_wsl"] = FlashEnvironment(
            name="local_wsl",
            env_type="local_wsl",
            description="本地 WSL Ubuntu (FLASH 4.8)",
            # flash_home 不传 → 自动设为 ~/{user_name}/FLASH/FLASH4.8（由 credentials 决定）
            mpi_path="/usr/local/mpich",
            hdf5_path="/usr/local/hdf5",
            hypre_path="/usr/local/hypre",
            default_nproc=4,
        )

        # 超算 NC-E 环境（remote_* 自动从 user_name 构造，默认从 credentials 读取）
        self._envs["supercomputer_nc_e"] = FlashEnvironment(
            name="supercomputer_nc_e",
            env_type="ssh_slurm",
            description="ParaCloud 并行云 NC-E (中卫)",
            ssh_credential="flash_ssh",
            # remote_flash_home / remote_work_dir 不传 → 自动用 ~/{user_name}/...
            mpi_path="/usr/local/mpich",
            hdf5_path="/usr/local/hdf5",
            hypre_path="/usr/local/hypre",
            default_nproc=32,
            default_walltime="02:00:00",
        )

        # 超算 BSCC-T6 环境
        self._envs["supercomputer_bscc_t6"] = FlashEnvironment(
            name="supercomputer_bscc_t6",
            env_type="ssh_slurm",
            description="ParaCloud 并行云 BSCC-T6 (中卫)",
            ssh_credential="flash_ssh_2",
            # remote_flash_home / remote_work_dir 不传 → 自动用 ~/{user_name}/...
            mpi_path="/usr/local/mpich",
            hdf5_path="/usr/local/hdf5",
            hypre_path="/usr/local/hypre",
            default_nproc=32,
            default_walltime="02:00:00",
        )

        self._active = "local_wsl"

    # ── 公开 API ──────────────────────────────────────

    def list_environments(self) -> List[FlashEnvironment]:
        """列出所有注册的环境。"""
        return list(self._envs.values())

    def get(self, name: str) -> Optional[FlashEnvironment]:
        """按名称获取环境。"""
        return self._envs.get(name)

    def get_active(self) -> Optional[FlashEnvironment]:
        """获取当前活跃环境。"""
        if self._active:
            return self._envs.get(self._active)
        return None

    def set_active(self, name: str) -> None:
        """设置活跃环境。"""
        if name not in self._envs:
            raise ValueError(f"环境 '{name}' 不存在。可用: {list(self._envs.keys())}")
        self._active = name
        self._save()

    def add(self, env: FlashEnvironment) -> None:
        """添加新环境。"""
        self._envs[env.name] = env
        self._save()

    def remove(self, name: str) -> bool:
        """删除环境。"""
        if name not in self._envs:
            return False
        del self._envs[name]
        if self._active == name:
            self._active = next(iter(self._envs)) if self._envs else None
        self._save()
        return True

    def auto_create_from_credentials(self) -> List[str]:
        """从本地凭据库自动创建环境。

        扫描所有 flash_ssh 开头的凭据，为每个创建一个环境。
        返回新创建的环境名列表。

        remote_flash_home / remote_work_dir 不传，
        自动从 user_name（默认从 credentials 读取）构造路径。
        """
        from flash._core.credentials import load_all_ssh_credentials
        
        all_ssh = load_all_ssh_credentials()

        created = []
        for cred_name, cred_data in all_ssh.items():
            env_name = f"ssh_{cred_name}"
            if env_name in self._envs:
                continue

            # 从凭据推断环境名称 (使用 RouteTester)
            try:
                from flash.flash_run.remote.route_tester import RouteTester
                label = RouteTester.account_label(cred_name, cred_data)
                desc = f"SSH {label}"
            except ImportError:
                rk = cred_data.get("route_key", cred_name)
                desc = f"SSH {rk}"

            env = FlashEnvironment(
                name=env_name,
                env_type="ssh_slurm",
                description=desc,
                ssh_credential=cred_name,
                # remote_flash_home / remote_work_dir 不传
                # → 自动用 ~/{user_name}/FLASH/FLASH4.8 和 ~/{user_name}/FLASH/run
                default_nproc=32,
                default_walltime="02:00:00",
            )
            self._envs[env_name] = env
            created.append(env_name)

        if created:
            self._save()
        return created

    def summary(self) -> str:
        """生成环境摘要文本。"""
        lines = ["FLASH 仿真环境管理", "=" * 50]
        for env in self._envs.values():
            active_mark = " <-- 当前" if env.name == self._active else ""
            type_str = "LOCAL(WSL)" if env.is_local() else f"SSH({env.ssh_credential})"
            lines.append(f"  [{env.name}] {type_str}{active_mark}")
            lines.append(f"    描述: {env.description}")
            if env.is_local():
                lines.append(f"    FLASH: {env.flash_home}")
            else:
                lines.append(f"    远程 FLASH: {env.remote_flash_home}")
                lines.append(f"    工作目录: {env.remote_work_dir}")
            lines.append("")
        return "\n".join(lines)


# ── 全局单例 ──────────────────────────────────────

_manager: Optional[FlashEnvManager] = None


def get_env_manager() -> FlashEnvManager:
    """获取全局 FlashEnvManager 单例。"""
    global _manager
    if _manager is None:
        _manager = FlashEnvManager()
    return _manager
