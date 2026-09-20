# FLASH 输出文件比较工具

## 概述

FLASH 提供三个级别的输出文件比较工具，用于验证仿真结果的可重复性和代码修改的正确性：

| 工具 | 路径 | 运行方式 | 适用场景 |
|------|------|---------|---------|
| **sfocu** | `tools/sfocu/` | 串行 C 程序 | 通用 checkpoint 比较 |
| **pfocu** | `tools/pfocu/` | 并行 MPI C 程序 | 大规模仿真比较 |
| **cmpExpIO** | `tools/cmpExpIO/` | 并行 MPI C++ 程序 | 带实验性 I/O 的比较 |

所有工具比较的输出格式统一，结果以 `SUCCESS` 或 `FAILURE` 结尾，便于自动化测试。

---

## 1. sfocu — 串行 FLASH 输出比较工具

### 功能

比较两个 FLASH checkpoint 文件，判断它们是否"相等"：
- **叶块结构匹配**: 每个叶块在两个数据集中必须具有相同的位置和大小
- **数据数组一致**: 叶块中的数据（`dens`, `pres` 等）必须相同

忽略块编号、时间戳、构建信息等无关元数据。

### 支持的格式

- HDF5 (`NO_HDF5` 宏关闭)
- HDF4 (`NO_HDF4` 宏关闭)
- **不支持**: F77 checkpoint 文件、跨多文件 checkpoint

### 编译

```bash
cd tools/sfocu
make -f Makefile.zingiber  # 或其他平台 Makefile
```

**编译选项** (在 Makefile 的 `CDEFINES` 宏中设置):
| 宏 | 作用 |
|----|------|
| `NO_HDF4` | 不包含 HDF4 支持 |
| `NO_HDF5` | 不包含 HDF5 支持 |
| `NEED_MPI` | 链接 MPI 库（用于并行 HDF5） |

**支持平台**: irix, linux, AIX, OSF1

### 用法

```bash
./sfocu <file1> <file2> [options]
./sfocu -h                # 查看所有选项
```

### 输出格式

```
sfocu: comparing file1 and file2

Min Error: inf(2|a-b| / max(|a+b|, 1e-99) )
Max Error: sup(2|a-b| / max(|a+b|, 1e-99) )
Abs Error: sup|a-b|
Mag Error: sup|a-b| / max(sup|a|, sup|b|, 1e-99)

Total leaf blocks compared: 4 (all other blocks are ignored)
-----+------------+-----------++-----------+-----------+-----------++-----------+-----------+-----------+
Var  | Bad Blocks | Min Error ||             Max Error             ||             Abs Error             |
-----+------------+-----------++-----------+-----------+-----------++-----------+-----------+-----------+
dens | 0          | 0         || 0         |  0        |  0        || 0         |  0        |  0        |
pres | 4          | 0         || 1.143e-09 |  370      |  370      || 4.231e-07 |  370      |  370      |
...
FAILURE
```

**输出字段**:
| 字段 | 含义 |
|------|------|
| `Bad Blocks` | 数据存在差异的叶块数 |
| `Min Error` | 最小相对误差 |
| `Max Error` | 最大相对误差（= `sup(2|a-b|/max(|a+b|,1e-99))`） |
| `Abs Error` | 绝对误差（= `sup|a-b|`） |
| `Mag Error` | 幅值相对误差（= `sup|a-b|/max(sup|a|,sup|b|,1e-99)`） |
| 最后六列 | 两个文件的 sum/max/min 统计（非体积加权！） |

**退出码**: `FAILURE`(非零) / `SUCCESS`(零)，方便脚本解析

### 模块结构

| 源文件 | 功能 |
|--------|------|
| `sfocu.c` | 主逻辑：块匹配、数据比较、报告输出 |
| `flash_reader.c`/`.h` | 文件读取抽象层 |
| `flash_reader_hdf4.c` | HDF4 读取器 |
| `flash_reader_hdf5.c` | HDF5 读取器 |
| `flash_reader_ncdf.c` | NetCDF 读取器 |
| `flash_reader_chombo.c` | Chombo 格式读取器 |
| `options.c`/`.h` | 命令行选项解析 |
| `sameblock.c`/`.h` | 块匹配逻辑 |
| `namecmp.c`/`.h` | 变量名比较（忽略大小写） |
| `test_reader.c` | 读取器单元测试 |
| `main.c` | 程序入口 |
| `Makefile` + 48 个平台 Makefile | 构建系统 |

