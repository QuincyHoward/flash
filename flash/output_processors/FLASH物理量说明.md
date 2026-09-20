# FLASH 物理量说明（chk 文件）

> **适用范围**：FLASH 4.8 激光-等离子体算例（LaserSlab 系：`ch_center`、`thin_layer_sandwich_si/al` 等），
> 1D/2D/3D 直角/柱坐标，三温（3T）+ 表格 EOS（ionmix `.cn4`）+ MGD 多群辐射扩散（grupbd=7）+ 激光能量沉积（ray tracing）。
>
> **数据来源**：
> - 源码：`flash/flash_src/FLASH4.8/FLASH4.8/source/`（下文相对路径均基于此）
> - 后处理器：`flash/output_processors/`（`DATA_CONFIG` 注册表、`FlashDataLoader`、`DataCalculator`）
> - 时空派生量算法：`PhysicsResearchTools/.../SimComp/CASES_Comp/`（fronts / traj_quant / phase_slope）
> - EOS 表：`flash/input_gen/gen_eos_op/ionmix/`（IONMIX `eos.cn4`，见《IONMIX用户指南》§5.4）
>
> **约定**：下表"FLASH 单位"指 chk 文件中存储的原始单位（FLASH 内部 CGS，温度为 K）；
> "to_si" 指 `output_processors/hdf5processor/flash_hdf5.py` 中 `DATA_CONFIG` 的 SI 换算系数。

---

## 0. chk 文件结构与单位约定

### 0.1 chk 与 plot 文件的区别

| 项目 | checkpoint（chk） | plot |
|------|------------------|------|
| 浮点精度 | float64 | float32 |
| 变量集 | 完整（unk 全部 + 面心量 + 粒子），典型 ~44 个 | 仅绘图变量，典型 ~9 个 |
| 用途 | 重启计算、完整物理分析 | 快速可视化 |

（依据：`output_processors/hdf5processor/flash_hdf5.py` 模块 docstring。）

### 0.2 chk 的 HDF5 数据集（根组平铺，无子组）

| 数据集 | 形状 | 含义 |
|--------|------|------|
| `unknown names` | (nvars,) | 物理变量名 → unk 索引的映射，**判断某变量是否存在以此为准** |
| `unknown cvars` | (nblocks, NZ, NY, NX, nvars) | 单元中心量（h5py C 序，即每块 `(Nz,Ny,Nx)` × 变量） |
| `unknown facevarsx/y/z` | … | 面心量（如 MHD `facex`） |
| `real scalars` | (n,) | `name`+`value` 复合类型：`time`/`dt`/`dtold`/`dtnew` 等 |
| `integer scalars` | (n,) | `nstep`/`nxb`/`nyb`/`nzb`/`dimensionality`/`globalnumblocks` 等 |
| `real/integer/logical/string runtime parameters` | (n,) | 全部运行时参数（**名全小写**，logical 存 0/1），含激光 `ed_time_P_S`/`ed_power_P_S`；详见 §1.7 |
| `sim info` | (n,) | setup 命令行、编译时间/编译器/编译选项（重建算例配置的权威入口，§1.7） |
| `bounding box` | (nblocks, NDIM, 2) | 每块各方向 min/max |
| `refine level` | (nblocks,) | AMR 细化级 |
| `node type` | (nblocks,) | **1 = 叶块**（参与物理计算；父块数据被子块覆盖，不可用） |
| `gid` | (nblocks, MN+2*NDIM+2*NDIM) | 块邻接/树结构 |

单元中心坐标由 bounding box 重建：`x_c(i) = xmin + (i + 0.5) * dx`（0-based 索引）。
AMR 块在边界有重叠单元，展平为全局 1D 网格时须按坐标去重——
`FlashHDF5File.extract_var_yt_style()` 已实现叶块筛选 + 坐标重建 + 去重（`_dedup_1d/2d/3d`）。

### 0.3 单位约定与铁律

1. **FLASH 内部全 CGS**：`dens [g/cm³]`、`velx [cm/s]`、`pres [dyne/cm²]`、比能量 `[erg/g]`、长度 `[cm]`、时间 `[s]`。
2. **★★★ 温度单位是 K，不是 eV**。`tele/tion/trad/temp` 均为 K。
   实测证据：`p=(n_i+n_e)kT` 仅当 T 取 K 时与 chk `pres` 吻合（差 1.4%）；
   `eint=(3/2)p/ρ` 在 290 K 与 chk `eint` 吻合 99.7%。
   显示 eV 须除以 `11604.518 K/eV`。
   （历史事故：换算常数曾误写 `1.16045e7`（大 1000×），已修。）
3. **能量积分须乘密度**：总内能 `E = ∫ ρ·eint dx`，漏乘 ρ 会虚报能量超支。
4. **变量是否存在取决于算例 Config 与启用的物理单元**——以 chk 内 `unknown names` 为准，
   `output_processors` 的 `DATA_CONFIG` 是通用注册表（加载时不在文件中的变量自动跳过）。
5. 项目实测：`+ug`（uniform grid）模式下 chk 首格满足 `x[0,0] == par_xmin + 64*dx`（64=nxb/2），
   域整体存在约 +1.9084 µm 的固有偏移，层位置校验一律**按实测坐标**。

---

## 1. chk 原始物理量（raw variables）

> 声明位置格式：源码文件相对路径（基于 `source/`）+ 行号。Fortran 片段为原文摘录。

### 1.1 流体核心量 — `physics/Hydro/HydroMain/unsplit/Config`

```fortran
# Variables required by the unsplit solvers
VARIABLE dens TYPE: PER_VOLUME  EOSMAP:  DENS # density
VARIABLE velx TYPE: PER_MASS    EOSMAPIN:VELX # x-velocity
VARIABLE vely TYPE: PER_MASS    EOSMAPIN:VELY # y-velocity
VARIABLE velz TYPE: PER_MASS    EOSMAPIN:VELZ # z-velocity
VARIABLE pres                   EOSMAP:  PRES # pressure
VARIABLE ener TYPE: PER_MASS    EOSMAP:  ENER # specific total energy (T+U)
VARIABLE gamc                   EOSMAP:  GAMC # sound-speed gamma
VARIABLE game                     EOSMAP:  GAME # internal energy gamma
VARIABLE temp                   EOSMAP:  TEMP # temperature
VARIABLE eint TYPE: PER_MASS    EOSMAP:  EINT # specific internal energy (U)
VARIABLE shok # flag variable for shock detection
```
（`source/physics/Hydro/HydroMain/unsplit/Config:59-70`）

| 变量 | 物理意义 | FLASH 单位 | to_si | 备注 |
|------|----------|-----------|-------|------|
| `dens` | 质量密度 ρ | g/cm³ | ×1e3 → kg/m³ | PER_VOLUME |
| `velx/vely/velz` | 速度分量 (u,v,w) | cm/s | ×0.01 → m/s | 1D 一般仅 velx |
| `pres` | 总压力 p=p_e+p_i+p_r | dyne/cm² | ×0.1 → Pa | EOS 恢复 |
| `ener` | 比总能量 e+u²/2 | erg/g | ×1e-4 → J/kg | PER_MASS |
| `eint` | 比内能 | erg/g | ×1e-4 → J/kg | EOSMAP EINT |
| `gamc` | 声速绝热指数 γ_c | 1 | — | c_s=√(γ_c·p/ρ)；声速族见 §2.8 |
| `game` | 内能指数 γ_e=1+p/(ρe)（e=p/(ρ(γ_e−1))）；表格 EOS 下暂与 gamc 同值 | 1 | — | 出处见 §2.8 |
| `temp` | （单温模式）温度 | K | — | 3T 模式下意义弱化 |
| `shok` | 激波检测标志 | 0/1 | — | 判据见 §3.4 |

