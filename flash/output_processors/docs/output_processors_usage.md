# Output Processors 使用说明

> `flash/output_processors` 包提供 FLASH 仿真 HDF5 输出文件的处理功能。
> 使用纯 h5py 实现，无需安装 yt，适合超算环境。
> 最后更新: 2026-07-04

---

## 目录

1. [简介](#1-简介)
2. [安装依赖](#2-安装依赖)
3. [快速开始](#3-快速开始)
4. [核心 API](#4-核心-api)
5. [数据采集（HDF5读取）](#5-数据采集hdf5读取)
6. [数据处理（加载与派生变量）](#6-数据处理加载与派生变量)
7. [数据可视化（绘图）](#7-数据可视化绘图)
8. [完整工作流示例](#8-完整工作流示例)
9. [高级功能](#9-高级功能)
10. [如何新增自定义变量](#10-如何新增自定义变量)
11. [性能调优](#11-性能调优)
12. [常见问题](#12-常见问题)

---

## 1. 简介

`output_processors` 包提供以下核心功能：

- **HDF5 文件读取** - `FlashHDF5File` 类（纯 h5py，无需 yt）
- **数据加载** - `FlashDataLoader` 类（自动处理 AMR 块结构）
- **派生变量计算** - `DataCalculator` 类（基于 DATA_CONFIG 注册表）
- **自适应可视化** - `FlashPlotter` 类（自动适配 1D/2D/3D 绘图）
- **激光参数提取** - 自动解析 `ed_time_*/ed_power_*` 运行时参数

### 模块结构

```
output_processors/
├── __init__.py              # 包导出
├── hdf5processor/          # HDF5 文件核心 I/O 层
│   ├── __init__.py
│   └── flash_hdf5.py       # FlashHDF5File, DataCalculator, DATA_CONFIG
├── loader/                  # 数据加载层
│   ├── __init__.py
│   └── data_loader.py      # FlashDataLoader, FlashDataContainer
├── plotter/                 # 可视化层
│   ├── __init__.py
│   └── plot_generator.py   # FlashPlotter
└── docs/                   # 文档
```

---

## 2. 安装依赖

```bash
pip install h5py numpy matplotlib
```

> **注意**: 本包纯 h5py 实现，无需 yt，适合超算环境。

---

## 3. 快速开始

### 3.1 加载单个 HDF5 文件并绘图

```python
import sys
sys.path.insert(0, 'path/to/PhySimX')

from output_processors.loader import FlashDataLoader
from output_processors.plotter import FlashPlotter

# 加载 HDF5 文件
loader = FlashDataLoader("lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

# 访问数据
print(f"仿真时间: {container.simulation_time:.4e} s")
print(f"维度: {container.ndim}D")
print(f"变量: {list(container.data.keys())}")

# 绘图
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="output/dens.png")
plotter.plot("tele", save_path="output/tele.png")
```

### 3.2 批量加载与绘图

```python
from output_processors.loader import FlashDataLoader
from output_processors.plotter import FlashPlotter

# 批量加载文件夹中的所有 HDF5 文件
containers = FlashDataLoader.load_folder(
    "output_dir/",
    pattern="*chk*",
    compute_derived=True
)

# 按时间排序
for c in containers:
    print(f"t = {c.simulation_time:.4e} s, dens_mean = {c.data['dens'].mean():.4e}")

# 批量绘图
FlashPlotter.plot_folder("output_dir/", "dens", save_dir="plots/")
```

---

## 4. 核心 API

### 4.1 三层架构

| 层次 | 类 | 说明 |
|------|-----|------|
| **采集** | `FlashHDF5File` | 底层 HDF5 读取，解析 AMR 结构 |
| **处理** | `FlashDataLoader` + `FlashDataContainer` | 加载数据，计算派生变量 |
| **可视化** | `FlashPlotter` | 自适应维度绘图，AMR 网格可视化 |

### 4.2 典型工作流

```python
# 1. 采集 - 读取 HDF5
from output_processors.hdf5processor import FlashHDF5File
ff = FlashHDF5File("file.h5")
ff.print_info(detailed=True)
ff.close()

# 2. 处理 - 加载为结构化容器
from output_processors.loader import FlashDataLoader
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)

# 3. 可视化 - 绘图
from output_processors.plotter import FlashPlotter
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png")
```

---

## 5. 数据采集（HDF5读取）

### 5.1 `FlashHDF5File` 类

底层 HDF5 文件读取器，直接操作 HDF5 数据集。

#### 基本用法

```python
from output_processors.hdf5processor import FlashHDF5File

# 打开文件
ff = FlashHDF5File("lasslab_hdf5_chk_0001")

# 打印文件信息
ff.print_info(detailed=True)

# 读取变量
dens = ff.read_var("dens")  # 形状: (nblocks, Nx) for 1D
print(f"密度形状: {dens.shape}")

# 读取网格坐标
grid = ff.read_grid()
print(f"全局 x 坐标: {grid['x_1d']}")

# 获取仿真时间
print(f"仿真时间: {ff.simulation_time:.4e} s")

# 获取激光参数
laser = ff.laser_groups
for g, data in laser.items():
    print(f"激光组 {g}: {len(data['time'])} 个时点")

ff.close()
```

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `ndim` | `int` | 空间维度（1/2/3） |
| `nblocks` | `int` | AMR 块数 |
| `nx`, `ny`, `nz` | `int` | 每块网格点数 |
| `varnames` | `list[str]` | 所有可用变量名 |
| `file_type` | `str` | 文件类型（"checkpoint" / "plot"） |
| `simulation_time` | `float` | 仿真时间 [s] |
| `simulation_step` | `int` | 仿真步数 |
| `laser_groups` | `dict` | 激光脉冲分组数据 |

#### 主要方法

| 方法 | 说明 |
|------|------|
| `read_var(name)` | 读取物理量数组（自动挤压单例维度） |
| `read_var_flat(name)` | 读取变量并展平为 1D 数组 |
| `read_grid()` | 重建坐标网格，返回字典 |
| `print_info(detailed)` | 打印文件结构摘要 |
| `stats(varname, data_dict)` | 计算变量统计量（min/max/mean/median/std） |
| `slice_1d(varname)` | 1D 数据按 x 坐标排序拼接 |

---

## 6. 数据处理（加载与派生变量）

### 6.1 `FlashDataLoader` 类

高级数据加载器，将 HDF5 原始数据转换为结构化容器。

#### 基本用法

```python
from output_processors.loader import FlashDataLoader

# 加载单个文件
loader = FlashDataLoader("lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

# 仅加载指定变量（速度更快）
container = loader.load_vars("dens", "tele", compute_derived=True)
```

#### 批量加载

```python
# 加载文件夹中的所有 HDF5 文件
containers = FlashDataLoader.load_folder(
    "output_dir/",
    pattern="*chk*",       # 文件匹配模式
    compute_derived=True,  # 是否计算派生变量
    sort_by_time=True      # 是否按仿真时间排序
)
print(f"共加载 {len(containers)} 个文件")
```

### 6.2 `FlashDataContainer` 类

结构化数据容器，保存处理后的仿真数据。

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `data` | `dict` | 原始变量字典 {变量名: ndarray} |
| `derived` | `dict` | 派生变量字典 {变量名: ndarray} |
| `grid` | `dict` | 坐标网格信息 |
| `ndim` | `int` | 空间维度 |
| `nblocks` | `int` | AMR 块数 |
| `simulation_time` | `float` | 仿真时间 [s] |
| `laser_groups` | `dict` | 激光脉冲参数 |
| `varnames` | `list` | 物理量名称列表 |

#### 主要方法

```python
# 获取变量（先查 data，再查 derived）
dens = container.get("dens")

# 获取变量单位
unit = container.unit("dens")  # "g/cm^3"

# 获取 SI 转换系数
to_si = container.to_si("dens")  # 1000.0 (g/cm^3 -> kg/m^3)
```

### 6.3 派生变量计算

`DataCalculator` 根据 `DATA_CONFIG` 自动计算派生变量。

#### 已注册的派生变量

| 变量名 | 公式 | 说明 |
|--------|------|------|
| `dens_targ` | `dens * targ` | 靶材料密度 |
| `dens_cham` | `dens * cham` | CH 烧蚀层密度 |
| `nele` | `ye * dens * NA` | 电子数密度 |
| `nion` | `sumy * dens * NA` | 离子数密度 |
| `ls_nele` | `nele / \|grad(nele)\|` | 电子密度梯度标长 |
| `ls_tele` | `tele / \|grad(tele)\|` | 电子温度梯度标长 |

#### 自定义派生变量

```python
from output_processors.hdf5processor import DataCalculator, NA

# 注册新派生变量
DataCalculator.register(
    varname="my_var",
    formula="ye * dens * NA",
    description="My custom variable",
    unit="1/cm^3",
    to_si=1e6
)

# 加载数据时会自动计算
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)
my_var = container.derived["my_var"]
```

---

## 7. 数据可视化（绘图）

### 7.1 `FlashPlotter` 类

自适应维度绘图器，根据数据维度自动选择绘图类型。

#### 基本用法

```python
from output_processors.plotter import FlashPlotter

plotter = FlashPlotter(container)

# 绘制单个变量
plotter.plot("dens", save_path="output/dens.png", title="Density (1D)")

# 绘制派生变量
plotter.plot("nele", save_path="output/nele.png", use_derived=True)

# 绘制所有变量
saved_files = plotter.plot_all(save_dir="output/plots/")
```

#### 自适应维度

| 维度 | 绘图类型 |
|------|----------|
| 1D | 线图 (x vs value) |
| 2D | 伪彩色图 (pcolormesh) |
| 3D | 切片伪彩色图（默认取 z 方向中平面） |

### 7.2 AMR 网格可视化

```python
# 绘制 AMR 块网格结构
plotter.plot_amr_grid("dens", save_path="amr_dens.png")

# 仅绘制网格（不叠加物理量）
plotter.plot_amr_grid(save_path="grid_only.png")
```

### 7.3 批量绘图

```python
# 批量处理文件夹中所有 HDF5 文件
saved = FlashPlotter.plot_folder(
    folder_path="output_dir/",
    var_name="dens",
    save_dir="plots/",
    pattern="*chk*"
)
print(f"共保存 {len(saved)} 张图")
```

---

## 8. 完整工作流示例

### 8.1 1D 仿真数据分析

```python
import sys
sys.path.insert(0, 'path/to/PhySimX')

from output_processors.loader import FlashDataLoader
from output_processors.plotter import FlashPlotter

# 1. 加载数据
loader = FlashDataLoader("inputfiles/hdf5files_1d/lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

# 2. 打印摘要
print(f"文件: {container.filepath}")
print(f"维度: {container.ndim}D, 块数: {container.nblocks}")
print(f"时间: {container.simulation_time:.4e} s")
print(f"变量: {list(container.data.keys())}")
print(f"派生: {list(container.derived.keys())}")

# 3. 获取数据
x = container.grid["x_1d"]  # 全局 x 坐标
dens = container.data["dens"]  # 密度数组
tele = container.data["tele"]  # 电子温度
nele = container.derived["nele"]  # 电子数密度（自动计算）

# 4. 绘图
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="output/dens.png")
plotter.plot("tele", save_path="output/tele.png")
plotter.plot("nele", save_path="output/nele.png", use_derived=True)

# 5. AMR 网格图
plotter.plot_amr_grid("dens", save_path="output/amr_grid.png")
```

### 8.2 2D/3D 仿真数据分析

```python
# 2D 数据
loader = FlashDataLoader("inputfiles/hdf5files_2d/lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

plotter = FlashPlotter(container)
plotter.plot("dens", save_path="output/dens_2d.png")  # 自动绘制 2D 伪彩色图
plotter.plot_amr_grid("dens", save_path="output/amr_2d.png")

# 3D 数据（自动取 z 方向中平面切片）
loader = FlashDataLoader("inputfiles/hdf5files_3d/lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

plotter = FlashPlotter(container)
plotter.plot("dens", save_path="output/dens_3d.png")  # 自动切片
```

### 8.3 时间序列分析

```python
# 批量加载时间序列数据
containers = FlashDataLoader.load_folder(
    "output_dir/",
    pattern="*chk*",
    compute_derived=True,
    sort_by_time=True
)

# 提取时间序列
times = [c.simulation_time for c in containers]
dens_max = [c.data["dens"].max() for c in containers]

# 绘制演化
import matplotlib.pyplot as plt
plt.figure(figsize=(8, 5))
plt.plot(times, dens_max, 'b-', linewidth=2)
plt.xlabel("Time [s]")
plt.ylabel("Max Density [g/cm^3]")
plt.savefig("output/dens_evolution.png", dpi=150)
plt.close()

# 批量绘图
FlashPlotter.plot_folder("output_dir/", "dens", save_dir="output/plots/")
```

---

## 9. 高级功能

### 9.1 激光参数提取

```python
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=False)

# 获取激光脉冲分组
laser = container.laser_groups
for g, data in laser.items():
    print(f"激光组 {g}:")
    print(f"  时间点: {data['time']}")
    print(f"  功率:   {data['power']}")
```

### 9.2 多子图复合绘图

```python
plotter = FlashPlotter(container)

# 多物理量并排比较
plotter.plot_multi_panel(
    var_names=["dens", "tele", "nele"],
    save_path="output/multi_panel.png"
)
```

### 9.3 仅加载指定变量

```python
# 仅加载 dens 和 tele（速度更快，内存更少）
loader = FlashDataLoader("file.h5")
container = loader.load_vars("dens", "tele", compute_derived=True)
```

---

## 10. 如何新增自定义变量

详见 `docs/how_to_add_custom_variables.md`。

### 快速示例

```python
from output_processors.hdf5processor import DataCalculator, NA

# 注册公式字符串
DataCalculator.register(
    varname="pele_calc",
    formula="ye * dens * NA * 1.380649e-16 * tele",  # pele = nele * KB * tele
    description="Electron pressure (erg/cm^3)",
    unit="erg/cm^3",
    to_si=0.1
)

# 使用
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)
pele = container.derived["pele_calc"]  # 自动计算
```

---

## 11. 性能调优

### 11.1 加速建议

1. **仅加载需要的变量** - 使用 `load_vars()` 而非 `load()`
2. **批量加载时使用模式匹配** - 使用 `pattern` 参数过滤文件
3. **按需计算派生变量** - 设置 `compute_derived=False`（如果不需要）
4. **复用 FlashDataLoader 对象** - 避免重复打开文件

### 11.2 内存优化

```python
# 仅加载元数据（不加载数据）
# 注意：当前版本不支持懒加载，需要手动实现
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=False)  # 不计算派生变量

# 仅加载部分变量
container = loader.load_vars("dens")  # 仅加载 dens
```

---

## 12. 常见问题

### Q1: 如何读取 HDF5 文件中的变量列表？

**A**: 使用 `FlashHDF5File.varnames` 属性：

```python
from output_processors.hdf5processor import FlashHDF5File
ff = FlashHDF5File("file.h5")
print(f"可用变量: {ff.varnames}")
```

### Q2: 如何获取仿真时间？

**A**: 使用 `FlashHDF5File.simulation_time` 或 `FlashDataContainer.simulation_time`：

```python
# 方法 1: 直接从 HDF5 文件读取
ff = FlashHDF5File("file.h5")
print(f"时间: {ff.simulation_time:.4e} s")

# 方法 2: 从容器读取
loader = FlashDataLoader("file.h5")
container = loader.load()
print(f"时间: {container.simulation_time:.4e} s")
```

### Q3: 如何绘制 AMR 网格？

**A**: 使用 `FlashPlotter.plot_amr_grid()`：

```python
plotter = FlashPlotter(container)
plotter.plot_amr_grid("dens", save_path="amr.png")
```

### Q4: 如何在超算上使用？

**A**: 本包纯 h5py 实现，无需 yt。只需：

```bash
pip install h5py numpy matplotlib --user
```

### Q5: 如何添加新变量到 DATA_CONFIG？

**A**: 编辑 `output_processors/hdf5processor/flash_hdf5.py` 中的 `DATA_CONFIG` 字典，或使用 `DataCalculator.register()` 动态注册。

---

## 相关文档

- 自定义变量教程: `docs/how_to_add_custom_variables.md`
- API 参考手册: `docs/api_reference.md`
- 测试说明: `test/README.md`

---

**维护者**: WorkBuddy AI
**最后更新**: 2026-07-04
