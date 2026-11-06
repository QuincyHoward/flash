---
title: 激光（EnergyDeposition）常见错误与排查
skill: flash-laser
category: pitfalls
source_anchors:
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:104-115
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:280-360
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserPulses/ed_setupPulses.F90:74-145
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition_init.F90:140-380
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90:160-220
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserRayTrace/CellAverage/ed_traceBlockRays2DCyl3D.F90:420-450
  - cases/NOTE.txt
manual_ref: "FLASH 4.8 User Guide, EnergyDeposition troubleshooting (待 Phase 1 Week 2 转换)"
created: 2026-06-17
last_verified: 2026-07-10
verifier: claude
status: beta
tags:
  - laser
  - pitfalls
  - troubleshooting
  - abort
  - debug
  - 错误排查
---

# 激光常见错误与排查

> **TL;DR**：12 个最常见错误，按"错误信息 → 原因 → 修复步骤"三段式组织。覆盖编译期、启动期、运行期、概念错误四类。**遇到 abort 先查这里**，90% 的常见问题能直接定位。

---

## 1. 物理原理

> 错误排查依赖对机制的理解。详见 [[knowledge/overview]] §1（物理原理）、[[knowledge/internals]] §3-4（调用流程）。

---

## 2. 错误分类速查表

| 类别 | 错误数 | 典型时机 |
|---|---|---|
| **A. 编译/链接期** | 2 | `make` 时 |
| **B. 启动期 abort**（参数验证） | 5 | `flash4` 启动后立即 abort |
| **C. 运行期数值异常** | 3 | 跑几步后 NaN / depo 异常 / ffpe-trap |
| **D. 概念错误**（不 abort 但结果错） | 2 | 跑完看结果才发现 |

**第一步诊断**：看 abort 信息中的 `[<routine_name>]` 前缀，直接定位到下面对应章节。

---

## A. 编译/链接期

### A.1 `ld: warning: libmpi.so.40 may conflict with libmpi.so.12`

**完整错误**：
```
/usr/bin/ld: warning: libmpi.so.12, needed by /home/ubuntu/local/flash/myFLASH4.8/hypre/lib/libHYPRE.so,
may conflict with libmpi.so.40
```

**原因**：本机（ares 主机）系统提供 `libmpi.so.40`，但 `libHYPRE.so` 链接的是用户自建 mpich 的 `libmpi.so.12`。两者冲突。

**修复步骤**（编译期 workaround）：
```bash
# 备份系统 MPI 库（需要 sudo）
sudo mv /lib/x86_64-linux-gnu/libmpi.so.40 /lib/x86_64-linux-gnu/libmpi.so.40.bak

# 重新编译
make -j4

# 编译完成后恢复（避免影响其他程序）
sudo mv /lib/x86_64-linux-gnu/libmpi.so.40.bak /lib/x86_64-linux-gnu/libmpi.so.40
```

**源码出处**：本机特有，记录在 `cases/NOTE.txt` 和 `note.txt`。

**永久方案**：在 `sites/ares/Makefile.h`（如存在）改 `LIB_MPI` 路径，让链接器优先找 mpich 的版本。

---

### A.2 `undefined reference to 'ed_<something>_<N>'`

**完整错误**：
```
undefined reference to `ed_wavelength_7'
undefined reference to `ed_lensX_7'
```

**原因**：parfile 里用了 `ed_<prop>_7`，但 setup 时 `ed_maxBeams` 默认 6，没有生成第 7 套参数槽。

**修复步骤**：
1. 检查 parfile 里最大用到的 beam 编号 N
2. 在 setup 命令加 `ed_maxBeams=N`（或更大）：
   ```bash
   ./setup laser_CH -2d -auto +pm4dev ... ed_maxBeams=10 ...
   ```
3. 重新 `make -j4`

**预防**：每个 recipe 在 parfile 顶部注释里写明"需要 `ed_maxBeams=N`"。

---

## B. 启动期 abort（参数验证）

### B.1 `ed_setupBeams: Not enough beam runtime parameters`

