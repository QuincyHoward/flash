# FLASH Python 数据分析库

## 概述

FLASH 提供了 Python 数据分析库，位于 `tools/python/`，用于后处理 FLASH HDF5 仿真输出。该库以 `flash` Python 包的形式提供，支持数据分析、可视化、文件读取和运行时参数 DSL 解析。

## 目录结构

```
python/
├── __init__.py          # 包入口, 加载 metadata.json
├── analysis.py          # 物理分析函数
├── output.py            # 输出文件读取与可视化
├── utils.py             # 工具函数
├── yt_derived_fields.py  # yt 导出场注册
├── _argparse.py         # argparse backport
├── dsl/                  # 领域特定语言
│   ├── __init__.py
│   ├── configuration.py  # Config 文件解析器
│   └── runtime_parameters.py  # 运行时参数文件解析
└── flashfile/            # HDF5 文件读取
    ├── FlashFile.py      # 通用 HDF5 读取器
    ├── FlashFile1d.py    # 1D 数据读取
    ├── FlashFile2d.py    # 2D 数据读取
    ├── sim_files.py      # 文件查找
    ├── timedep.py        # 时变数据查看器
    └── radmgd.py         # 多群辐射扩散通量
```

## 1. 包初始化 (`__init__.py`)

加载 `metadata.json`，导出:
- `__version__` — 版本字符串（格式：`4.8 (git_hash)`）
- `FLASH_SRC_DIR` — FLASH 源代码路径
- `FLASH_CLEAN_SRC_DIR` — 干净源码路径
- `MPIRUN_CMD` — MPI 运行命令

## 2. 物理分析 (`analysis.py`)

**依赖**: `numpy`, `scipy.optimize`

```python
from flash import analysis
```

### `fit_power_law(t, r)`

拟合 $R = R_0 t^\alpha$ 幂律（如激波传播）。

**参数**:
- `t` — 时间数组
- `r` — 半径数组

**返回**: `(r0, alpha)` — 拟合系数

### `shock_detect(r, v, threshold, min_threshold)`

检测激波位置。

**参数**:
- `r` — 位置数组
- `v` — 速度/密度数组
- `threshold` — 初始梯度阈值
- `min_threshold` — 最低阈值下限

**返回**: `(shock_r, shock_v, idx)` — 激波位置、值、索引

**算法**: 计算 `dv/dr`，通过梯度符号变化定位激波，逐步降低阈值直到找到。

## 3. 输出文件处理 (`output.py`)

**依赖**: `numpy`, `scipy.interpolate`, `yt`, `flash.analysis`, `flash.yt_derived_fields`

```python
from flash import output
```

### `slice(axis, coord, field, pf)`

沿指定轴切片，将 AMR 数据插值到均匀网格。

**参数**:
- `axis` — 切片轴 (0=x, 1=y, 2=z)
- `coord` — 切片坐标
- `field` — 物理场名（如 `'dens'`）
- `pf` — yt 参数文件对象或 HDF5 文件路径

**返回**: `(x, y, z)` — 均匀网格坐标和场数据

### `slice_gradient(axis, coord, field, pf)`

切片 + 计算梯度。

**返回**:
- `adat`, `bdat` — 两个方向的坐标
- `dfdadat`, `dfdbdat` — 两个方向的梯度
- `magdat` — 梯度幅值

### `lineout(p1, p2, field, pf)`

沿两点提取射线数据。

**返回**: `(x, y, z, v)` — 射线上的坐标和场值

### `shock_on_lineout(p1, p2, field, pf)`

在射线上检测激波。

**返回**: `(shock_position, shock_value)`

### `load_laser_dat(filename)`

读取 FLASH `LaserEnergyProfile.dat` 文件为 numpy 结构化数组。

**缓存机制**: `slice_cache` 和 `ray_cache` 缓存已计算的切片/射线，避免重复计算。

## 4. 工具函数 (`utils.py`)

```python
from flash import utils
```

| 函数 | 说明 |
|------|------|
| `strip_comments(line, comment_char, quote_char)` | 去除行中的注释 |
| `message(s)` | 格式化成功消息（终端绿色） |
| `warning(s)` | 格式化警告消息（终端黄色） |
| `failure(s)` | 格式化失败消息（终端红色） |

## 5. yt 导出场 (`yt_derived_fields.py`)

向 yt 注册 FLASH 专属的导出场，注册后 yt 可直接使用这些场名。

| 场名 | 公式 | log10 |
|------|------|-------|
| `nion` | `dens * sumy * 6.022E23` | 是 |
| `abar` | `1.0 / sumy` | 否 |
| `velo` | `sqrt(velx^2 + vely^2 + velz^2)` | 是 |
| `velr_rz` | `velx`（柱坐标径向） | 是 |
| `velz_rz` | `vely`（柱坐标轴向） | 是 |
| `velt_rz` | `velz`（柱坐标角向） | 是 |