### 1.2 三温（3T）量 — `physics/Hydro/HydroMain/unsplit/multiTemp/Config`（unsplit_rad 同款）

```fortran
VARIABLE pion                   EOSMAP:  PRES1  # ion pressure
VARIABLE pele                   EOSMAP:  PRES2  # electron pressure
VARIABLE prad                   EOSMAP:  PRES3  # radiation pressure

VARIABLE tion                   EOSMAP:  TEMP1  # ion "temperature"
VARIABLE tele                   EOSMAP:  TEMP2  # electron "temperature"
VARIABLE trad                   EOSMAP:  TEMP3  # radiation "temperature"

VARIABLE volx
VARIABLE voly
VARIABLE volz

VARIABLE eion TYPE: PER_MASS  EOSMAP: EINT1  # specific internal energy of ions (and neutrals?)
VARIABLE eele TYPE: PER_MASS  EOSMAP: EINT2  # specific internal energy of electrons
VARIABLE erad TYPE: PER_MASS  EOSMAP: EINT3  # specific internal energy of radiation

VARIABLE dbgs                           # debug for shocks
```
（`source/physics/Hydro/HydroMain/unsplit/multiTemp/Config:4-23`）

| 变量 | 物理意义 | FLASH 单位 | to_si | 备注 |
|------|----------|-----------|-------|------|
| `tele` | 电子温度 T_e | **K** | — | eV = /11604.518 |
| `tion` | 离子温度 T_i | **K** | — | |
| `trad` | 辐射温度 T_r | **K** | — | MGD 中 e_r=a_r·T_r⁴ |
| `pele` | 电子分压 p_e | dyne/cm² | ×0.1 → Pa | |
| `pion` | 离子分压 p_i | dyne/cm² | ×0.1 → Pa | |
| `prad` | 辐射分压 p_r=a_r·T_r⁴/3 | dyne/cm² | ×0.1 → Pa | |
| `eele` | 电子比内能 | erg/g | ×1e-4 → J/kg | 含热能+电离能（表格 EOS） |
| `eion` | 离子（含中性）比内能 | erg/g | ×1e-4 → J/kg | |
| `erad` | 辐射比内能 | erg/g | ×1e-4 → J/kg | MGD 能量密度 e_r=a_r·T_r⁴ [erg/cm³]，注意 per-mass/per-volume 约定以场景为准 |
| `tite` | 电子-离子温度平衡诊断（源码注释 "Temp. ions / temp. electrons"） | — | — | 仅当场景启用时存在 |
| `pipe` | 离子/电子分压比诊断（源码注释 "Pres. ions / pres. electrons"） | 1 | — | |

> `tite`/`pipe` 声明：`source/physics/Eos/EosMain/multiTemp/Config:52-53`。

> 校验关系：`pres ≈ pele + pion + prad`；`eint ≈ eele + eion (+ erad)`。

### 1.3 物种质量分数与丰度（ye / sumy）

物种变量由 setup 参数 `species=...` 声明（LaserSlab 说明见
`source/Simulation/SimulationMain/LaserSlab/Config:14-22`），变量名即物种短名，
每个占 unk 一个槽位，值为**质量分数 Y_k ∈ [0,1]**，`Σ Y_k = 1`：

| 变量 | 物理意义 | 场景示例 |
|------|----------|----------|
| `targ` / `tar1..tar6` | 靶层质量分数 | SNBVTi2_ml：tar2=Ti，tar1/3/4/6=CH |
| `cham` | 腔体（CH 泡沫/氦）质量分数 | |
| `shld` / `samp` | 屏蔽层 / 样品层质量分数 | thin_layer_sandwich 系 |

电子丰度 `ye` 与离子丰度 `sumy`（每克物质的摩尔数）由 EOS 写回
（`source/physics/Eos/EosMain/multiTemp/Eos_putData.F90:278-286`）：

```fortran
if(ye_map /= NONEXISTENT) then
   Ye = eosData(zbar+n) / eosData(abar+n)
   solnData(ye_map,i,j,k) = Ye
   ...
if(sumy_map /= NONEXISTENT) then
   solnData(sumy_map,i,j,k) = 1.0/eosData(abar+n)
```

反向换算（`Eos_getData.F90:378-395`，EOS 读入侧）：

```fortran
!! cal says abar=1/sumy
   eosData(abar+n) =  1.0 /  solnData(sumy_map,i,j,k)
!! cal says zbar=ye / sumy and he claims sumy are never zero
   eosData(zbar+n) = solnData(ye_map,i,j,k) /  solnData(sumy_map,i,j,k)
```

| 变量 | 物理意义 | FLASH 单位 | to_si | 定义 |
|------|----------|-----------|-------|------|
| `ye` | 电子丰度（每克物质电子摩尔数） | mol/g | 1 | ye = zbar/abar = Σ_k Y_k·Z_k/A_k（全电离极限） |
| `sumy` | 离子丰度（每克物质离子摩尔数） | mol/g | 1 | sumy = 1/abar = Σ_k Y_k/A_k |
| `Y_k`（targ/cham/…） | 物种质量分数 | 1 | — | Σ Y_k = 1 |

由此 **zbar = ye/sumy、abar = 1/sumy** 是 chk 内生关系（§2 直接派生）。

### 1.4 激光量（EnergyDeposition / Laser）

声明（`source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config`）：

```fortran
D depo_variable  The DEPO variable stores the laser energy deposition in each cell
D &              if ed_depoVarName is set to "depo" (which should be the default below).
D &              If the variable is declared with TYPE: PER_VOLUME, the deposited energy is stored
D &              as an energy density; otherwise the deposited energy stored is stored as a
D &              specific energy (per mass unit).
VARIABLE depo TYPE: PER_MASS
```
（`Laser/Config:18-23`）

```fortran
D          ed_irradVarName      Name of the variable used for storing the computed
D &                             laser radiation field energy density; the default
D &                             is "lase". ...
PARAMETER  ed_irradVarName             STRING    "lase"
```
（`Laser/Config:131-138`；`ed_depoVarName STRING "depo"` 在 :129）

LaserSlab 侧声明（`source/Simulation/SimulationMain/LaserSlab/Config:88-89`）：

```fortran
D lase_variable saves (density of) the irradiated energy from EnergyDeposition unit, cf. RP ed_irradVarName
VARIABLE lase TYPE: PER_VOLUME
```

| 变量 | 物理意义 | 默认单位 | 备注 |
|------|----------|---------|------|
| `depo` | 激光能量沉积（本步沉积能量的累计存储，供复用与诊断） | **erg/g**（默认 PER_MASS 声明） | 单位随声明改变：PER_VOLUME → erg/cm³ |
| `lase` | 激光辐射场能量密度（ray tracing 沿迹累计） | **erg/cm³**（PER_VOLUME） | 变量名由 `ed_irradVarName` 指定 |