**完整错误**：
```
ed_setupBeams: Not enough beam runtime parameters. See Log File!
```

**原因**：`ed_numberOfBeams`（parfile 设定） > `ed_maxBeams`（setup 编译期设定，默认 6）。

**和 A.2 区别**：
- A.2 是链接期报错（参数变量根本不存在）
- B.1 是运行期报错（变量存在但数量不够）

**修复**：同 A.2，setup 时加 `ed_maxBeams=N`。

**源码**：`LaserBeams/ed_setupBeams.F90:104-115`：

```fortran
if (ed_numberOfBeams > ED_MAXBEAMS) then
    call Logfile_stampMessage ("ed_setupBeams: ERROR")
    call Logfile_stampMessage ("# of beams > maximum # of beam runtime parameters!")
    call Logfile_stampMessage ("Increase the maximum number of beam runtime parameters")
    call Logfile_stampMessage ("using the ed_maxBeams=<number of beams> setup option.")
    call Driver_abortFlash    ("ed_setupBeams: Not enough beam runtime parameters. See Log File!")
end if
```

---

### B.2 `ed_setupPulses: Wrong time order for pulse sections!`

**原因**：`ed_time_<p>_<s>` 序列**没有严格递增**。常见错误：
- 写错时间单位（如把 `0.1e-9` 写成 `0.1`）
- 段顺序混乱（s=3 的时间小于 s=2）
- 复制粘贴时改错了

**修复**：检查 parfile，确保 `ed_time_<p>_<s>` 严格递增（s 越大时间越晚）：

```fortran
# ❌ 错误示例
ed_time_1_1 = 0.0
ed_time_1_2 = 0.5e-9    # 比 _3 还晚
ed_time_1_3 = 0.1e-9
ed_time_1_4 = 1.0e-9

# ✅ 正确
ed_time_1_1 = 0.0
ed_time_1_2 = 0.1e-9
ed_time_1_3 = 0.5e-9
ed_time_1_4 = 1.0e-9
```

**源码**：`LaserPulses/ed_setupPulses.F90:120-124`：

```fortran
if (pulseTime <= oldTime) then
    call Driver_abortFlash ("ed_setupPulses: Wrong time order for pulse sections!")
end if
```

---

### B.3 `ed_setupPulses: Negative pulse power specified!`

**原因**：`ed_power_<p>_<s>` 写了负值。FLASH 不允许负功率（即使你想表达"反向"也无效，激光是单向的）。

**修复**：把负值改 0 或正值。如果想"关闭脉冲"，把功率设为 0 即可：

```fortran
# ❌ 错误：用负值表示关
ed_power_1_1 = -1.0

# ✅ 正确：用 0 表示关
ed_power_1_1 = 0.0
```

**源码**：`LaserPulses/ed_setupPulses.F90:117-119`。

---

### B.4 `ed_setupBeams: invalid 3D beam cross section function type!`

**完整错误**：
```
Beam # , cross section function type =  1 flattopGaussian
Should be: uniform, radialweighted, gaussian2D, gaussianInverse2D
ed_setupBeams: invalid 3D beam cross section function type!
```

**原因**：`ed_crossSectionFunctionType_<i>` 字符串拼错，或大小写错，或不在白名单。

**3D 几何白名单**（源码 `ed_setupBeams.F90:336-343`）：
- `uniform`
- `radialweighted`
- `gaussian2D`
- `gaussianInverse2D`

**2D 几何白名单**（`:285-292`）：
- `uniform`
- `gaussian1D`
- `gaussianInverse1D`

**修复**：
1. 检查字符串拼写（**全小写**、末尾 `1D`/`2D` 不是 `1d`/`2d`）
2. 确认几何类型匹配（3D 用 `*2D`，2D 用 `*1D`）
3. 如果用了自定义函数（如 `flattopGaussian`），必须在源码 `ed_setupBeams.F90:336-343` 加白名单 + 重新 setup+make

---

### B.5 `ed_setupBeams: target semiaxes lengths out of order (major < minor)!`

