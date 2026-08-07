"""
FLASH 运行脚本生成器 — ShellScriptGenerator
═════════════════════════════════════════

为 3 个平台生成可执行脚本，支持从零开始的完整 FLASH 流程:
  1. Setup (./setup ...)
  2. Compile (make -j)
  3. Copy input files (.par, .cn4)
  4. Run (mpirun/srun)
  5. Save output

资源配置:
  根据 resource_config.json 中的维度和平台配置，
  自动设置 nprocs、SLURM 内存等参数。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ShellScriptGenerator:
    """FLASH 运行脚本生成器。

    生成的脚本执行完整流程: 编译环境检查 → (可选) Setup + Make →
    复制输入文件 → 运行仿真 → 收集输出。

    支持基于 dimension (1d/2d/3d) 和 platform (local/hpc)
    自适应加载 resource_config.json 中的资源配置。
    """

    # 配置文件路径 (与 generator.py 同目录)
    _RESOURCE_CONFIG_PATH = Path(__file__).parent / "resource_config.json"

    # 默认 setup 命令模板 (1D LaserSlab)
    DEFAULT_SETUP_CMD = (
        "./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio "
        "species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    )
    #示意的setup指令
    CUSTOM_SETUP_CMD = (
"""./setup -auto LaserSlab \
-1d +cartesian -nxb=16 \
-maxblocks=1024 \
species=cham,targ,samp,shld \
+mgd mgd_meshgroups=10 \
ed_maxPulseSections=300 \
+hdf5typeio +mtmmmt +laser +uhd3t \
-objdir="$build_dir" \
-parfile="$parfile"
"""
    )

    ## ── 资源加载 ────────────────────────────────────

    @classmethod
    def load_resource_config(cls) -> Dict[str, Any]:
        """从 resource_config.json 加载完整资源配置。

        Returns:
            解析后的完整配置字典
        """
        path = cls._RESOURCE_CONFIG_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"resource_config.json 不存在: {path}"
            )
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _resolve_env(
        cls, full_config: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """解析 platform 字符串并返回对应环境的资源配置。

        resource_config.json 结构:
          {
            "local": { "wsl_ubuntu22": { "1d": {...}, "2d": {...}, ... } },
            "hpc":   { "scfa2696": {...}, "sch0348": {...} }
          }

        platform 格式:
          - "hpc/scfa2696"  → group="hpc", env="scfa2696" → 精确匹配
          - "local"         → group="local", 取第一个 env
          - "hpc"           → group="hpc",   取第一个 env

        Args:
            full_config: load_resource_config() 返回的完整配置
            platform:    "group/env" 或 "group" 格式

        Returns:
            对应环境的完整字典 (含 node_mem_total_gb, 1d, 2d, 3d 等)
        """
        # 拆分 group 和 env
        parts = platform.split("/", 1)
        group = parts[0]
        env = parts[1] if len(parts) > 1 else None

        res_group = full_config.get(group, {})
        if not res_group:
            return {}

        if env:
            # 精确匹配环境
            return res_group.get(env, {})
        else:
            # 取该 group 下的第一个环境
            for key in sorted(res_group.keys()):
                # 跳过非字典键 (如 description)
                if isinstance(res_group[key], dict):
                    return res_group.get(key, {})
            return {}

    @classmethod
    def get_dimension_config(
        cls,
        dimension: int = 1,
        platform: str = "local",
    ) -> Dict[str, Any]:
        """获取指定维度和平台的资源配置项。

        Args:
            dimension: 仿真维度 1/2/3
            platform: 平台标识 "local" / "hpc" / "hpc/scfa2696" / "local/wsl_ubuntu22"

        Returns:
            该维度的资源配置字典 (含 max_cpu_percent, max_parallel 等)
        """
        full = cls.load_resource_config()
        res_env = cls._resolve_env(full, platform)

        dim_key = f"{dimension}d"
        dim_cfg = res_env.get(dim_key, {})
        result = dict(dim_cfg)
        # 注入环境级平台属性 (如 node_mem_total_gb, node_cores, slurm_partition)
        for k, v in res_env.items():
            if not k.endswith("d") and k != "description":
                result[k] = v
        return result

    # ── 静态辅助方法 ─────────────────────────────────

    @staticmethod
    def build_setup_cmd(
        sim_path: str = "LaserSlab",
        objdir: str = "object_1d",
        parfile: str = "laserslab.par",
        flags: str = "-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
    ) -> str:
        """构建完整的 setup 命令字符串 (含 -objdir 和 -parfile)。

        FLASH 语法说明:
          -objdir=<path>   编译输出目录
          -parfile=<name>  默认运行时参数文件名

        Args:
            sim_path: 仿真路径 (如 LaserSlab)
            objdir: 对象目录路径 (如 object)
            parfile: .par 文件名 (用于 -parfile=<name>)
            flags: 其他 setup 标志

        Returns:
            完整的 setup 命令
        """
        return f"./setup -auto {sim_path} {flags} -objdir={objdir} -parfile={parfile}"

    @staticmethod
    def extract_sim_path(setup_cmd: str) -> str:
        """从 setup 命令中提取 -auto 后的仿真路径。"""
        import re
        m = re.search(r'-auto\s+(\S+)', setup_cmd)
        if m:
            return m.group(1)
        return "LaserSlab"

    @staticmethod
    def extract_objdir(setup_cmd: str, default: str = "object_1d") -> str:
        """从 setup 命令中提取 -objdir= 后的值。"""
        import re
        m = re.search(r'-objdir=(\S+)', setup_cmd)
        if m:
            return m.group(1)
        return default

    # ── 初始化 ──────────────────────────────────────

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化 ShellScriptGenerator。

        支持以下新增的配置键:
          - dimension: int (1/2/3, 默认 1), 用于从 resource_config.json 自动配置资源
          - platform: str ("local"|"hpc", 默认 "local"), 平台类型
          - slurm_mem_gb: float (默认 None), 显式指定 SLURM 内存 (GB),
                          为 None 时根据 resource_config.json 自动计算

        Args:
            config: 可选的自定义配置字典，覆盖默认值
        """
        defaults = {
            "wsl_distro": "Ubuntu-22.04",
            "flash_home": "$HOME/FLASH/FLASH4.8",  # 提供 sim_user_dir 时会在下方自动推导为 $HOME/{sim_user_dir}/FLASH/FLASH4.8
            "object_dir": "object_1d",
            "flash_exe": "flash4",
            "nprocs": 1,
            "par_file": "laserslab.par",
            "sim_user_dir": "default",
            "sim_path": "LaserSlab",
            "setup_cmd": self.DEFAULT_SETUP_CMD,
            "mpi_runner": "mpirun",
            "build_cores": 4,
            # 新增: 维度与平台
            "dimension": 1,
            "platform": "local",
            # SLURM
            "slurm_partition": "v5_192",  # scfa2696账号“v5_192队列: 单节点48核192G内存”;sch0348账号“v6_384队列：单节点96核384G内存”
            "slurm_nodes": 1,
            "slurm_ntasks_per_node": 32,
            "slurm_ntasks": 4,  # 实际 MPI 任务数, 由 resource_config 的 ntasks_per_job 覆盖
            "slurm_walltime": "01:00:00",
            "slurm_job_name": "FLASH_batch",
            "slurm_account": "",
            "slurm_email": "",
            "slurm_gpus": 0,
            "slurm_modules": ["mpich/3.2-gcc9.3", "hdf5/1.8.18"],
            # 内存 (GB), None 表示从 resource_config 自动计算
            "slurm_mem_gb": None,
        }
        self.config = {**defaults, **(config or {})}
        # Auto-detect sim_path & object_dir from setup_cmd if not explicitly set
        if config is None or "sim_path" not in config:
            self.config["sim_path"] = self.extract_sim_path(self.config["setup_cmd"])
        if config is None or "object_dir" not in config:
            self.config["object_dir"] = self.extract_objdir(self.config["setup_cmd"])

        # ── flash_home 自动推导 (FLASH 唯一安装路径约定: ~/{user_name}/FLASH/FLASH4.8) ──
        # 当调用方提供了 sim_user_dir (由 credentials 动态获取) 且未显式指定 flash_home 时,
        # 自动生成 "$HOME/{sim_user_dir}/FLASH/FLASH4.8", 保证超算/WSL 脚本指向正确安装位置。
        sud = self.config.get("sim_user_dir") or "default"
        if config is None or "flash_home" not in config:
            if sud and sud != "default":
                self.config["flash_home"] = f"$HOME/{sud}/FLASH/FLASH4.8"

        # ── 从 resource_config.json 加载并应用资源配置 ──
        self._resource_config = self.load_resource_config()
        self._apply_resource_defaults()

    def _apply_resource_defaults(self) -> None:
        """根据 dimension 和 platform 从 resource_config 自动应用默认值。

        规则:
          - local:    保存当前资源配置用于外部查询, 不自动改写 nprocs
          - hpc:      自动计算:
                       - slurm_ntasks = ntasks_per_job 或 node_cores * max_cpu_percent / 100 / max_parallel
                       - slurm_partition / slurm_modules 从资源配置自动覆盖
                       - (不设 --mem: select/linear 下整节点分配, 内存限制无效)
          - 用户显式传入的值不被覆盖
        """
        try:
            dim_key = f"{self.config['dimension']}d"
            platform = self.config.get("platform", "local")

            res = self._resource_config
            # 使用 _resolve_env 处理嵌套的环境层级
            res_env = self._resolve_env(res, platform)
            res_dim = res_env.get(dim_key, {})

            # 保存当前生效的资源配置快照
            self._current_dim_resource = dict(res_dim)
            for k, v in res_env.items():
                if not k.endswith("d") and k != "description":
                    self._current_dim_resource.setdefault(k, v)

            # ── 从资源配置自动覆盖 SLURM 相关默认值 ──
            if "slurm_partition" in res_env and self.config.get("slurm_partition") is not None:
                self.config["slurm_partition"] = res_env["slurm_partition"]
            if "slurm_modules" in res_env and isinstance(res_env["slurm_modules"], list):
                self.config["slurm_modules"] = res_env["slurm_modules"]

            # ── 判断是否为 HPC 平台 ──
            is_hpc = platform.startswith("hpc")

            # ── 内存自动计算: 已禁用 (select/linear 下整节点分配, --mem 限制无效) ──
            # if is_hpc and self.config.get("slurm_mem_gb") is None:
            #     mem_gb = self._calc_hpc_mem_gb(self._current_dim_resource)
            #     if mem_gb is not None and mem_gb > 0:
            #         self.config["slurm_mem_gb"] = mem_gb

            # ── MPI 任务数自动计算 (仅 HPC) ──
            if is_hpc:
                auto_ntasks = self._calc_hpc_ntasks(self._current_dim_resource)
                if auto_ntasks is not None and auto_ntasks > 0:
                    self.config["slurm_ntasks"] = auto_ntasks
                    # 也更新旧 key 保持向后兼容
                    self.config["slurm_ntasks_per_node"] = auto_ntasks

        except Exception:
            # 资源加载失败时静默回退，确保不破坏原有行为
            self._current_dim_resource = {}

    @staticmethod
    def _calc_hpc_mem_gb(dim_resource: Dict[str, Any]) -> Optional[int]:
        """计算 HPC 单个仿真的内存分配 (GB)，返回整数。

        SLURM 的 --mem 参数不接受浮点数 (如 45.6G 会报 Invalid --mem specification)，
        因此强制取整。

        公式: node_mem_total_gb * max_cpu_percent / 100 / max_parallel
        结果取整 (int), 确保 SLURM 兼容。

        Args:
            dim_resource: 维度资源配置字典

        Returns:
            整数 GB, 无法计算时返回 None
        """
        total_mem = dim_resource.get("node_mem_total_gb")
        cpu_pct = dim_resource.get("max_cpu_percent", 95)
        max_par = dim_resource.get("max_parallel", 1)

        if not total_mem or total_mem <= 0:
            return None
        mem_auto = dim_resource.get("mem_per_job_auto", False)
        mem_explicit = dim_resource.get("mem_per_job_gb", 0.0)
        if mem_explicit and mem_explicit > 0:
            return int(mem_explicit)
        if not mem_auto:
            return None
        return int(total_mem * cpu_pct / 100.0 / max_par)

    @staticmethod
    def _calc_hpc_ntasks(dim_resource: Dict[str, Any]) -> Optional[int]:
        """计算 HPC 单作业的 MPI 任务数 (用于 #SBATCH --ntasks 和 srun -n)。

        由于 SelectType=select/linear, sbatch 作业总是分配整节点。
        --ntasks 仅控制 srun 启动的 MPI 进程数, 不影响 SLURM 分配的 CPU 数。
        建议保持与资源使用量匹配 (1D=4, 2D=12, 3D=22)。

        优先级:
          1. ntasks_per_job (显式配置，推荐)
          2. 自动公式: node_cores * max_cpu_percent / 100 / max_parallel
        结果取整 (int), 至少为 1。

        Args:
            dim_resource: 维度资源配置字典

        Returns:
            整数 MPI 任务数, 无法计算时返回 None
        """
        # 优先级 1: 显式 ntasks_per_job
        exc = dim_resource.get("ntasks_per_job")
        if exc is not None and isinstance(exc, (int, float)) and exc > 0:
            return int(exc)

        # 优先级 2: 自动公式
        node_cores = dim_resource.get("node_cores")
        cpu_pct = dim_resource.get("max_cpu_percent", 95)
        max_par = dim_resource.get("max_parallel", 1)

        if not node_cores or node_cores <= 0:
            return None
        ntasks = int(node_cores * cpu_pct / 100.0 / max_par)
        return max(ntasks, 1)

    # ── 公开属性 ────────────────────────────────────

    @property
    def resource_config(self) -> Dict[str, Any]:
        """完整的 resource_config.json 内容 (只读)。"""
        return dict(self._resource_config)

    @property
    def current_dim_resource(self) -> Dict[str, Any]:
        """当前维度/平台适用的资源配置项 (只读)。
        
        Returns:
            {
                "max_cpu_percent": 80,
                "max_parallel": 3,
                "node_mem_total_gb": 192,  # (仅 hpc)
                ...
            }
        """
        return dict(self._current_dim_resource)

    # ── Windows .bat ───────────────────────────────────

    def generate_windows_script(self, par_file: Optional[str] = None) -> str:
        """Windows .bat: 通过 WSL 执行完整 FLASH 流程。"""
        cfg = self.config
        par = par_file or cfg["par_file"]
        run_dir = "/tmp/flash_run_$(date +%s)"

        sim_setup_cmd = (
            "cd $FLASH_HOME && "
            f"SIM_SRC_DIR=\"$FLASH_HOME/source/Simulation/SimulationMain/{cfg['sim_path']}\" && "
            "mkdir -p \"$SIM_SRC_DIR\" && "
            "cp \"$SCRIPT_DIR\"/Config \"$SIM_SRC_DIR\"/ 2>/dev/null || true && "
            "cp \"$SCRIPT_DIR\"/Makefile \"$SIM_SRC_DIR\"/ 2>/dev/null || true && "
            "cp \"$SCRIPT_DIR\"/Simulation_*.F90 \"$SIM_SRC_DIR\"/ 2>/dev/null || true && "
            "cp \"$SCRIPT_DIR\"/*.cn4 \"$SIM_SRC_DIR\"/ 2>/dev/null || true && "
            f"cp \"$SCRIPT_DIR\"/$PAR_FILE \"$SIM_SRC_DIR\"/ 2>/dev/null || true && "
            "if [ ! -d \"{cfg['object_dir']}\" ]; then "
            "eval \"$SETUP_CMD\" && "
            "cd {cfg['object_dir']} && "
            "make -j$BUILD_CORES && "
            "cd $FLASH_HOME; "
            "fi && "
            f"cp \"$SCRIPT_DIR\"/$PAR_FILE {run_dir}/ && "
            f"cp \"$SCRIPT_DIR\"/*.cn4 {run_dir}/ 2>/dev/null; "
            f"cd {run_dir} && {cfg['mpi_runner']} -np $NPROCS $FLASH_HOME/{cfg['object_dir']}/{cfg['flash_exe']} -par_file $PAR_FILE && "
            "cp *.h5 *chk* *plt* \"$SCRIPT_DIR\"/output/ 2>/dev/null"
        )

        lines = [
            "@echo off",
            "setlocal enabledelayedexpansion",
            "",
            "REM FLASH Windows Terminal Run Script (Full Pipeline)",
            "REM Generated by ShellScriptGenerator",
            "",
            f"set WSL_DISTRO={cfg['wsl_distro']}",
            f"set FLASH_HOME={cfg['flash_home']}",
            f"set PAR_FILE={par}",
            f"set NPROCS={cfg['nprocs']}",
            f"set BUILD_CORES={cfg['build_cores']}",
            f"set SETUP_CMD={cfg['setup_cmd']}",
            "",
            'for /f "delims=" %%i in (\'wsl -d %WSL_DISTRO% wslpath "!CD!"\') do set WSL_DIR=%%i',
            "echo Working dir: !WSL_DIR!",
            "",
            "echo [Step 1/6] Copying source files to SimulationMain...",
            'wsl -d %WSL_DISTRO% -- bash -c \'mkdir -p "~/FLASH/FLASH4.8/source/Simulation/SimulationMain/""\'',
            "echo [Step 2/6] Setup and compile (if needed)...",
            f'wsl -d %WSL_DISTRO% -- bash -c \'{sim_setup_cmd}\'',
            "if !ERRORLEVEL! neq 0 (echo FLASH failed with error !ERRORLEVEL! & goto :end)",
            "",
            "echo [Step 3/6] Copying output back...",
            "mkdir !WSL_DIR!\\output 2>nul",
            'wsl -d %WSL_DISTRO% -- bash -c \'cp "%WSL_DIR%"/*.h5 "!WSL_DIR!\\output" 2>/dev/null; cp "!WSL_DIR!"/*chk* "!WSL_DIR!\\output" 2>/dev/null; cp "!WSL_DIR!"/*plt* "!WSL_DIR!\\output" 2>/dev/null\'',
            "echo Done! Output saved to output/",
            ":end",
            "endlocal",
        ]
        return "\n".join(lines) + "\n"

    # ── WSL .sh ────────────────────────────────────────

    def generate_wsl_script(self, par_file: Optional[str] = None) -> str:
        """WSL/Linux .sh: 从零开始完整 FLASH 流程。

        流程: setup → make → 复制输入文件 → 运行 → 收集输出
        """
        cfg = self.config
        par = par_file or cfg["par_file"]
        obj_dir = cfg["object_dir"]

        lines = [
            "#!/bin/bash",
            "# FLASH WSL/Linux Run Script (Full Pipeline)",
            "# Generated by ShellScriptGenerator",
            "#",
            "# Performs: setup → compile → copy input → run → collect output",
            "",
            'set -e',
            "",
            '# ── 加载 FLASH 编译/运行环境 (MPI + HDF5) ──',
            '# 与 FlashSimulatorEngine 保持一致: 非交互 shell 不加载 .bashrc 的 FLASH env 块,',
            '# 这里显式导出 MPICH/HDF5 路径 (找不到时静默跳过, 由系统 PATH 兜底)。',
            'if [ -d /usr/local/mpich ]; then export MPI_HOME=/usr/local/mpich; fi',
            'if [ -d /usr/local/hdf5 ]; then export HDF5_HOME=/usr/local/hdf5; export HDF5_ROOT=/usr/local/hdf5; fi',
            'if [ -d /usr/local/hypre ]; then export HYPRE_HOME=/usr/local/hypre; fi',
            'export PATH="${MPI_HOME:+$MPI_HOME/bin:}${HDF5_HOME:+$HDF5_HOME/bin:}$PATH"',
            'export LD_LIBRARY_PATH="${MPI_HOME:+$MPI_HOME/lib:}${HDF5_HOME:+$HDF5_HOME/lib:}${HYPRE_HOME:+$HYPRE_HOME/lib:}${LD_LIBRARY_PATH:-}"',
            "",
            f'FLASH_HOME="{cfg["flash_home"]}"',
            f'PAR_FILE="{par}"',
            f"NPROCS={cfg['nprocs']}",
            f'OBJ_DIR="{cfg["object_dir"]}"',
            f'FLASH_BIN="$FLASH_HOME/$OBJ_DIR/{cfg["flash_exe"]}"',
            f'SETUP_CMD="{cfg["setup_cmd"]}"',
            f"BUILD_CORES={cfg['build_cores']}",
            f'SIM_USER_DIR="{cfg["sim_user_dir"]}"',
            f'SIM_PATH="{cfg["sim_path"]}"',
            "",
            '# Determine script directory',
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'echo "=== FLASH Full Pipeline ==="',
            'echo "  FLASH_HOME:   $FLASH_HOME"',
            'echo "  Object dir:   $OBJ_DIR"',
            'echo "  Sim path:     $SIM_PATH"',
            'echo "  Par file:     $PAR_FILE"',
            'echo "  Input dir:    $SCRIPT_DIR"',
            "",
            '# ── Step 1: Check FLASH source ──',
            'echo ""',
            'echo "[1/5] Checking FLASH environment..."',
            'if [ ! -d "$FLASH_HOME" ]; then',
            '    echo "ERROR: FLASH_HOME not found: $FLASH_HOME"',
            "    exit 1",
            "fi",
            'echo "  FLASH home found: $FLASH_HOME"',
            "",
            '# ── Step 2: Copy source files to SimulationMain ──',
            'echo ""',
            'echo "[2/5] Copying source files to SimulationMain..."',
            'SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"',
            'mkdir -p "$SIM_SRC_DIR"',
            'echo "  Simulation source dir: $SIM_SRC_DIR"',
            '# Copy all FLASH setup source files (Config, Makefile, .F90)',
            'cp "$SCRIPT_DIR"/Config "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR"/Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR"/Simulation_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true',
            '# Copy data files (.cn4, .par)',
            'cp "$SCRIPT_DIR"/*.cn4 "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR/$PAR_FILE" "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'echo "  Source files ready in SimulationMain."',
            "",
            '# ── Step 3: Setup + Compile ──',
            'echo ""',
            'echo "[3/5] Setup and compiling FLASH..."',
            'cd "$FLASH_HOME"',
            "",
            'if [ -d "$OBJ_DIR" ] && [ -f "$FLASH_BIN" ]; then',
            '    echo "  Object dir exists with binary, skipping setup+make."',
            'else',
            '    echo "  Running setup..."',
            "    eval $SETUP_CMD",
            '    echo "  Setup done. Compiling..."',
            "    cd $OBJ_DIR",
            "    make -j$BUILD_CORES",
            '    echo "  Compilation done."',
            "fi",
            "",
            '# ── Step 4: Copy input files to run dir ──',
            'echo ""',
            'echo "[4/6] Copying input files to run directory..."',
            'cd "$FLASH_HOME/$OBJ_DIR"',
            'mkdir -p outputfiles',
            'cp "$SCRIPT_DIR/$PAR_FILE" ./ 2>/dev/null || true',
            'cp "$SCRIPT_DIR"/*.cn4 ./ 2>/dev/null || true',
            'echo "  Input files ready in $FLASH_HOME/$OBJ_DIR."',
            "",
            '# ── Step 5: Run FLASH ──',
            'echo ""',
            'echo "[5/6] Running FLASH simulation..."',
            f"{cfg['mpi_runner']} -np $NPROCS $FLASH_BIN -par_file $PAR_FILE 2>&1 | tee flash_run.log",
            'FLASH_EXIT=${PIPESTATUS[0]}',
            'echo "  FLASH exit code: $FLASH_EXIT"',
            "",
            '# ── Step 6: Collect output ──',
            'echo ""',
            'echo "[6/6] Collecting output files..."',
            'mkdir -p "$SCRIPT_DIR/outputfiles"',
            'cp *.h5 "$SCRIPT_DIR/outputfiles/" 2>/dev/null || true',
            'cp *chk* "$SCRIPT_DIR/outputfiles/" 2>/dev/null || true',
            'cp *plt* "$SCRIPT_DIR/outputfiles/" 2>/dev/null || true',
            'cp flash_run.log "$SCRIPT_DIR/outputfiles/" 2>/dev/null || true',
            "",
            '# Summary',
            'echo ""',
            'echo "=== Summary ==="',
            'echo "  Input files:  $SCRIPT_DIR"',
            'echo "  Output files: $SCRIPT_DIR/outputfiles/"',
            'nfiles=$(ls "$SCRIPT_DIR/outputfiles/"*.h5 2>/dev/null | wc -l)',
            'echo "  HDF5 files:   $nfiles"',
            'echo "  FLASH exit:   $FLASH_EXIT"',
            'echo "=== Done ==="',
            "",
            'exit $FLASH_EXIT',
        ]
        return "\n".join(lines) + "\n"

    # ── SLURM .slurm ──────────────────────────────────

    def generate_slurm_script(self, par_file: Optional[str] = None) -> str:
        """超算 SLURM .slurm: 完整 FLASH 流程（模块加载→setup→编译→运行）

        注意 — select/linear 调度:
          超算使用 SelectType=select/linear, 每个 sbatch 作业必然分配
          整节点 (如 48核)。--ntasks 仅控制 MPI 进程数 (srun -n),
          不影响 SLURM 分配的 CPU 数。--mem 限制在此模式下同样无效。
          因此 sbatch 头不设 --mem, --ntasks 设为合理值用于 srun。
          并发提交多个作业即可利用多节点并行执行不同变体。
        """
        cfg = self.config
        par = par_file or cfg["par_file"]
        obj_dir = cfg["object_dir"]

        # Module loading lines
        module_lines = []
        for mod in cfg.get("slurm_modules", []):
            module_lines.append(f"module load {mod}")

        # ── 确定 MPI 任务数 ──
        # 优先使用 slurm_ntasks (从 resource_config 的 ntasks_per_job 或自动公式计算)
        # 回退到旧的 slurm_ntasks_per_node, 最后回退到 1
        ntasks = (
            cfg.get("slurm_ntasks")
            or cfg.get("slurm_ntasks_per_node")
            or 1
        )

        lines = [
            "#!/bin/bash",
            f"#SBATCH --job-name={cfg['slurm_job_name']}",
            f"#SBATCH -p {cfg['slurm_partition']}",
            f"#SBATCH -N {cfg['slurm_nodes']}",
            f"#SBATCH --ntasks={ntasks}",
            f"#SBATCH --output={cfg['slurm_job_name']}_out.txt",
            f"#SBATCH --error={cfg['slurm_job_name']}_err.txt",
            "# Note: SelectType=select/linear → entire node allocated regardless of --ntasks.",
            "# --mem and --ntasks limits are advisory only; the scheduler allocates full nodes.",
        ]

        if cfg.get("slurm_account"):
            lines.append(f"#SBATCH --account={cfg['slurm_account']}")
        if cfg.get("slurm_email"):
            lines.append(f"#SBATCH --mail-user={cfg['slurm_email']}")
            lines.append("#SBATCH --mail-type=ALL")
        if cfg.get("slurm_gpus", 0) > 0:
            lines.append(f"#SBATCH --gres=gpu:{cfg['slurm_gpus']}")

        lines += [
            "",
            "set -e",
            "",
            '# ── Step 1: Load environment ──',
            'echo "[1/6] Loading environment modules..."',
            "module purge",
        ]
        lines += module_lines
        lines += [
            "",
            f'FLASH_HOME="{cfg["flash_home"]}"',
            f'PAR_FILE="{par}"',
            f'OBJ_DIR="{obj_dir}"',
            f'FLASH_BIN="$FLASH_HOME/$OBJ_DIR/{cfg["flash_exe"]}"',
            f'SETUP_CMD="{cfg["setup_cmd"]}"',
            f"BUILD_CORES={cfg['build_cores']}",
            f'SIM_USER_DIR="{cfg["sim_user_dir"]}"',
            f'SIM_PATH="{cfg["sim_path"]}"',
            "",
            '# Get script directory (uses SLURM_SUBMIT_DIR when submitted via sbatch, PWD as fallback)',
            'SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"',
            "",
            '# ── Step 2: Copy source files to SimulationMain ──',
            'echo ""',
            'echo "[2/6] Copying source files to SimulationMain..."',
            'SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"',
            'mkdir -p "$SIM_SRC_DIR"',
            'echo "  Simulation source dir: $SIM_SRC_DIR"',
            '# Copy all FLASH setup source files',
            'cp "$SCRIPT_DIR"/Config "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR"/Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR"/Simulation_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true',
            '# Copy data files (.cn4, .par)',
            'cp "$SCRIPT_DIR"/*.cn4 "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'cp "$SCRIPT_DIR/$PAR_FILE" "$SIM_SRC_DIR"/ 2>/dev/null || true',
            'echo "  Source files ready in SimulationMain."',
            "",
            '# ── Step 3: Setup + Compile ──',
            'echo ""',
            'echo "[3/6] Checking and compiling FLASH..."',
            'cd "$FLASH_HOME"',
            "",
            'if [ -d "$OBJ_DIR" ] && [ -f "$FLASH_BIN" ]; then',
            '    echo "  Binary exists, skipping setup+make."',
            'else',
            '    echo "  Running setup..."',
            "    eval $SETUP_CMD",
            '    echo "  Setup done. Compiling..."',
            "    cd $OBJ_DIR",
            "    make -j$BUILD_CORES",
            '    echo "  Compilation done."',
            "fi",
            "",
            '# ── Step 4: Copy input files to run dir ──',
            'echo ""',
            'echo "[4/6] Copying input files..."',
            'cd "$FLASH_HOME/$OBJ_DIR"',
            'cp "$SCRIPT_DIR/$PAR_FILE" ./ 2>/dev/null || echo "  WARNING: par file not in submit dir, using existing"',
            'cp "$SCRIPT_DIR"/*.cn4 ./ 2>/dev/null || true',
            'echo "  Input files ready."',
            "",
            '# ── Step 5: Run FLASH ──',
            'echo ""',
            'echo "[5/6] Running FLASH simulation (srun)..."',
            '# TOTAL_TASKS from SLURM (#SBATCH -n), or default to 4 for direct execution',
            "TOTAL_TASKS=${SLURM_NTASKS:-4}",
            f"srun -n $TOTAL_TASKS $FLASH_BIN -par_file $PAR_FILE 2>&1 | tee flash_run.log",
            'FLASH_EXIT=${PIPESTATUS[0]}',
            'echo "  FLASH exit code: $FLASH_EXIT"',
            "",
            '# ── Step 6: Collect output ──',
            'echo ""',
            'echo "[6/6] Collecting output files..."',
            'OUTPUT_DIR="$SCRIPT_DIR/outputfiles_$(date +%Y%m%d_%H%M%S)"',
            'mkdir -p "$OUTPUT_DIR"',
            'mv *.h5 *chk* *plt* flash_run.log "$OUTPUT_DIR"/ 2>/dev/null || true',
            "",
            '# Summary',
            'echo ""',
            'echo "=== Summary ==="',
            'echo "  Output dir: $OUTPUT_DIR"',
            'nfiles=$(ls "$OUTPUT_DIR"/*.h5 2>/dev/null | wc -l)',
            'echo "  HDF5 files: $nfiles"',
            'echo "  FLASH exit:  $FLASH_EXIT"',
            'echo "=== Done ==="',
            "",
            'exit $FLASH_EXIT',
        ]
        return "\n".join(lines) + "\n"

    # ── Batch SLURM (select/linear 多变体顺序执行) ─────────────────

    @staticmethod
    def generate_batch_slurm_script(
        variants: List[Dict[str, Any]],
        partition: str = "v5_192",
        total_ntasks: int = 48,
        walltime: str = "01:00:00",
        mem_gb: int = 45,
        job_name: str = "FLASH_batch",
        extras: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成批次 SLURM 脚本 — 单个作业内顺序执行多个仿真变体。

        适用于 select/linear 调度策略（整节点分配）。
        一个 sbatch 作业获得整节点后，通过顺序 srun 执行各变体。
        注意: select/linear 不支持步骤级并行，变体之间串行执行。

        Args:
            variants: [{power_factor, par_file, run_dir}, ...]
                      power_factor — 功率因子/标签（用于日志和作业步名）
                      par_file — .par 文件名
                      run_dir — 包含 .par 和 .cn4 的运行目录
            partition: SLURM 分区名
            total_ntasks: SLURM 分配的 MPI 任务总数（= 节点核数）
            walltime: 最大运行时间
            mem_gb: 内存分配 (GB)
            job_name: 作业名
            extras: 额外配置 (flash_home, modules, etc.)

        Returns:
            SLURM 脚本内容
        """
        n_variants = len(variants)
        if n_variants == 0:
            return "#!/bin/bash\necho 'No variants to run'\n"

        ntasks_per_variant = max(1, total_ntasks // n_variants)
        if extras is None:
            extras = {}
        modules = extras.get("modules", ["mpich/3.2-gcc9.3", "hdf5/1.8.18"])
        flash_home = extras.get("flash_home", "$HOME/FLASH/FLASH4.8")
        flash_exe = extras.get("flash_exe", "flash4")

        lines = [
            "#!/bin/bash",
            f"#SBATCH -J {job_name}",
            f"#SBATCH -p {partition}",
            "#SBATCH -N 1",
            f"#SBATCH --ntasks={total_ntasks}",
            f"#SBATCH --mem={mem_gb}G",
            f"#SBATCH -t {walltime}",
            f"#SBATCH --output={job_name}_out.txt",
            f"#SBATCH --error={job_name}_err.txt",
            "",
			"# Note: SelectType=select/linear → entire node allocated (48 CPUs per job).",
			"# srun steps run sequentially (select/linear does not support step-level",
			"# parallelism). Each step uses a subset of the node's cores.",
            "",
            "set -e",
            "",
            '# ── Load environment ──',
        ]
        for mod in modules:
            lines.append(f"module load {mod}")
        lines += [
            "",
            f'FLASH_HOME="{flash_home}"',
            f'FLASH_BIN="$FLASH_HOME/{flash_exe}"',
            'BASE_DIR="${SLURM_SUBMIT_DIR:-$PWD}"',
            "",
            '# ── Check FLASH binary ──',
            'if [ ! -f "$FLASH_BIN" ]; then',
            '    echo "FLASH binary not found at $FLASH_BIN"',
            '    echo "Please compile FLASH first or set the correct path"',
            '    exit 1',
            'fi',
            "",
            '# ── Run all variants sequentially (select/linear → no step-level parallelism) ──',
            f'NTASKS_PER_VARIANT={ntasks_per_variant}',
            f'N_VARIANTS={n_variants}',
            f'echo "Running {n_variants} variants sequentially, {ntasks_per_variant} cores each"',
            'VARIANT_FAILED=0',
            '',
        ]

        # Add sequential srun steps for each variant
        for i, v in enumerate(variants):
            pf = v.get("power_factor", f"variant_{i}")
            par = v.get("par_file", "laserslab.par")
            run_dir = v.get("run_dir", ".")
            step_name = f"power_{pf}"
            lines += [
                '',
                f'echo "[{i+1}/{n_variants}] Running variant: {step_name}"',
                f'cd {run_dir}',
                f'srun -n{ntasks_per_variant} --job-name={step_name}'
                f' $FLASH_BIN -par_file {par} 2>&1 | tee flash_run.log',
                f'if [ $? -ne 0 ]; then',
                f'  echo "[{i+1}/{n_variants}] WARNING: {step_name} failed, continuing"',
                f'  VARIANT_FAILED=$((VARIANT_FAILED + 1))',
                f'fi',
                f'echo "[{i+1}/{n_variants}] Done: {step_name}"',
            ]

        lines += [
            '',
            '# ── Summary ──',
            'echo "=== Summary ==="',
            f'echo "Completed: {n_variants} variants"',
            'echo "Failed: $VARIANT_FAILED"',
            'echo "=== Done ==="',
            '',
            'exit $VARIANT_FAILED',
        ]

        return "\n".join(lines) + "\n"

    # ── Save ──────────────────────────────────────────

    def save(
        self,
        output_path: Union[str, Path],
        script_type: str = "wsl",
        par_file: Optional[str] = None,
    ) -> Path:
        generators = {
            "windows": self.generate_windows_script,
            "wsl": self.generate_wsl_script,
            "slurm": self.generate_slurm_script,
        }
        gen = generators.get(script_type)
        if gen is None:
            raise ValueError(
                f"Invalid script_type: {script_type}. "
                f"Choose from: {list(generators.keys())}"
            )

        content = gen(par_file=par_file)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if script_type == "windows":
            out.write_text(content, encoding="utf-8")
        else:
            out.write_bytes(content.encode("utf-8"))

        try:
            out.chmod(0o755)
        except Exception:
            pass

        return out
