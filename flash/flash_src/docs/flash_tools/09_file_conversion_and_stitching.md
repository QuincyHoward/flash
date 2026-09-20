# FLASH 文件转换与缝合工具

## 概述

FLASH 提供文件转换、格式转换和数据缝合工具，用于在不同格式之间转换仿真数据，或将大型数据集拼接为完整文件。

## 1. 文件转换工具 (converterTools/)

### 概述

`tools/converterTools/` 提供 FLASH2→FLASH3 格式的变量名映射转换工具。

### 文件列表

```
converterTools/
├── genVarMap.py            # 生成变量名映射文件
├── makeVarMap.py           # 解析 HDF5 XML 转储提取变量名
├── HDF5protonData2Visit    # HDF5 质子数据→VisIt 格式
├── PIcreateHDF5file        # PI 数据→HDF5 格式
├── PIfiles2pgm            # PI 文件→PGM 图像格式
└── THSCfiles2pdf          # THSC 文件→PDF 格式
```

### 1.1 genVarMap.py — 变量名映射生成

生成 FLASH2 到 FLASH3 的变量名映射文件。

```bash
python genVarMap.py [options] <flash2_file>

选项:
  -o <filename>     : 输出变量映射文件名（默认: flash2vars）
  -p [filename]     : 输出粒子映射文件名（默认: flash2parts）
  -d                : 使用默认映射（不交互）
  --noPartMap       : 不生成粒子映射
```

**工作流**:
1. 调用 `h5dump -x` 生成 XML 格式的 HDF5 转储
2. 通过管道传给 `makeVarMap.py` 提取 `unknown names` 数据集
3. 交互式询问每个变量的 FLASH3 映射名（或使用 `-d` 默认映射）

### 1.2 makeVarMap.py — HDF5 XML 解析

使用 SAX XML 解析器从 `h5dump -x` 输出的 XML 中提取 FLASH2 变量名。

```bash
h5dump -x flash2_file | python makeVarMap.py
```

**机制**: 解析 `hdf5:Dataset` 元素的 `Name` 属性，提取 `unknown names` 数据集内容。

### 1.3 其他转换器

| 程序 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `HDF5protonData2Visit` | 质子数据格式转换 | HDF5 | VisIt 格式 |
| `PIcreateHDF5file` | PI 数据格式转换 | PI 格式 | HDF5 |
| `PIfiles2pgm` | 图像格式转换 | PI 文件 | PGM 图像 |
| `THSCfiles2pdf` | 文档格式转换 | THSC 文件 | PDF |

---

## 2. FLASH 文件缝合 (flashStitch)

### 概述

`tools/fileTools/flashStitch/` 提供将跨多个文件的 FLASH checkpoint 缝合为单一完整文件的工具。

### 文件列表

```
flashStitch/
├── Makefile
├── Makefile.zingiber
├── README                    # 使用说明
├── constants.h               # 常量定义
├── main.c                    # 程序入口
├── options.c / options.h     # 选项解析
├── flashStitcher.c           # 缝合主逻辑
├── flashStitcher.h           # 缝合器头文件
├── flash_reader.c / flash_reader.h        # 文件读取
└── flash_reader_hdf5.c       # HDF5 读取器
```

### 功能

- 将 MPI 多文件 checkpoint 合并为单一 HDF5 文件
- 处理跨文件的数据分布
- 重建全局块结构
- 合并所有 UNK 变量数据

### 编译

```bash
cd tools/fileTools/flashStitch
make                     # Linux
make -f Makefile.zingiber # 特定集群
```

### 使用方式

```bash
./flashStitcher <input_prefix> <output_file> [options]
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `flashStitcher.c` (41KB) | 主缝合逻辑：读取多个文件，合并块数据，写入单一文件 |
| `flashStitcher.h` | 缝合器数据结构和函数声明 |
| `flash_reader.c`/`.h` | 文件读取抽象层 |
| `flash_reader_hdf5.c` (13KB) | HDF5 格式专用读取器 |
| `options.c`/`.h` | 命令行选项解析 |
| `constants.h` | 常量和宏定义 |

---

## 3. convertspect3d — FLASH→Spect3D 格式转换

### 概述

将 FLASH checkpoint 或 plot 文件转换为 Spect3D 辐射传输代码所需的 EXODUS II 格式。

**路径**: `tools/scripts/convertspect3d`

### 用法

```bash
python convertspect3d --species=cham,targ [--extra=trad,r001] <checkpoint_file>
```

**选项**:
| 选项 | 说明 |
|------|------|
| `--species` | 指定质量分数变量（逗号分隔） |
| `--extra` | 额外变量（逗号分隔） |

### 转换细节

**输出格式**: EXODUS II (NETCDF3_64BIT)，文件扩展名为 `.exo`

**自动计算物理量**:
| 量 | 公式 | 说明 |
|----|------|------|
| `nele` | `NA * dens * ye` | 电子数密度 |
| `nion` | `NA * dens * sumy` | 离子数密度 |
| `zbar` | `ye / sumy` | 平均电离度 |
| `abar` | `1 / sumy` | 平均原子量 |

**数据处理**:
- 读取 FLASH 网格几何信息（Cartesian/Cylindrical）
- 处理物种质量分数转换（部分密度）
- 输出 Spect3D 网格块结构

**依赖**: `tables` (PyTables), `netCDF4`, `numpy`, `flash.flashfile`
