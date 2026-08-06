# gen_newpara — FLASH 新参数多区密度剖面生成指南

> **基于**: test/newpara/ 系列测试 + 多区实战 + FLASH4.8 官方文档  
> **版本**: 2026-06-30  
> **目录**: `input_gen/gen_newpara/`

---

## 1. 概述

`gen_newpara` 子包提供 FLASH 新参数添加、多区域划分和密度剖面控制的完整流程封装。所有功能均通过 WSL Ubuntu-22.04 上的 FLASH 4.8 实际编译运行验证。

### 核心能力

| 功能 | 说明 | 验证状态 |
|------|------|----------|
| 新参数 5 步流程 | Config → .F90 → .par 文件添加新运行时参数 | ✅ 编译+运行通过 |
| 增量边界区域划分 | 用运行时参数控制区域边界 | ✅ 三区验证通过 |
| 5 种密度剖面 | 常量/指数衰减/指数增长/线性/高斯 | ✅ R²=0.994 |
| 多区单仿真混合 | 一个仿真中不同区域使用不同剖面 | ✅ 5区同时验证 |
| 物种名限制检测 | ≤4 字符，防止 FLASH 静默截断 | ✅ check_species_names() |

---

## 2. 新参数 5 步流程

FLASH 中添加新运行时参数需按固定顺序修改 5 个文件：

```
Config → Simulation_data.F90 → Simulation_init.F90 → Simulation_initBlock.F90 → .par 文件
```

### 2.1 各文件职责

| # | 文件 | 操作 | 示例 |
|---|------|------|------|
| 1 | `Config` | 用 `PARAMETER` 行注册参数 | `PARAMETER sim_polyHeight REAL 0.005` |
| 2 | `Simulation_data.F90` | 声明 Fortran 变量 | `real, save :: sim_polyHeight` |
| 3 | `Simulation_init.F90` | 用 `RuntimeParameters_get` 读取 | `call RuntimeParameters_get('sim_polyHeight', ...)` |
| 4 | `Simulation_initBlock.F90` | 在初始条件中使用 | `bound3 = bound2 + sim_polyHeight` |
| 5 | `.par` 文件 | 设置参数初始值 | `sim_polyHeight = 20.0e-04` |

### 2.2 Config 参数格式

```
D sim_paramName Description of the parameter
PARAMETER sim_paramName TYPE default [allowed_values]
```

| TYPE | Fortran 对应 | 示例 |
|------|-------------|------|
| `REAL` | `real, save` | `PARAMETER sim_rho REAL 2.7` |
| `INTEGER` | `integer, save` | `PARAMETER sim_nblocks INTEGER 4` |
| `BOOLEAN` | `logical, save` | `PARAMETER sim_useFlag BOOLEAN FALSE` |
| `STRING` | 无需声明 | `PARAMETER sim_eos STRING "eos_tab"` |

### 2.3 ⚠️ 常见错误

| 错误 | 原因 | 后果 |
|------|------|------|
| 漏掉 `RuntimeParameters_get` | 只在 Config 注册，未在 init 中读取 | 参数值**静默无效** |
| Config 类型与 Fortran 声明不一致 | PARAMETER 是 REAL，data 模块声明为 integer | 编译错误或未定义行为 |
| 物种名 > 4 字符 | `targ2`(5字符) → `targ` | 与现有物种冲突！ |

---

## 3. ⚠️ 强制约束: 物种名 ≤ 4 字符

**这是 FLASH 4.8 的限制：超过 4 字符的物种名会被静默截断。**

### 问题演示

```
species=cham,targ,targ2    ← targ2 是 5 个字符
FLASH 静默截断:
  cham  → CHAM_SPEC (1)
  targ  → TARG_SPEC  (2)
  targ2 → targ       (2)  ← 与 TARG_SPEC 冲突！
```

### 允许的名称

| 名称 | 长度 | 使用场景 |
|------|------|----------|
| `cham` | 4 | 腔室(稀薄氦) |
| `targ` | 4 | 靶 |
| `foam` | 4 | 泡沫 |
| `samp` | 4 | 样本  |
| `shld` | 4 | 屏蔽层 |

