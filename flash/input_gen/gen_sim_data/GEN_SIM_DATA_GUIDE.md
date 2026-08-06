# gen_sim_data 说明文档

## 概述

`gen_sim_data` 子包用于生成 FLASH 仿真的 `Simulation_data.F90` 文件。该文件是 FLASH 仿真 setup 的核心模块之一，用于**定义和存储仿真的运行时参数变量**。

**生成器类型**: 自包含生成器（硬编码模板）  
**输出文件**: `Simulation_data.F90`  
**输出位置**: `SimulationMain/<SetupName>/Simulation_data.F90`

---

## Simulation_data.F90 文件结构

### 标准格式

```fortran
!!****if* source/Simulation/SimulationMain/<SetupName>/Simulation_data
!!
!! NAME
!!  Simulation_data
!!
!! SYNOPSIS
!!  Use Simulation_data
!!
!! DESCRIPTION
!!  Stores the local data for Simulation setup: <SetupName>
!!
!! PARAMETERS
!!  <参数说明>
!!
!!***

module Simulation_data

  implicit none
#include "constants.h"   ! 或 #include "Eos.h" 等

  !! *** Runtime Parameters *** !!
  real,    save :: sim_param1, sim_param2
  integer, save :: sim_intParam
  logical, save :: sim_boolParam

  !! *** Variables pertaining to this Simulation *** !!
  integer, parameter :: sim_nProfile = 1000
  real, dimension(sim_nProfile), save :: sim_rProf, sim_rhoProf

end module Simulation_data
```

---

## 参数分类（基于 139 个 refs 示例）

### 1. 通用参数（几乎所有仿真）

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sim_smallX` | real | 最小物质分数 |
| `sim_smallRho` | real | 最小密度 |
| `sim_smallP` | real | 最小压力 |
| `sim_pi` | real | π 常数 |
| `sim_meshMe` | integer | MPI 进程 ID |
| `sim_killdivb` | logical | 是否清除磁场散度 |

### 2. 域定义参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `sim_xMin`, `sim_xMax` | real | X 轴范围 |
| `sim_yMin`, `sim_yMax` | real | Y 轴范围 |
| `sim_zMin`, `sim_zMax` | real | Z 轴范围 |
| `sim_Lx`, `sim_Ly`, `sim_Lz` | real | 域长度 |
| `sim_initGeom` | character | 初始几何类型 |

### 3. 流体仿真参数

#### 3.1 欧拉流体（Hydro）

| 参数名 | 说明 |
|--------|------|
| `sim_rhoAmbient` | 环境密度 |
| `sim_pAmbient` | 环境压力 |
| `sim_gamma` | 绝热指数 |
| `sim_expEnergy` | 爆炸能量（Sedov） |
| `sim_rInit` | 初始激波位置 |

#### 3.2 磁流体（MHD）

| 参数名 | 说明 |
|--------|------|
| `sim_BxAmbient` | X 方向环境磁场 |
| `sim_betaAmbient` | 环境等离子体 β |
| `sim_neAmbient` | 环境电子密度 |
| `sim_dBPert` | 磁场扰动幅度 |
| `sim_modeNumb` | 波模数 |

### 4. 激光-等离子体参数（LaserSlab 系列）

| 参数名 | 说明 |
|--------|------|
| `sim_rhoTarg` | 靶密度 |
| `sim_teleTarg` | 靶电子温度 |
| `sim_tionTarg` | 靶离子温度 |
| `sim_tradTarg` | 靶辐射温度 |
| `sim_eosTarg` | 靶 EOS 类型 |
| `sim_rhoCham` | 腔密度 |
| `sim_teleCham` | 腔电子温度 |
| `sim_targetRadius` | 靶半径 |
| `sim_targetHeight` | 靶高度 |
| `sim_vacuumHeight` | 真空区域高度 |

### 5. 辐射流体参数（RadSlab 等）

| 参数名 | 说明 |
|--------|------|
| `sim_radSourceType` | 辐射源类型 |
| `sim_radSourceTMax` | 辐射源最大时间 |
| `sim_radSourcePeak` | 辐射源峰值 |
| `sim_radSourceFWHM` | 辐射源半高宽 |
| `sim_nGroups` | 辐射能群数量 |
| `sim_mgdDomainBC` | 多群边界条件 |

### 6. 重力/天体物理参数

| 参数名 | 说明 |
|--------|------|
| `sim_boltz` | 玻尔兹曼常数 |
| `sim_mH` | 氢原子质量 |
| `sim_newt` | 万有引力常数 |
| `sim_absErrMax` | 绝对误差上限 |
| `sim_relErrMax` | 相对误差上限 |

### 7. EOS 相关参数

| 参数名 | 说明 |
|--------|------|
| `sim_eosArr` | EOS 参数数组 |
| `sim_vecLen` | 向量长度 |
| `sim_mode` | EOS 模式 |
| `sim_abar_1`, `sim_abar_2` | 平均原子量 |
| `sim_gamma_1`, `sim_gamma_2` | 绝热指数 |

### 8. 剖面数据数组（用于复杂初始条件）

```fortran
integer, parameter :: sim_nProfile = 1000
real, dimension(sim_nProfile), save :: sim_rProf   ! 径向坐标
real, dimension(sim_nProfile), save :: sim_rhoProf ! 密度剖面
real, dimension(sim_nProfile), save :: sim_pProf   ! 压力剖面
real, dimension(sim_nProfile), save :: sim_vProf   ! 速度剖面
```

---

## 生成器 API

### 当前实现（硬编码模板）

```python
from gen_sim_data import SimDataGenerator

