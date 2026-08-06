# gen_config — FLASH Config 文件生成器说明文档

## 目录
1. [概述](#概述)
2. [Config 文件格式详解](#config-文件格式详解)
3. [gen_config 生成器 API](#gen_config-生成器-api)
4. [使用示例](#使用示例)
5. [参考示例 (refs/)](#参考示例-refs)
6. [关键参数说明](#关键参数说明)
7. [常见问题](#常见问题)

---

## 概述

`gen_config` 子包用于生成 FLASH 仿真的 `Config` 文件。Config 文件是 FLASH 仿真的关键配置文件，定义了：
- 所需的物理模块 (`REQUIRES`)
- 可选的物理模块 (`REQUESTS`)
- 运行时参数 (`PARAMETER`)
- 额外变量 (`VARIABLE`)
- 数据文件 (`DATAFILES`)
- 编译时选项 (`PPDEFINE`, `USESETUPVARS`)

**生成器类型**: 自包含（硬编码默认模板）
**默认模板来源**: `SimulationMain/LaserSlab/Config`
**输出文件**: `Config`（无扩展名）

---

## Config 文件格式详解

### 1. 基本结构

```
# 注释
REQUIRES <模块路径>
REQUESTS <模块路径>

PPDEFINE <宏名称> <值>

SPECIES <物种名称>

USESETUPVARS <设置变量>
IF <条件>
   <指令>
ENDIF

D <参数描述>
PARAMETER <参数名> <类型> <默认值> [范围]

VARIABLE <变量名> TYPE: <类型>

DATAFILES <文件名>
```

### 2. 关键指令详解

#### REQUIRES 和 REQUESTS

- `REQUIRES`: 必需的物理模块，如果缺失则设置失败
- `REQUESTS`: 可选的物理模块，如果可用则包含

**示例**:
```
REQUIRES Driver
REQUIRES physics/Hydro
REQUIRES physics/Eos

REQUESTS physics/Diffuse/DiffuseMain/Unsplit
REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
```

**常用模块路径**:
| 模块 | 路径 |
|------|------|
| 流体力学 | `physics/Hydro` |
| EOS (多温) | `physics/Eos/EosMain/multiTemp/Gamma` |
| EOS (表) | `physics/Eos/EosMain/Tabulated` |
| 激光 | `+laser` (setup选项) |
| 能量沉积 | `physics/EnergyDeposition` |
| 热传导 | `physics/Diffuse/DiffuseMain/Unsplit` |
| 不透明度 | `physics/materialProperties/Opacity` |
| 粒子 | `Particles/ParticlesMain` |
| HDF5 I/O | `+hdf5typeio` (setup选项) |

#### PARAMETER 定义

定义仿真运行时参数，可以在 `.par` 文件中覆盖。

**格式**:
```
D <参数描述>
PARAMETER <参数名> <类型> <默认值> [有效范围]
```

**类型**:
- `STRING`: 字符串
- `REAL`: 浮点数
- `INTEGER`: 整数
- `BOOLEAN`: 布尔值 (`.true.`/`.false.`)

**示例**:
```
D sim_rhoTarg Initial target density
PARAMETER sim_rhoTarg   REAL 2.7

D sim_initGeom Initial geometry
PARAMETER sim_initGeom STRING "slab" ["slab","sphere"]

D useLaser Use laser or not
PARAMETER useLaser BOOLEAN .false.
```

#### VARIABLE 声明

声明额外的流体变量。

**格式**:
```
D <变量描述>
VARIABLE <变量名> TYPE: <类型>
```

**类型**:
- `PER_MASS`: 比质量（如密度）
- `PER_VOLUME`: 比体积
- `FACEVAR`: 面变量
- `MASS_SCALAR`: 质量标量

**示例**:
```
D lase_variable irradiated energy density
VARIABLE lase TYPE: PER_VOLUME

D sele_variable specific entropy
MASS_SCALAR sele EOSMAP: SELE
```

#### DATAFILES 声明

声明仿真所需的数据文件（如EOS表、不透明度表）。

**格式**:
```
DATAFILES <文件名>
```

**示例**:
```
DATAFILES al-imx-003.cn4
DATAFILES he-imx-005.cn4
DATAFILES al-imx-003.ses
```

这些文件会在 `setup` 时复制到仿真目录。

#### PPDEFINE 预处理器宏

定义Fortran预处理器宏。

**格式**:
```
PPDEFINE <宏名称> <值>
```

**示例**:
```
PPDEFINE PLANAR_SEDOV       0
PPDEFINE CYLINDRICAL_SEDOV  1
PPDEFINE SPHERICAL_SEDOV    2
```

在Fortran代码中可以使用:
```fortran
#if defined(PLANAR_SEDOV)
    geo = 0
#endif
```

#### USESETUPVARS 和条件编译

根据setup命令行参数条件包含配置。

**格式**:
```
USESETUPVARS <变量名>

IF <变量名>
   <指令>
ENDIF
```

**示例**:
```
USESETUPVARS ThreeT

IF ThreeT
   REQUESTS physics/Diffuse/DiffuseMain/Unsplit
   REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
ENDIF
```

**使用**:
```bash
./setup -auto LaserSlab -2d +3t   # 包含 ThreeT 块
./setup -auto LaserSlab -2d       # 不包含 ThreeT 块
```

#### SPECIES 物种声明

声明模拟中的物种（材料）。

**格式**:
```
SPECIES <物种名称>
```

**示例**:
```
SPECIES cham    # 腔室材料
SPECIES targ    # 靶材料
```

在setup命令行中指定:
```bash
./setup -auto LaserSlab -2d species=cham,targ
```

---

## gen_config 生成器 API

### 类: ConfigGenerator

**位置**: `gen_config/generator.py`

**描述**: 自包含的Config文件生成器，使用硬编码的默认模板。

### 初始化

```python
from gen_config import ConfigGenerator

generator = ConfigGenerator()
```

### 方法: generate()

生成Config文件内容字符串。

**签名**:
```python
def generate(
    self,
    simulation_path: str = "hello/LaserSlab1d_new",
    target_material: Any = None,
    chamber_gas: Any = None,
    extra_datafiles: Optional[List[str]] = None,
    include_thomson: bool = False,
) -> str:
```

**参数**:
- `simulation_path`: 仿真路径标识（用于注释）
- `target_material`: 靶材 Material 对象（预留，暂不处理）
- `chamber_gas`: 腔室气体 Material 对象（预留，暂不处理）
- `extra_datafiles`: 额外的 DATAFILES 列表
- `include_thomson`: 是否包含 Thomson 散射诊断

**返回**: Config文件内容字符串

### 方法: save()

生成并保存Config文件。

**签名**:
```python
def save(
    self,
    output_path: Union[str, Path],
    simulation_path: str = "hello/LaserSlab1d_new",
    target_material: Any = None,
    chamber_gas: Any = None,
    extra_datafiles: Optional[List[str]] = None,
    include_thomson: bool = False,
) -> Path:
```

**参数**:
- `output_path`: 输出文件路径
- 其他参数同 `generate()`

**返回**: 输出文件的 Path 对象

---

## 使用示例

### 示例 1: 生成默认 Config

```python
from gen_config import ConfigGenerator

generator = ConfigGenerator()

# 生成默认Config（基于LaserSlab模板）
content = generator.generate()

# 保存到文件
output_path = generator.save("path/to/Simulation/Config")
print(f"Saved to: {output_path}")
```

### 示例 2: 生成包含 Thomson 散射诊断的 Config

```python
generator = ConfigGenerator()

# 包含Thomson散射诊断变量
content = generator.generate(
    simulation_path="hello/LaserSlab1d_diag",
    include_thomson=True,
)

# 保存
generator.save("path/to/Simulation/Config", include_thomson=True)
```

### 示例 3: 添加额外的 DATAFILES

```python
generator = ConfigGenerator()

# 添加额外的EOS表
content = generator.generate(
    extra_datafiles=["polystyrene-imx-008.cn4", "au-imx-001.cn4"],
)

# 保存
generator.save(
    "path/to/Simulation/Config",
    extra_datafiles=["polystyrene-imx-008.cn4"],
)
```

### 示例 4: 自定义 Config（高级）

如果需要完全不同的Config，可以直接修改生成的字符串：

```python
generator = ConfigGenerator()

# 生成默认Config
content = generator.generate()

# 修改内容（例如，更改仿真类型从LaserSlab到Sod）
content = content.replace(
    "Configuration file for hello/LaserSlab1d_new simulation",
    "Configuration file for Sod shock-tube simulation"
)
content = content.replace(
    "REQUIRES physics/Hydro",
    "REQUIRES physics/Hydro\nREQUIRES physics/Eos/EosMain/Multigamma"
)

# 保存
with open("path/to/Simulation/Config", "w") as f:
    f.write(content)
```

---

## 参考示例 (refs/)

`gen_config/refs/` 目录包含 186 个Config文件示例，来自不同的FLASH仿真。

### 主要示例列表

| 文件名 | 仿真类型 | 关键特征 |
|--------|---------|---------|
| `Config` (无数字) | 基础模板 | 参考用 |
| `Config (10)` | ... | ... |
| `Config (100)` | ... | ... |
| ... | ... | ... |

### 如何参考这些示例

1. **阅读示例**: 直接查看 `refs/` 中的Config文件
2. **提取参数**: 了解特定仿真需要哪些参数
3. **修改模板**: 基于默认模板，添加需要的PARAMETER和VARIABLE

**示例**: 参考 `Blast2` 的Config

```bash
# 查看 Blast2 的Config
cat gen_config/refs/Config

# 提取关键参数
# - PPDEFINE: PLANAR_SEDOV, CYLINDRICAL_SEDOV, SPHERICAL_SEDOV
# - PARAMETER: sim_rhoIn, sim_pIn, sim_EIn, sim_rIn
# - SPECIES: FLD1, FLD2, FLD3
```

---

## 关键参数说明

### 激光-等离子体仿真参数

这些参数通常出现在 `LaserSlab` 类型的仿真中：

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `sim_initGeom` | STRING | "slab" | 初始几何 ("slab" 或 "sphere") |
| `sim_targetRadius` | REAL | 0.0050 | 靶半径 |
| `sim_targetHeight` | REAL | 0.0250 | 靶高度 |
| `sim_vacuumHeight` | REAL | 0.0200 | 真空区域厚度 |
| `sim_rhoTarg` | REAL | 2.7 | 靶密度 (g/cc) |
| `sim_teleTarg` | REAL | 290.11375 | 靶初始电子温度 (K) |
| `sim_tionTarg` | REAL | 290.11375 | 靶初始离子温度 (K) |
| `sim_tradTarg` | REAL | 290.11375 | 靶初始辐射温度 (K) |
| `sim_eosTarg` | STRING | "eos_tab" | 靶EOS类型 ("eos_tab" 或 "eos_gam") |
| `sim_rhoCham` | REAL | 2.655e-07 | 腔室密度 (g/cc) |
| `sim_teleCham` | REAL | 290.11375 | 腔室电子温度 (K) |
| `sim_eosCham` | STRING | "eos_gam" | 腔室EOS类型 |

### 流体力学测试参数

这些参数通常出现在 `Sod`、`Sedov` 等测试中：

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `sim_rhoLeft` | REAL | 1.0 | 左状态密度 |
| `sim_rhoRight` | REAL | 0.125 | 右状态密度 |
| `sim_pLeft` | REAL | 1.0 | 左状态压力 |
| `sim_pRight` | REAL | 0.1 | 右状态压力 |
| `sim_uLeft` | REAL | 0.0 | 左状态速度 |
| `sim_uRight` | REAL | 0.0 | 右状态速度 |
| `sim_posn` | REAL | 0.5 | 间断位置 |
| `sim_xangle` | REAL | 0.0 | 间断法线与x轴夹角 (度) |
| `sim_yangle` | REAL | 90.0 | 间断法线与y轴夹角 (度) |

---

## 常见问题

### 1. 如何为新的仿真类型生成Config？

**答**: 当前生成器使用硬编码的LaserSlab模板。如需其他类型，可以：
1. 生成默认Config
2. 手动修改内容
3. 或将需要的Config示例复制到 `refs/` 目录，并扩展生成器以支持多个模板

### 2. 如何添加自定义参数？

**答**: 修改生成的Config内容字符串，添加PARAMETER行：

```python
content = generator.generate()

# 添加自定义参数
custom_params = """
D my_custom_param My custom parameter
PARAMETER my_custom_param REAL 1.0
"""

# 插入到 "RUNTIME PARAMETERS" 部分之后
lines = content.split("\n")
insert_idx = 0
for i, line in enumerate(lines):
    if "RUNTIME PARAMETERS" in line:
        insert_idx = i + 3  # 跳过注释行
        break
lines.insert(insert_idx, custom_params)
content = "\n".join(lines)
```

### 3. DATAFILES 文件放在哪里？

**答**: DATAFILES 声明的文件必须位于以下位置之一：
- FLASH的 `sites/` 目录
- 仿真的源目录
- `setup` 命令的 `-site` 选项指定的目录

在PhySimX中，EOS数据文件通常放在 `gen_eos_op/eos_op_data/` 目录，并在 `setup` 时复制。

### 4. 如何验证生成的Config是否正确？

**答**: 使用FLASH的 `setup` 命令验证：

```bash
cd /path/to/FLASH4.8
./setup -auto MySimulation -1d -nxb=10 +hdf5typeio
```

如果Config有误，setup会报错并指示哪一行有问题。

---

## 进阶：扩展生成器支持多个模板

当前生成器只支持LaserSlab模板。如需支持多个模板，可以扩展生成器：

```python
class ConfigGenerator:
    def __init__(self, template="LaserSlab"):
        self.templates = {
            "LaserSlab": DEFAULT_CONFIG_CONTENT,
            "Sod": self._load_template("Sod"),
            "Sedov": self._load_template("Sedov"),
        }
        self.default_content = self.templates.get(template, DEFAULT_CONFIG_CONTENT)
    
    def _load_template(self, name):
        # 从 refs/ 目录加载模板
        ref_path = Path(__file__).parent / "refs" / f"{name}_Config"
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8")
        return DEFAULT_CONFIG_CONTENT
```

---

## 参考资料

1. FLASH User Guide - Chapter 4: Simulation Configuration
2. FLASH Source Code - `source/Simulation/SimulationMain/*/Config`
3. PhySimX Documentation - `input_gen/gen_config/`

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