### 检测方法

使用 `gen_checker` 的 `check_species_names()` 方法自动检测。

---

## 4. 增量边界 

取代硬编码的固定区间，使用**累加参数**计算区域边界。

### Fortran 代码模式

```fortran
! 增量边界计算
b0 = sim_vacuumHeight     ! 真空右边界
b1 = b0 + sim_zone1Height  ! 区域 1 右边界
b2 = b1 + sim_zone2Height  ! 区域 2 右边界
b3 = b2 + sim_zone3Height  ! 区域 3 右边界

! 区域判断
if (xcent(i) >= b0 .and. xcent(i) < b1) then
   species = TARG_SPEC
else if (xcent(i) >= b1 .and. xcent(i) < b2) then
   species = TARG_SPEC
else
   species = CHAM_SPEC
end if
```

### 优势

- 所有边界由 `.par` 文件控制
- 区域的增删只需添加/删除参数，无需改代码逻辑
- 支持任意数量区域（已验证 5 区同时运行）

---

## 5. 密度剖面 (Density Profile)

在每个区域内，密度不再是常数，而是 `ρ = ρ₀ × f(x_local)` 的函数形式。

### 5.1 五种剖面类型

| 类型 | 名称 | 公式 | 参数 |
|------|------|------|------|
| 0 | constant | `ρ(x) = ρ₀` | 无 |
| 1 | exp_decay | `ρ(x) = ρ₀ × exp(-x_local / p1)` | p1 = e-folding 长度 [cm] |
| 2 | exp_growth | `ρ(x) = ρ₀ × exp(+x_local / p1)` | p1 = e-folding 长度 [cm] |
| 3 | linear | `ρ(x) = ρ₀ × (p1 + p2 × x_local / w)` | p1 = 截距, p2 = 斜率 |
| 4 | gaussian | `ρ(x) = ρ₀ × exp(-0.5 × ((x-p1×w)/(p2×w))²)` | p1 = 中心位置(相对), p2 = 宽度(相对) |

其中：
- `x_local` = 当前 cell 距 zone 左边界的距离 [cm]
- `w` = zone 宽度 [cm]
- `ρ₀` = 该物种的基础密度 (`sim_rhoTarg`)

### 5.2 参数设置 (.par)

```ini
# Zone 1: exponential decay, e-folding = 10 um
sim_zone1Height = 0.004
sim_zone1Profile = 1
sim_zone1P1 = 0.001
sim_zone1P2 = 0.0

# Zone 2: gaussian, center at 50%, width 25% of zone
sim_zone2Height = 0.004
sim_zone2Profile = 4
sim_zone2P1 = 0.5
sim_zone2P2 = 0.25
```

### 5.3 Fortran 实现 (`density_profile` 函数)

```fortran
real function density_profile(profile, x_local, width, p1, p2)
  select case(profile)
  case(0); density_profile = 1.0
  case(1); density_profile = exp(-x_local / p1)
  case(2); density_profile = exp(x_local / p1)
  case(3)
    x_norm = x_local / max(width, 1.0e-30)
    density_profile = p1 + p2 * x_norm
  case(4)
    arg = (x_local - p1 * width) / (p2 * width)
    density_profile = exp(-0.5 * arg * arg)
  case default; density_profile = 1.0
  end select
end function
```

### 5.4 验证结果

在铝靶 (ρ₀=2.7) 上测试指数衰减 (p1=5μm)：
- **R² = 0.9939** 与解析曲线 `2.7×exp(-(x-0.014)/5e-4)` 吻合 ✅

---

## 6. 单仿真多区混合剖面

在**一个** FLASH 仿真中包含多个区域，每个区域使用不同的剖面类型。

### 配置示例 (5 区)

