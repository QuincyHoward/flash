# `+ug` 均匀网格分辨率机制 —— 源码证据 + 实测矩阵

> 生成：2026-09-10 ｜ 场景：`t002`（SNB vs FL-SH 对比场景）
> 探针脚本：`scripts/probe/ug_resolution_probe.py` ｜ 原始数据：`results/ug_resolution/`

---

## 0. 结论速览（先看这个）

`+ug` 下 **分辨率不是只能靠核数提升**。控制变量是三个，核数只是其中之一：

| 模式 | 总格数公式 | 分辨率与核数的关系 |
|---|---|---|
| **固定块模式**（`-nxb=N`） | `N_cells = iProcs × NXB` | 核数不变时，**加大 `-nxb` 即可提高分辨率** |
| **非固定块模式**（`-nofbs` + par `iGridSize`） | `N_cells = iGridSize` | **完全解耦**：改 `iProcs` 不改 `dx` |

旧表述「SNB 分辨率只能靠 `iProcs` 提升 / 不存在固定分辨率扫核数」**只在
"固定块模式且不动 `-nxb`"这一前提下成立**，不能作为一般结论。

一个**必须记住的坑**：非固定块模式不能只靠"不给 `-nxb`"来进入 ——
必须显式给 `-nofbs`，否则 FLASH 默认仍定义 `FIXEDBLOCKSIZE`（`NXB=8`），
par 里的 `iGridSize` 会被**静默忽略**。

---

## 1. 源码证据

`setup ... +ug` 选中的是 `source/Grid/GridMain/UG`（t001 的 `NonLTConduct.log:32`
实证打印 `Grid/GridMain/UG`），不是 paramesh。

`source/Grid/GridMain/UG/Grid_init.F90:186-194`：

```fortran
#ifdef FIXEDBLOCKSIZE
  gr_gIndexSize(IAXIS) = gr_axisNumProcs(IAXIS) * NXB      ! 总格数 = iProcs × NXB
  gr_gIndexSize(JAXIS) = gr_axisNumProcs(JAXIS) * NYB
  gr_gIndexSize(KAXIS) = gr_axisNumProcs(KAXIS) * NZB
#else
  if (any((gr_gIndexSize / gr_axisNumProcs) <= 0)) then
     call Driver_abortFlash("[Grid_init] Must set runtime parameters "
          // "iGridSize, jGridSize, kGridSize so that a block contains "
          // "at least one cell.")
  end if
#endif
```

其中非固定块分支的 `gr_gIndexSize` 来自 par（`Grid_init.F90:108-110`）：

```fortran
call RuntimeParameters_get("iGridSize", gr_gIndexSize(IAXIS))
call RuntimeParameters_get("jGridSize", gr_gIndexSize(JAXIS))
call RuntimeParameters_get("kGridSize", gr_gIndexSize(KAXIS))
```

网格间距与坐标（`UG/gr_createDomain.F90:200-215`）：

```fortran
gr_delta(IAXIS) = (gr_imax - gr_imin) / gr_gIndexSize(IAXIS)
...
gr_iCoords(CENTER,i,1) = gr_imin + j*gr_delta(IAXIS) + halfDelta
```

块划分（`UG/Grid_init.F90:171-172`）—— **一块一进程**：

```fortran
gr_globalNumBlocks = gr_meshNumProcs
gr_globalOffset    = gr_meshMe
```

`UG/Config` 的明文声明：

```
D nblockx number of blocks along X - ignored by UG Grid
D iGridSize Global number of interior cells in the i direction
D & ONLY needed when running in NON_FIXED_BLOCKSIZE mode
```

### 1.1 如何进入非固定块模式：必须 `-nofbs`

`bin/parseCmd.py:282` → `elif arg == '--nofbs': GVars.setupVars.set("fixedBlockSize", False)`
`bin/Readme.SetupVars:97-99` → `fixedBlockSize` 由 `-nofbs` / `-fbs` 切换
`bin/setup_shortcuts.txt:105` → `nofbs:-nofbs:+ug:parallelIO=True:`

**副作用**（`source/IO/IOMain/hdf5/Config`）：

```
IF not fixedBlockSize
   DEFAULT parallel
ENDIF
IF not parallelIO and not fixedBlockSize
   SETUPERROR No serial I/O implementation for NoFBS UG
ENDIF
```

即 `-nofbs` 会强制并行 HDF5 IO，**与 `+serialIO` / `parallelIO=False` 不兼容**。

---

## 2. 实测矩阵

环境：WSL Ubuntu-22.04，24 核 / 11 GB；场景 `t002` FL-SH 腿；`tmax = 2.0e-10 s`。
格数由 plt 的 x 坐标长度实测（`FlashDataLoader`）。