激光脉冲波形以**运行时参数**存于 `real runtime parameters`（存储机制见 §1.7）：
`ed_time_P_S` / `ed_power_P_S`（**P=脉冲编号、S=时间点/段编号**）。
源码默认值为 **−1.0 哨兵**（"未设置"），并非 0.0（`Laser/Config:208-209`；
注释单位 "The time (s)" / "The power (W)"，1D 均匀束下 power 实为**强度口径 W/cm²**）。
最大脉冲数/段数由 **setup 选项** `ed_maxPulses=` / `ed_maxPulseSections=` 控制
（PPDEFINE 编译期宏，**不是运行时参数**，chk 中查不到；实测 SNBOneCH_ml：
300 段注册、82 段使用，峰值 3.15e14 W/cm²）。
解析器：`FlashHDF5File.laser_groups`（`output_processors/loader/data_loader.py:586-638`，
正则 `ed_time_(\d+)_(\d+)` / `ed_power_(\d+)_(\d+)`，返回 `{pulse: {time[], power[]}}`）。

### 1.5 辐射输运（MGD）辅助量 — `physics/RadTrans/RadTransMain/MGD/Config`

```fortran
VARIABLE ABSR
VARIABLE EMIS
VARIABLE MGDC
```
（:13/:17/:20）

| 变量 | 物理意义 | FLASH 单位 | 备注 |
|------|----------|-----------|------|
| `absr` | 群积分辐射吸收率（吸收能量速率） | erg·cm⁻³·s⁻¹ | RAD_ABSORB，含 ρκ 权重 |
| `emis` | 群积分辐射发射率 | erg·cm⁻³·s⁻¹ | RAD_EMIT |
| `mgdc` | MGD 扩散系数 | cm²/s | 内部诊断 |

> `trad`（TEMP3）即 MGD 的辐射温度自变量；多群信息（每群强度）不在 chk 常规变量内，
> 群不透明度从 ionmix 表侧查询（§4）。

### 1.6 chk 头部标量（时间/步数/网格）

| 标量 | 类别 | 单位 | 含义 |
|------|------|------|------|
| `time` | real scalar | s | 当前仿真时刻（**chk 的 t**） |
| `dt` / `dtold` / `dtnew` | real scalar | s | 当前/上一/下一时间步长 |
| `nstep` | integer scalar | — | 步数 |
| `nxb/nyb/nzb` | integer scalar | — | 每块网格数 |
| `dimensionality` | integer scalar | — | 空间维数 |
| `globalnumblocks` | integer scalar | — | 全局块数 |

（读取实现：`output_processors/hdf5processor/flash_hdf5.py` `real_scalars`/`integer_scalars` 属性；
`simulation_time = real_scalars["time"]`。）

### 1.7 运行时参数与 `sim info`（chk 头部数据集，非 unk 变量）

除物理场外，chk 根组还平铺存储 **4 个运行时参数数据集**：
`real / integer / logical / string runtime parameters`（复合类型 `name`+`value`），
以及记录 setup 命令行与编译信息的 `sim info`。读取要点（SNBOneCH_ml chk 实测沉淀）：

1. **参数名一律小写**（`ed_wavelength_1`、`sim_tele`）——源码/par 中的大小写在 chk 中不保留，查询时用小写；
2. **logical 以 0/1 存储**，无布尔字面量；
3. **string 定长、空格填充**（如 `basenm = "snbonechug_"`），比较前先 `strip()`；
4. **激光脉冲参数未设置时默认 −1.0（哨兵）**，判"是否启用"用 `> 0`（§1.4）；
5. **`+ug` 运行没有 AMR 参数**：`lrefine_max`/`refine_var_*` 仅 AMR 运行注册，
   `+ug` chk 中查不到属**正常现象**；网格由 `dx = (xmax−xmin)/(nxb·nblockx)` 唯一确定
   （实测：(0.01−(−0.04)) cm/(128×8) = 0.4883 µm）；
6. `sim info` 是**重建算例配置的权威入口**（setup 命令行、编译器、编译时间/选项）。

实测 setup 行（`sim info` 摘录）：

```text
setup.py -auto SNBOneCH_ml -1d +cartesian +ug -nxb=128 +hdf5typeio
species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 +mtmmmt +laser +uhd3t
+mgd mgd_meshgroups=10 ed_maxPulseSections=300
```

**常用参数速查**（★ = chk 实测，SNBOneCH_ml +ug 短测；单位为 FLASH 内部 CGS，另注明者除外）：

| 参数（chk 内小写） | 类别 | 单位 | 含义 | ★ 实测 |
|--------------------|------|------|------|--------|
| `xmin` / `xmax` | real | cm | 计算域边界 | −0.04 / 0.01 |
| `nblockx` | integer | — | x 向块数 | 8 |
| `nxb` | integer | — | 每块网格数 | 128（⇒ dx = 0.4883 µm） |
| `tmax` | real | s | 终止时间 | 2e-10 |
| `dtinit` / `dtmin` / `dtmax` | real | s | 初始/下限/上限步长 | 1e-15 / 1e-16 / 2e-12 |
| `cfl` | real | — | CFL 数 | 0.2 |
| `nend` | integer | — | 最大步数 | 1e8 |
| `xl/xr/yl/yr(/zl/zr)_boundary_type` | string | — | 边界条件 | outflow（x）、periodic（y/z） |
| `geometry` | string | — | 几何 | cartesian |
| `basenm` / `log_file` | string | — | 文件名基 / 日志名 | snbonechug_ / snbonech.log |
| `eosmode` | string | — | EOS 调用模式 | dens_ie_recal_gather |
| `riemannsolver` | string | — | 黎曼求解器 | HLL |
| `smallx` | real | — | 最小质量分数地板 | 1e-99 |
| `rt_mgdnumgroups` | integer | — | MGD 能群数 | 10 |
| `rt_mgdbounds_*` | real | eV | 群边界节点（对数间隔） | 0.1 … 6309.573 |
| `ed_wavelength_1` | real | **µm（例外：非 CGS）** | 激光波长 | 0.351（= 351 nm） |
| `ed_lensx_1` / `ed_targetx_1` | real | cm | 透镜/靶面初始位置 | −1 / 0（透镜在域外） |
| `ms_<物种>a` / `ms_<物种>z` | real | g/mol / — | 各物种摩尔质量/平均电荷 | cham: 4.002602/2；tar*·shld·samp: 6.509/3.5 |
| `sim_rhocham` | real | g/cm³ | 腔体密度 | 1e-6 |
| `sim_rho<物种>` | real | g/cm³ | 层初始密度 | tar*/shld/samp: 1.0 |
| `sim_tar1radius` … `sim_tar6radius` | real | cm | 各靶层边界半径 | 1e-4 … 6e-4 |
| `sim_sampheight` | real | cm | 样品层厚度 | 0.005 |
| `sim_tele` / `sim_tion` / `sim_trad` | real | K | 初始温度 | 290.11375 |

**按物种/分区的参数族命名规则**：`ms_<物种>a/z`、`sim_rho<物种>`、`sim_<量><分区>`
（如 gen_newpara 生成的 `sim_teleTarg`/`sim_teleCham` 等，chk 内即小写 `sim_teletarg`…）。
同一物理量按层/物种批量出现，解析脚本应**按前缀枚举**而非逐一硬编码。

