# gen_sim_init — Simulation_init.F90 生成器说明文档

## 目录
1. [概述](#概述)
2. [Simulation_init.F90 文件格式](#simulation_initf90-文件格式)
3. [gen_sim_init 生成器 API](#gen_sim_init-生成器-api)
4. [使用示例](#使用示例)
5. [参考示例 (refs/)](#参考示例-refs)
6. [常见问题](#常见问题)

---

## 概述

`gen_sim_init` 子包用于生成 FLASH 仿真的 `Simulation_init.F90` 文件。这个Fortran子程序初始化仿真参数，从 `.par` 文件中读取运行时参数并存储在模块变量中。

**生成器类型**: 自包含（硬编码默认模板）
**默认模板来源**: `SimulationMain/LaserSlab/Simulation_init.F90`
**输出文件**: `Simulation_init.F90`

---

## Simulation_init.F90 文件格式

### 基本结构

```fortran
!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_init
!!
!! NAME
!!
!!  Simulation_init
!!
!! SYNOPSIS
!!
!!  Simulation_init()
!!
!! DESCRIPTION
!!
!!  Initializes all the parameters needed for a particular simulation
!!
!! PARAMETERS
!!
!!***

subroutine Simulation_init()
  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get
  
  implicit none

#include "constants.h"
#include "Flash.h"

  ! 读取运行时参数
  call RuntimeParameters_get('sim_targetRadius', sim_targetRadius)
  call RuntimeParameters_get('sim_rhoTarg', sim_rhoTarg)
  ! ...

end subroutine Simulation_init
```

### 关键部分

1. **头注释**: 遵循FLASH文档规范
2. **use声明**: 引入需要的模块
3. **参数读取**: 使用 `RuntimeParameters_get` 读取 `.par` 文件中的参数
4. **初始化逻辑**: 可选的特殊初始化代码

---

## gen_sim_init 生成器 API

### 类: SimInitGenerator

**位置**: `gen_sim_init/generator.py`

### 方法: generate(params)

生成 `Simulation_init.F90` 内容。

**签名**:
```python
def generate(self, params: Optional[Dict[str, Any]] = None) -> str:
```

**参数**:
- `params`: 可选参数字典（预留，当前未使用）

**返回**: Fortran源代码字符串

### 方法: save(output_path, params)

生成并保存文件。

**签名**:
```python
def save(
    self,
    output_path: Union[str, Path],
    params: Optional[Dict[str, Any]] = None,
) -> Path:
```

---

## 使用示例

### 示例 1: 生成默认 Simulation_init.F90

```python
from gen_sim_init import SimInitGenerator

generator = SimInitGenerator()

# 生成默认内容（基于LaserSlab模板）
content = generator.generate()

# 保存
output_path = generator.save("path/to/Simulation/Simulation_init.F90")
print(f"Saved to: {output_path}")
```

### 示例 2: 自定义 Simulation_init.F90（高级）

当前生成器使用硬编码模板。如需自定义，可以修改生成的字符串：

```python
generator = SimInitGenerator()

# 生成默认内容
content = generator.generate()

# 修改内容（例如，添加自定义参数读取）
custom_lines = """
  ! 读取自定义参数
  call RuntimeParameters_get('my_custom_param', my_custom_param)
"""

# 在 "implicit none" 之后插入
lines = content.split("\n")
insert_idx = 0
for i, line in enumerate(lines):
    if "implicit none" in line:
        insert_idx = i + 1
        break
lines.insert(insert_idx, custom_lines)
content = "\n".join(lines)

# 保存
with open("path/to/Simulation/Simulation_init.F90", "w") as f:
    f.write(content)
```

---

## 参考示例 (refs/)

`gen_sim_init/refs/` 目录包含 143+ 个 `Simulation_init.F90` 示例，来自不同的FLASH仿真。

### 主要示例

| 示例 | 描述 |
|------|------|
| `Simulation_init.F90` | 基础LaserSlab版本 |
| `Simulation_init (10).F90` ... | 各种变体 |

### 如何参考这些示例

1. **查看示例**: 直接读取 `refs/` 中的文件
2. **了解初始化模式**: 不同仿真如何读取和初始化参数
3. **提取关键代码**: 复制需要的代码片段

**示例**: 参考 Sod 的 `Simulation_init.F90`

```bash
cat gen_sim_init/refs/Simulation_init.F90 | head -50

# 提取关键部分:
# - 如何读取左右状态参数
# - 如何设置初始条件
```

---

## 常见问题

### 1. 如何为新的仿真类型生成 Simulation_init.F90？

**答**: 当前生成器使用硬编码的LaserSlab模板。如需其他类型：
1. 生成默认版本
2. 手动修改以匹配目标仿真的初始化需求
3. 或将需要的示例复制到 `refs/` 目录，并扩展生成器

### 2. Simulation_init.F90 和 Simulation_initBlock.F90 有什么区别？

**答**:
- `Simulation_init.F90`: 初始化仿真级参数（一次）
- `Simulation_initBlock.F90`: 初始化每个块的流体数据（每个块调用一次）

### 3. 如何验证生成的 Fortran 代码是否正确？

**答**: 使用FLASH编译：

```bash
cd /path/to/FLASH4.8
make
```

如果Fortran代码有语法错误，编译时会报错。

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
