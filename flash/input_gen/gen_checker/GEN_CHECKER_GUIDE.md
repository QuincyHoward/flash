# gen_checker — 依赖检查器说明文档

## 概述

`gen_checker` 子包提供 FLUID 仿真依赖检查功能，验证仿真目录是否包含所有必需的文件。同时提供绘图工具，用于可视化脉冲、密度分布、光线追踪等。

**主要功能**:
1. 依赖检查（7个关键文件）
2. 脉冲绘图（pulse_plotter）
3. 密度绘图（density_plotter）
4. 光线绘图（ray_plotter）

## 依赖检查

### 检查项

依赖检查器验证以下7个关键文件是否存在：

1. `.par` - 参数文件
2. `.cn4` - EOS表文件
3. `Config` - 配置文件
4. `Simulation_initBlock.F90` - 块初始化
5. `Simulation_init.F90` - 仿真初始化
6. `Simulation_data.F90` - 数据模块
7. `Makefile` - 编译配置

### 可选检查

- FLASH二进制是否存在
- Python依赖（numpy, matplotlib, h5py）
- MPI是否可用

## gen_checker API

### 类: DependencyChecker

**位置**: `gen_checker/checker.py`

### 使用示例

```python
from gen_checker import DependencyChecker

# 创建检查器
checker = DependencyChecker("path/to/Simulation/")

# 执行所有检查
results = checker.check_all()

# 打印摘要
print(checker.summary())

# 检查是否所有依赖都满足
if checker.all_passed():
    print("All dependencies satisfied!")
else:
    print("Missing files:")
    for result in results:
        if not result.status:
            print(f"  - {result.name}: {result.message}")
```

### 输出示例

```
=== FLASH Simulation Dependency Check ===
✓ .par file exists
✓ .cn4 EOS table exists
✓ Config file exists
✓ Simulation_initBlock.F90 exists
✓ Simulation_init.F90 exists
✓ Simulation_data.F90 exists
✓ Makefile exists
✗ FLASH binary not found (optional)

Passed: 7/8
```

## 绘图工具

### pulse_plotter

绘制激光脉冲时间-功率曲线。

```python
from gen_checker.ploter import pulse_plotter

# 从.par文件读取脉冲数据并绘图
pulse_plotter.plot(
    par_file="path/to/flash.par",
    output_file="pulse_plot.png"
)
```

### density_plotter

绘制密度分布图。

```python
from gen_checker.ploter import density_plotter

# 从FLASH输出文件读取密度数据并绘图
density_plotter.plot(
    hdf5_file="path/to/plotfile.h5",
    output_file="density_plot.png"
)
```

### ray_plotter

绘制光线追踪图。

```python
from gen_checker.ploter import ray_plotter

# 绘制激光光线传播路径
ray_plotter.plot(
    par_file="path/to/flash.par",
    output_file="ray_plot.png"
)
```

## 集成到仿真流程

```python
from gen_checker import DependencyChecker

# 在编译前检查依赖
checker = DependencyChecker("path/to/Simulation/")
if not checker.all_passed():
    print("Cannot compile: missing dependencies")
    print(checker.summary())
    exit(1)

# 编译...
# 运行...

# 运行后绘图
from gen_checker.ploter import pulse_plotter, density_plotter
pulse_plotter.plot("flash.par", "pulse.png")
density_plotter.plot("plotfile.h5", "density.png")
```

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
