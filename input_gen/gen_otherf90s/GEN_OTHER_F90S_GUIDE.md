# gen_otherf90s 说明文档

## 概述

`gen_otherf90s` 子包用于**存储 FLASH 仿真的其他 Fortran 文件示例**，这些文件通常不支持自动生成，但可作为参考或手动复制使用。

**生成器类型**: 无生成器（仅参考文件库）  
**参考文件目录**: `ref_f90s/`  
**文件数量**: 277 个 Fortran 文件 (`.F90`)

---

## 子包结构

```
gen_otherf90s/
├── __init__.py          # 空文件（无生成器）
└── ref_f90s/            # 参考 Fortran 文件库
    ├── custom/          # 自定义 prolongation 文件
    ├── gr/              # 引力相对论相关文件
    └── ...              # 其他分类
```

---

## 参考文件分类（基于 ref_f90s 目录）

### 1. custom/ - 自定义 Prolongation 文件

**用途**: 自定义网格细化时的插值方法

**典型文件**:
- `Simulation_customizeProlong.F90` - 主文件
- `Simulation_customizeProlong (2).F90` - (5).F90 - 变体

**关键功能**:
```fortran
subroutine Simulation_customizeProlong(Dbfq, levmask, nops)
  !! 自定义 AMR prolongation 操作
end subroutine
```

### 2. gr/ - 引力相对论（General Relativity）文件

**用途**: 引力相对论模块的相关子程序

**典型文件**:
- `gr_expandDomain.F90` - 扩展计算域
- `gr_hgSolve.F90` - 双曲线引力求解器
- `gr_hypreUpdateSoln.F90` - Hypre 求解器更新
- `gr_markJeans.F90` - Jeans 不稳定性标记
- `gr_markRefineDerefine.F90` - 自适应细化条件
- `gr_pfftSpecifyTransform.F90` - 并行 FFT 变换
- `gr_ptAdvance.F90` - 粒子推进

**关键模块**:
```fortran
module gr_hypre
  !! Hypre 求解器接口
end module

subroutine gr_markJeans()
  !! 标记需要满足 Jeans 不稳定性条件的区块
end subroutine
```

---

## 文件命名规则

### 标准命名

```
<ModuleName>.F90
```

示例: `Simulation_customizeProlong.F90`, `gr_hypreUpdateSoln.F90`

### 变体命名

```
<ModuleName> (<number>).F90
```

示例: `Simulation_customizeProlong (2).F90` - 表示同一模块的不同实现或变体

---

## 使用场景

### 场景 1: 手动复制参考文件

当仿真需要特定的自定义功能时，可以从 `ref_f90s/` 复制文件到 FLASH 源码目录：

```bash
cp ref_f90s/custom/Simulation_customizeProlong.F90 \
   FLASH4.8/source/Simulation/SimulationMain/<SetupName>/
```

### 场景 2: 学习 FLASH 模块实现

通过阅读 `ref_f90s/` 中的文件，了解特定模块的实现细节：

- **自定义细化**: 阅读 `custom/Simulation_customizeProlong.F90`
- **引力相对论**: 阅读 `gr/gr_*.F90`

### 场景 3: 作为生成器模板（未来扩展）

如果需要为这些文件创建生成器，可以将 `ref_f90s/` 中的文件作为模板。

---

## 与其他生成器的关系

`gen_otherf90s` 存储的文件通常是**其他生成器不覆盖的部分**：

| 生成器 | 覆盖文件 | `gen_otherf90s` 覆盖文件 |
|--------|----------|--------------------------|
| `gen_sim_init` | `Simulation_init.F90` | - |
| `gen_sim_initblock` | `Simulation_initBlock.F90` | - |
| `gen_sim_data` | `Simulation_data.F90` | - |
| - | - | `Simulation_customizeProlong.F90` |
| - | - | `gr_*.F90` |

---

## 典型文件内容示例

### 示例 1: Simulation_customizeProlong.F90

```fortran
!!****if* source/Simulation/SimulationMain/<SetupName>/Simulation_customizeProlong
!!
!! NAME
!!  Simulation_customizeProlong
!!
!! SYNOPSIS
!!  call Simulation_customizeProlong(Dbfq, levmask, nops)
!!
!! DESCRIPTION
!!  Customize AMR prolongation operations for specific setup.
!!
!! ARGUMENTS
!!  Dbfq     - Data buffer for prolongation
!!  levmask  - Refinement level mask
!!  nops     - Number of operations
!!
!!***

subroutine Simulation_customizeProlong(Dbfq, levmask, nops)

  implicit none

  !! ... implementation ...

end subroutine Simulation_customizeProlong
```

### 示例 2: gr_markJeans.F90

```fortran
!!****if* source/Physics/Gravity/GravityMain/GeneralRelativistic/gr_markJeans
!!
!! NAME
!!  gr_markJeans
!!
!! SYNOPSIS
!!  call gr_markJeans()
!!
!! DESCRIPTION
!!  Mark blocks for refinement based on Jeans instability criterion.
!!
!!***

subroutine gr_markJeans()

  use Grid_interface, ONLY: Grid_getBlkPtr

  implicit none

  !! ... implementation ...

end subroutine gr_markJeans
```

---

## 注意事项

1. **无自动生成**: 此子包不提供自动生成功能，需手动复制或修改文件
2. **文件分类**: 参考文件按功能分类存放在子目录中（`custom/`, `gr/`, 等）
3. **变体管理**: 同一模块的不同实现用 `(number)` 区分
4. **手动维护**: 如需更新这些参考文件，需手动从 FLASH 源码复制

---

## 未来扩展建议

如果需要为这些文件创建生成器，可以：

1. **识别参数化部分**: 找出文件中可参数化的部分（如变量名、阈值等）
2. **创建模板**: 将参考文件转换为带占位符的模板
3. **实现生成器**: 在 `gen_otherf90s/` 中添加 `generator.py`

示例：

```python
class CustomProlongGenerator:
    def generate(self, prolong_type: str = "default"):
        """生成 Simulation_customizeProlong.F90"""
        pass

class GRModuleGenerator:
    def generate(self, module_name: str):
        """生成 gr_*.F90 文件"""
        pass
```

---

## 文件清单

- **参考文件目录**: `gen_otherf90s/ref_f90s/`
- **文件总数**: 277 个 `.F90` 文件
- **分类目录**: `custom/`, `gr/`, 等

---

## 更新日期

2026-07-03