| 区域 | x 范围 [μm] | 剖面类型 | 参数 |
|------|------------|---------|------|
| 真空 | [0, 50) | N/A | ρ=1e-6 |
| Zone 1 | [50, 90) | 常量 (type=0) | ρ=2.7 |
| Zone 2 | [90, 130) | 指数衰减 (type=1) | p1=10μm |
| Zone 3 | [130, 170) | 指数增长 (type=2) | p1=10μm |
| Zone 4 | [170, 210) | 线性 (type=3) | p1=0.5, p2=1.0 |
| Zone 5 | [210, 250) | 高斯 (type=4) | p1=0.5, p2=0.25 |

### 新增参数 (20 个)

```ini
# 5 个区域 × 4 参数/区 = 20 个运行时参数
sim_zone1Height sim_zone1Profile sim_zone1P1 sim_zone1P2
sim_zone2Height sim_zone2Profile sim_zone2P1 sim_zone2P2
sim_zone3Height sim_zone3Profile sim_zone3P1 sim_zone3P2
sim_zone4Height sim_zone4Profile sim_zone4P1 sim_zone4P2
sim_zone5Height sim_zone5Profile sim_zone5P1 sim_zone5P2
```

### setup 命令

```bash
./setup -auto QC/LaserSlab_multizone_profile -1d +cartesian -nxb=16 \
  +hdf5typeio species=cham,targ \
  +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
  -objdir=QC/LaserSlab_multizone_profile
```

---

## 7. 物种质量分数

每个 cell 的主要物种获得 ~1.0 的质量分数，其他物种获得 `sim_smallX` (1e-99) 痕量。

```fortran
do n = SPECIES_BEGIN, SPECIES_END
   if (n == species) then
      call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, &
           1.0e0-(NSPECIES-1)*sim_smallX)
   else
      call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, sim_smallX)
   end if
enddo
```

---

## 8. 文件完整清单

### 标准 FLASH 输入目录

```
flash_input/
├── Config                  ← 注册运行时参数
├── Makefile                ← "Simulation += Simulation_data.o"
├── Simulation_data.F90     ← 变量声明
├── Simulation_init.F90     ← 参数读取
├── Simulation_initBlock.F90 ← 初始化 + 密度剖面
├── laserslab_*.par         ← 参数赋值
├── al-imx-003.cn4          ← 铝 EOS 表
├── he-imx-005.cn4          ← 氦 EOS 表
├── polystyrene-imx-008.cn4 ← 聚苯乙烯 EOS (可选)
└── run_flash.sh            ← WSL 运行脚本
```

### 输出文件

FLASH 运行后生成：
- `lasslab_hdf5_chk_*` — 检查点文件 (包含所有变量)
- `lasslab_hdf5_plt_cnt_*` — 绘图文件 (仅 plot_var 列出的变量)
- `lasslab_forced_hdf5_plt_cnt_0000` — 强制最终绘图

### 检查点 vs 绘图文件

| 特性 | 检查点 (.chk) | 绘图 (.plt) |
|------|-------------|------------|
| 数据精度 | float64 | float32 |
| 变量数 | 全部 | 仅 plot_var |
| 用途 | 重启仿真 | 快速可视化 |
| 文件大小 | 较大 | 较小 |

---

## 9. ⚠️ 已知限制与注意事项

### 9.1 网格参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `nxb` | 16 | 标准值，增加会减少 block 数 |
| `nblockx` | 4 | 初始 block 数，用于 AMR |
| `lrefine_max` | 3-4 | 最大细化级别，4 级 dx ≈ 4μm |
| `xmin/xmax` | 覆盖所有区域 | 必须包含真空区和所有 target 区 |

### 9.2 参数传递规则

- Config 中注册的参数 **必须在** Simulation_init.F90 中读取
- 但 Config 中的 `REAL` 类型在 Fortran 中可能是 `integer`(FLASH 内部映射)
- `.par` 文件中的参数名 **必须** 与 Config 中的 `PARAMETER` 名完全一致

### 9.3 剖面参数约束

| 剖面类型 | 约束 | 违规后果 |
|---------|------|---------|
| exp_decay (1) | p1 > 0 | p1 ≤ 0 退化为常量 |
| exp_growth (2) | p1 > 0 | p1 ≤ 0 退化为常量 |
| linear (3) | 无硬约束 | p2 可负 → 递减线性 |
| gaussian (4) | p2 > 0 | p2 ≤ 0 退化为常量 |

