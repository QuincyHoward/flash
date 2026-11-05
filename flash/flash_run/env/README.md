# flash_run/env — 环境与资源配置

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

## 1. 职责定位

FLASH 仿真的环境与资源参数管理：**装置参数**（超算分区/模块/库路径）、**资源档位**（装置判档×维度→核数/内存）、**venv 路径**（三平台唯一事实源）、**多环境管理**（SSH/WSL 环境切换与运行命令生成）。配置落盘 `~/.physimx/`，仓库不携带用户配置。

## 2. 模块清单

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `__init__.py` | 13 | 只导出 `FlashEnvironment`、`FlashResourceConfig`；`FlashEnvManager`/`get_env_manager` 需从 `env_manager` 模块导入 | — |
| `devices.py` | 276 | **超算装置参数唯一事实源**（分区/模块/库路径），与场景无关；新代码禁止再硬编码装置参数 | `device_default`、`credential_name`、`intel_mpi_lib_dirs`、`runtime_lib_dirs`、`main()` |
| `resource_config.py` | 666 | 资源配置管理器：`classify_device` 装置判档 × 维度 → 核数/内存/并行档位 | `FlashResourceConfig`、`classify_device`、`get_resource_config`、`main()` |
| `env_manager.py` | 536 | 多环境管理（列出/切换/当前环境/生成运行命令） | `FlashEnvironment`、`FlashEnvManager`、`get_env_manager` |
| `venv_paths.py` | 166 | 三平台 venv 路径唯一事实源（2026-10-24 解耦改造） | `repo_root`、`platform_tag` |

## 3. 资源档位（现状）

`classify_device()` 将运行机器判为 **laptop / desktop / hpc** 三档；配置类为 `LocalDimensionConfig` / `HPCDimensionConfig`（基类 `DeviceDimensionConfig`）。历史版本为「本地/超算」二分（本地 1D 80%·3并行、超算 1D 95%·4并行等，代码中 `get_local_config`/`get_hpc_config` 仍可用），现按档位给出更细的核数/内存建议；`FlashResourceConfig.get_effective_nproc(dimension, is_hpc, total_cpus)` 为有效进程数统一计算入口。

## 4. 快速上手

```bash
python -m flash.flash_run.env.resource_config    # 查看当前装置判档与资源配置
```

```python
# env/__init__.py 只导出这两个；FlashEnvManager 需从 env_manager 导入
from flash.flash_run.env import FlashEnvironment, FlashResourceConfig, get_resource_config
from flash.flash_run.env.env_manager import FlashEnvManager, get_env_manager

mgr = get_env_manager()                     # 单例
for env in mgr.list_environments():
    print(f"{env.name}: {env.description}")
mgr.set_active("supercomputer_nc_e")
env = mgr.get_active()
cmd = env.build_run_command(par_file="flash.par", nproc=4)

rc = get_resource_config()
print(rc.summary())
```

### 添加新环境

```python
new_env = FlashEnvironment(
    name="my_hpc",
    env_type="ssh_slurm",
    description="我的超算环境",
    ssh_credential="my_ssh",                 # 凭据键名（见 _core/credentials）
    remote_flash_home="~/my_flash/FLASH4.8",
    remote_work_dir="~/my_flash/run",
    default_nproc=64,
    default_walltime="04:00:00",
)
mgr.add_environment(new_env)
```

### FlashEnvironment 主要属性/方法

属性：`name`（唯一标识）、`env_type`（`"local_wsl"` | `"ssh_slurm"`）、`user_name`（路径前缀，**运行期解析**）、`flash_home`/`remote_flash_home`/`remote_work_dir`、`ssh_credential`、`default_nproc`、`default_walltime`。
方法：`build_run_command(par_file, nproc, flash_exe)`、`build_sbatch_script(...)`、`get_effective_nproc(dimension, total_cpus)`、`get_mem_per_job_gb(...)`。

### FlashEnvManager 主要方法

`list_environments()` / `get(name)` / `get_active()` / `set_active(name)` / `add(env)` / `remove(name)` / `auto_create_from_credentials()` / `summary()`。

## 5. 配置存储

| 内容 | 位置 |
|---|---|
| 环境配置 | `~/.physimx/flash_envs/environments.json` |
| 资源配置 | `~/.physimx/flash_resource/resource_config.json` |

## 6. 导航

上级：[../README.md](../README.md)（含工程铁律） · 相邻：[../remote/README.md](../remote/README.md)、[../modes/README.md](../modes/README.md)
