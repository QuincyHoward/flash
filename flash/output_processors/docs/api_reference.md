# API 参考手册

> `flash/output_processors` 包完整 API 参考。
> 最后更新: 2026-07-04

---

## 目录

1. [模块结构](#1-模块结构)
2. [hdf5processor 模块](#2-hdf5processor-模块)
3. [loader 模块](#3-loader-模块)
4. [plotter 模块](#4-plotter-模块)
5. [异常情况](#5-异常情况)
6. [配置参数](#6-配置参数)

---

## 1. 模块结构

```
output_processors/
├── __init__.py              # 包导出
├── hdf5processor/          # HDF5 文件处理
│   ├── __init__.py         # 导出 FlashHDF5File, DataCalculator, DATA_CONFIG, VAR_ALIASES, NA
│   └── flash_hdf5.py       # 核心实现
├── loader/                  # 数据加载器
│   ├── __init__.py         # 导出 FlashDataLoader, FlashDataContainer
│   └── data_loader.py      # 核心实现
├── plotter/                 # 可视化
│   ├── __init__.py         # 导出 FlashPlotter
│   └── plot_generator.py   # 核心实现
└── docs/                   # 文档
```

---

## 2. hdf5processor 模块

### 2.1 `FlashHDF5File` 类

HDF5 文件读取器（纯 h5py 实现，无需 yt）。

#### 构造函数

```python
FlashHDF5File(filepath: str)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `filepath` | `str` | HDF5 文件路径 |

#### 上下文管理器

```python
with FlashHDF5File("file.h5") as ff:
    # 使用 ff
    pass  # 自动关闭文件
```

#### 属性（只读）

| 属性 | 类型 | 说明 |
|--------|------|------|
| `filepath` | `str` | 文件路径 |
| `ndim` | `int` | 维度（1, 2, 3） |
| `nblocks` | `int` | 块数 |
| `nx`, `ny`, `nz` | `int` | 每块网格点数 |
| `varnames` | `list[str]` | 所有可用变量名 |
| `file_type` | `str` | 文件类型（"checkpoint" / "plot"） |
| `sim_info` | `dict` | 仿真元信息 |
| `simulation_time` | `float` | 仿真时间 [s] |
| `simulation_step` | `int` | 时间步编号 |
| `laser_groups` | `dict` | 激光脉冲分组数据 |
| `real_scalars` | `dict` | 实型标量值 |
| `integer_scalars` | `dict` | 整型标量值 |
| `runtime_params` | `dict` | 运行时参数 |
| `coordinate_system` | `str` | 坐标系统类型（自动检测） |
| `coord_labels` | `dict` | 坐标轴物理标签 |

#### 主要方法

##### `read_var(name)`

读取物理量数组（自动挤压单例维度）。

```python
dens = ff.read_var("dens")
# 1D: 形状 (nblocks, Nx)
# 2D: 形状 (nblocks, Ny, Nx)
# 3D: 形状 (nblocks, Nz, Ny, Nx)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 变量名（如 `"dens"`, `"tele"`） |

**返回**: `np.ndarray`

**异常**:
- `KeyError` - 变量不存在

##### `read_var_flat(name)`

读取变量并展平为 1D 数组。

```python
dens_flat = ff.read_var_flat("dens")  # 形状 (nblocks * Nx,)
```

**返回**: `np.ndarray`

##### `read_grid()`

重建坐标网格。

```python
grid = ff.read_grid()
# grid = {
#   "x_1d": np.ndarray,      # 全局去重 x 坐标
#   "y_1d": np.ndarray,      # 全局去重 y 坐标（2D/3D）
#   "z_1d": np.ndarray,      # 全局去重 z 坐标（3D）
#   "x_global": list,        # 每块 x 坐标列表
#   "y_global": list,        # 每块 y 坐标列表
#   "z_global": list,        # 每块 z 坐标列表
#   "x_edges": list,         # 每块 x 边界列表
# }
```

**返回**: `dict`

##### `extract_var_yt_style(var_name="dens", use_cell_centers=True)`

**纯 h5py yt 风格数据提取** — 超算环境无需安装 yt。

使用 AMR 叶节点筛选+坐标重建+去重，实现与 yt 一致的数据提取。

```python
ff = FlashHDF5File("chk_0000")

# 1D Cartesian: 返回 (x, data)
x, dens = ff.extract_var_yt_style("dens")

# 2D Cylindrical R-Z: 返回 (r, z, data)
r, z, dens = ff.extract_var_yt_style("dens")

# 3D Cartesian: 返回 (x, y, z, data)
x, y, z, dens = ff.extract_var_yt_style("dens")

# 坐标系统自动检测
print(ff.coordinate_system)  # "cartesian_1d", "cylindrical_rz", "cartesian_3d"
print(ff.coord_labels)       # 坐标轴中文标签
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `var_name` | `str` | 变量名，默认 "dens" |
| `use_cell_centers` | `bool` | 是否使用单元中心坐标 |

**返回**: `tuple[np.ndarray, ...]` (维度不同返回不同)

**支持的坐标系统**:
| 系统 | 状态 | 返回值 |
|------|------|--------|
| `cartesian_1d` | ✅ 已实现 | `(x, data)` |
| `cylindrical_rz` | ✅ 已实现 | `(r, z, data)` |
| `cartesian_3d` | ✅ 已实现 | `(x, y, z, data)` |
| `cartesian_2d` | ❌ 未实现 | 抛 `NotImplementedError` |
| `cylindrical_3d` | ❌ 未实现 | 抛 `NotImplementedError` |

**实现原理**:
1. 读取 `node_type` 数据集，只使用叶节点 (node_type == 1)
2. 通过 `bounding box` 重建每个块的单元中心坐标
3. 展平所有块的数据，使用 `(x) / (x,y) / (x,y,z)` 元组去重
4. 与 yt 提取结果的差异通常在 float32 精度级别（< 1e-12）

##### `print_info(detailed=False)`

打印文件结构摘要。

```python
ff.print_info(detailed=True)  # 打印详细信息
```

##### `stats(varname, data_dict=None)`

计算变量统计量。

```python
stats = ff.stats("dens")
# stats = {"min": ..., "max": ..., "mean": ..., "median": ..., "std": ...}
```

**返回**: `dict`

##### `slice_1d(varname, grid=None, data_dict=None)`

对 1D 数据按 x 坐标排序拼接。

```python
x, y = ff.slice_1d("dens")  # 返回排序后的 x, y 数组
```

**返回**: `(np.ndarray, np.ndarray)`

#### 静态方法

##### `get_config(varname)`

获取变量配置信息。

```python
cfg = FlashHDF5File.get_config("dens")
# cfg = {"unit": "g/cm^3", "description": "Mass density", ...}
```

**返回**: `dict`

---

### 2.2 `DataCalculator` 类

派生变量计算器。

#### 构造函数

```python
DataCalculator(data_dict: dict)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `data_dict` | `dict` | {变量名: ndarray} 字典 |

#### 实例方法

##### `compute(varname)`

计算单个派生变量。

```python
calc = DataCalculator(container.data)
nele = calc.compute("nele")
```

**返回**: `np.ndarray`

##### `compute_all()`

计算所有可计算的派生变量。

```python
calc = DataCalculator(container.data)
derived = calc.compute_all()
# derived = {"nele": ndarray, "nion": ndarray, ...}
```

**返回**: `dict`

##### `get_available_derived()`

返回当前数据可计算的派生变量列表。

```python
calc = DataCalculator(container.data)
available = calc.get_available_derived()
# available = ["nele", "nion", "ls_nele", ...]
```

**返回**: `list[str]`

#### 实例方法（动态注册）

##### `register(varname, formula, description, unit, unit_si, to_si, depends)`

注册新的派生变量。

```python
calc = DataCalculator(container.data)
calc.register(
    varname="my_var",
    formula="ye * dens * NA",
    description="My custom variable",
    unit="1/cm^3",
    unit_si="1/m^3",
    to_si=1e6,
    depends=["ye", "dens"]
)
```

---

## 3. loader 模块

### 3.1 `FlashDataLoader` 类

高级数据加载器。

#### 构造函数

```python
FlashDataLoader(filepath: str)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `filepath` | `str` | HDF5 文件路径 |

#### 实例方法

##### `load(compute_derived=True)`

加载单个文件。

```python
container = loader.load(compute_derived=True)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `compute_derived` | `bool` | 是否计算派生变量 |

**返回**: `FlashDataContainer`

##### `load_vars(*var_names, compute_derived=True)`

仅加载指定变量。

```python
container = loader.load_vars("dens", "tele", compute_derived=True)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `*var_names` | `str` | 变量名列表 |
| `compute_derived` | `bool` | 是否计算派生变量 |

**返回**: `FlashDataContainer`

#### 静态方法

##### `load_folder(folder_path, pattern="*chk*", compute_derived=True, sort_by_time=True)`

批量加载文件夹中的所有文件。

```python
containers = FlashDataLoader.load_folder(
    "output_dir/",
    pattern="*chk*",
    compute_derived=True,
    sort_by_time=True
)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `folder_path` | `str` | 文件夹路径 |
| `pattern` | `str` | 文件匹配模式 |
| `compute_derived` | `bool` | 是否计算派生变量 |
| `sort_by_time` | `bool` | 是否按仿真时间排序 |

**返回**: `list[FlashDataContainer]`

---

### 3.2 `FlashDataContainer` 类

数据容器。

#### 主要属性

| 属性 | 类型 | 说明 |
|--------|------|------|
| `filepath` | `str` | 文件路径 |
| `ndim` | `int` | 维度 |
| `nblocks` | `int` | 块数 |
| `nx`, `ny`, `nz` | `int` | 每块网格点数 |
| `data` | `dict` | 原始变量字典 |
| `derived` | `dict` | 派生变量字典 |
| `grid` | `dict` | 网格信息 |
| `simulation_time` | `float` | 仿真时间 [s] |
| `simulation_step` | `int` | 时间步编号 |
| `laser_groups` | `dict` | 激光脉冲参数 |
| `varnames` | `list` | 物理量名称列表 |
| `config` | `dict` | 变量配置信息（DATA_CONFIG 副本） |

#### 主要方法

##### `get(varname)`

获取变量（先查 `data`，再查 `derived`）。

```python
dens = container.get("dens")
nele = container.get("nele")  # 从 derived 中查找
```

**返回**: `np.ndarray`

**异常**:
- `KeyError` - 变量不存在

##### `unit(varname)`

获取变量单位。

```python
unit = container.unit("dens")  # "g/cm^3"
```

**返回**: `str`

##### `to_si(varname)`

获取到 SI 单位的转换系数。

```python
to_si = container.to_si("dens")  # 1000.0
```

**返回**: `float`

---

## 4. plotter 模块

### 4.1 `FlashPlotter` 类

自适应维度绘图器。

#### 构造函数

```python
FlashPlotter(container: FlashDataContainer)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `container` | `FlashDataContainer` | 数据容器 |

#### 实例方法

##### `plot(varname, save_path=None, title=None, show=False, use_derived=False, **kwargs)`

自适应维度的主绘图接口。

```python
plotter.plot("dens", save_path="dens.png", title="Density (1D)")
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `varname` | `str` | 物理量名 |
| `save_path` | `str` | 保存路径 |
| `title` | `str` | 图像标题 |
| `show` | `bool` | 是否显示 |
| `use_derived` | `bool` | 是否优先从 derived 中查找 |

##### `plot_all(save_dir="output_processors_plots", var_names=None, include_derived=True)`

绘制所有（或指定）物理量并保存。

```python
saved_files = plotter.plot_all(save_dir="output/plots/")
```

**返回**: `list[str]` (保存的文件路径列表)

##### `plot_amr_grid(varname=None, save_path=None, title=None, show=False)`

绘制 AMR 块网格结构，可选覆盖物理量伪彩色。

```python
plotter.plot_amr_grid("dens", save_path="amr.png")
```

##### `plot_multi_panel(var_names, save_path=None)`

多物理量并排比较图。

```python
plotter.plot_multi_panel(
    var_names=["dens", "tele", "nele"],
    save_path="multi_panel.png"
)
```

#### 类方法

##### `plot_folder(folder_path, var_name="dens", save_dir=None, pattern="*chk*", compute_derived=True)`

批量处理文件夹中所有 HDF5 文件并绘图。

```python
saved = FlashPlotter.plot_folder(
    "output_dir/",
    var_name="dens",
    save_dir="plots/"
)
```

**返回**: `list[str]` (保存的文件路径列表)

##### `plot_folder_all_vars(folder_path, save_dir=None, pattern="*chk*", var_names=None)`

批量处理文件夹，每个文件绘制多个变量。

```python
saved = FlashPlotter.plot_folder_all_vars(
    "output_dir/",
    save_dir="plots/",
    var_names=["dens", "tele"]
)
```

**返回**: `list[str]`

---

## 5. 异常情况

### 5.1 异常类型

| 异常 | 说明 | 处理方法 |
|------|------|----------|
| `FileNotFoundError` | HDF5 文件不存在 | 检查文件路径 |
| `KeyError` | 变量不存在于 HDF5 文件 | 使用 `ff.varnames` 查看可用变量 |
| `ValueError` | 数据形状无法解析 | 报告 bug |
| `MemoryError` | 内存不足（3D 大数据） | 仅加载部分变量 |

### 5.2 错误处理示例

```python
from output_processors.hdf5processor import FlashHDF5File

try:
    ff = FlashHDF5File("file.h5")
    dens = ff.read_var("dens")
except FileNotFoundError:
    print("错误: 文件不存在")
except KeyError:
    print(f"错误: 变量 'dens' 不存在")
    print(f"可用变量: {ff.varnames}")
except Exception as e:
    print(f"未知错误: {e}")
finally:
    ff.close()
```

---

## 6. 配置参数

### 6.1 `DATA_CONFIG` 字典

`DATA_CONFIG` 是 `flash_hdf5.py` 中定义的全局字典，存储所有已知变量的元信息。

```python
from output_processors.hdf5processor import DATA_CONFIG

# 查看变量配置
cfg = DATA_CONFIG.get("dens", {})
print(cfg)
# {
#   "unit": "g/cm^3",
#   "unit_si": "kg/m^3",
#   "to_si": 1000.0,
#   "description": "Mass density",
#   "category": "raw"
# }
```

### 6.2 `VAR_ALIASES` 字典

变量别名映射。

```python
from output_processors.hdf5processor import VAR_ALIASES

# 查看别名
print(VAR_ALIASES)
# {"targ": ["target"], "cham": ["ch", "ablator"], ...}
```

---

## 相关文档

- 使用说明: `docs/output_processors_usage.md`
- 自定义变量教程: `docs/how_to_add_custom_variables.md`
- 性能调优指南: `docs/performance_tuning.md`

---

**维护者**: WorkBuddy AI
**最后更新**: 2026-07-04
