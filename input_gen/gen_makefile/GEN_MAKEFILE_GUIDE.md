# gen_makefile — FLASH Makefile 生成器说明文档

## 概述

`gen_makefile` 子包用于生成 FLASH 仿真的 `Makefile` 文件。Makefile 指定仿真需要编译的额外源文件（如 `Simulation_data.F90`）。

**生成器类型**: 自包含（当前非常简单）
**输出文件**: `Makefile`

## Makefile 格式

FLASH 的 Makefile 用于指定额外的编译对象：

```makefile
Simulation += Simulation_data.o
Simulation += Simulation_init.o
Simulation += Simulation_initBlock.o
```

## gen_makefile 生成器 API

### 类: MakefileGenerator

**位置**: `gen_makefile/generator.py`

```python
from gen_makefile import MakefileGenerator

generator = MakefileGenerator()

# 生成 Makefile 内容
content = generator.generate(sim_path="QC/LaserSlab1d_new")

# 保存
output_path = generator.save("path/to/Simulation/Makefile")
```

## 使用示例

```python
from gen_makefile import MakefileGenerator

generator = MakefileGenerator()
output_path = generator.save("path/to/Simulation/Makefile")
print(f"Generated: {output_path}")
```

## 注意

当前生成器非常简单，只生成基本的 Makefile 内容。如需更复杂的 Makefile（如包含多个文件），需要手动修改生成的文件或扩展生成器。

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