> 参数完整语义、默认值与生成链路见
> `flash/input_gen/gen_newpara/RP_Reference.md`（运行时参数详解，含 chk 实测对照）与
> `flash/input_gen/gen_par/GEN_PAR_GUIDE.md`（par 模板结构与生成器）。

---

## 2. 直接派生量（chk 原始量的单点代数组合）

> 全部由 `output_processors` 的 `DataCalculator` 按 `DATA_CONFIG` 的 `formula` 自动计算
> （`flash_hdf5.py:188-348`），加载时 `FlashDataLoader.load(compute_derived=True)` 默认开启，
> 结果存于 `FlashDataContainer.derived`。

### 2.1 数密度：nele / nion

$$n_e = y_e \cdot \rho \cdot N_A, \qquad n_{ion} = sumy \cdot \rho \cdot N_A$$

```python
NA = 6.02214076e23  # 阿伏伽德罗数 [1/mol]
"nele": {
    "unit": "1/cm^3", "unit_si": "1/m^3", "to_si": 1e6,
    "description": "Electron number density = ye * dens * NA",
    "category": "derived", "depends": ["ye", "dens"],
    "formula": "ye * dens * NA",
},
"nion": {
    "unit": "1/cm^3", "unit_si": "1/m^3", "to_si": 1e6,
    "description": "Ion number density = sumy * dens * NA",
    "category": "derived", "depends": ["sumy", "dens"],
    "formula": "sumy * dens * NA",
},
```
（`flash_hdf5.py:72, 213-224`。量纲自检：mol/g × g/cm³ × mol⁻¹ = cm⁻³。）

### 2.2 平均电荷态与平均质量数：zbar / abar

$$\bar Z = \frac{y_e}{sumy}, \qquad \bar A = \frac{1}{sumy}$$

与 FLASH 内部 EOS 完全同式（§1.3 `Eos_getData.F90:381,389`），因此派生 zbar 与 EOS 表值自洽；
亦可与 ionmix 表插值交叉校验（§4.2）。

### 2.3 组分分密度：dens_targ / dens_cham / dens_shld / dens_samp

$$\rho_k = \rho \cdot Y_k \quad [\mathrm{g/cm^3}]$$

```python
"dens_targ": {..., "description": "Target component density = dens * targ",
              "category": "derived", "depends": ["dens", "targ"], "formula": "dens * targ"},
```
（`flash_hdf5.py:189-212`。多分层场景的层识别、拉格朗日层质心均以此为基。
CASES_Comp 中记作 `dtar = dens_<marker>`，与 FLASH 场互验相对差 <1e-4。）

### 2.4 温度换算：K → eV

$$T_e[\mathrm{eV}] = T_e[\mathrm{K}] / 11604.518$$

换算常数 `K_BOLTZ_EV_PER_K = 11604.518`（历史版本曾误写 1.16045e7，大 1000×，已修——
凡新代码引用换算常数必须以 11604.518 K/eV 为准）。

### 2.5 梯度标长：ls_nele / ls_tele（Thomson 散射诊断量）

$$L_{n_e} = \frac{n_e}{|\partial n_e/\partial x|}, \qquad L_{T_e} = \frac{T_e}{|\partial T_e/\partial x|}$$

数值实现（`flash_hdf5.py:347-448`）：块内 x 方向中心差分
（内部 `(f_{i+1}-f_{i-1})/(2dx)`，边界一阶差分），
梯度幅值 < 1e-30 处置为 1e30（饱和）。2D 取每行、3D 取 z 中间平面广播。

```python
def _gradient_1d(arr, dx):
    grad = np.zeros_like(arr)
    grad[..., 1:-1] = (arr[..., 2:] - arr[..., :-2]) / (2 * dx)
    grad[..., 0] = (arr[..., 1] - arr[..., 0]) / dx
    grad[..., -1] = (arr[..., -1] - arr[..., -2]) / dx
    return grad
```
单位：cm（to_si ×0.01 → m）。

### 2.6 热力学自洽校验量（推荐对每个新算例执行一次）

| 校验式 | 依据 | 允差（项目实测） |
|--------|------|-----------------|
| `pres ≈ (n_i + n_e)·k_B·T`（T 取 K） | 理想等离子体 | 1.4% |
| `eint ≈ (3/2)·pres/ρ` | 单原子理想气体 | 99.7% 吻合（290 K 点） |
| `pres ≈ pele + pion + prad` | 分压定义 | ~1% |
| `Σ Y_k = 1`、`ye/sumy = zbar(表)` | EOS 表 | <1e-4 |

### 2.7 能量密度的正确积分口径

总内能、沉积能量等沿 x 的积分一律为
$$E = \int \rho(x)\, e(x)\, \mathrm{d}x \quad [\mathrm{erg/cm^2}]$$
（1D 面密度口径）。**漏乘 ρ 是历史事故来源**（曾虚报激光能量超支）。

### 2.8 声速族（五种口径）

"声速"在不同物理语境下指不同量；chk 原始量足以计算全部常用口径。
单位均为 cm/s，转 µm/ns **×1e-5**（§5.1）。

| # | 名称 | 公式 | 所需 chk 量 | 典型用途 |
|---|------|------|-------------|----------|
| ① | 流体（绝热）声速 c_s | √(γ_c·p/ρ) | `gamc`,`pres`,`dens` | 流动稳定性、CFL、激波判据（与 FLASH 内部完全一致） |
| ② | 分压声速 c_k | √[(5/3)·p_k/ρ]，k∈{e,i} | `pele`,`pion`,`dens` | 电子/离子分通道贡献分解 |
| ③ | 理想等离子体声速 | √[(5/3)·k_B(T_i+Z̄T_e)/(Ā·m_p)] | `tele`,`tion`,`zbar`,`sumy` | 无 gamc 场景的解析估计、跨算例对比 |
| ④ | 离子声速 c_IA | √(Z̄·k_B·T_e/m_i)（冷离子） | `tele`,`zbar`,`sumy` | 冕区离子声波、LPI/双流不稳定性判据 |
| ⑤ | 辐射-气体混合声速 | √[((5/3)p_g+(4/3)p_r)/ρ]，p_g=p−p_r | `pres`,`prad`,`dens` | 辐射压显著时（Marshak 热波、辐射激波） |

> ⑤ 的来历：混合绝热指数 Γ=(5/3·p_g+4/3·p_r)/(p_g+p_r)，故 Γ·p/ρ ≡ (5/3·p_g+4/3·p_r)/ρ；
> 其中 p_r = a_r·T_r⁴/3 亦可由 `prad` 直接读取。

**γ_c 的来源（表格 EOS 合成，非常数）**：`gamc` 由 EOS 表偏导合成
（`source/physics/Eos/EosMain/Tabulated/eos_tabIonmix4.F90:585-598`）：

$$\gamma_c \;=\; \frac{T}{\rho}\,\frac{\left(\partial P/\partial T\right)_\rho^{\,2}}{\det}\;+\;\rho\left(\frac{\partial P}{\partial\rho}\right)_T$$

（det 为热力学雅可比；退化时源码兜底 `gamc = 5./3.  !hackhackhack!`，
同处另有 `game = gamc  !for now`——§1.1 中 `game` 行"暂与 gamc 同值"即出于此。）

