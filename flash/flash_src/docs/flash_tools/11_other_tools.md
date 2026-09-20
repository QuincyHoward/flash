# FLASH 其他工具

## 概述

本文档涵盖 `tools/` 中不属于上述主要分类的工具：模板生成、CMake 支持、漂移分析、诊断、Chombo 比较、Tau 性能分析、测试套件、Python 绑定文档和 setup.py 安装脚本。

---

## 1. Stencillator — 有限差分模板生成器

### 概述

`tools/Stencillator/` 使用 Python 和 curses 交互界面生成有限差分模板（stencil）系数。适用于非均匀网格和复杂几何的高阶差分格式设计。

### 文件列表

```
Stencillator/
├── stencillator.py         # 主程序（交互式模板生成）
├── stencillator_sym.py     # 对称模板生成
├── fnormalUGalldir.inp     # 示例输入：均匀网格所有方向
├── stencilABCDGH.inp       # 示例输入：ABCDGH 模板
└── syminput.inp            # 对称模板输入
```

### stencillator.py — 主程序

基于 Ncurses 的交互式差分模板生成工具。

**特点**:
- 交互式 CUI 界面，实时显示模板矩阵
- 支持非均匀网格间距
- 支持点值（Pointwise）和单元平均（Cell Average）两种假设
- 生成模板系数矩阵

**模板配置参数**:
| 参数 | 含义 | 默认值 |
|------|------|--------|
| `NL` | 左侧单元数 | 3 |
| `NC` | 中间列单元数 | 3 |
| `NCELLS` | 总单元数 | 6 |
| `NBASIS` | 基函数数 | 6 |

**物理假设**:
- `POINTWISE = True` — 单元值取单元中心点值
- `POINTWISE = False` — 单元值取单元平均值

**坐标设置示例**:
```python
xx = [-0.5, -0.5, -0.5,  0.5,  0.5,  0.5 ]
yy = [-0.5,  0.5,  1.5, -0.5,  0.5,  1.5 ]
```

### stencillator_sym.py — 对称模板生成

基于对称模板的差分格式生成器，用于需要对称性约束的场景。

### 输入文件格式

输入文件（`.inp`）包含模板配置参数，定义网格点坐标和差分需求。

| 输入文件 | 说明 |
|----------|------|
| `fnormalUGalldir.inp` (9KB) | 均匀网格，所有方向 |
| `stencilABCDGH.inp` (2KB) | ABCDGH 模板 |
| `syminput.inp` (1KB) | 对称模板输入 |

---

## 2. CMake 支持

### 概述

`tools/cmake/` 提供 FLASH CMake 构建系统的模块查找文件（Find modules）。

### 文件列表

```
cmake/
├── FindHDF5.cmake         # HDF5 库查找
├── FindHYPRE.cmake        # HYPRE 库查找
├── FindLAPACK.cmake       # LAPACK 库查找
├── FindPYBIND11.cmake     # pybind11 库查找
└── defaults.cmake         # 默认 CMake 配置
```

### FindHDF5.cmake

查找 HDF5 库的 CMake 模块：

```cmake
set(HDF5_ROOT ${HDF5_DIR})
set(HDF5_PREFER_PARALLEL TRUE)
find_package(HDF5 MODULE REQUIRED ${HDF5_COMPONENTS})
```

**特点**:
- 设置 `H5_USE_16_API` 编译器标志
- 创建 `hdf5::hdf5` 导入目标
- 支持 HDF5 并行 I/O

### FindHYPRE.cmake

查找 HYPRE（高性能预处理库）的 CMake 模块。

### FindLAPACK.cmake

查找 LAPACK 线性代数库的 CMake 模块。

### FindPYBIND11.cmake

查找 pybind11（Python-C++ 绑定库）的 CMake 模块。

### defaults.cmake

默认 CMake 配置设置。

---

## 3. driftDee — 漂移分析

### 概述

`tools/driftDee/drifter.py` 用于分析 FLASH 漂移元组日志（drift tuple logs），比较两个日志文件的差异。

