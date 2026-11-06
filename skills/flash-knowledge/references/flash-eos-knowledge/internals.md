---
title: Eos 内部实现 — 公共 API + Eos_wrapped 流程 + eos_mapLookup + 表加载
skill: flash-eos
category: internals
source_anchors:
  - source/physics/Eos/Eos_interface.F90:L1-L170
  - source/physics/Eos/EosMain/Eos.F90:L237
  - source/physics/Eos/EosMain/Eos_wrapped.F90:L91-L251
  - source/physics/Eos/EosMain/Eos_getData.F90:L102-L277
  - source/physics/Eos/EosMain/Eos_data.F90:L91
  - source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_initHelmholtz.F90:L113-L200
manual_ref: "FLASH 4.8 User Guide §13-15"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - eos
  - internals
  - api
  - wrapped
  - map-lookup
---

# Eos 内部实现

> **TL;DR**：Eos 公共 API 只 12 个函数。`Eos_wrapped` 是最常调的（block 级包装）：取 block 指针 → 循环每行 cell 调 `Eos_getData`（block → eosData）→ 调 `Eos`（kernel）→ `Eos_putData`（eosData → block）→ 释放指针。本文件讲：① 12 公共 API；② Eos_wrapped 流程；③ eos_mapLookup 机制；④ Helmholtz 表加载；⑤ EOS 模式枚举映射。

---

## 1. 公共 API 总览

源码：`source/physics/Eos/Eos_interface.F90`（170 行，12 个 interface）

### 1.1 API 分类

| 类别 | 函数 | 数量 |
|---|---|---|
| **主入口** | `Eos`（kernel 调度）、`Eos_wrapped`（block 包装）、`Eos_arrayWrapped`（pre-fetched pointer） | 3 |
| **生命周期** | `Eos_init`、`Eos_finalize` | 2 |
| **数据搬运** | `Eos_getData`、`Eos_putData`、`Eos_getTempData`、`Eos_getTempDataFromVec`、`Eos_getTempDataF` | 5 |
| **辅助** | `Eos_getAbarZbar`、`Eos_getParameters`、`Eos_guardCells`、`Eos_logDiagnostics`、`Eos_unitTest` | 5 |

### 1.2 关键 API 详解

#### `Eos`（kernel 调度）

源码：`source/physics/Eos/EosMain/Eos.F90:L237`

```fortran
subroutine Eos(mode, vecLen, eosData, massFrac, mask, vecBegin, vecEnd, diagFlag)
```

按 `eos_type`（在 `Eos_init` 时设）分发到具体实现：
- `eos_idealGamma`（Gamma）
- `eos_mgamma`（Multigamma）
- `eos_helmholtz`（Helmholtz）
- `eos_tabulated`（Tabulated）
- `eos_nuclear`（EosNuclear）

`eos_type` 是整数常量（`EOS_GAM/EOS_HLM/EOS_MGAM/EOS_TAB/EOS_NUC`，定义在 `Eos.h:L106-L111`）。

#### `Eos_wrapped`（最常调）

源码：`source/physics/Eos/EosMain/Eos_wrapped.F90:L91-L251`

```fortran
subroutine Eos_wrapped(mode, range, blockID, gridDataStruct)
```

Driver/Hydro/Grid 都调这个。内部流程见 §2。

#### `Eos_getData`（block → eosData）

源码：`source/physics/Eos/EosMain/Eos_getData.F90:L102`

```fortran
subroutine Eos_getData(axis, pos, vecLen, solnData, gridDataStruct, &
                       eosData, massFrac, eosMask)
```

把 block 的一行 cell（沿 IAXIS）拷到 1D `eosData` 数组。关键逻辑：

- **eintSwitch**（行 253）：如果 `ENER - EKIN > max(smalle, eintSwitch × EKIN)`，用减法（`EINT = ENER - EKIN`）；否则用 `EINT_VAR` 直接值（避免大数消去）。
- **TEMP_VAR 总是拷贝**（行 277）：即使 mode 是 dens_ie（不需要 T 输入），也拷贝 T 作为 Newton-Raphson 初始猜测。

#### `Eos_putData`（eosData → block）

源码：`source/physics/Eos/EosMain/Eos_putData.F90:L96`

