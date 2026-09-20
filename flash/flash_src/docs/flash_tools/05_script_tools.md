# FLASH 脚本工具

## 概述

`tools/scripts/` 目录包含 FLASH 开发、构建、运行和可视化相关的各种脚本，覆盖代码质量、运行管理、性能分析和可视化等。

## 目录结构

```
scripts/
├── codeCheck.py            # 代码质量检查与修复
├── cleanPM.py              # F77→F90 格式转换
├── csv2html.py             # CSV→HTML 表格转换
├── extract_rays.py         # 射线数据 → VTK 提取
├── fixRobodocHeaders.py    # RoboDoc 头修复
├── fixUseOnlyLines.py      # USE ONLY 声明修复
├── flash-assist.py         # 运行时 plot 文件压缩
├── flmake                  # flmake 入口（7 行转发）
├── flashtimes              # HDF5 时间步提取
├── consdat                 # 守恒量检查
├── convertspect3d          # FLASH→Spect3D 格式转换
├── symmetry                # 对称性检查
├── getUseAndCallInfo.py    # USE/调用信息提取
├── interfacesDict.py       # 接口字典构建
├── makefile-clean.py       # Makefile 规则清理
├── replacescript.py        # 批量源码重命名
├── rpDoc.py                # 运行时参数文档生成
├── steptime.py             # 时间步性能分析
├── update.py               # 夜间自动更新
├── fcndefs.bash            # 路径辅助函数
├── binary_size.sh          # 二进制大小分析
├── checklinks.sh           # 文档死链检查
├── recode.sh               # 批量 F77→F90 转换
├── setup_rundir.sh         # 运行目录设置
├── setup_top.sh            # 项目顶层目录设置
├── HPCToolkit/             # 性能分析（HPCToolkit）
├── plot_integrated_quantities/  # 集成量绘图
├── setup_compact_app/      # 紧致应用构建
├── pyFlash/                # Python 绑定文档
├── thread_speedup/         # 线程加速分析
└── visitScripts/           # VisIt 可视化脚本
```

---

## 1. 代码质量工具

### 1.1 codeCheck.py — 代码规范检查与修复

FLASH 源码质量检查主工具，对 Fortran/C 源文件执行编码规范检查。

**用法**:
```bash
python codeCheck.py --mode=check|fix|list|edit \
    --report-file=<file> --target=<dir/file> --method=<method_list>
```

**检查项 (13 项)**:
| 违规类型 | 说明 |
|----------|------|
| `devComments` | DEV 注释标记残留 |
| `implicitNone` | 缺少 IMPLICIT NONE |
| `intent` | 缺少 INTENT 声明 |
| `save` | 裸 SAVE 语句 |
| `noTabs` | 制表符混用 |
| `cleanSource` | 非 ASCII 字符 |
| `commonBlock` | COMMON 块使用 |
| `fileName` | 文件名与主函数名不一致 |
| `useOnly` | USE 未用 ONLY |
| `FnArgsCheck` | 函数参数声明不一致 |
| `RoboDocCheck` | RoboDoc 头不一致 |
| `deallocateCheck` | 分配/释放不匹配 |
| `interfaces` | API 接口一致性 |
| `longLines` | 行超 132 字符 |

**修复项 (4 项)**:
| 修复名 | 功能 |
|--------|------|
| `addImplNone` | 添加 IMPLICIT NONE |
| `TabsToSpace` | 制表符转空格 |
| `inclRoboDoc` | 移除 RoboDoc 头中的 `#include` |
| `GenRoboDoc` | 自动生成 RoboDoc 头 |

**依赖**: `interfacesDict.py`

### 1.2 fixRobodocHeaders.py — RoboDoc 头修复

递归扫描 `source/` 目录，修复 `.F90` 和 `.c` 文件的 RoboDoc 头路径和 `internal` 标记。

```bash
python fixRobodocHeaders.py    # 从 tools/scripts/ 运行
```

### 1.3 fixUseOnlyLines.py — USE ONLY 修复

确保所有 `use <unit>_interface, ONLY: ...` 声明与实际子程序调用一致。

```bash
python fixUseOnlyLines.py -auto                           # 检查所有单元
python fixUseOnlyLines.py Grid Hydro                      # 只检查指定单元
python fixUseOnlyLines.py -dry-run Grid                   # 试运行不修改
```

**功能**: 自动添加缺失接口、修正大小写、移除废弃的 `#include` 行。

**依赖**: `getUseAndCallInfo.py`, `interfacesDict.py`

### 1.4 getUseAndCallInfo.py — USE/调用信息提取

解析 Fortran 源文件，提取关于指定 FLASH 单元的 `use` 声明和子程序调用信息。