### 9.4 性能指南

- 每区至少 **5 个 cell** 才能体现剖面特征 (lrefine_max=4 时 dx≈4μm)
- 超过 10 个 zone 建议增大 `nblockx` 或 `lrefine_max`
- AMR 细化开销随区域边界数增加

---

## 10. 测试与验证

### 10.1 运行单元检查

```bash
# 运行全部 15 项检查
python -c "
from input_gen.gen_checker import DependencyChecker
c = DependencyChecker('./my_simulation/flash_input')
c.check_all()
print(c.summary())
"
```

### 10.2 验证三区密度

使用 `test/newpara/flash_profile/analyze_density_indep.py` 或 `analyze_profile.py` 读取 HDF5 初始密度图。

### 10.3 参考文件

| 路径 | 内容 |
|------|------|
| `test/newpara/` | 基础 3 区双靶实现 (chy+targ+poly) |
| `test/newpara/flash_profile/` | 密度剖面单区测试 |
| `test/newpara/flash_profile/multizone_profile/` | 5 区单仿真混合剖面 |
| `test/newpara/flash_profile/run_all_profiles.py` | 5 种剖面全扫描脚本 |
| `docs/newparaset/README.md` | FLASH 新参数官方流程文档 |

---

## 11. API 参考: NewParaGenerator

```python
from input_gen.gen_newpara import NewParaGenerator

gen = NewParaGenerator()
gen.add_zone(height=0.004, profile=0, name="constant")
gen.add_zone(height=0.004, profile=1, p1=0.001, name="exp_decay")
gen.add_zone(height=0.004, profile=4, p1=0.5, p2=0.25, name="gaussian")

# 生成所有 FLASH 源文件
files = gen.generate_all("./output_dir/")
# files: {"config": Path, "sim_data": Path, "sim_init": Path,
#          "init_block": Path, "par": Path}
```

### ZoneConfig

```python
from input_gen.gen_newpara import ZoneConfig

z = ZoneConfig(height=0.004, profile=1, p1=0.001, name="my_zone")
z.validate()  # → [] 如果无错误, 否则返回错误列表
```

---

---

## 12. FLASH 4.8 内置运行时参数参考

> **参见**: [RP_Reference.md](./RP_Reference.md) — 完整的内置参数参考手册

`gen_newpara/` 包含一份独立的 FLASH 4.8 内置运行时参数参考手册：

**RP_Reference.md** 记录了所有**不需要在仿真 Config 中重新注册声明**的内置参数：

| 模块 | 关键参数 | 说明 |
|------|---------|------|
| Driver | `tmax`, `nend`, `dtinit`, `restart` | 时间步进控制 |
| Grid | `geometry`, `xmin/xmax`, `lrefine_max`, `nblockx`, `refine_var_*` | 网格与 AMR |
| IO | `basenm`, `plotFileIntervalStep`, `checkpointFileIntervalStep`, `plot_var_*` | 文件输出 |
| Hydro | `cfl` | CFL 条件 |
| Eos/Opacity | `eos_targTableFile`, `op_targFileName` | 材料属性表 |
| Laser | `ed_numberOfBeams`, `ed_lensX_*`, `ed_pulse*` | 激光参数 |

**核心规则**: 这些参数**仅需在 `.par` 文件中赋值**，FLASH 会自动读取。不要在仿真 Config 中用 `PARAMETER` 重复声明，也不要在 `Simulation_init.F90` 中手动 `RuntimeParameters_get`。

---

## 13. 英文标注规则

**所有 FLASH 分析图必须使用英语标注** — 包括标题(title)、图例(legend)、轴标签(xlabel/ylabel)、注释(annotation)。中文仅在 AI 回复的文字中使用，不在图中出现。原因：
- FLASH 社区国际化共享
- DejaVu Sans 字体缺少 CJK 字符集
- 避免 Unicode 渲染问题

此规则已在 `flash-create-simulation` skill 中记录，所有 `analyze_*.py` 脚本遵循。