**依赖**: [Dee](http://www.quicksort.co.uk/DeeDoc.html) — Python 关系代数库

### 用法

```bash
python drifter.py <drift_log_A> <drift_log_B>
```

**工作流**:
1. 加载两个日志文件为关系（relations）`a` 和 `b`
2. 进入交互式 Python shell
3. 使用关系代数分析差异

### 关系模式

日志文件的元组格式: `(inst, step, src, blk, leaf, unk, val)`

| 字段 | 含义 |
|------|------|
| `inst` | 指令序号 |
| `step` | 时间步 |
| `src` | 源单元 |
| `blk` | 块编号 |
| `leaf` | 是否叶块 |
| `unk` | UNK 变量名 |
| `val` | 值 |

### 内置函数

| 函数 | 说明 |
|------|------|
| `read_tups(path)` | 读取日志文件为关系 |
| `latest(r)` | 对每个(step,blk,unk)取最大 inst |
| `diff(a,b)` | 找出 a 中有但 b 中没有的(blk,unk,val) |
| `gen(**a)` | 生成单例关系 |

---

## 4. diagnosticsTools — 诊断工具

### 概述

`tools/diagnosticsTools/PIslides` 是 PI（Particle-In-Cell 或类似）数据的诊断分析工具。

**文件**: 单个可执行脚本，无扩展名。

**功能**: 生成 PI 数据的诊断幻灯片/报告。

---

## 5. cmp_chombo — Chombo 格式比较

### 概述

`tools/cmp_chombo/cmp_chombo.sh` 是 Chombo 网格格式的数据比较脚本。

**功能**: 比较两个 Chombo 格式的数据文件。

### 用法

```bash
bash cmp_chombo.sh <file1> <file2>
```

---

## 6. Tau 性能工具

### 概述

`tools/tau/select.tau` 是 TAU（Tuning and Analysis Utilities）性能分析工具的 Select 文件。

**功能**: 配置 TAU 性能分析的选择规则，指定何时插入性能监测代码（测量 Fortran/C++ 函数调用、MPI 通信等）。

**依赖**: TAU 性能分析框架（需单独安装）

---

## 7. testSuite — 测试套件

### 概述

`tools/testSuite/` 包含 FLASH 测试套件的 LaTeX 文档。

| 文件 | 大小 | 说明 |
|------|------|------|
| `from_old_testSuite.tex` | 2KB | 旧版测试套件文档片段 |
| `testSuiteGrid.tex` | 7KB | 网格测试套件文档 |

---

## 8. pyFlash — Python 绑定文档

### 概述

`tools/scripts/pyFlash/` 包含 pyFlash（FLASH Python 绑定）的 Sphinx 文档源文件。

### 文件列表

```
pyFlash/
├── pyFlashDoc.py               # 文档生成脚本
└── source/
    ├── index.rst               # 文档主页
    ├── GettingStarted.rst      # 入门指南
    ├── Simulation.rst          # 仿真自定义文档
    ├── pyFlashAPI.rst          # API 参考
    ├── conf.py                 # Sphinx 配置
    └── _templates/
        ├── custom-class-template.rst
        └── custom-module-template.rst
```

### pyFlashDoc.py — 文档生成

自动生成 pyFlash 的 Sphinx HTML 文档。

```bash
python pyFlashDoc.py
```

**工作流**:
1. 运行 `./setup python` 配置 Python 绑定
2. 用 CMake 构建 Python 模块
3. 提取所有运行时参数写入 `flash/parm.py`
4. 运行 Sphinx `make html`

**输出**: `pyDocs/build/` 中的 HTML 文档

**依赖**: CMake, Doxygen, Sphinx, pybind11

### pyFlash 功能

pyFlash 允许使用 Python 替代传统 Fortran 进行 FLASH 仿真配置和自定义:

1. **Python 参数文件** (`flashPar.py`):
   - 定义 `setupArgs()` 和 `parms()` 函数
   - 替代传统 `flash.par`

2. **仿真自定义**:
   - `init()` — 替代 `Simulation_init.F90`
   - `initBlock(blockID)` — 替代 `Simulation_initBlock.F90`（使用 `gr.Block` API 和 numpy）
   - `adjustEvolution()` — 替代 `Simulation_adjustEvolution.F90`
   - `bc[IJK][LO|HI]()` — 自定义边界条件

### 入门要求

- C++ 编译器
- CMake
- pybind11 >= 3.9
- Python >= 3.9

setup 示例:
```bash
./setup Sedov -auto +python -cmake
```

---

## 9. tools/setup.py — FLASH 包安装脚本

### 概述

`tools/setup.py` 是整个 FLASH Python 工具箱的标准安装脚本，位于 `tools/` 根目录。

### 安装

```bash
cd FLASH4.8
python tools/setup.py install
```

### 安装过程

| 步骤 | 内容 |
|------|------|
| 1. 生成元数据 | 创建 `python/metadata.json`，包含源码路径、版本号和 Git 哈希 |
| 2. 安装包 | 安装 `flash`, `flash.flmake`, `flash.dsl`, `flash.flashfile` 包 |
| 3. 安装脚本 | 安装 `flmake`, `consdat`, `convertspect3d`, `flashtimes`, `symmetry` |
| 4. 生成补全 | 为 `flmake` 命令生成 bash 自动补全脚本 |
| 5. 清理 | 删除临时 `metadata.json` 和空日志文件 |

### metadata.json 格式

```json
{
  "FLASH_SRC_DIR": "/path/to/FLASH4.8",
  "FLASH_CLEAN_SRC_DIR": "/path/to/FLASH4.8/.clean",
  "MPIRUN_CMD": "mpirun",
  "version": "4.8 (git_revision_hash)"
}
```

### 版本号

从 `RELEASE` 文件（位于 FLASH 根目录）读取，内容为 `4.8`。

### bash 自动补全

安装后，`flmake` 命令支持 Tab 自动补全（仿真名、选项、目录等）。

需要将以下内容添加到 `~/.bashrc`:
```bash
if [ -f /path/to/flmake-completion ] ; then
    source /path/to/flmake-completion
fi
```

---

## 10. 辅助资源

### IDL SmartFrameLinker

`tools/idlamrlib/smartframelinker.tar` 包含用于 IDL 的智能帧链接工具，支持 AMR 数据的大规模可视化渲染。