```bash
python getUseAndCallInfo.py <unitName> <filename>
```

**返回**: `SubroutineInfo` 列表，包含子程序名、类型、行号、use 行索引、调用列表等。

### 1.5 interfacesDict.py — 接口字典

构建 FLASH 代码库中所有 API 级接口文件的字典，检查声明一致性和大小写匹配。

```python
from interfacesDict import InterfacesDict
idict = InterfacesDict(pathToFlash)
```

**支持的状态码**:
- `INTERFACE_FILE_MISSING` — 缺少接口文件
- `INTERFACE_DECL_IN_ORDER` — 声明正常
- `INTERFACE_DECL_NO_FILE` — 有声明无对应文件
- `INTERFACE_DECL_MISSING` — 缺少声明
- `INTERFACE_DECL_EXTRA` — 多余声明
- `INTERFACE_CASE_MISMATCH` — 大小写不匹配

### 1.6 cleanPM.py — F77→F90 格式转换

将 Fortran 固定格式（F77）源代码转换为自由格式（F90）。

```bash
python cleanPM.py -i input.F -o output.F90
python cleanPM.py -i - -o -    # 使用 stdin/stdout
```

**功能**: 续行合并、续行符转换、添加 `!!REORDER` 指令。

### 1.7 recode.sh — 批量 F77→F90 转换

使用 `cleanPM.py` 批量转换 Paramesh 目录下的 `.F` 文件。

```bash
bash recode.sh    # 假设 ~/FLASH3/source/ 为 FLASH 根目录
```

---

## 2. 运行管理工具

### 2.1 setup_top.sh — 项目顶层目录创建

创建 FLASH 项目顶层目录结构。

```bash
setup_top.sh <directory_name> [GID=group_id] \
    [FLASH_PATH=/path/to/source] [SITE=site_name]
```

**功能**:
- 创建目录并设置组权限和 SGID 位
- 创建源代码符号链接
- 导入批处理提交脚本
- 生成 OPERATOR_GUIDELINES 文档

### 2.2 setup_rundir.sh — 运行目录设置

创建 FLASH 运行目录，支持新建和重启。

```bash
# 新建运行
setup_rundir.sh

# 重启运行
setup_rundir.sh RESTART_CHK=/path/to/chk RESTART_LOG=/path/to/flash.log
```

**功能**:
- 自动递增运行目录编号 (`rundir_000`, `rundir_001`...)
- 复制 `flash4` 和数据文件
- 通过 SVN 记录源代码版本（`FLASH_SVN_INFO`, `FLASH_SVN_DIFF`）
- 编辑 `flash.par`: 设置 `basenm`, `restart`, 文件编号

### 2.3 update.py — 夜间自动更新

```bash
python update.py
```

执行 SVN update → codeCheck → rpDoc → fixRobodocHeaders → SVN commit（失败则 revert）。

### 2.4 flmake — 构建系统入口

仅 7 行，将调用转发到 `flash.flmake.main`：

```python
from flash.flmake.main import main
if __name__ == '__main__':
    main()
```

---

## 3. 性能分析工具

### 3.1 steptime.py — 时间步性能分析

从 FLASH 日志文件提取每个时间步的性能信息。

```bash
python steptime.py LOGFILE [-v] [--chunk-size N]
```

**输出表格**:
| 列 | 含义 |
|----|------|
| step | 时间步编号 |
| sim time | 仿真时间 |
| dt | 时间步长 |
| wall time | 墙钟时间 |
| wall/dt | 每步墙钟时间 |
| wall/cell | 每单元墙钟时间 |
| CPU-hrs/cell/step | 每单元每步 CPU 小时 |

### 3.2 HPCToolkit/differential_profile.sh — 差分性能分析

使用 HPCToolkit 进行多 MPI 进程数下的性能可缩放性分析。

```bash
# 单实验
differential_profile.sh -n 8

# 多实验（对比 1 核和 4 核）
differential_profile.sh -n '1 4' -s /path/to/objdir -r /path/to/rundir
```

**依赖**: HPCToolkit (`hpcrun`, `hpcstruct`, `hpcprof-mpi`)

### 3.3 thread_speedup/speedup_in_flash_log_file.sh — 线程加速分析

从多个线程数的 FLASH 日志中提取计时数据并合并。

```bash
bash speedup_in_flash_log_file.sh
# 需要子目录: 1/, 2/, 4/ 各含 flash.log
# 输出: time_n_threads.txt
```

### 3.4 binary_size.sh — 二进制大小分析

分析 FLASH 可执行文件的 text/data/bss 段大小。

```bash
bash binary_size.sh ./flash4 [num_bss_allocs]
```

