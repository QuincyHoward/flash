# gen_shell_script — FLASH 运行脚本生成器说明文档

## 概述

`gen_shell_script` 子包用于生成 FLASH 仿真的运行脚本（shell脚本或batch脚本）。这些脚本自动化编译和运行流程，支持本地和HPC环境。

**生成器类型**: 资源配置驱动
**配置文件**: `resource_config.json`
**输出文件**: `run_flash.sh`, `run_flash.bat`, `submit_flash.slurm`

## 生成器 API

### 类: ShellScriptGenerator

**位置**: `gen_shell_script/generator.py`

### 主要方法

#### generate(sim_path, dimension, platform, ...)

生成运行脚本。

```python
from gen_shell_script import ShellScriptGenerator

generator = ShellScriptGenerator()

# 生成本地运行脚本
script = generator.generate(
    sim_path="QC/LaserSlab1d_new",
    dimension=1,
    platform="local",
)

# 生成HPC提交脚本
script = generator.generate(
    sim_path="QC/LaserSlab1d_new",
    dimension=2,
    platform="hpc/scfa2696",  # 中卫HPC
)
```

#### save(output_path, ...)

保存脚本文件。

```python
output_path = generator.save(
    "path/to/run_flash.sh",
    sim_path="QC/LaserSlab1d_new",
    dimension=1,
    platform="local",
)
```

## 资源配置

`resource_config.json` 文件定义不同平台和维度的资源配置：

```json
{
  "local": {
    "wsl_ubuntu22": {
      "1d": {"nprocs": 4, "memory_mb": 4096},
      "2d": {"nprocs": 8, "memory_mb": 8192},
      "3d": {"nprocs": 16, "memory_mb": 16384}
    }
  },
  "hpc": {
    "scfa2696": {
      "1d": {"nprocs": 48, "memory_mb": 196608},
      "2d": {"nprocs": 96, "memory_mb": 393216}
    }
  }
}
```

## 使用示例

### 示例 1: 生成本地运行脚本

```python
from gen_shell_script import ShellScriptGenerator

generator = ShellScriptGenerator()
generator.save(
    "run_flash.sh",
    sim_path="QC/LaserSlab1d_new",
    dimension=1,
    platform="local",
)
```

### 示例 2: 生成HPC提交脚本

```python
generator.save(
    "submit_flash.slurm",
    sim_path="QC/LaserSlab2d_new",
    dimension=2,
    platform="hpc/scfa2696",
)
```

## 脚本执行流程

生成的脚本通常执行以下步骤：

1. 检查编译环境（FLASH路径、编译器）
2. （可选）运行 `./setup` 配置仿真
3. 运行 `make` 编译
4. 复制输入文件（`.par`, `.cn4`）
5. 运行仿真（`mpirun` 或 `srun`）
6. 收集输出文件

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
