# FLASH 环境配置管理

管理 FLASH 仿真在不同计算环境中的配置。

## 功能

- **多环境支持**: 本地 WSL、远程超算 SSH/SLURM
- **维度感知**: 根据仿真维度 (1D/2D/3D) 自动调整资源配置
- **自动同步**: 从凭据系统自动同步用户名
- **持久化存储**: 配置保存在 `~/.physimx/flash_envs/environments.json`

## 主要类

### FlashEnvironment

单个 FLASH 运行环境配置。

**属性**:
- `name`: 环境名称 (唯一标识)
- `env_type`: 环境类型 (`"local_wsl"` | `"ssh_slurm"`)
- `description`: 环境描述
- `user_name`: 用户名称 (用于构造路径前缀)
- `flash_home`: FLASH 安装路径 (本地)
- `remote_flash_home`: FLASH 安装路径 (远程)
- `remote_work_dir`: 工作目录 (远程)
- `ssh_credential`: 凭据名称
- `default_nproc`: 默认进程数
- `default_walltime`: 默认墙钟时间
- `bundle_input_files`: 是否打包输入文件

**方法**:
- `build_run_command(par_file, nproc, flash_exe)`: 构建运行命令
- `build_sbatch_script(...)`: 生成 SLURM/SBATCH 提交脚本
- `get_effective_nproc(dimension, total_cpus)`: 计算有效进程数
- `get_mem_per_job_gb(dimension, detected_total_gb)`: 计算每作业内存
- `to_dict()`: 序列化为字典
- `from_dict(d)`: 从字典反序列化

### FlashEnvManager

FLASH 运行环境管理器 (单例模式)。

**方法**:
- `list_environments()`: 列出所有注册的环境
- `get(name)`: 按名称获取环境
- `get_active()`: 获取当前活跃环境
- `set_active(name)`: 设置活跃环境
- `add(env)`: 添加新环境
- `remove(name)`: 删除环境
- `auto_create_from_credentials()`: 从凭据自动创建环境
- `summary()`: 生成环境摘要文本

### FlashResourceConfig

FLASH 仿真资源配置管理器 (单例模式)。

按维度和计算环境管理 CPU/内存/并行数配置。

**配置维度**:
- **本地 WSL**:
  - 1D: 80% CPU, 3 并行
  - 2D: 80% CPU, 2 并行
  - 3D: 80% CPU, 1 并行

- **超算**:
  - 1D: 95% CPU, 4 并行, 自动内存分配
  - 2D: 95% CPU, 3 并行, 自动内存分配
  - 3D: 95% CPU, 2 并行, 自动内存分配

**方法**:
- `get_local_config(dimension)`: 获取本地 WSL 配置
- `set_local_config(dimension, ...)`: 修改本地 WSL 配置
- `get_hpc_config(dimension)`: 获取超算配置
- `set_hpc_config(dimension, ...)`: 修改超算配置
- `get_effective_nproc(dimension, is_hpc, total_cpus)`: 计算有效进程数
- `get_resource_config()`: 获取全局单例
- `reset_to_defaults()`: 重置为默认配置

## 用法

### 基本用法

```python
from flash.flash_run.env import FlashEnvManager, get_env_manager
from flash.flash_run.env.resource_config import FlashResourceConfig, get_resource_config

# 获取环境管理器 (单例)
mgr = get_env_manager()

# 列出所有环境
for env in mgr.list_environments():
    print(f"{env.name}: {env.description}")

# 切换环境
mgr.set_active("supercomputer_nc_e")

# 获取当前环境
env = mgr.get_active()
print(f"当前环境: {env.name} ({env.env_type})")

# 生成运行命令
cmd = env.build_run_command(par_file="flash.par", nproc=4)
print(cmd)

# 获取资源配置
rc = get_resource_config()
print(rc.summary())
```

### 添加新环境

```python
from flash.flash_run.env import FlashEnvironment, FlashEnvManager

mgr = FlashEnvManager()

# 创建新环境
new_env = FlashEnvironment(
    name="my_hpc",
    env_type="ssh_slurm",
    description="我的超算环境",
    ssh_credential="my_ssh",
    remote_flash_home="~/my_flash/FLASH4.8",
    remote_work_dir="~/my_flash/run",
    default_nproc=64,
    default_walltime="04:00:00",
)

# 添加到管理器
mgr.add(new_env)
print(f"已添加环境: {new_env.name}")
```

### 修改资源配置

