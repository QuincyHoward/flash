# gen_sim_initblock — Simulation_initBlock.F90 生成器说明文档

## 目录
1. [概述](#概述)
2. [Simulation_initBlock.F90 文件格式](#simulation_initblockf90-文件格式)
3. [GridBuilder API](#gridbuilder-api)
4. [gen_sim_initblock 生成器 API](#gen_sim_initblock-生成器-api)
5. [使用示例](#使用示例)
6. [参考示例 (refs/)](#参考示例-refs)
7. [常见问题](#常见问题)

---

## 概述

`gen_sim_initblock` 子包用于生成 FLASH 仿真的 `Simulation_initBlock.F90` 文件。这个Fortran子程序初始化每个块（block）的流体数据，包括密度、温度、压力、速度等。

**生成器类型**: 基于 GridBuilder（动态生成Fortran代码）
**核心类**: `GridBuilder`, `Region`
**输出文件**: `Simulation_initBlock.F90`

---

## Simulation_initBlock.F90 文件格式

### 基本结构

```fortran
subroutine Simulation_initBlock(blockId)
  use Simulation_data
  use Grid_interface, ONLY : Grid_getBlkIndexLimits, &
       Grid_getCellCoords, Grid_putPointData
  
  implicit none

#include "constants.h"
#include "Flash.h"

  integer, intent(in) :: blockId
  integer :: i, j, k
  integer :: blkLimits(2, MDIM)
  real, allocatable :: xcent(:), ycent(:), zcent(:)
  real :: rho, tele, tion, trad

  ! 获取网格坐标
  call Grid_getBlkIndexLimits(blockId, blkLimits, blkLimitsGC)
  allocate(xcent(...))
  call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., xcent, ...)
  ! ...

  ! 主循环：遍历所有网格点
  do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
     do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
        do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)
           
           ! 根据位置设置物理量
           if (xcent(i) < sim_targetRadius) then
              rho = sim_rhoTarg
              tele = sim_teleTarg
           else
              rho = sim_rhoCham
              tele = sim_teleCham
           endif
           
           ! 写入数据
           call Grid_putPointData(blockId, CENTER, DENS_VAR, EXTERIOR, axis, rho)
           call Grid_putPointData(blockId, CENTER, TEMP_VAR, EXTERIOR, axis, tele)
           ! ...
        end do
     end do
  end do

end subroutine Simulation_initBlock
```

### 关键部分

1. **网格坐标获取**: 使用 `Grid_getCellCoords` 获取每个维度的坐标
2. **主循环**: 遍历块内所有网格点（i, j, k）
3. **区域判断**: 根据坐标判断属于哪个区域（靶、腔室等）
4. **物理量赋值**: 使用 `Grid_putPointData` 写入密度、温度等

---

## GridBuilder API

### 类: GridBuilder

**位置**: `gen_sim_initblock/grid.py`

**描述**: 用于构建仿真网格区域，并生成对应的Fortran代码。

### 初始化

```python
from gen_sim_initblock.grid import GridBuilder, Region

builder = GridBuilder()
```

### 方法: add_region(region)

添加一个区域。

```python
region = Region(
    name="target",
    condition="x < 0.01",  # 区域条件
    properties={"rho": 2.7, "tele": 290.11375},  # 物理量
)
builder.add_region(region)
```

### 类: Region

**描述**: 表示仿真域中的一个区域（如靶材、腔室）。

**属性**:
- `name`: 区域名称
- `condition`: Fortran条件表达式（用于生成 `if` 语句）
- `properties`: 物理属性字典（rho, tele, tion, trad等）

---

## gen_sim_initblock 生成器 API

### 函数: generate_initblock_f90(grid_builder, output_path)

生成 `Simulation_initBlock.F90` 文件。

**签名**:
```python
def generate_initblock_f90(
    grid_builder: GridBuilder,
    output_path: Union[str, Path],
    sim_path: str = "hello/LaserSlab1d_new",
) -> Path:
```

**参数**:
- `grid_builder`: 配置好的 GridBuilder 对象
- `output_path`: 输出文件路径
- `sim_path`: 仿真路径（用于注释）

**返回**: 输出文件路径

---

## 使用示例

### 示例 1: 生成1D激光-等离子体仿真的 Simulation_initBlock.F90

```python
from gen_sim_initblock.grid import GridBuilder, Region
from gen_sim_initblock.generator import generate_initblock_f90

# 创建 GridBuilder
builder = GridBuilder()

# 定义靶区域 (x < 0.01 cm)
target_region = Region(
    name="target",
    condition="xcent(i) < 0.01",
    properties={
        "rho": 2.7,           # 铝密度
        "tele": 290.11375,    # 电子温度
        "tion": 290.11375,    # 离子温度
        "trad": 290.11375,    # 辐射温度
    },
)
builder.add_region(target_region)

# 定义腔室区域 (x >= 0.01 cm)
chamber_region = Region(
    name="chamber",
    condition="xcent(i) >= 0.01",
    properties={
        "rho": 2.655e-07,     # 氦密度
        "tele": 290.11375,
        "tion": 290.11375,
        "trad": 290.11375,
    },
)
builder.add_region(chamber_region)

# 生成 Fortran 代码
output_path = generate_initblock_f90(
    builder,
    "path/to/Simulation/Simulation_initBlock.F90",
    sim_path="hello/LaserSlab1d_new",
)
print(f"Saved to: {output_path}")
```

### 示例 2: 生成2D仿真（包含真空区域）

```python
from gen_sim_initblock.grid import GridBuilder, Region

builder = GridBuilder()

# 定义靶区域 (圆柱形)
target_region = Region(
    name="target",
    condition="sqrt(xcent(i)**2 + ycent(j)**2) < 0.005",
    properties={"rho": 2.7, "tele": 290.11375},
)
builder.add_region(target_region)

# 定义真空区域
vacuum_region = Region(
    name="vacuum",
    condition="(sqrt(xcent(i)**2 + ycent(j)**2) >= 0.005) and (sqrt(xcent(i)**2 + ycent(j)**2) < 0.025)",
    properties={"rho": 1.0e-10, "tele": 290.11375},
)
builder.add_region(vacuum_region)

# 定义腔室区域
chamber_region = Region(
    name="chamber",
    condition="sqrt(xcent(i)**2 + ycent(j)**2) >= 0.025",
    properties={"rho": 2.655e-07, "tele": 290.11375},
)
builder.add_region(chamber_region)

# 生成
generate_initblock_f90(builder, "path/to/Simulation_initBlock.F90")
```

### 示例 3: 使用预设的LaserSlab配置

```python
from gen_sim_initblock.presets import LaserSlabBuilder

# 使用预设的 LaserSlab 配置
builder = LaserSlabBuilder(
    target_radius=0.005,   # 靶半径 (cm)
    target_height=0.025,   # 靶高度 (cm)
    vacuum_height=0.02,    # 真空区域厚度 (cm)
    rho_targ=2.7,          # 靶密度
    rho_cham=2.655e-07,    # 腔室密度
)

# 生成
generate_initblock_f90(builder, "path/to/Simulation_initBlock.F90")
```

---

## 参考示例 (refs/)

`gen_sim_initblock/refs/` 目录包含 146+ 个 `Simulation_initBlock.F90` 示例。

### 主要示例

| 示例 | 描述 |
|------|------|
| `Simulation_initBlock.F90` | 基础LaserSlab版本 |
| `Simulation_initBlock.F90.3D` | 3D版本 |
| `Simulation_initBlock.F90.Xdir` | X方向变体 |

### 如何参考这些示例

1. **查看示例**: 了解不同仿真的区域设置方法
2. **学习Fortran代码模式**: 如何编写高效的区域判断逻辑
3. **提取关键代码**: 复制需要的区域定义

---

## 常见问题

### 1. 如何定义复杂的区域（如球形靶）？

**答**: 在 `Region.condition` 中使用相应的几何条件：

```python
# 球形靶
region = Region(
    name="sphere_target",
    condition="sqrt(xcent(i)**2 + ycent(j)**2 + zcent(k)**2) < radius",
    properties={"rho": 2.7, "tele": 290.11375},
)

# 圆柱形靶
region = Region(
    name="cyl_target",
    condition="sqrt(xcent(i)**2 + ycent(j)**2) < radius and abs(zcent(k)) < height/2",
    properties={"rho": 2.7, "tele": 290.11375},
)
```

### 2. 如何设置梯度初始条件（如线性密度梯度）？

**答**: 当前 `Region` 系统只支持分段常数初始条件。如需梯度，需要直接修改生成的Fortran代码：

```fortran
! 在生成的主循环中添加
if (xcent(i) < sim_targetRadius) then
    rho = sim_rhoTarg * (1.0 + 0.1 * xcent(i) / sim_targetRadius)
else
    rho = sim_rhoCham
endif
```

### 3. Simulation_initBlock.F90 中的 guard cells 是什么？

**答**: Guard cells（守护单元）是每个块周围的额外网格点，用于存储来自相邻块的数据，用于实现高阶插值。在 `Simulation_initBlock.F90` 中，通常只初始化内部单元，guard cells 由FLASH自动填充。

---

## 进阶：扩展 GridBuilder

如需支持更复杂的初始条件（如梯度、随机噪声），可以扩展 `GridBuilder`：

```python
class AdvancedGridBuilder(GridBuilder):
    def add_gradient_region(self, name, condition, prop_gradients):
        """添加具有梯度性质的区域。
        
        prop_gradients: {"rho": (rho0, grad_rho), ...}
        """
        # 生成特殊的Fortran代码来处理梯度
        pass
```

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