| 用例 | 模式 | setup 关键标志 | nxb | iProcs | par iGridSize | 预期格数 | **实测格数** | dx 预期 | **dx 实测** | 墙钟 |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 固定块 | `-nxb=64` | 64 | 8 | – | 512 | **512** ✅ | 0.9766 µm | 0.9766 µm | 12.96 s |
| A2 | 固定块 | `-nxb=128` | 128 | 8 | – | 1024 | **1024** ✅ | 0.4883 µm | 0.4883 µm | 54.20 s |
| A3 | 固定块 | `-nxb=128` | 128 | 16 | – | 2048 | **2048** ✅ | 0.2441 µm | 0.2441 µm | 157.07 s |
| A4 | 非固定块 | `-nofbs` | – | 8 | 1024 | 1024 | **1024** ✅ | 0.4883 µm | 0.4883 µm | 50.30 s |
| A5 | 非固定块 | `-nofbs` | – | 16 | 1024 | 1024 | **1024** ✅ | 0.4883 µm | 0.4883 µm | 44.86 s |
| ~~A4′~~ | ~~只去掉 `-nxb`~~ | （无 `-nxb`、无 `-nofbs`） | – | 8 | 1024 | 1024 | **64** ❌ | 0.4883 µm | **7.8125 µm** | 0.79 s |
| ~~A5′~~ | ~~只去掉 `-nxb`~~ | （同上） | – | 16 | 1024 | 1024 | **128** ❌ | 0.4883 µm | **3.9062 µm** | 1.70 s |

（A4′/A5′ 是失败的第一版尝试，保留以示 `-nofbs` 的必要性：实测格数 = `iProcs × 8`，
即 NXB 取了默认值 8，`iGridSize` 被忽略。）

### 2.1 判读

1. **A1 → A2（核数不变 8 核，只把 `-nxb` 64→128）**：512 → **1024** 格，
   dx 0.9766 → **0.4883 µm**（÷2）。
   → `-nxb` 是**独立于核数**的分辨率旋钮。

2. **A4 → A5（`iGridSize` 不变 1024，核数 8→16）**：格数均为 **1024**，dx 均为 0.4883 µm。
   两次运行**逐字节等价**（均 4462 步、时间步序列相同）。
   → 非固定块模式下分辨率**与核数完全解耦**；核数只影响单个块的大小与并行开销。

3. **A2 vs A4（同为 1024 格 / 8 核，两种模式）**：格数、dx、解完全一致；
   墙钟 54.20 s vs 50.30 s（差别来自编译期数组维度不同带来的内存/缓存效应）。
   → 两种模式在**同一分辨率**下给出同一物理结果，可互换。

4. **并行效率**：A4（1024 格 / 8 块）50.30 s vs A5（1024 格 / 16 块）44.86 s ——
   核数翻倍只快 **11%**。UG 是"一块一进程"，块数增加会带来守卫单元通信开销，
   小规模算例下**核数收益很低**（与 SNBOneCH 的 WSL 探测结论一致）。

5. **分辨率的价格**：512 → 1024 格，墙钟 12.96 → 54.20 s（**4.2×**）。
   因为 `dx` 减半同时使扩散时间步减半（2144 → 4462 步），成本 ≈ `N_cells × N_steps`。

---

## 3. 修正后的规范表述

> **`+ug` 分辨率控制（三条独立路径）**
> 1. `+ug -nxb=N`（固定块）：`dx = 域宽/(iProcs·NXB)` —— 核数不变时加大 `-nxb` 即可细化；
> 2. `+ug -nofbs` + par `iGridSize=M`（非固定块）：`dx = 域宽/M` —— 与核数**完全解耦**；
> 3. `iProcs`：在固定块模式下等价于分辨率旋钮，在非固定块模式下只影响分块/并行开销。
>
> **约束**：UG 一块一进程 → `mpiexec -n` 必须严格等于 `iProcs`；
> 非固定块模式必须显式 `-nofbs`，且强制并行 HDF5 IO。
> **SNB 场景实践**：SNB 要求均匀网格（非局域热流沿平均自由程跨格点积分），
> 但"分辨率只能靠核数"是误读 —— 固定块模式下 `-nxb` 才是最省算力的旋钮。

---

## 4. 本场景的选择

速度优先（用户指令）→ 生产配置取 **A1：`-nxb=64`, `iProcs=8` → 512 格，dx ≈ 0.98 µm**。
备选：需要更细网格时改 `-nxb=128`（1024 格，dx 0.49 µm，成本 4.2×），
或改 `-nofbs iGridSize=1024` 以便在保持分辨率的同时扫核数。
