# FLASH 紧致应用构建系统

## 概述

紧致应用（Compact App）构建系统位于 `tools/scripts/setup_compact_app/`，用于从完整 FLASH 代码库中提取最小化的"迷你应用"（mini-apps），仅保留特定物理模块。

## 适用场景

- 测试特定物理过程（仅需 EOS、Hydro、Gravity 等少量单元）
- 教学和演示
- 性能分析（最小化代码规模）
- 快速原型开发

## 目录结构

```
setup_compact_app/
├── Makefile.py              # Makefile 解析/编辑
├── README                   # 使用示例
├── RELEASE-NOTES            # 发布说明
├── remove_unit_refs.py      # 单元引用移除（三阶段清理）
├── run_setup.sh             # 批量构建所有紧致应用
├── setup_compact_app.sh     # 单紧致应用构建脚本
└── user_documentation.txt   # 用户文档（217 行）
```

## 可用紧致应用

| 应用 | 说明 | 文件数 | 源码行 |
|------|------|--------|--------|
| Multigamma | 多 Gamma 核反应 | ~28 | ~6600 |
| Helmholtz | Helmholtz EOS | ~18 | ~2300 |
| Poisson3 | Poisson 求解器 | ~9 | ~1200 |
| PFFT | 并行 FFT | ~10 | ~8000 |
| IO | I/O 测试 | ~16 | ~1400 |
| GCell | GuardCell 测试 | ~12 | ~2000 |
| Sedov | Sedov 激波 | ~34 | ~7500 |

## 构建原理

### 工作流

```
setup_compact_app.sh <simulation_name> [setup_options]
```

1. 读取仿真目录中的 `UNITS_TO_DELETE_FOR_COMPACT_APP` 文件
2. 将列出的单元通过 `--kill-unit`/`--without-unit` 传递给 `./setup`
3. 执行标准 setup
4. 调用 `remove_unit_refs.py` 清理残留引用

### Makefile.py — Makefile 解析

`UnitMakefile` 类用于解析和编辑 FLASH 单元的 Makefile:

```python
from Makefile import UnitMakefile
um = UnitMakefile()
um.readFromFile("Grid", "Makefile.Grid")
um.removeObjects(["Grid_foo.o"])
um.writeToFile("Makefile.Grid")
```

**方法**:
| 方法 | 功能 |
|------|------|
| `readFromFile(unit, name)` | 解析 Makefile，提取目标和依赖 |
| `writeToFile(name)` | 写回修改后的 Makefile |
| `removeObjects(remList)` | 移除指定的 `.o` 文件及其依赖 |

### remove_unit_refs.py — 三阶段清理

**阶段 1 — Fortran 源文件清理**:
- 移除已删除单元的 `use` 声明
- 移除对已删除单元子程序的调用
- 自动添加缺失的接口引用

**阶段 2 — Makefile 依赖清理**:
- 编辑 Makefile，移除跨单元依赖
- 删除已移除单元的编译目标

**阶段 3 — 静态分析清理**:
- 基于 `getUseAndCallInfo.py` 的静态分析
- 移除所有未被调用的子程序

**用法**:
```bash
python remove_unit_refs.py <unit_file> <objdir>
```

**依赖**: `Makefile.py`, `getUseAndCallInfo.py`

## 批量构建

### run_setup.sh

一次性生成所有 FLASH 紧致应用并打包:

```bash
bash run_setup.sh
```

**输出**: `compact_apps_r<revision>.tar.gz`

**流程**: 对每个紧致应用运行 `setup_compact_app.sh` → 移动 → 压缩。

## 详细用法示例

### 创建单个紧致应用

```bash
# 创建 Multigamma 紧致应用
./setup_compact_app.sh unitTest/Eos/Multigamma -auto +nofbs -3d -portable

# 创建 GuardCell 紧致应用
./setup_compact_app.sh unitTest/Grid/GuardCell -auto +nofbs -3d

# 创建 Sedov 紧致应用
./setup_compact_app.sh unitTest/Hydro/Sedov -auto +nofbs -3d
```

### 构建和运行

```bash
cd <app_dir>
make -j4
./flash4
```

### 用户文档

`user_documentation.txt` 包含完整的：
- 各应用的构建和运行说明
- Uniform Grid 和 AMR (Paramesh) 网格的缩放参数
- GuardCell、EOS、Hydrodynamics、I/O、PFFT、Gravity、Diffusion 各测试的详细说明
- HDF5 并行 I/O 技术细节
