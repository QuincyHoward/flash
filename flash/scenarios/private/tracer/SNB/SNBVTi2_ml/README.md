# SNBVTi — VCH + Ti 多层示踪靶 + SNB 非局域热传导

**一句话**：仿照 `TiTi` 家族的结构与材料布局，把 `shld` 屏蔽层的 **Ti 换成 V（钒）**，
`tar2` 保留 **Ti 示踪层**，其余 `tar*` 全部用 **CH** 表示，热传导改用 **SNB 模型**；
只做 **2.0 µm** 一种示踪深度。

---

## 1. 三个场景的对照关系

| 场景 | 热传导 | shld | tar2 | 定位 |
|---|---|---|---|---|
| `SNBOneCH_ml` | SNB | CH (1.0) | CH (1.0) | 纯 CH 基线 |
| **`SNBVTi`** | **SNB** | **V (6.11)** | **Ti (4.54)** | **本场景：V 屏蔽 + Ti 示踪** |
| `TiTi2` | SH（标准） | Ti (4.54) | Ti (4.54) | 非 SNB 对照 |

⇒ 与 `SNBOneCH_ml` 的**唯一物理差异**：`shld` CH→V、`tar2` CH→Ti；
与 `TiTi2` 的**唯一物理差异**：`shld` Ti→V、热传导 SH→SNB。

## 2. 分层拓扑（8 物种 / 12 区）

域 `x ∈ [-0.04, 0.01] cm`（= [-400, 100] µm），`delta = 0.1 µm`，`D = 50 µm`。

| 区 | 范围 | 物种 | 材料 | ρ [g/cm³] |
|---|---|---|---|---|
| — | `x < 0` | `cham` | He | 1e-6 |
| 1 | `0 … delta` | **`shld`** | **V** | **6.11** |
| 2 | `delta … L1` | `samp` | CH | 1.0 |
| 3 | `L1 … L1+delta` | `tar1` | CH | 1.0 |
| 4 | `L1+delta … L2` | `samp` | CH | 1.0 |
| 5 | `L2 … L2+delta` | **`tar2`** | **Ti** | **4.54** |
| 6 | `L2+delta … L3` | `samp` | CH | 1.0 |
| 7 | `L3 … L3+delta` | `tar3` | CH | 1.0 |
| 8 | `L3+delta … L4` | `samp` | CH | 1.0 |
| 9 | `L4 … L4+delta` | `tar4` | CH | 1.0 |
| 10 | `L4+delta … L6` | `samp` | CH | 1.0 |
| 11 | `L6 … L6+delta` | `tar6` | CH | 1.0 |
| 12 | `L6+delta … L6+delta+D` | `samp` | CH | 1.0 |

`L1/L2/L3/L4/L6 = 1/2/3/4/6 µm`。
> **机制**：`Simulation_initBlock.F90` 用 `sim_shldRadius` 作为**所有** `tar*` 薄层的
> 公共厚度（`bnd4 = sim_tar1Radius + sim_shldRadius` 等），故 6 个标记层等厚。

## 3. 关键运行参数（对齐 `t001` / `SNBOneCH_ml` 已验证基线）

| 参数 | 值 | 说明 |
|---|---|---|
| `diff_eleFlMode` | `fl_harmonic` | 电子限流模式 |
| `diff_eleFlCoef` | `0.06` | |
| `rt_mgdFlMode` / `rt_mgdFlCoef` | `fl_harmonic` / `1.0` | MGD 辐射通量 |
| **`gr_hypreUseFloor`** | **`.false.`** | ★★★ **SNB 铁律**，缺失即崩塌 |
| `RiemannSolver` | `HLL` | 强稀疏下不产生负内能 |
| `cfl` / `tstep_change_factor` / `dtmax` | `0.2` / `1.10` / `2.0e-12` | |
| `nxb` / `iprocs` | `128` / `131` | ★ `+ug` 下 `nproc` 必须 == `iprocs` |
| `tmax`（验证默认） | `1.0e-11` s | 极短验证值；正式运行用 `--tmax` |

**网格铁律**：`dx = 域宽/(iprocs·nxb) = 0.02982 µm ≤ 0.03 µm`，
0.1 µm 薄层覆盖 **3.35** 个单元中心（≥ 3）。

## 4. 用法