**原因**：`ed_targetSemiAxisMajor_<i>` < `ed_targetSemiAxisMinor_<i>`。FLASH 强制 Major ≥ Minor。

**修复**：交换两个值，让 Major 是大的那个。

**源码**：`ed_setupBeams.F90:316-318`。

**注意**：如果想做 a < b 的椭圆，反转主轴方向（用 `ed_semiAxisMajorTorsionAxis` + 90° 扭转）而不是直接交换数值。

---

## C. 运行期数值异常

### C.1 `depo` 全为 0（激光能量没沉积）

**症状**：plotfile 里 `depo` 变量全是 0；`TELE_VAR` 在 target 区域没升高。

**5 种可能原因 + 诊断步骤**：

| # | 原因 | 诊断方法 | 修复 |
|---|---|---|---|
| 1 | **pulse 时段没覆盖当前 simTime** | 检查日志的 `current simulation time` 是否在 `[ed_time_1_1, ed_time_1_N]` 内 | 调整 `ed_time_*_*` 覆盖模拟时段 |
| 2 | **lens 或 target 落域外** | 检查 `ed_lens{X,Y,Z}` 和 `ed_target{X,Y,Z}` 是否在 `[xmin,xmax]×[ymin,ymax]×[zmin,zmax]` 内 | 调整坐标到域内 |
| 3 | **wavelength 错导致 N_c 太低** | 算 N_c = π m_e c²/(e² λ²)，对照域内最大 N_e；若 N_c < max(N_e) 则 ray 全部被反射 | 改 wavelength（短波长 N_c 高） |
| 4 | **target 椭圆完全在域外** | 用 `ed_printBeams=.true.` 看日志的 target 坐标 | 调整 target 到域内 |
| 5 | **useEnergyDeposition = .false.** 或 setup 时没 `+laser` | 检查日志有无 `[EnergyDeposition_init]` 输出 | parfile 设 `.true.`，setup 加 `+laser` |

**诊断流程图**：
```
日志有 [EnergyDeposition_init]?
├── 否 → useEnergyDeposition=.false. 或没 +laser
└── 是
    └── 日志有 "laser is on"?
        ├── 否 → pulse 时段问题（原因 1）
        └── 是
            └── plotfile 的 depo 全 0?
                ├── 是 → 坐标 / N_c 问题（原因 2-4）
                └── 否（极小但非零）→ ray 数太少或 gridWeight 不准
```

---

### C.2 沉积图有明显噪点 / 颗粒感

**症状**：`depo` 分布应该平滑（如高斯），但实际看起来像噪点。

**原因**：ray 数太少，统计涨落明显。

**修复**：
1. 增大 `ed_numberOfRays_<i>`：
   - 圆光斑高斯：≥ 2048
   - 平顶 super-Gaussian：≥ 4096（α 越大要越多）
   - 多束配置：每束 ≥ 2048
2. 改 gridType：圆光斑用 `radial2D`（比 `square2D` 高效），矩形用 `rectangular2D`
3. 增加 `ed_gridnRadialTics_<i>`（如 32 → 64）

**注意**：每次加 ray 数后检查 `ed_maxRayCount`（A.2 节）。

**为什么不能改 cross-section 来"平滑"**：cross-section 决定**形状**，不影响**采样精度**。详见 [[knowledge/overview]] §2.3。

---

### C.3 `ffpe-trap` 触发 / NaN / 数值溢出

**症状**：用 `-debug` 编译时报 `ffpe-trap=invalid,zero,overflow`；或 `TELE_VAR` 出现 NaN。

**3 种典型原因**：

#### C.3.a `ed_gaussianRadius_<i>` 为 0 或负值

**症状**：`ed_beamCrossSectionFunctions.F90` 里 `xf = (x-Cx)/Rx` 除零。

**修复**：`ed_gaussianRadius*_<i>` 必须 > 0。

#### C.3.b `ed_targetSemiAxisMinor_<i>` = 0 导致除零

**症状**：gridWeight 计算时 aspectRatio = Major/Minor 除零。

**修复**：Minor 必须 > 0；想做圆斑就让 Major = Minor。

