# gen_Grid_markRefineDerefine — AMR 网格细化条件说明文档

## 概述

`gen_Grid_markRefineDerefine` 子包包含 FLASH AMR（自适应网格细化）的 `Grid_markRefineDerefine.F90` 文件示例。

**当前状态**: 暂无自动生成器，需手动编写或从refs/复制
**参考文件**: `refs/Grid_markRefineDerefine.F90` 及多个变体
**输出文件**: `Grid_markRefineDerefine.F90`

## Grid_markRefineDerefine.F90 用途

这个Fortran子程序定义AMR网格细化和粗化条件。FLASH根据用户输入的`refine_var_*`参数，调用此子程序判断是否细化或粗化特定区域的网格。

## 关键技术要点（已为用户核心规范）

### 1. AMR细化变量配置规则

在`.par`文件中配置：
```python
lrefine_max = 4          # 最大细化等级
refine_var_1 = "dens"    # 细化变量1：密度
refine_var_2 = "tele"    # 细化变量2：电子温度
```

### 2. 1D/2D/3D 坐标获取差异

| 维度 | 坐标获取 | 循环结构 |
|------|---------|---------|
| 1D | 只需`xcent(i)` | `do i = ...` |
| 2D | 需要`xcent(i)`, `ycent(j)` | `do j = ...; do i = ...` |
| 3D | 需要`xcent(i)`, `ycent(j)`, `zcent(k)` | `do k = ...; do j = ...; do i = ...` |

### 3. 典型细化逻辑（LaserSlab 1D）

```fortran
! 在靶区域 (x < sim_targetRadius) 细化到最高等级
if (xcent(i) < sim_targetRadius) then
    need_refine = .true.
endif

! 在密度梯度大的区域细化
if (abs(dens(i+1) - dens(i)) / dx > threshold) then
    need_refine = .true.
endif
```

## 使用示例

### 从refs/复制并修改

```bash
# 复制1D版本
cp gen_Grid_markRefineDerefine/refs/Grid_markRefineDerefine.F90 \
   path/to/Simulation/Grid_markRefineDerefine.F90

# 根据仿真维度修改坐标获取和循环结构
```

## 参考文档

详见 `gen_Grid_markRefineDerefine/refs/Grid_markRefineDerefine_编写指南.md`

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