```bash
cd <flash 包目录>

# ① 只生成输入文件 + 静态自检（不连超算）
python flash/scenarios/private/tracer/SNB/SNBVTi/SNBVTi.py --generate-only

# ② 超算 NC-E 极短验证（首次必须完整编译，勿加 --skip-build）
python flash/scenarios/private/tracer/SNB/SNBVTi/SNBVTi.py \
    --tmax 1.0e-11 --nproc 131 --account flash_ssh

# ③ 同场景二次运行（复用已编译 flash4）
python flash/scenarios/private/tracer/SNB/SNBVTi/SNBVTi.py \
    --tmax 1.0e-11 --nproc 131 --account flash_ssh --skip-build

# ④ 指定出图目录
python flash/scenarios/private/tracer/SNB/SNBVTi/SNBVTi.py \
    --tmax 1.0e-11 --account flash_ssh --skip-build \
    --plots-dir flash/scenarios/private/tracer/SNB/SNBVTi/plots
```

## 5. 2026-09-13 NC-E 验证结果（已通过）

| 项 | 结果 |
|---|---|
| 构建作业 | JobID **4864839**，COMPLETED（45 s） |
| 运行作业 | JobID **4864841**，COMPLETED，**`RUN_EXIT=0`** |
| 墙钟 | **32.97 s** |
| 终态 | `time = 1.0014e-11 s` ≥ `tmax`，`nstep = 87`，`dt = 1.5568e-13 s` |
| 网格 | `iprocs = 131` == nproc，`nxb = 128` |
| 闸门 | `gr_hypreUseFloor = .false.` 运行前校验通过 |
| 物种 | 8 个全部 nonzero（16768 = 131×128 格） |
| 面积分 | `shld` **14.6**（V 最重）> `tar2` **5.15**（Ti）> `tar1/3/4/6` **3.0**（CH 等厚） |
| 产物 | `snbvtiug_hdf5_chk_0000/0001`、`snbvtiug_hdf5_plt_cnt_0000`、`LaserEnergyProfile.dat` |

出图见 `plots/`：`snbvti_dens_profiles.png`、`snbvti_species_zoom.png`（另附初始预诊断图
`flash_input/pre_diag_*.png`）。

## 6. 材料表（IONMIX4 cn4，已按权威读法核验）

| 文件 | Z | 用于 |
|---|---|---|
| `V-BADGER-TOPS.cn4` | **23** (V) | `shld` |
| `Ti-BADGER-TOPS.cn4` | **22** (Ti) | `tar2` |
| `CH-QC-1-001.cn4` | **6,1** (C:H) | `samp` + `tar1/3/4/6` |
| `He-BADGER-TOPS-Final.cn4` | **2** (He) | `cham` |

> ⚠ **不要用 `CH-BADGER-TOPS-Final.cn4`** —— 文件名与内容不符，
> 其实际组成为 **Z=3**（非 C:H），IONMIX4 读取器会拒绝加载。

## 7. 前置条件

**必须在 FLASHSNB（SNB 专用 FLASH）中编译运行**。SNB 物理由 9 个覆盖 F90 承载
（`diff_advanceTherm.F90` / `mgd_qesh.F90` / `Conductivity.F90` /
`Driver_evolveFlash.F90` / `Grid_advanceDiffusion.F90` /
`hy_uhd_DataReconstructNormalDir_PPM.F90` / `hy_uhd_dataReconstOneStep.F90` /
`hy_uhd_getRiemannState.F90` / `hy_uhd_ragelike.F90`），
部署时从远端 `SNB_1D_laser` 参考单元原样复制（**License §3：不入库**）。

**默认超算 = NC-E**（`--account flash_ssh`，用户 `scfa2696`）。

## 8. 文档

- `docs/01_场景说明与拓扑.md` — 几何/物种/材料逐项说明与设计依据
- `docs/02_超算验证流程.md` — NC-E 端到端流程、委托复用机制与踩坑
- `../SNB/SNB/docs/05_坑位清单.md` — **P25**：委托复用的两类隐藏依赖（必读）

## 9. 目录结构

```
SNBVTi/
├── SNBVTi.py              场景主脚本（生成 / 自检 / 委托 HPC / 出图）
├── README.md              本文件
├── docs/                  说明与流程文档
├── flash_input/           生成物（par / Config / F90 / cn4 / 预诊断图）
├── flash_output/hpc_flash_ssh/   超算回传结果
└── plots/                 验证图像
```

> 本地保留 `flash_input/`、`plots/`、`flash_output/` 供人工核查；
> `*.cn4`、`snbvtiug_*`、`_*.sh`、`*.out` 等运行产物不入库。