#### C.3.c 自定义截面函数在边缘发散

**症状**：你写了 `gaussianInverse2D` 但没限制 `targetSemiAxis`，导致 gridWeight 累加溢出。

**修复**：自定义函数必须在 `targetSemiAxis` 边界处有限值；`gaussianInverse*` 类型务必 `targetSemiAxis > gaussianRadius`。

**通用调试技巧**：
- 临时去掉 `-debug` 改 `-O2`，看是否还 NaN（如不报，是真数值问题；如还报，是逻辑错）
- 加 `ed_printRays=.true.` 看具体哪根 ray 出问题
- 用 `cellWallThicknessFactor=1.0e-4`（默认 1e-6 → 1e-4）增加数值裕度

---

## D. 概念错误（不 abort 但结果错）

### D.1 2D RZ 没开 `ed_laser3Din2D`（吸收率严重偏低）

**症状**：跑完了不报错，但激光吸收率只有 10-30%（预期 60-80%）；`depo` 在 r=0 附近极强、其他地方几乎没沉积。

**原因**：2D RZ 几何默认 ray 只在 (r,z) 平面内运动。所有 ray 都沿同一方向，根本没"扫过" target 圆面，只在中心轴附近沉积。

**修复**：
```fortran
ed_laser3Din2D           = .true.       # ★ 2D RZ 必须
ed_laser3Din2DwedgeAngle = 0.1          # 楔角（度，< 180）
```

**源码**：`LaserBeams/ed_setupBeams.F90:128-132`：
```fortran
beams3D = ...
   .or. (ed_gridGeometry == GRID_2DCYLINDRICAL .and. ed_laser3Din2D)
```

→ 不开就走 `beams2D` 分支，模拟不出真实锥形入射。

**诊断方法**：看 `depo` 分布——如果**只在 r=0 一条线上**有沉积，几乎肯定是这个问题。

---

### D.2 单位混淆（最常见，影响最大）

**症状**：跑完了不报错，但结果**完全不合理**——光斑大小、能量沉积、温度峰值都偏离预期几个数量级。

**单位陷阱速查表**（详见 [[knowledge/params]] §8）：

| 参数 | 正确单位 | 容易错写成 | 后果 |
|---|---|---|---|
| `ed_wavelength_<i>` | **μm** | cm（`1.053e-4`） | N_c 算错 10⁸ 倍，全反射或全穿透 |
| `ed_wavelength_<i>` | **μm** | nm（`1053`） | N_c 算错 10⁶ 倍 |
| `ed_lens{X,Y,Z}_<i>` | **cm** | mm（`120.0`） | lens 跑到域外 |
| `ed_target{X,Y,Z}_<i>` | **cm** | μm（`100`） | target 跑到域外 |
| `ed_targetSemiAxis*_<i>` | **cm** | μm（`100`） | 光斑半径 100 cm 比域大 |
| `ed_gaussianRadius*_<i>` | **cm** | μm（`100`） | 高斯极窄，全部能量集中一点 |
| `ed_time_<p>_<s>` | **s** | ns（`0.1` 而非 `0.1e-9`） | pulse 时段超出模拟时段 |
| `ed_power_<p>_<s>` | **W** | erg/s（`3.0e18`） | 功率过大，温度溢出 |
| `ed_semiAxisMajorTorsionAngle_<i>` | **度** | 弧度（`0.785`） | 椭圆方向几乎不变 |

**诊断方法**：
- 用 `ed_printBeams=.true.` 看日志，对照"wavelength in cm"、"lensX in cm"等行
- 算几个关键数（如 N_c、target 椭圆面积）对照物理直觉

**预防**：在 parfile 注释里**每个参数都写单位**，如：
```fortran
ed_wavelength_1               = 1.053         # μm（不是 cm/nm！）
ed_lensZ_1                    = 12.0          # cm
ed_targetSemiAxisMajor_1      = 0.01          # cm（= 100 μm）
```

---

## 3. 调试通用流程

### 3.1 abort 时该收集什么信息