**①在解算器中的地位**：`hy_uhd_shockDetect.F90:114` 以 `c=√(γ_c·p/ρ)` 作激波判据的速度尺度（§3.3）；
CFL 步长估计同样基于 max(c_s+|u|)。

```python
# 声速族一键计算：输入 chk cgs 量（温度 K！铁律 §0.3-2），输出 µm/ns
KB, MP = 1.380649e-16, 1.67262192e-24          # erg/K, g
G53 = 5.0 / 3.0
def sound_speeds(dens, pres, pele, pion, prad, tele, tion, zbar, abar, gamc=None):
    out = {}
    if gamc is not None:
        out["cs"]     = np.sqrt(gamc * pres / dens)                        # ①
    out["cs_e"]   = np.sqrt(G53 * pele / dens)                           # ② 电子
    out["cs_i"]   = np.sqrt(G53 * pion / dens)                           # ② 离子
    out["cs_mix"] = np.sqrt((G53 * (pres - prad) + (4.0/3.0) * prad) / dens)  # ⑤
    out["cs_id"]  = np.sqrt(G53 * KB * (tion + zbar * tele) / (abar * MP))    # ③
    out["cs_ia"]  = np.sqrt(zbar * KB * tele / (abar * MP))              # ④
    return {k: v * 1e-5 for k, v in out.items()}                         # cm/s → µm/ns
```

**交叉校验建议**：全电离理想气体极限下 ①≈③（γ_c→5/3、p=(n_i+n_e)k_B·T）；
两者显著偏离 ⇒ 简并/部分电离/辐射贡献（表格 EOS 捕捉、解析式③未含），此时以 ① 为准。
`zbar/abar` 取 §2.2 的 chk 内生值（ye/sumy）。

---

## 3. 时空场派生量（前沿位置/速度、轨迹量化、拟合分析）

> 算法来源：`PhysicsResearchTools/src/project/Report/Report_ICMRE/Paper_My/SimComp/CASES_Comp/`
> （`fronts/`、`traj_quant/`、`phase_slope/`）。下文相对路径均基于该目录。

### 3.0 数据准备：统一时空网格

- 空间：`[-500, 100] µm` × 30000 点（`SPACE_RANGE_CM=(-500e-4,100e-4)` cm）；
- 时间：`[0, 1.75] ns` × 500 点（`TIME_RANGE_S=(0,1.75e-9)` s）；
- 统一场：`PHYS_FIELDS = ['dens','nele','tele','zbar','pres','depo','velx']`
  + 示踪标记场（`targ` 或 `tar1..tar6`，`shld/samp/cham`），派生 `dens_<marker> = dens × Y`；
- 提取：yt 射线采样（`cases_h5.py`）或 h5py 直读（`fronts/extract_shok.py:76-117`，
  叶块 `node type==1`，`x_c = xmin+(i+0.5)dx`，与 yt 逐点对拍 1520/1520 一致）；
- 插值：两步 `np.interp`（先空间后时间，越界填 0）。

### 3.1 临界密度面 x_c(t) 与速度 v_c

激光临界密度：
$$N_C = \frac{m_e\omega_0^2}{4\pi e^2} \approx \frac{1.1155\times10^{21}}{\lambda_{\mu m}^2}\ \mathrm{cm^{-3}}$$

351 nm（3ω）激光：`N_C = 1.1155e21 / 0.351² ≈ 9.05e21 cm⁻³`（`phase_slope/ps_core.py:62-63`）。

**判据**：每个时刻取 `nele` **首个欠密→过密向上穿越**（`nele ≤ N_C` → `> N_C` 的第一对相邻格元），
两格元间对 `nele=N_C` 线性插值（`ps_core.py:145-173`）：

```python
sgn = nele2d > N_C
up = ~sgn[:, :-1] & sgn[:, 1:]          # 首个欠密->过密穿越
j = np.flatnonzero(up[i])[0]
a, b = nele2d[i, j], nele2d[i, j + 1]
xc[i] = xg_um[j] + (N_C - a) / (b - a) * (xg_um[j + 1] - xg_um[j])
```

速度 `v_c = d x_c/dt` 用统一差分链（§3.4）。

### 3.2 烧蚀面 x_a(t) 与烧蚀速度 v_a

**判据（不是密度梯度最大处，也不是固定温度阈值面）**：在同时满足
① 过密区 `nele > N_C`；② `60 eV < tele_eV < 600 eV`（温区带，`ABL_LO/ABL_HI`）；
③ `x > x_c + 0.5 µm`（`ABL_XMARGIN`）的格元中，取**电子温度梯度 dT/dx 最小**的格元
（`ps_core.py:70-72, 163-173`）：

```python
gT = np.gradient(tele2d_eV, xg_um, axis=1)
mask = (nele2d > N_C) & (tele2d_eV > ABL_LO) & (tele2d_eV < ABL_HI)
m &= xg_um > xc[i] + ABL_XMARGIN
xa[i] = xg_um[j[np.argmin(gT[i, j])]]    # dT/dx 最小格元
```

有效格元 <3 个时置 NaN。匀滑版 `xa_sm = savgol(medfilt(xa, 9), w, 3)`，`w = min(51, max(7, n//4))` 取奇
（`fronts/fronts_core.py:229-237`）。

**烧蚀速度常数**：`v_a` 取 x_a(t) 全时段（有效点 ≥10）直线拟合斜率
`v_a, x0 = np.polyfit(tg[m], xa[m], 1)`（`ps_core.py:198-205`），同时写 `va.csv`。

### 3.3 冲击波阵面 x_s(t) 与激波速度 v_s

**shok 标志的物理含义**（`source/physics/Hydro/HydroMain/unsplit/hy_uhd_shockDetect.F90:74-170`）：
声速 `c = √(γ_c·p/ρ)`（:114），未除以网格间距的压缩率与压力梯度：

```fortran
beta = 0.5   ! gradP 判据系数
delta= 0.1   ! divV 判据系数
...
divv = 0.5*( U(VELX_VAR,i+1)-U(VELX_VAR,i-1) + U(VELY_VAR,j+1)-U(VELY_VAR,j-1) + ... )  ! 未除 dx
gradPx = 0.5*( U(PRES_VAR,i+1) - U(PRES_VAR,i-1) )   ! 未除 dx
...
if ( abs(gradPx)+abs(gradPy)+abs(gradPz) .ge. beta*minP ) SW1 = .true.
if ( -delta*minC .ge. divv ) SW2 = .true.
if (SW1 .and. SW2) U(SHOK_VAR,i,j,k) = 1.    ! 激波区=1
```
即**"压力梯度超阈 + 流动压缩"双判据**，激波区内 `shok=1`，其余为 0。

**x_s 提取链**（`fronts/fronts_core.py:52-117, 178-214, 280-312`）：
1. 单时刻候选：`shok > 0.5` 格元按索引间隔 >2 切分为连续区域，每区取 **shok 加权质心**；
2. 跨时刻跟踪：每 10 步（CADENCE）降采样后贪心最近邻连接——与轨迹末端距离 ≤ `vmax·dt`
   （`TRACK_VMAX = 200 µm/ns`），断流 ≤3 步可续接，轨迹 ≥8 点才保留；