把 eosData 写回 unk。写 PRES/EINT/TEMP/GAMC/GAME。

#### `Eos_init`

源码：`source/physics/Eos/EosMain/Eos_init.F90:L43`（1T）/ `multiTemp/Eos_init.F90:L67`（3T）

读 runtime parameter、加载表（Helmholtz/Tabulated）、设 `eos_type`、调用 `eos_fillMapLookup` 建 UNK 索引映射。

### 1.3 `Eos_computeDt` 不存在

**重要**：Eos 单元**没有** `Eos_computeDt`。grep `source/physics/Eos/` 找不到任何 `eos_dt` 参数。

时间步限制走 **Heatexchange**（基于 e-i 耦合时间尺度）或 **Diffuse**（基于热传导）。

---

## 2. Eos_wrapped 完整流程

源码：`source/physics/Eos/EosMain/Eos_wrapped.F90:L91-L251`

### 2.1 10 步流程

```
Eos_wrapped(mode, range, blockID, gridDataStruct)
│
├── Step 1: 验证 mode（行 131-153）
│   └── if mode 不在允许列表 → Driver_abortFlash
│       允许列表：MODE_DENS_IE / MODE_DENS_PRES / MODE_DENS_TEMP / MODE_DENS_ENTR
│                 MODE_EOS_NOP / MODE_EOS_WRAPPERONLY
│                 （3T 还含 _ION/_ELE/_RAD/_EQUI/_GATHER/...）
│
├── Step 2: 早退出（行 156, 159）
│   ├── MODE_EOS_NOP → 立即返回
│   └── range 为空（IAXIS 范围 0）→ 立即返回
│
├── Step 3: 选 gridDataStruct（行 164-168）
│   └── 默认 CENTER；可传 FACEVARS / GRIDVAR / WORK
│
├── Step 4: 取 block 指针（行 169）
│   └── call Grid_getBlkPtr(blockID, solnData, dataStruct)
│
├── Step 5: 可选 OpenMP 并行（行 172）
│   └── threadEosWithinBlock=.TRUE. 且 NDIM > 1 时启用
│
├── Step 6: 分配工作空间（行 179-182）
│   ├── massFraction(NSPECIES × vecLen)
│   └── eosData(EOS_NUM × vecLen)
│
├── Step 7: 设 eosMask（行 184-188）
│   └── 哪些导数要算（默认只要 P, T；CV_VAR 等需要时设）
│
├── Step 8: 循环 (k, j)（行 195-239）
│   for k = blkLimits(LOW,KAXIS) to blkLimits(HIGH,KAXIS):
│     for j = blkLimits(LOW,JAXIS) to blkLimits(HIGH,JAXIS):
│       ├── Eos_getData(IAXIS, pos, vecLen, solnData, ...)  # 拷一行到 eosData
│       ├── Eos(mode, vecLen, eosData, massFraction, mask=eosMask)  # 调 kernel
│       └── Eos_putData(IAXIS, pos, vecLen, solnData, ...)  # 写回 unk
│
├── Step 9: 释放指针（行 251）
│   └── call Grid_releaseBlkPtr(blockID, solnData, dataStruct)
│
└── Step 10: 返回
```

### 2.2 为什么是这个结构

**为什么不直接对每个 cell 调 `Eos`**：
- 性能：每次 `Eos` 调用有固定开销（参数检查、查 eos_type）；批量调用（vecLen = NXB）摊薄开销
- Helmholtz 表插值对 vecLen 个 cell 一次性做更高效
- OpenMP 在 (k, j) 循环上并行更直观

**为什么 getData + Eos + putData 三步**：
- 解耦：`Eos` kernel 只关心 1D eosData 数组，不知道 Grid/unk 存在
- 可测试：unit test 可以直接构造 eosData 调 Eos，不需要 block
- 灵活：不同 gridDataStruct（CENTER/FACEVARS）共用 kernel

### 2.3 调用者怎么用

调用者（Driver/Hydro/sourceTerms）：

```fortran
! 标准用法：对一个 block 调
call Eos_wrapped(MODE_DENS_IE, blkLimits, blockID, CENTER)

! 已经持有 solnData 指针的优化版
call Eos_arrayWrapped(MODE_DENS_IE, blkLimits, solnData, CENTER)

! 只对 guard cell 调
call Eos_guardCells(eosMode, blockID, corners=/.true.,t/, layers=NGUARD)
```

