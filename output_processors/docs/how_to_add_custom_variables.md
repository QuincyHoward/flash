# 如何新增自定义变量

> 本教程介绍如何在 `output_processors` 包中新增自定义变量（派生变量）。
> 最后更新: 2026-07-04

---

## 目录

1. [简介](#1-简介)
2. [方法 1: 使用 DataCalculator.register()](#2-方法-1-使用-datacalculatorregister)
3. [方法 2: 直接修改 DATA_CONFIG](#3-方法-2-直接修改-data_config)
4. [变量命名规范](#4-变量命名规范)
5. [示例：添加物理变量](#5-示例添加物理变量)
6. [调试与验证](#6-调试与验证)
7. [常见问题](#7-常见问题)

---

## 1. 简介

`output_processors` 使用 `DataCalculator` 类管理派生变量。派生变量是基于 HDF5 文件中的原始变量计算得到的新变量。

### 变量类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **原始变量** | HDF5 文件中直接存储的变量 | `dens`, `tele`, `tion`, `pres` |
| **派生变量** | 通过公式计算得到的新变量 | `nele`, `nion`, `dens_targ`, `ls_nele` |

### 已注册的变量

查看 `output_processors/hdf5processor/flash_hdf5.py` 中的 `DATA_CONFIG` 字典：

```python
from output_processors.hdf5processor import DATA_CONFIG

# 打印所有已注册变量
for vname, cfg in DATA_CONFIG.items():
    cat = "原始" if cfg["category"] == "raw" else "派生"
    print(f"{vname:15s} [{cat}] {cfg['unit']:12s} {cfg['description']}")
```

---

## 2. 方法 1: 使用 DataCalculator.register()

**适用场景**: 动态注册新的派生变量（无需修改源代码）。

### 2.1 基本用法

```python
from output_processors.hdf5processor import DataCalculator, NA

# 注册公式: nele = ye * dens * NA
DataCalculator.register(
    varname="nele",
    formula="ye * dens * NA",
    description="Electron number density",
    unit="1/cm^3",
    unit_si="1/m^3",
    to_si=1e6,
    depends=["ye", "dens"]
)
```

### 2.2 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `varname` | `str` | 变量名（如 `"nele"`） |
| `formula` | `str` | 计算公式（支持变量名、NA 常数） |
| `description` | `str` | 物理意义描述 |
| `unit` | `str` | 常用单位（如 `"1/cm^3"`） |
| `unit_si` | `str` | SI 单位（如 `"1/m^3"`） |
| `to_si` | `float` | 从常用单位到 SI 的转换系数 |
| `depends` | `list` | 依赖变量列表（可选，自动推断） |

### 2.3 支持的操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `+` | 加法 | `"dens + 1.0"` |
| `-` | 减法 | `"tele - tion"` |
| `*` | 乘法 | `"ye * dens * NA"` |
| `/` | 除法 | `"pres / pele"` |
| `**` | 幂 | `"dens**2"` |
| `()` | 括号 | `"(ye + sumy) / 2"` |

### 2.4 支持的常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `NA` | 6.02214076e+23 | 阿伏伽德罗常数 |

### 2.5 完整示例

```python
from output_processors.hdf5processor import DataCalculator, NA

# 示例 1: 电子数密度
DataCalculator.register(
    varname="nele",
    formula="ye * dens * NA",
    description="Electron number density",
    unit="1/cm^3",
    unit_si="1/m^3",
    to_si=1e6
)

# 示例 2: 电离度
DataCalculator.register(
    varname="ionization_degree",
    formula="ye / (ye + sumy)",
    description="Ionization degree (0-1)",
    unit="1",
    unit_si="1",
    to_si=1.0
)

# 示例 3: 电子压强 (pele = nele * KB * tele)
KB = 1.380649e-16  # 玻尔兹曼常数 (erg/K)
DataCalculator.register(
    varname="pele_calc",
    formula="ye * dens * NA * KB * tele",
    description="Electron pressure (erg/cm^3)",
    unit="erg/cm^3",
    unit_si="Pa",
    to_si=0.1
)

# 使用
from output_processors.loader import FlashDataLoader

loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)

nele = container.derived["nele"]  # 自动计算
```

---

## 3. 方法 2: 直接修改 DATA_CONFIG

**适用场景**: 新增原始变量（HDF5 文件中存在，但未在 `DATA_CONFIG` 中注册）。

### 3.1 DATA_CONFIG 结构

`DATA_CONFIG` 是字典，存储所有已知变量的元信息。

```python
DATA_CONFIG = {
    "dens": {
        "unit": "g/cm^3",
        "unit_si": "kg/m^3",
        "to_si": 1000.0,
        "description": "Mass density",
        "category": "raw",  # "raw" 或 "derived"
    },
    "nele": {
        "unit": "1/cm^3",
        "unit_si": "1/m^3",
        "to_si": 1e6,
        "description": "Electron number density",
        "category": "derived",
        "depends": ["ye", "dens"],
        "formula": "ye * dens * NA",
    },
    ...
}
```

### 3.2 添加新原始变量

如果 HDF5 文件中有新的数据集（如 `magx` 表示 X 方向磁场），需要添加到 `DATA_CONFIG`：

编辑 `output_processors/hdf5processor/flash_hdf5.py`：

```python
DATA_CONFIG = {
    # ... 现有变量 ...

    # 新增: X 方向磁场
    "magx": {
        "unit": "Gauss",
        "unit_si": "T",
        "to_si": 1e-4,
        "description": "Magnetic field (X direction)",
        "category": "raw",
    },

    # 新增: Y 方向磁场
    "magy": {
        "unit": "Gauss",
        "unit_si": "T",
        "to_si": 1e-4,
        "description": "Magnetic field (Y direction)",
        "category": "raw",
    },
}
```

### 3.3 添加新派生变量到 DATA_CONFIG

也可以直接在 `DATA_CONFIG` 中添加派生变量（与方法 1 等效）：

```python
DATA_CONFIG = {
    # ... 现有变量 ...

    # 新增派生变量: 磁压 (B^2 / (8*pi))
    "mag_pressure": {
        "unit": "erg/cm^3",
        "unit_si": "Pa",
        "to_si": 0.1,
        "description": "Magnetic pressure",
        "category": "derived",
        "depends": ["magx", "magy", "magz"],
        "formula": "(magx**2 + magy**2 + magz**2) / (8 * 3.1415926535)",
    },
}
```

---

## 4. 变量命名规范

### 4.1 命名约定

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 原始变量 | 与 HDF5 数据集名一致 | `dens`, `tele`, `pres` |
| 派生变量 | 描述性名称，小写 + 下划线 | `nele`, `ls_nele`, `temp_gradient` |
| 梯度尺度长度 | `ls_<varname>` | `ls_nele`, `ls_tele` |
| 组件密度 | `dens_<component>` | `dens_targ`, `dens_cham` |

### 4.2 避免冲突

- ❌ 不要覆盖现有变量名（如 `dens`, `tele`）
- ✅ 使用描述性名称
- ✅ 在 `description` 字段中详细说明变量含义

---

## 5. 示例：添加物理变量

### 5.1 示例 1: 添加电子压强 (pele)

电子压强公式: `pele = nele * KB * tele`

```python
from output_processors.hdf5processor import DataCalculator

KB = 1.380649e-16  # 玻尔兹曼常数 (erg/K)

# 注册派生变量
DataCalculator.register(
    varname="pele_calc",
    formula="ye * dens * NA * KB * tele",
    description="Electron pressure (erg/cm^3)",
    unit="erg/cm^3",
    unit_si="Pa",
    to_si=0.1
)

# 使用
from output_processors.loader import FlashDataLoader

loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)

pele = container.derived["pele_calc"]
print(f"电子压强范围: [{pele.min():.4e}, {pele.max():.4e}]")
```

### 5.2 示例 2: 添加熵 (entropy)

理想气体熵公式: `S = pres / (dens^gamma)`

```python
from output_processors.hdf5processor import DataCalculator

GAMMA = 5.0 / 3.0  # 绝热指数

# 注册派生变量
DataCalculator.register(
    varname="entropy",
    formula="pres / (dens**GAMMA)",
    description="Entropy (erg/cm^3 / (g/cm^3)^gamma)",
    unit="erg/cm^3 / (g/cm^3)^gamma",
    unit_si="J/m^3 / (kg/m^3)^gamma",
    to_si=1.0
)
```

### 5.3 示例 3: 添加梯度标长

梯度标长公式: `L = var / |grad(var)|`

```python
from output_processors.hdf5processor import DataCalculator, NA

# 注册派生变量（需要在 _CALC_FUNCS 中注册特殊计算函数）
# 注意: 复杂数值计算需要在 flash_hdf5.py 中添加专用函数

# 当前已实现的梯度标长变量:
#   - ls_nele: 电子密度梯度标长
#   - ls_tele: 电子温度梯度标长
```

---

## 6. 调试与验证

### 6.1 验证变量注册

```python
from output_processors.hdf5processor import DATA_CONFIG, DataCalculator

# 查看所有已注册的变量
print("已注册变量:")
for vname, cfg in DATA_CONFIG.items():
    cat = "原始" if cfg["category"] == "raw" else "派生"
    print(f"  {vname:15s} [{cat}] {cfg['description']}")

# 查看可计算的派生变量
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=False)
calc = DataCalculator(container.data)
available = calc.get_available_derived()
print(f"\n可计算的派生变量: {available}")
```

### 6.2 测试变量计算

```python
from output_processors.loader import FlashDataLoader

# 加载数据
loader = FlashDataLoader("file.h5")
container = loader.load(compute_derived=True)

# 检查变量是否存在
varname = "my_var"
if varname in container.derived:
    print(f"{varname} 计算成功!")
    print(f"  形状: {container.derived[varname].shape}")
    print(f"  范围: [{container.derived[varname].min():.4e}, {container.derived[varname].max():.4e}]")
else:
    print(f"{varname} 不存在!")
    print("可用派生变量:", list(container.derived.keys()))
```

### 6.3 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| `KeyError: 'varname'` | 变量名不存在于 DATA_CONFIG | 检查拼写，或先注册变量 |
| `ValueError: shape mismatch` | 公式返回形状不一致 | 确保公式返回与 `dens` 相同形状的数组 |
| `NameError: name 'NA' is not defined` | 公式中使用了未定义的常量 | 在 formula 中直接使用 `NA`（已内置） |

---

## 7. 常见问题

### Q1: 注册后变量没有出现？

**A**: 检查以下步骤：
1. 注册代码是否在 `load(compute_derived=True)` **之前**执行？
2. 变量名是否拼写正确？
3. 公式中引用的变量是否存在于 `DATA_CONFIG` 中？

### Q2: 如何覆盖已有变量？

**A**: 重新注册同名变量会覆盖之前的注册：

```python
# 第一次注册
DataCalculator.register("my_var", formula="dens * 1.0", ...)

# 覆盖注册
DataCalculator.register("my_var", formula="dens * 2.0", ...)  # 覆盖
```

### Q3: 如何在项目启动时自动注册变量？

**A**: 在项目的 `__init__.py` 或启动脚本中添加注册代码：

```python
# myproject/__init__.py
from output_processors.hdf5processor import DataCalculator, NA

# 自动注册项目特定变量
def register_project_variables():
    DataCalculator.register("qc_nele", formula="ye * dens * NA", ...)
    # ... 其他变量 ...

register_project_variables()
```

### Q4: 派生变量可以用于 2D/3D 数据吗？

**A**: 可以！公式会自动应用于所有维度。但需要注意：
- 公式中的操作必须支持数组运算（如 `*`、`+`）
- 如果需要复杂数值计算（如梯度），需要在 `flash_hdf5.py` 中添加专用函数

---

## 相关文档

- 使用说明: `docs/output_processors_usage.md`
- API 参考手册: `docs/api_reference.md`

---

**维护者**: WorkBuddy AI
**最后更新**: 2026-07-04