3. 物理筛选（从多条候选轨迹选真激波）：① v_s 与 v_a 中位数同号；② `|v_s_med| > |v_a_med|`；
   ③ 位置中位数在 x_a 运动方向前方（`median(x−x_a)·va_med > 0`）；④ 初始位置距 x_a ≤ 20 µm
   （`X0_TOL`）；满足者中取点数最多、d0 最小者；
4. 台阶轨迹先 SG(win≈7, poly=3) 预平滑，再 `np.interp` 插回 500 点全网格，v_s 用统一差分链。

### 3.4 统一速度差分链（全库标准）

$$\tilde x = \mathrm{savgol}(\mathrm{medfilt}(x, 9), w, 3),\quad
v = \mathrm{savgol}(\mathrm{medfilt}(\partial\tilde x/\partial t, 9), w, 3),\quad
v[\,3:-3\,]$$

```python
def velocity(t_ns, x_um):
    w = _win(len(t_ns))                       # min(51, max(7, n//4)), 奇
    xs = savgol_filter(medfilt(x_um, 9), w, 3)
    v = np.gradient(xs, t_ns)                 # 中心差分
    v = savgol_filter(medfilt(v, 9), w, 3)
    return v[3:-3]
```
（`phase_slope/ps_core.py:233-246`。输出 µm/ns，两端各截 3 点。
`fronts_core` 的 v_a、v_s；ffab 的 `v_pre/v_post`（求导前/后平滑对照）为例外对照实现。）

### 3.5 拉格朗日层轨迹量化（traj_quant）

- **质心**：`dens_<marker>` 剖面 ≥ max/2 的连续区段做质量加权质心
  `Σ(x·ρ)/Σρ`（1D [t]，cm）（`vch_new_h5.py:118-130`）；
- **采样**：沿质心轨迹取**最近格元**逐时刻采样（`tq_core.py:124-174`）；
- **换算**（`tq_core.py:13-25, 49-53`）：

| 量 | 换算 | 常数 |
|----|------|------|
| 时间 | s→ns ×1e9 | |
| 空间 | cm→µm ×1e4 | CM2UM |
| 温度 tele/tion/trad | K→eV ×(1/11604.518) | K2EV |
| 压力 pres/pele/pion/prad | dyn/cm²→Mbar ×1e-12 | MBAR_PER_DYN |
| 比能 ener/eint/eele/eion/erad | erg/g→eV/ion ×ᾱ·m_p/1.60218e-12 | EV_ERG, MP；ᾱ 按层材料：CH 6.5、Ti 47.867、C 12.011、Si 28.0855 |
| 比动能 | `emom = ½·dens·velx²` [erg/cm³] → eV/ion | 同上 |
| emis/absr | erg·cm⁻³·s⁻¹ 原生不换算 | 低于峰值 1e-8 掩膜为 NaN |

- **层速度**：`u_lag = velocity(t, x_centroid)`；**烧蚀框架速度** `u = u_lag − v_a`
  （v_a 不可用时退化为 u_lag）（`ps_core.py:364-369`）。

### 3.6 相位/阶段划分与温度斜率模型（phase_slope）

五阶段（`ps_core.py:288-312`）：

| 阶段 | 区间 | 定义 |
|------|------|------|
| P1_shock | [t0, t_rev] | u 首次正→负零点（`t_rev`，须其后 0.2 ns 内 u<−20 µm/ns 确认） |
| P2_ablation | [t_rev, t_nc−0.05 ns] | 质心轨迹处 nele 首次向下穿 N_C（`t_nc`，线性插值） |
| P3_cross_nc | t_nc ± 0.05 ns | 跨临界密度 |
| P4_corona | [t_nc+0.05, t_off] | `t_off` = tele 达峰时刻（激光关闭） |
| P5_laser_off | [t_off, t_end] | 激光关闭后 |

**T2 温度斜率模型**（`ps_core.py:316-390`）：
$$\frac{\mathrm{d}(T^{5/2})}{\mathrm{d}t} = K_2\,u - K_2\,a_2$$
其中 T 先换算为速度平方单位：`TCONV = (1+Z)·EV_ERG/(ABAR·m_p)·1e-10 [(µm/ns)²/eV]`
（CH：Z=3.5，ABAR=6.5）；`dT52 = savgol(T_e^{5/2}, win=15, poly=3, deriv=1, delta=dt)`；
逐相位窗口内 `linfit(u, dT52)` 得 K2、a2=−b/K2。

### 3.7 幂律拟合族

| 拟合 | 模型 | 窗口 | 实现 |
|------|------|------|------|
| 烧蚀面 x_a(t) | `x_a = a·t^b`（过原点，ln-ln 线性回归） | [0.4, 1.2] ns | `traj_quant/xa_fit/xa_fit.py:84-93`；候选指数 b=1/2（Marshak 热波）、2/5（Sedov-Taylor）、2/3、3/4、1（匀速）；诊断 `b_eff(t)=v_a(t)·t/x_a(t)` |
| 轨迹场 y(t) | `y = a·(t−t0)^b`（t0 扫描 0→窗起点、步 2 ps，取 ln-SSE 最小） | [0.4, 1.2] ns | `traj_quant/fields_fit_ab/ffab_core.py:279-338`；`scipy.curve_fit` 绝对口径交叉验证 |
| 同时刻密度剖面 | linear / quadratic / exponential `a·e^{bi}` / power `a·i^b` / logarithmic（i=拉格朗日质量深度 1/2/3 µm） | 每时刻 | `traj_quant/dens_fit/dens_fit.py:101-141`；判别指标 relSSE + LOO，统计窗口内最优模型占比 |

### 3.8 能量积分类

- 总内能 `E_int = ∫ρ·eint dx`（面密度，erg/cm²）；
- 比动能场 `emom = ½·ρ·velx²`（erg/cm³）→ 沿轨迹 eV/ion；
- 沉积能量核对：∫ρ·depo dx（PER_MASS 声明）或 ∫depo dx（PER_VOLUME 声明）对照激光注入能量
  （`ed_power` 脉形积分）。

---

## 4. 结合 ionmix eosop（eos.cn4）的派生物理场

> IONMIX 说明见 `flash/input_gen/gen_eos_op/ionmix/ionmix/docs/IONMIX用户指南.md`（下称《指南》）。
> FLASH 表格 EOS（`eos_tab`）直接读取 IONMIX 输出的 `.cn4` 表
> （`source/physics/Eos/EosMain/Tabulated/`、`localAPI/eos_tabIonmix.F90`）；
> LaserSlab `Config` 的 `DATAFILES al-imx-002.cn4 / he-imx-005.cn4 / ...` 即随算例携带的表。
> 用户 EOS 规范（项目固化）：`ntemp=61 / dlgtmp=0.105 / ndens=71 / dlgden=0.14 / densnn=1e16 / trad=200.0`，
> `grupbd` 7 能群，**不同辐射能群不混用于同一 EOS case**。

### 4.1 cn4 数据表结构（《指南》§5.4）