**blockList 循环**：调用者自己做（不像 Hydro 一次接 blockList）。

---

## 3. eos_mapLookup 机制（关键间接层）

源码：`source/physics/Eos/EosMain/Eos_data.F90:L91`、`Eos_map.h:L39-L106`

### 3.1 问题

不同模式下，UNK 变量索引（`DENS_VAR`, `PRES_VAR`, `EINT_VAR`, `TEMP_VAR`, `GAMC_VAR`, `GAME_VAR`, `ENTR_VAR`, `CV_VAR`, ...）不同。3T 模式还有 `TEION_VAR`, `TELE_VAR`, ... `EELE_VAR`, `PION_VAR`, ...

如何让同一个 `Eos_getData` 函数处理所有模式？

### 3.2 解决方案：3D 映射数组

```fortran
integer, dimension(50, 2, NUM_GRID_DATA_STRUCTS) :: eos_mapLookup
! 索引：(role, in_or_out, dataStruct)
```

**role**（来自 `Eos_map.h:L39-L106`）：

| Role 常量 | 含义 |
|---|---|
| `EOSMAP_DENS` | 密度 |
| `EOSMAP_PRES` | 压力 |
| `EOSMAP_TEMP` | 温度 |
| `EOSMAP_EINT` | 内能 |
| `EOSMAP_GAMC` | 声速 γ |
| `EOSMAP_GAME` | 能量 γ |
| `EOSMAP_ENTR` | 熵 |
| `EOSMAP_CV` | 比热 cv |
| `EOSMAP_CP` | 比热 cp |
| ...（共 ~50 个） |

**in_or_out**：1=输入，2=输出。

**dataStruct**：CENTER / FACEVARS / GRIDVAR / ...

### 3.3 填充流程

`Eos_init` 调用 `eos_fillMapLookup`（每变体自己实现），把 role 映射到 UNK 索引：

```fortran
! Gamma 1T 模式
eos_mapLookup(EOSMAP_DENS, IN, CENTER) = DENS_VAR
eos_mapLookup(EOSMAP_PRES, OUT, CENTER) = PRES_VAR
eos_mapLookup(EOSMAP_TEMP, OUT, CENTER) = TEMP_VAR
eos_mapLookup(EOSMAP_EINT, IN, CENTER) = EINT_VAR

! 3T 模式（不同变体填不同）
eos_mapLookup(EOSMAP_EINT, IN, CENTER) = EION_VAR   ! 当前 component
eos_mapLookup(EOSMAP_TEMP, IN, CENTER) = TEION_VAR
```

### 3.4 使用

`Eos_getData` 不直接读 `solnData(DENS_VAR, ...)`，而是：

```fortran
dens_idx = eos_mapLookup(EOSMAP_DENS, IN, CENTER)
eosData(EOS_DENS) = solnData(dens_idx, i, j, k)
```

**好处**：getData 代码不区分 1T/3T，由 mapLookup 决定具体读哪个 UNK 变量。

---

## 4. EOS 模式枚举映射

### 4.1 字符串 → 整数

用户 parfile 写 `"dens_ie"`（字符串），`Eos_init` 在 Hydro_init 里转成整数 `MODE_DENS_EI = 102`：

```fortran
! source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L891
call RuntimeParameters_get("eosMode", eosModeString)
select case (trim(eosModeString))
case ("dens_ie")      ; hy_eosMode = MODE_DENS_EI
case ("dens_pres")    ; hy_eosMode = MODE_DENS_PRES
case ("dens_temp")    ; hy_eosMode = MODE_DENS_TEMP
case ("dens_ie_recal_gather") ; hy_eosMode = MODE_DENS_EI_RECAL_GATHER
case default          ; call Driver_abortFlash("Unknown eosMode: " // eosModeString)
end select
```

### 4.2 完整常量表

源码：`source/Simulation/constants.h:L297-L341`

#### 1T 主模式