---

## 2. pfocu — 并行 FLASH 输出比较工具

### 功能

pfocu 是 sfocu 的并行版本，大部分源代码共享。用于大规模仿真输出的快速验证。

### 与 sfocu 的区别

| 特性 | sfocu | pfocu |
|------|-------|-------|
| 运行方式 | 串行 | MPI 并行 |
| 所需库 | HDF4/HDF5 | HDF4/HDF5 + MPE 库 |
| 域分解 | 无 | 使用 MPE 库 |
| 适用规模 | 中小规模 | 大规模 |

### 编译

修改 sfocu 的 Makefile:
1. 添加 MPE 库链接
2. 将 `sfocu` 引用改为 `pfocu`
3. 参考 `tools/pfocu/Makefile.zingiber`

### 模块结构

| 源文件 | 功能 |
|--------|------|
| `pfocu.c` | 主逻辑（并行化版本） |
| `working.c` | 工作数据管理 |
| `main.c` | 入口点 |
| `sameblock.c`/`.h` | 块匹配 |
| `options.c`/`.h` | 选项解析 |
| `flash_reader*.c`/`.h` | 文件读取（与 sfocu 相同） |
| `test_reader.c` | 读取器测试 |

---

## 3. cmpExpIO — 实验性 I/O 比较工具

### 功能

基于 C++ 和 MPI 的并行 checkpoint 比较工具，支持实验性 I/O 特性。

### 用法

```bash
mpirun -np N ./cmpExpIO <checkpoint_file1> <checkpoint_file2> [-i]
```

**选项**:
- `-i` — 使用独立并行 I/O（默认: 集合式并行 I/O）

### 架构

采用工厂模式实现文件读取:

```
FlashFileFactory
  ├── FlashFile (抽象基类)
  │   ├── HDF5_File    (HDF5 格式)
  │   └── PNETCDF_File (Parallel NetCDF 格式)
  └── DataBufferComparer (数据比较引擎)
```

### 待办功能

根据 `TODO` 文件:
1. 支持 `face` 和 `scratch` 变量的分析
2. 空 plot 文件的优雅退出
3. 扩展对象模型减少代码重复

### 源文件

| 文件 | 功能 |
|------|------|
| `main.cpp` | 主入口，MPI 初始化，文件比较流程 |
| `FlashFile.hpp` | 抽象文件接口 |
| `FlashFileFactory.cpp`/`.hpp` | 工厂模式文件创建 |
| `HDF5_File.cpp`/`.hpp` | HDF5 文件实现 |
| `PNETCDF_File.cpp`/`.hpp` | Parallel NetCDF 文件实现 |
| `DataBufferComparer.cpp`/`.hpp` | 数据缓冲区比较引擎 |
| `WorkCoordinator.cpp`/`.hpp` | 工作分配协调 |
| `flash_types.hpp` | 类型定义 |
| `Makefile` / `Analysis_Makefile.tuxedo` | 构建配置 |

---

## 4. GridDumpCompare — 网格转储比较

### 功能

比较 FLASH 中 `Grid_dump` 函数输出的两个二进制转储文件，判断是否相同。

### Python 版本

```bash
python tools/GridDumpCompare.py [-t tolerance] <fileA> <fileB>
```

- 读取双精度二进制数组
- 比较每个元素，跟踪最大差异
- 支持容差比较（`-t` 选项）

### Fortran 版本

`tools/GridDumpCompare.F90` 提供相同的 Fortran 实现，用于超算环境。

### 输入文件格式

`tools/GridDumpCompareInput` 是示例输入配置文件。

### 退出码

| 码 | 含义 |
|----|------|
| 0 | 文件相同（或在容差内） |
| 1 | 文件不同（超过容差） |