```python
from flash.flash_run.env.resource_config import get_resource_config

rc = get_resource_config()

# 修改本地 1D 配置
rc.set_local_config(
    dimension=1,
    max_cpu_percent=90,  # 使用 90% CPU
    max_parallel=2,        # 最多 2 个并行
)

# 修改超算 2D 配置
rc.set_hpc_config(
    dimension=2,
    max_cpu_percent=100,  # 使用 100% CPU
    max_parallel=2,         # 最多 2 个并行
)

print(rc.summary())
```

### 从凭据自动创建环境

```python
from flash.flash_run.env import FlashEnvManager

mgr = FlashEnvManager()

# 扫描所有 flash_ssh 开头的凭据，自动创建环境
created = mgr.auto_create_from_credentials()
print(f"自动创建了 {len(created)} 个环境: {created}")
```

## 配置存储

环境配置: `~/.physimx/flash_envs/environments.json`

```json
{
  "active": "local_wsl",
  "environments": {
    "local_wsl": {
      "name": "local_wsl",
      "env_type": "local_wsl",
      "description": "本地 WSL Ubuntu (FLASH 4.8)",
      "user_name": "hello",
      "flash_home": "~/hello/FLASH/FLASH4.8",
      "mpi_path": "/usr/local/mpich",
      ...
    },
    "supercomputer_nc_e": {
      "name": "supercomputer_nc_e",
      "env_type": "ssh_slurm",
      "description": "ParaCloud 并行云 NC-E (中卫)",
      "ssh_credential": "flash_ssh",
      "remote_flash_home": "~/scfa2696/FLASH/FLASH4.8",
      ...
    }
  }
}
```

资源配置: `~/.physimx/flash_resource/resource_config.json`

```json
{
  "local": {
    "1d": {"max_cpu_percent": 80, "max_parallel": 3},
    "2d": {"max_cpu_percent": 80, "max_parallel": 2},
    "3d": {"max_cpu_percent": 80, "max_parallel": 1}
  },
  "hpc": {
    "1d": {"max_cpu_percent": 95, "max_parallel": 4, "mem_per_job_auto": true},
    "2d": {"max_cpu_percent": 95, "max_parallel": 3, "mem_per_job_auto": true},
    "3d": {"max_cpu_percent": 95, "max_parallel": 2, "mem_per_job_auto": true}
  }
}
```

## 命令行用法

### 查看/修改资源配置

```bash
# 查看所有配置
python -m physimx_sim.flash.flash_run.env.resource_config

# 查看本地 1D 配置
python -m physimx_sim.flash.flash_run.env.resource_config local 1

# 修改本地 1D 配置 (CPU 90%, 2 并行)
python -m physimx_sim.flash.flash_run.env.resource_config local 1 90 2

# 查看超算 2D 配置
python -m physimx_sim.flash.flash_run.env.resource_config hpc 2

# 重置为默认配置
python -m physimx_sim.flash.flash_run.env.resource_config reset
```

## 预定义环境

安装后自动创建 3 个默认环境:

1. **local_wsl**: 本地 WSL Ubuntu
   - flash_home: `~/hello/FLASH/FLASH4.8`
   - 默认 4 进程

2. **supercomputer_nc_e**: ParaCloud NC-E (中卫)
   - 凭据: `flash_ssh`
   - 默认 32 进程, 2 小时墙钟时间

3. **supercomputer_bscc_t6**: ParaCloud BSCC-T6 (中卫)
   - 凭据: `flash_ssh_2`
   - 默认 32 进程, 2 小时墙钟时间

## 注意事项

1. **user_name 自动同步**: 环境管理器会自动从凭据系统同步 `user_name`，确保路径正确。

2. **路径构造**: 如果创建环境时不传 `flash_home` / `remote_flash_home` / `remote_work_dir`，会自动从 `user_name` 构造:
   - `flash_home`: `~/${user_name}/FLASH/FLASH4.8`
   - `remote_flash_home`: `~/${user_name}/FLASH/FLASH4.8`
   - `remote_work_dir`: `~/${user_name}/FLASH/run`

3. **资源配置维度**: 修改资源配置后，运行命令时会自动使用新配置。

4. **超算内存计算**: 如果 `mem_per_job_auto=True`，每作业内存会自动计算:
   ```
   mem_per_job = (总内存 * max_cpu_percent / 100) / max_parallel
   ```

## 依赖

- `flash._core.credentials`: 密码管理
- `paramiko`: SSH/SFTP (仅远程环境)