遇到 abort 时，把这 4 样东西准备好再排查：

1. **完整 abort 信息**（含 `[<routine>]` 前缀和 message）
2. **`cases/<name>/setup_call`**（确认 setup 命令）
3. **`flash.par` 激光段**（确认实际配置）
4. **日志开头 100 行**（含 `ed_printMain/Pulses/Beams` 输出）

### 3.2 启用调试模式

```bash
# 1. 重新 setup 加 -debug
./setup laser_CH -2d -auto +pm4dev ... -debug -objdir=cases/<name>_debug

# 2. make（这次会用 FFLAGS_DEBUG，含 -ffpe-trap 和 bounds-check）
cd cases/<name>_debug && make -j4

# 3. parfile 加调试开关
ed_printMain   = .true.
ed_printPulses = .true.
ed_printBeams  = .true.
# ed_printRays  = .true.   # 慎用，输出量极大
```

### 3.3 调试 ray 追踪问题

如果是 ray 追踪数值问题（不是 abort）：

```fortran
# 1. 开 LaserIO 看具体 ray 路径
ed_useLaserIO                  = .true.
ed_laserIOMaxNumberOfPositions = 10000
ed_laserIOMaxNumberOfRays      = 32        # 先看少量 ray

# 2. 跑几步后看 plotfile 里的 ray 数据
# 用 yt 加载 plotfile，画 ray 轨迹
```

### 3.4 二分法定位问题

如果不确定哪个参数导致问题：
1. 复制 parfile 到 `flash_debug.par`
2. 把激光参数**全部还原到 Recipe 1**（最小可运行）
3. 确认能跑通
4. 一次只改一个参数，跑到失败为止
5. 失败的那次改动就是问题源

---

## 4. 已知陷阱汇总（指向其他 knowledge）

> 这些陷阱在对应 knowledge 里已详述，本节只列索引。

| 陷阱 | 详见 |
|---|---|
| setup 变量 vs runtime parameter 混淆 | [[knowledge/params]] §6 |
| `-HUGE(1.0)` 默认值的意义 | [[knowledge/params]] §5 |
| lens 只有 Major 没有 Minor | [[knowledge/params]] §8.4 |
| `RAY_BEAM` 正负号约定 | [[knowledge/internals]] §9.1 |
| `ed_checkReuseDepo` 复用机制 | [[knowledge/internals]] §9.4 |
| Cell Average vs Cubic Interpolation | [[knowledge/internals]] §9.5 |
| 自动归一化保证 Σ P_ray = P_beam | [[knowledge/overview]] §2.3 |

---

## 5. 延伸阅读

### 5.1 本 skill 内
- [[knowledge/overview]] — 物理原理（理解为什么会出这些错）
- [[knowledge/params]] — 参数完整字典（对照单位、默认值、白名单）
- [[knowledge/internals]] — 内部调用图（理解 abort 来源）
- [[knowledge/recipes]] — 正确配置范例（对照排查错配）

### 5.2 跨 skill
- `flash-pitfall-finder` skill — 自动匹配本文件中的条目
- `flash-source-reader` skill — 想看 abort 信息对应的源码行
- `flash-case-runner` skill — 集成了 abort → pitfall 自动诊断流程

### 5.3 外部资源
- `cases/NOTE.txt` — 本机特定的 libmpi 冲突说明
- FLASH 邮件列表档案（google 搜 abort 信息原文）
- `tools/scripts/codeCheck.py` — 静态检查

---

## 6. 维护说明

本文件是"活的"踩坑库。**每遇到一个新 abort 或异常**，按 D-004 决策（[[../../SKILL.md]] §3 自动扩写规则）：
1. 解决后立刻生成草稿到 `agent/drafts/pending/`
2. 用户 review 后 promote 到本文件
3. 在 §9 变更日志加一行

---

## 7. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-06-17 | 初始创建（12 条踩坑，覆盖编译/启动/运行/概念四类，含调试通用流程） | claude |
| 2026-07-10 | last_verified 更新（对照源码行号核对，无内容修改） | claude |