generator = SimDataGenerator()
content = generator.generate()  # 返回 LaserSlab1d 模板
generator.save("path/to/Simulation_data.F90")
```

### 模板来源

当前模板从 `LaserSlab1d/Simulation_data.F90` 提取，包含：
- 靶参数（`sim_rhoTarg`, `sim_teleTarg` 等）
- 腔参数（`sim_rhoCham`, `sim_teleCham` 等）
- 几何参数（`sim_targetRadius`, `sim_initGeom` 等）

---

## 扩展生成器（未来工作）

当前生成器使用单一硬编码模板。如果需要支持多种仿真类型，可以扩展为：

```python
class SimDataGenerator:
    TEMPLATES = {
        "LaserSlab": "...",  # 激光等离子体模板
        "Sedov": "...",      # Sedov 爆炸模板
        "MHD": "...",        # 磁流体模板
        "RadHydro": "...",   # 辐射流体模板
    }
    
    def generate(self, setup_type: str = "LaserSlab", **params):
        """根据 setup_type 选择模板并填充参数。"""
        template = self.TEMPLATES[setup_type]
        return template.format(**params)
```

---

## 使用示例

### 示例 1：生成 LaserSlab 的 Simulation_data.F90

```python
from physimx_sim.flash.input_gen.gen_sim_data import SimDataGenerator

generator = SimDataGenerator()
output_path = generator.save(
    "FLASH4.8/source/Simulation/SimulationMain/LaserSlab1d/Simulation_data.F90"
)
print(f"Generated: {output_path}")
```

### 示例 2：典型 Simulation_data.F90 内容（LaserSlab）

```fortran
module Simulation_data

  implicit none
#include "constants.h"

  !! *** Runtime Parameters *** !!  
  real, save :: sim_targetRadius
  real, save :: sim_targetHeight
  real, save :: sim_vacuumHeight

  real,    save :: sim_rhoTarg  
  real,    save :: sim_teleTarg 
  real,    save :: sim_tionTarg 
  real,    save :: sim_tradTarg 
  real,    save :: sim_zminTarg
  integer, save :: sim_eosTarg

  real,    save :: sim_rhoCham  
  real,    save :: sim_teleCham 
  real,    save :: sim_tionCham 
  real,    save :: sim_tradCham 
  integer, save :: sim_eosCham  

  logical, save :: sim_killdivb = .FALSE.
  real, save :: sim_smallX
  character(len=MAX_STRING_LENGTH), save :: sim_initGeom

end module Simulation_data
```

---

## 与其他生成器的关系

`Simulation_data.F90` 通常与以下文件配合使用：

| 文件 | 生成器 | 关系 |
|------|--------|------|
| `Config` | `gen_config` | 定义运行时参数默认值 |
| `Simulation_init.F90` | `gen_sim_init` | 读取 Config 参数并初始化 Simulation_data |
| `Simulation_initBlock.F90` | `gen_sim_initblock` | 使用 Simulation_data 中的参数设置初始条件 |
| `example.par` | `gen_par` | 设置仿真参数（部分参数与 Simulation_data 对应） |

**重要**: `Config` 中定义的参数会在仿真启动时读入，然后在 `Simulation_init.F90` 中存储到 `Simulation_data` 模块的变量中。

---

## 常见仿真类型的 Simulation_data 示例

### 1. LaserSlab（激光等离子体）

**文件**: `refs/Simulation_data (10).F90`, `(50).F90`, `(100).F90` 等  
**关键参数**: `sim_rhoTarg`, `sim_teleTarg`, `sim_rhoCham`

### 2. Sedov（爆炸波）

**文件**: `refs/Simulation_data (113).F90` 等  
**关键参数**: `sim_expEnergy`, `sim_rhoAmbient`, `sim_pAmbient`

### 3. MHD（磁流体）

**文件**: `refs/Simulation_data (10).F90` (HallWhistlerWaves)  
**关键参数**: `sim_BxAmbient`, `sim_betaAmbient`, `sim_modeNumb`

### 4. 辐射流体（RadSlab）

**文件**: `refs/Simulation_data (100).F90`  
**关键参数**: `sim_radSourceType`, `sim_nGroups`

---

## 注意事项

1. **参数命名约定**: 所有参数以 `sim_` 开头，后接驼峰命名（如 `sim_rhoTarg`）
2. **保存属性**: 所有变量必须使用 `save` 属性，确保在仿真过程中持久化
3. **include 文件**: 根据使用的 FLASH 模块选择 `#include "constants.h"` 或 `#include "Eos.h"`
4. **数组剖面**: 复杂初始条件可能需要 allocatable 数组存储剖面数据
5. **与 Config 同步**: `Simulation_data.F90` 中声明的变量必须在 `Config` 中有对应的运行时参数定义

---

## 文件清单

- **生成器**: `gen_sim_data/generator.py`
- ** refs 示例**: `gen_sim_data/refs/Simulation_data (*).F90` (139 个)
- **输出文件**: `SimulationMain/<SetupName>/Simulation_data.F90`

---

## 更新日期

2026-07-03