```
头部: ntemp ndens | 原子序数列表 | 相对丰度
 1  ngrups                     1            —
 2  温度数组 T_i               ntemp        eV          升序
 3  数密度数组 n_j             ndens        cm^-3       升序（核子数密度）
 4  zbar        (T,n)          ntemp×ndens  —           平均电荷态
 5  dzbar/dT    (T,n)          ntemp×ndens  eV^-1
 6  P_ion       (T,n)          ntemp×ndens  J/cm^3      n_tot·T·1.602e-19
 7  P_ele       (T,n)          ntemp×ndens  J/cm^3      n_e·T·1.602e-19
 8  dP_ion/dT   (T,n)          ntemp×ndens  J/(cm^3·eV)
 9  dP_ele/dT   (T,n)          ntemp×ndens  J/(cm^3·eV)
10  e_ion       (T,n)          ntemp×ndens  J/g
11  e_ele       (T,n)          ntemp×ndens  J/g
12  cv_ion      (T,n)          ntemp×ndens  J/(g·eV)
13  cv_ele      (T,n)          ntemp×ndens  J/(g·eV)
14  d(E_ion)/dρ (T,n)          ntemp×ndens  J·cm^3/g
15  d(E_ele)/dρ (T,n)          ntemp×ndens  J·cm^3/g
16  能群边界                    ngrups+1     eV
17  Rosseland 群不透明度        ntemp×ndens×ngrups  cm²/g
18  Planck 吸收群不透明度       ntemp×ndens×ngrups  cm²/g
19  Planck 发射群不透明度       ntemp×ndens×ngrups  cm²/g
```

**存储顺序**：二维数组先温度（内循环）后密度（外循环）；三维数组先能群、再温度、最后密度；
格式 `4e12.6`。注意 IONMIX 的密度维是**核子数密度** n_tot [cm⁻³]，
查表前须由 chk 量换算：`n_tot = nion = sumy·ρ·N_A`（§2.1）。

### 4.2 zbar 场：双路径互验

- **路径 A（chk 内生）**：`zbar = ye/sumy`（§2.2），即 FLASH eos_tab 运行时实际使用的值；
- **路径 B（表侧独立）**：以 `(T_e[eV]→表温轴, nion→表密度轴)` 双线性/log 插值 cn4 的 zbar 块，
  得到与 chk 无关的独立估计。

两路径偏差应 ≈0（同一张表）；若显著偏差，说明该格元温度/密度**越出表覆盖范围**
（FLASH 对越界做截断/外推，属常见静默失配点）。附加诊断：`dzbar/dT` 大值区即电离锋面，
其位置可与烧蚀面 x_a 对照（电离波 vs 热波）。

### 4.3 不透明度场与辐射输运派生量

对每个能群 g（grupbd=7）：

| 派生量 | 公式 | 单位 | 用途 |
|--------|------|------|------|
| 群不透明度场 | `κ_g = interp_cn4(T_e 或 T_r, nion)[Rosseland/PlanckA/PlanckE, g]` | cm²/g | 逐格元 |
| 质量吸收系数 | `κ_g·ρ` | cm⁻¹ | 与 MGD 内部 ρκ 一致 |
| 辐射平均自由程 | `λ_g = 1/(κ_g·ρ)` | cm | Rosseland 版用于扩散区 |
| 群光学厚度 | `τ_g(x₁→x₂) = ∫ κ_g ρ dx` | 1 | τ≪1 光学薄 / τ≫1 光学厚 |
| 光深加权发射 | `η_g = κ_g^E·ρ·B_g(T_r)` | erg·cm⁻³·s⁻¹ | 与 chk `emis` 对照 |

查表温度轴选择：**输运吸收用 T_r（与 MGD Planck 权重一致），发射用 T_e（non-LTE）**；
`emis/absr`（chk）是全群积分量，可与 Σ_g 结果对照。
`κ^E/κ^A ≠ 1` 指示 non-LTE（《指南》§9 Q8，implot07 同款判据）。

### 4.4 压力/能量分量校验与热力学分解

| 校验 | 公式 | 说明 |
|------|------|------|
| 电子分压 | `pele(chk) ↔ P_ele(表)`（J/cm³→dyne/cm² ×1e7） | 表侧为理想式 `n_e·T·k_B`，non-LTE 下 n_e 由 IONMIX 自洽电离给出 |
| 离子分压 | `pion(chk) ↔ P_ion(表)` | |
| 电子比内能 | `eele(chk) ↔ e_ele(表)`（J/g→erg/g ×1e7） | 表值含电离能储项，故 eele ≠ (3/2)p_e/ρ 是**正常的**（差值=电离能） |
| 电子热容 | `cv_ele(表)` | 电离阈值处峰值 = 电离潜热，用于解释 tele 平台 |
| dE/dρ | 表 14/15 块 | Gruneisen 类诊断 |

电离能储量的场估计：`E_ioniz(x) ≈ e_ele(x) − (3/2)·p_e(x)/ρ`（erg/g），
可定量给出"激光能量中多少变成电离而非热"。

### 4.5 冷却率与电离物理量

- **等离子体冷却率**（《指南》§2.5.5）：
  $$\Lambda(T) = \frac{4\sigma_{SB}\,\rho\,T^4}{n_e\,n_{tot}}\,\sigma_P^E \quad [\mathrm{erg\cdot cm^3/s}]$$
  由 cn4 的 Planck 发射不透明度 + chk 的 (ρ, n_e, n_tot, T_e) 组合得到辐射冷却时间
  `τ_cool = e_ele / (n_e·n_tot·Λ)`（结合 §4.4），与热传导/流体时标比较可判能量输运主导机制。
- **电离松弛时标**：`τ_ion ≈ |∂Z/∂T|⁻¹ · |∂T/∂t|⁻¹ · ΔZ`——用表 5 块 dzbar/dT 与 chk 时空场
  ∂T_e/∂t 估计电离波扫过一层所需时间，判断电离是否始终跟随热波（LTE 近似自洽性）。

### 4.6 等离子体微观参数（chk + 表联合）

以下为结合 `n_e`（§2.1）、`tele`（K→eV）、`zbar`（§4.2）的教科书派生量（Spitzer 类），
单位均为 CGS：

| 量 | 公式 | 用途 |
|----|------|------|
| 库仑对数 | lnΛ = 23.5 − ln(n_e^{1/2} T_e^{−5/4}) − 10.3·Z^{1/2}/T_e^{5/4}（eV, cm⁻³） | Spitzer 输运系数入口 |
| Debye 长度 | λ_D = √(k_B T_e / 4π n_e e²) | 准中性判据 |
| 电子-离子碰撞频率 | ν_ei ≈ 2.91e−6 · n_e[cm⁻³]·Z·lnΛ / T_e[eV]^{3/2} | 耦合/阻尼时标 |
| 电子热传导系数 | κ_SP ∝ T_e^{5/2}/Z·lnΛ（与 chk 场 `cond`（若存在）对照） | SNB 局域 vs FLASH 内建对照 |

> SNB（非局域）场景下 `cond` 字段为 Spitzer 局域基准，非局域修正由 SNB 模块内部处理，
> chk 中另有 SNB 诊断场（依场景 Config 而定）。

---

## 5. 单位换算与常见陷阱总表

### 5.1 换算速查