```
MODE_DENS_TEMP       101   # (ρ, T) → (P, e)
MODE_DENS_EI         102   # (ρ, e) → (P, T)  ★ 默认
MODE_DENS_PRES       103   # (ρ, P) → (e, T)
MODE_EOS_NOP          55   # no-op
MODE_EOS_WRAPPERONLY 67   # 只 getData/putData
MODE_DENS_ENTR      1207   # (ρ, s) → (T, P, e)
```

#### 3T per-component

```
MODE_DENS_TEMP_ION   30101   # 离子温度
MODE_DENS_TEMP_ELE   30201   # 电子温度
MODE_DENS_TEMP_RAD   30301   # 辐射温度
MODE_DENS_TEMP_COMP  31101   # 物质（ion+ele）
MODE_DENS_TEMP_ALL   31201   # 所有独立
MODE_DENS_TEMP_EQUI  31301   # 全平衡
MODE_DENS_TEMP_MAT_EQUI 32401 # 离子+电子平衡

MODE_DENS_EI_ION     30102
MODE_DENS_EI_ELE     30202
...
MODE_DENS_EI_RECAL_GATHER 31602   # ★ +3t 默认
MODE_DENS_EI_SELE_GATHER  32522   # 激波电子特殊
MODE_DENS_EI_SHOCKSELE_GATHER 33522
```

### 4.3 为什么这么多模式

每个调用点需求不同：
- Hydro 之前：`dens_ie` + `_GATHER`（廉价）
- AMR refine 后：`dens_ie_recal_gather`（完全重算）
- 初始化：`dens_temp` 或 `dens_ie_equi`（假设平衡）
- 激波附近：`dens_ie_shocksele_gather`（特殊处理）

---

## 5. Helmholtz 表加载机制

源码：`source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_initHelmholtz.F90`

### 5.1 加载流程

```
Eos_init
└── if (eos_type == EOS_HLM):
    └── eos_initHelmholtz()
        │
        ├── PE0 only:
        │   ├── 检查 helm_table.bdat 是否存在
        │   ├── 存在 → 直接读 bdat（快）
        │   └── 不存在 → 读 helm_table.dat（7.7 MB ASCII，慢）
        │       └── 写 helm_table.bdat（供下次用）
        │
        ├── 广播到所有 PE（21 次 MPI_BCAST）：
        │   ├── eos_f (211×71)              # 自由能
        │   ├── eos_fpk (211×71×9)          # 自由能 9 个偏导
        │   ├── eos_ef (211×71)             # 电子化学势
        │   ├── eos_xf (211×71)             # 数密度
        │   └── ...（共 21 个数组）
        │
        └── 验证表完整性（行 200）
```

### 5.2 为什么 PE0 读再广播

如果每个 PE 都读 7.7 MB 文件，文件系统会卡（特别是 NFS 上）。MPI_BCAST 把表数据高效传给所有 PE。

### 5.3 bdat 不能跨机器

**重要陷阱**：`helm_table.bdat` 是 Fortran binary，含 endianness + 浮点格式。**跨架构（如 x86 → ARM）拷贝会读错数据**。

**修复**：换机器时删 bdat，重新读 dat。源码注释（`eos_initHelmholtz.F90:L222`）。

### 5.4 内存占用

表占内存：
- `eos_f`：211×71×8 byte = 120 KB
- `eos_fpk`：211×71×9×8 = 1.1 MB
- `eos_ef`、`eos_xf`：每个 120 KB
- 总计 ~3 MB per PE

---

## 6. Eos_getData 的 eintSwitch 机制

源码：`source/physics/Eos/EosMain/Eos_getData.F90:L253-L277`

### 6.1 问题

Hydro 更新的是 `ENER_VAR`（总能 E_total = e + v²/2）。Eos 要的是 `EINT_VAR`（内能 e）。

怎么得到 e？最直观：`e = E_total - E_kin`。但如果 `E_kin ≫ e`（如高流速），减法会丢有效位数（catastrophic cancellation）。

### 6.2 eintSwitch 解法

`Eos_getData` 行 253：

```fortran
if ( (ENER - EKIN) > max(smalle, eintSwitch * EKIN) ) then
    ! 减法结果可信
    EINT = ENER - EKIN
else
    ! 减法可能丢精度，用 EINT_VAR 直接值
    EINT = EINT_VAR
end if
```

**eintSwitch = 0**（默认）：总是用 `EINT_VAR`（Hydro 单独演化辅助内能方程，`use_auxEintEqn=.TRUE.`）。