**注意**: `NA = 6.022E23`（阿伏伽德罗常数）用于 `nion` 计算。

## 6. HDF5 文件读取 (`flashfile` 子包)

### 6.1 FlashFile（通用基类）

```python
from flash.flashfile import FlashFile
ff = FlashFile('sedov_hdf5_chk_0010')
```

**方法**:

| 方法 | 说明 |
|------|------|
| `integerScalar(name, rtp)` | 读取整型标量 |
| `realScalar(name, rtp)` | 读取浮点标量 |
| `stringScalar(name, rtp)` | 读取字符串标量 |
| `varnames()` | 返回所有变量名列表 |
| `exists(name)` | 检查 HDF5 节点是否存在 |
| `var(name)` | 获取变量数据节点 |

**兼容性**: 支持 PyTables 2.x 和 3.x。

### 6.2 FlashFile1d（1D 读取）

```python
from flash.flashfile import FlashFile1d
ff1d = FlashFile1d('sim_hdf5_chk_0001')
coord = ff1d.coord()          # 1D 单元中心坐标
data = ff1d.getVar('dens')    # 密度数据
bounds = ff1d.blockBounds()   # 叶块边界
```

### 6.3 FlashFile2d（2D 读取）

```python
from flash.flashfile import FlashFile2d
ff2d = FlashFile2d('sim_hdf5_chk_0001')
ug = ff2d.uniformGrid('dens')  # AMR 投影到均匀网格
data = ff2d.getVar('dens')     # 1D 展平数据
```

支持 AMR 细化级别自适应下采样。

### 6.4 辐射通量计算 (`radmgd.py`)

多群辐射扩散（MGD）通量分析:

```python
from flash.flashfile import FlashFile1d, radmgd
ff = FlashFile1d('rad_hdf5_chk_0001')

# 统计辐射群组数
ng = radmgd.numGroups(ff)

# 计算通量限制扩散通量
flux = radmgd.computeFlux(ff, opac_func, alpha=1.0)
```

**通量公式**: $F = -D \nabla u$，其中 $D = 1/(3\kappa + |\nabla u|/(3\times 10^{10} \alpha u + \epsilon))$

### 6.5 文件查找 (`sim_files.py`)

```python
from flash.flashfile import sim_files
files = sim_files('sedov', ftype='chk', directory='.')
# 返回: ['sedov_hdf5_chk_0001', 'sedov_hdf5_chk_0002', ...]
```

### 6.6 时变查看器 (`timedep.py`)

基于 matplotlib 键盘事件的帧浏览工具:

```python
from flash.flashfile import TimeDep
import matplotlib.pyplot as plt

def paint(frame, fig):
    fig.clear()
    # 绘制第 frame 帧数据

td = TimeDep(plt.gcf(), lambda: 100, 0, paint)
plt.show()
```

**键盘控制**:
- `→` / `←`: 下一帧/上一帧
- `PageUp` / `PageDown`: 跳 10 帧

## 7. 运行时参数 DSL (`dsl/runtime_parameters.py`)

```python
from flash.dsl import runtime_parameters

# 加载参数文件
params = runtime_parameters.load('flash.par')
print(params['dens'])        # 浮点数
print(params['plot_var'])    # 嵌套列表

# 写入参数文件
runtime_parameters.dump(params, 'new_flash.par')
```

**类型转换规则**:
| 格式 | Python 类型 |
|------|-------------|
| `'string'` 或 `"string"` | `str` |
| `123`, `-45` | `int` |
| `1.23`, `1e-3` | `float` |
| `.true.`, `.false.` | `bool` |
| `a_1_2 = value` | 嵌套列表 `[[v11,v12],[v21,v22]]` |

## 8. Config 文件 DSL (`dsl/configuration.py`)

核心类解析 FLASH 单元配置:

```python
from flash.dsl.configuration import Configuration, ConfigurationUnion

cfg = Configuration('source/Simulation/SimulationMain/Sedov/Config', top_unit=True)
union = ConfigurationUnion([cfg1, cfg2])
print(union.variable_names)   # 所有变量名
print(union.nvar)             # 总变量数
```

**支持的指令**: `D`, `PARAMETER`, `VARIABLE`, `FACEVAR`, `LIBRARY`, `GUARDCELLS`, `FLUX`, `SPECIES`, `MASS_SCALAR`, `PARTICLEPROP`, `PARTICLETYPE`, `PARTICLEMAP`, `SUGGEST`, `REQUIRES`, `REQUESTS`, `EXCLUSIVE`, `KERNEL`, `LINKIF`, `CONFLICTS`, `PPDEFINE`, `NONREP`, `CHILDORDER`, `DATAFILES`, `SCRATCHVAR*`, `EOSMAP`

**预处理**: `IF`, `ELSEIF/ELIF`, `ELSE`, `ENDIF`, `USESETUPVARS`, `SETUPERROR`