| 量 | FLASH（chk） | 常用 | 换算 |
|----|-------------|------|------|
| 长度 | cm | µm | ×1e4 |
| 时间 | s | ns | ×1e9 |
| 密度 | g/cm³ | g/cm³ | —（SI ×1e3） |
| 速度 | cm/s | µm/ns | ×1e4×1e-9=×1e-5 |
| 压力 | dyne/cm² | Mbar | ×1e-12 |
| 温度 | **K** | eV | ÷11604.518 |
| 比能 | erg/g | eV/ion | ×ᾱ·m_p/1.60218e-12 |
| 能量密度 | erg/cm³ | J/m³ | ×0.1 |
| 数密度 | cm⁻³ | cm⁻³ | —（SI ×1e6） |
| 临界密度 | n_c = 1.1155e21/λ_µm² | cm⁻³ | λ=0.351 µm → 9.05e21 |

### 5.2 陷阱清单（历史事故沉淀）

1. **温度单位**：chk 温度为 K；K/eV 混淆 → Te 差 1000×（`K_BOLTZ_EV_PER_K` 曾错写）。
2. **能量积分漏 ρ**：`∫ρ·eint dx`，漏乘虚报超支。
3. **父块数据不可用**：只读 `node type==1` 叶块；AMR 边界重叠需按坐标去重。
4. **depo/lase 单位随声明变**：depo 默认 PER_MASS（erg/g）、lase PER_VOLUME（erg/cm³），
   积分公式相应不同（§3.8）。
5. **ionmix 密度维是核子数密度** n_tot，不是 ρ 也不是 n_e；查表用 `nion`。
6. **erad 双约定**：multiTemp Config 声明 PER_MASS（EINT3），MGD 能量密度为 a_r·T_r⁴（per-volume），
   对照脚本时先确认场景口径。
7. **`+ug` 域偏移**：chk 首格 `x = par_xmin + (nxb/2)·dx`，层位校验用实测坐标。
8. **变量存在性**：以 chk `unknown names` 为准；`DATA_CONFIG` 是超集注册表。
9. **运行时参数名全小写 + 哨兵默认值**：chk 参数名一律小写（源码大小写不保留，§1.7）；
   激光 `ed_time_*/ed_power_*` 未设置时为 **−1.0**（哨兵，非 0.0），判"是否启用"用 `> 0`。
10. **`+ug` 无 AMR 参数**：chk 中查不到 `lrefine_*`/`refine_var_*` 属正常（仅 AMR 运行注册）；
    dx 由 `dx=(xmax−xmin)/(nxb·nblockx)` 计算（§1.7）。

---

## 6. 附录

### 6.1 变量速查索引

| 变量 | 类别 | 单位(K=K) | 源码声明 | 派生入口 |
|------|------|-----------|----------|----------|
| dens | raw | g/cm³ | unsplit/Config:59 | dens_targ 等分密度 |
| velx/vely/velz | raw | cm/s | unsplit/Config:60-62 | emom=½ρu² |
| pres | raw | dyne/cm² | unsplit/Config:63 | 与 Σp_k 校验 |
| ener/eint | raw | erg/g | unsplit/Config:64,68 | ∫ρe dx |
| gamc/game | raw | 1 | unsplit/Config:65-66 | c_s=√(γp/ρ)（声速族 §2.8） |
| temp | raw | K | unsplit/Config:67 | |
| shok | raw | 0/1 | unsplit/Config:69 + hy_uhd_shockDetect.F90 | x_s 提取（§3.3） |
| tele/tion/trad | raw | K | unsplit/multiTemp/Config:8-10 | ls_tele、x_a、T2 模型 |
| pele/pion/prad | raw | dyne/cm² | 同上:4-6 | 表侧校验（§4.4） |
| eele/eion/erad | raw | erg/g | 同上:18-20 | 电离能分解（§4.4） |
| ye/sumy | raw | mol/g | Eos_putData.F90:278-286 | nele/nion/zbar/abar |
| targ/cham/shld/samp(/tar1..6) | raw | 质量分数 | setup species 机制 | dens_<marker>、层质心 |
| lase | raw | erg/cm³ | LaserSlab/Config:89 | 激光场诊断 |
| depo | raw | erg/g（默认） | ED Laser/Config:23 | 沉积能量积分 |
| absr/emis | raw | erg·cm⁻³·s⁻¹ | RadTrans MGD/Config:13,17 | 辐射冷却（§4.5） |
| mgdc | raw | cm²/s | RadTrans MGD/Config:20 | 扩散系数诊断 |
| time/dt/nstep/nxb… | scalar | s / — | chk 头部（§1.6） | 时间轴 |
| nele/nion | derived | cm⁻³ | output_processors DATA_CONFIG | §2.1 |
| zbar/abar | derived | 1 | = ye/sumy（Eos_getData.F90 同式） | §2.2 / §4.2 |
| dens_targ/cham/shld/samp | derived | g/cm³ | DATA_CONFIG formula | §2.3 |
| ls_nele/ls_tele | derived | cm | DATA_CONFIG + _gradient_1d | §2.5 |
| x_c / x_a / x_s 及速度 | 场派生 | µm, µm/ns | CASES_Comp fronts/ps_core | §3.1-3.4 |
| κ_g、λ_g、τ_g、Λ | 表联合 | cm²/g, cm, —, erg·cm³/s | ionmix cn4 + chk 场 | §4.3-4.5 |
| tite/pipe | raw | — / 1 | Eos multiTemp/Config:52-53 | 平衡诊断（§1.2） |
| cond/fllm/dfcf | raw（热传导场景） | — | DiffuseMain(/Unsplit)/Config | 热传导/限流诊断 |
| qesh…corq、mfpe/mfpr、r001–r010 | raw（SNB 专属） | 混合 | 场景私有 SNB Config:38-55 | 非局域热通量诊断 |
| c_s 族（cs/cs_e/cs_i/cs_id/cs_ia/cs_mix） | derived | µm/ns | §2.8 公式 | 声速族 |
| runtime parameters ×4 + `sim info` | 头部数据集 | — | §1.7 | 参数速查表 |

### 6.2 参考资料

1. FLASH 4.8 User Guide：`flash/flash_src/docs/flash4_ug_4p8.pdf`
2. 方程-源码映射：`flash/flash_src/docs/src_finding/`（hy_uhd_unsplitUpdate / RadTrans /
   EnergyDeposition / ThermalConduction 各 1 份）
3. `output_processors/`：`hdf5processor/flash_hdf5.py`（DATA_CONFIG、extract_var_yt_style）、
   `loader/data_loader.py`（FlashDataLoader、laser_groups）、`extraction_modes.py`
4. CASES_Comp 前沿与轨迹算法：`fronts/fronts_core.py`、`fronts/extract_shok.py`、
   `phase_slope/ps_core.py`、`traj_quant/tq_core.py`、`traj_quant/{xa_fit,dens_fit,fields_fit_ab}/`
5. 《IONMIX用户指南》v2.1：`flash/input_gen/gen_eos_op/ionmix/ionmix/docs/`
   （MacFarlane, CPC 56 (1989) 259–278）
6. Multispecies 机制：`source/physics/multispecies/`（物种 A/Z/abundance 属性）
7. 运行时参数详解与生成：`flash/input_gen/gen_newpara/RP_Reference.md`（含 chk 实测对照）、
   `flash/input_gen/gen_par/GEN_PAR_GUIDE.md`（par 模板结构与生成器）
8. 表格 EOS 的 γ_c 合成：`source/physics/Eos/EosMain/Tabulated/eos_tabIonmix4.F90`（:585-598）
9. 激波判据中的声速：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_shockDetect.F90`（:74-170）