**输出**: text/data/bss 段大小（MB）、BG/P 模式可用内存估算、最大 bss 段分配列表。

---

## 4. 后处理工具

### 4.1 extract_rays.py — 射线数据提取

从 FLASH 射线追踪 plot 文件中提取光线数据并生成 VTK 文件。

```bash
python extract_rays.py <filename1> [filename2 ...]
```

**输出**: `<前缀>_las_<cycle>.vtk`（VTK 非结构化网格）

**数据字段**: `TIME`, `CYCLE`, 光线标签, 光线功率

**依赖**: `tables` (PyTables), `numpy`

### 4.2 convertspect3d — FLASH→Spect3D 格式转换

将 FLASH checkpoint/plot 文件转换为 Spect3D EXODUS II 格式。

```bash
python convertspect3d --species=cham,targ [--extra=trad,r001] <checkpoint_file>
```

**输出**: `.exo` 文件（NETCDF3_64BIT 格式）

**自动计算**:
| 量 | 公式 |
|----|------|
| `nele` | `NA * dens * ye` |
| `nion` | `NA * dens * sumy` |
| `zbar` | `ye / sumy` |
| `abar` | `1 / sumy` |

**依赖**: `tables`, `netCDF4`, `numpy`, `flash.flashfile`

### 4.3 consdat — 守恒量检查

加载 FLASH 集成量 `.dat` 文件，检查质量、动量和能量守恒。

```bash
python consdat <filename.dat>
```

**文件格式**: 列: time, mass, xmom, ymom, zmom, etot, ekin, eint [, emag]

### 4.4 flashtimes — 时间步提取

从 HDF5 文件中提取时间步编号和仿真时间。

```bash
python flashtimes <file1> [file2 ...]
```

### 4.5 symmetry — 对称性检查

检查二维 FLASH 数据关于对角线的对称性。

```bash
python symmetry dens --expr=dens --relative --minval=1e-10 <files...>
python symmetry "velx,vely" --expr="sqrt(velx**2+vely**2)" <files...>
```

### 4.6 flash-assist.py — 运行时 plot 文件压缩

实时监控 FLASH 运行日志，自动用 GZIP 压缩新生成的 HDF5 plot 文件。

```bash
python flash-assist.py /path/to/run/dir [--logfile=/path/to/flash.log]
```

**功能**: 监控 `[IO_writePlotfile] close:` 日志行，调用 `h5repack -f GZIP=1` 压缩。
原文件移到 `*-orig.h5`。

**依赖**: `h5repack` (HDF5 工具链)

---

## 5. 文档工具

### 5.1 rpDoc.py — 运行时参数文档生成

遍历所有 FLASH 单元，生成运行时参数文档。

```bash
python rpDoc.py    # 从 tools/scripts/ 运行
```

**输出**: `docs/designDocs/rpDoc.txt`, `rpDuplications.txt`, `rp_*.txt`

### 5.2 csv2html.py — CSV→HTML 转换

```bash
python csv2html.py <csvfile> <htmlfile>
```

生成带交替行颜色的 CSS 样式 HTML 表格。

### 5.3 checklinks.sh — 死链检查

```bash
bash checklinks.sh
```

用 `wget` 递归检查 FLASH 用户指南网站上的死链接。

---

## 6. 辅助工具

### 6.1 replacescript.py — 批量重命名

批量查找替换 Fortran 子程序/函数名，支持 `svn mv` 文件重命名。

```bash
python replacescript.py <name_map_file>
```

**输入文件格式**: `oldname\tnewname`（每行）

**依赖**: `perl`, `svn`

### 6.2 makefile-clean.py — Makefile 规则清理

从 Makefile 中移除目标规则（含 `:` 的行），只保留变量赋值。

```bash
python makefile-clean.py <Makefile> > NewMakefile
```

### 6.3 fcndefs.bash — 路径辅助函数

```bash
source fcndefs.bash
pathmungeany /usr/local/mpi/bin
pathmungeany /usr/local/mpi/lib first LD_LIBRARY_PATH
```

类似 RedHat 的 `pathmunge`，避免环境变量路径重复。

### 6.4 plot_integrated_quantities — 集成量绘图

使用 gnuplot 自动绘制 FLASH 集成量对比图。

```bash
FILE1=bgp_rtflame.dat FILE2=bgq_rtflame.dat simulation_plot.sh
```

**输出**: `<PLOT_NAME>.ps` 和 `<PLOT_NAME>.pdf`

**配置方式**: 通过 `plot_parameters.sh` 或环境变量设置文件和标签。

**依赖**: `gnuplot`, `ps2pdf` (ghostscript)