**eintSwitch > 0**（如 0.1）：当 `E_int > 0.1 × E_kin` 时用减法（更精确），否则用 EINT_VAR。

### 6.3 TEMP_VAR 总是拷贝（行 277）

即使 mode 是 dens_ie（T 是输出不是输入），`Eos_getData` 也把 `TEMP_VAR` 拷到 eosData。

**为什么**：Helmholtz 的 Newton-Raphson 迭代需要**初始 T 猜测**。`TEMP_VAR` 是上一步的 T，是好初值。

---

## 7. EOS 模式的合法性检查

源码：`source/physics/Eos/EosMain/Eos_wrapped.F90:L131-L153`（1T）

```fortran
if (mode == MODE_DENS_TEMP .or. mode == MODE_DENS_EI .or. &
    mode == MODE_DENS_PRES .or. mode == MODE_DENS_ENTR .or. &
    mode == MODE_EOS_NOP .or. mode == MODE_EOS_WRAPPERONLY) then
    ! OK
else
    call Driver_abortFlash("Eos_wrapped: invalid mode")
end if
```

3T 版本（`multiTemp/Eos_wrapped.F90:L132-L158`）接受更多模式（per-component、_EQUI、_GATHER 等）。

**为什么检查**：防止用户传错 mode 值导致未定义行为。

---

## 8. 完整调用关系（文字 + 缩进）

```
Driver_evolveFlash
│
├── (初始化) Driver_initFlash
│   └── Eos_init ★
│       ├── 读 eos_* runtime parameters
│       ├── 加载 Helmholtz 表（PE0 读 + 广播）
│       ├── 加载 ionmix/sesame 表（如 Tabulated）
│       ├── 设 eos_type（EOS_GAM / EOS_HLM / EOS_MGAM / EOS_TAB / EOS_MTYPE）
│       └── 调 eos_fillMapLookup（建 UNK 索引映射）
│
├── Simulation_initBlock（用户设 (ρ, e) 或 (ρ, T)）
│   └── Eos_wrapped(eosModeInit, blkLimits, blockID, CENTER) ★
│       └── 让初始 (ρ, e) → 自洽 (P, T)
│
├── (主循环每步)
│   ├── Grid_fillGuardCells(CENTER, ALLDIR, doEos=.true.)
│   │   └── 内部调 Eos（让插值的 guard cell 自洽）★
│   │
│   ├── Hydro_computeDt → Driver_computeDt 汇总 dt
│   │
│   ├── Hydro(...) ★
│   │   ├── Riemann state 重构（用 PRES）
│   │   ├── 保守更新（更新 ENER_VAR）
│   │   └── 末尾调 Eos_wrapped(hy_eosModeAfter, ...) ★
│   │
│   ├── Eos_wrapped(eosMode, blkLimits, blockID, CENTER) ★（让全局变量一致）
│   │
│   ├── Driver_sourceTerms
│   │   ├── Heatexchange（3T 平衡）→ Eos_wrapped per-component ★
│   │   ├── Laser（沉积到 EELE_VAR）→ Eos_wrapped dens_ie_ele ★
│   │   └── Burn / Cool / ... → 可能调 Eos_wrapped ★
│   │
│   ├── RadTrans（辐射传输，改 ERAD_VAR）
│   │   └── 调 Eos_wrapped dens_ie_rad ★
│   │
│   └── Grid_updateRefinement
│       └── AMR refine 后 Eos_wrapped dens_ie_recal_gather ★
│
└── (收尾) Driver_finalizeFlash
    └── Eos_finalize ★（基本空）
```

---

## 9. 延伸阅读

- **Eos 总览**：`knowledge/overview.md`
- **参数字典**：`knowledge/params.md`
- **典型配置**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **Hydro 单元**：`flash-hydro` skill（怎么用 EOS 算的 P,T）
- **Heatexchange 单元**：`flash-sourceterms`（Phase 2 后）

---

## 10. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：10 段 internals；12 公共 API 分类；Eos_wrapped 10 步流程含行号；eos_mapLookup 间接映射机制；Helmholtz 表加载流程；EOS 模式枚举映射；eintSwitch 防消去机制；完整文字调用图（按 L-002） | claude |
