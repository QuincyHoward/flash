# 超算仿真交付清单（2026-10-18，ms_shld 修正后重算）

远程账号 `flash_ssh` = scfa2696@NC-E（分区 `v5_192`，7 核/作业）
统一参数：`tmax = 1.6e-9 s`，1D Cartesian AMR，激光 5e14 W/cm²

---

## 1. 已完成仿真一览（8 条）

| # | 场景名 | JobID | 屏蔽层 | Ti 示踪层 | 辐射 | 墙钟 | 末态 t |
|---|---|---|---|---|---|---|---|
| 1 | TiTi1 | 4908604 | Ti (4.54 g/cm³, A=47.867, Z=22) | tar1 @1 µm | 开 | 02:34:52 | 1.6001 ns |
| 2 | TiTi2 | 4908608 | 同上 | tar2 @2 µm | 开 | 02:31:52 | 1.6000 ns |
| 3 | TiTi3 | 4908611 | 同上 | tar3 @3 µm | 开 | 02:31:28 | 1.6000 ns |
| 4 | VCH_ml | 4908614 | V (6.11 g/cm³, A=50.9415, Z=23) | 多层 VCH/CH（无单层示踪） | 开 | 02:31:02 | 1.6001 ns |
| 5 | VCH_ml_F | 4908619 | 同上 | 同上 | **关 (RADIATION_OFF)** | 01:13:51 | 1.6000 ns |
| 6 | VTi1 | 4908405 | V (6.11, 50.9415, 23) | tar1 @1 µm | 开 | 02:51:29 | 1.6000 ns |
| 7 | VTi2 | 4908407 | 同上 | tar2 @2 µm | 开 | 02:33:47 | 1.6001 ns |
| 8 | VTi3 | 4908409 | 同上 | tar3 @3 µm | 开 | 02:34:39 | 1.6000 ns |

全部 `COMPLETED`、`ExitCode=0`、无 `.part` 残留。

---

## 2. 本地存放位置（Windows）

工作根：`E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\`

### 2.1 输出（HDF5 帧 + 运行日志）

| 场景 | 本地路径 | 文件数 | plt / chk | 体积 |
|---|---|---|---|---|
| TiTi1 | `TiTi\flash_output\hpc\TiTi1\` | 390 | 66 / 323 | 585 MB |
| TiTi2 | `TiTi\flash_output\hpc\TiTi2\` | 387 | 65 / 321 | 585 MB |
| TiTi3 | `TiTi\flash_output\hpc\TiTi3\` | 383 | 65 / 317 | 566 MB |
| VCH_ml | `VCH_ml\flash_output\hpc\VCH_ml\` | 377 | 64 / 312 | 550 MB |
| VCH_ml_F | `VCH_ml_F\flash_output\hpc\VCH_ml_F\` | 380 | 64 / 315 | 566 MB |
| VTi1 | `VTi\flash_output\hpc\VTi1\` | 421 | 71 / 349 | 635 MB |
| VTi2 | `VTi\flash_output\hpc\VTi2\` | 378 | 64 / 313 | 587 MB |
| VTi3 | `VTi\flash_output\hpc\VTi3\` | 381 | 64 / 316 | 570 MB |

合计 **约 4.6 GB**。帧命名 `lasslab_hdf5_plt_cnt_NNNN`（绘图帧，2000 步/帧）
与 `lasslab_hdf5_chk_NNNN`（检查点，400 步/帧），另有 1 个 `*forced*` 首帧。

### 2.2 实际提交的输入（从超算回取的正本）

| 场景 | 本地路径 | 关键文件 |
|---|---|---|
| TiTi1/2/3 | `TiTi\hpc_inputs\TiTi1|2|3\` | `laserslab_titi{1,2,3}.par`、`Config`、`Makefile`、4 张 cn4 |
| VCH_ml | `VCH_ml\hpc_inputs\VCH_ml\` | `laserslab_vchml.par` |
| VCH_ml_F | `VCH_ml_F\hpc_inputs\VCH_ml_F\` | `laserslab_vch_ml_f.par` |
| VTi1/2/3 | `VTi\hpc_inputs\VTi1|2|3\` | `laserslab_vti{1,2,3}.par` |

每套均含 `MANIFEST.txt`（远端路径 + 该场景真正使用的 par 名）。

### 2.3 场景脚本（可重新生成输入）

| 场景 | 脚本 |
|---|---|
| TiTi1/2/3 | `TiTi\TiTi1.py` `TiTi2.py` `TiTi3.py`（派生器 `build_titi_family.py`） |
| VCH_ml | `VCH_ml\VCH_ml.py` |
| VCH_ml_F | `VCH_ml_F\VCH_ml_F.py` |
| VTi1/2/3 | `VTi\VTi1.py` `VTi2.py` `VTi3.py`（派生器 `build_vti_family.py`） |

### 2.4 工具与分析产物

| 文件 | 用途 |
|---|---|
| `VTi\scripts\hpc_fetch.py` | 跨场景并行增量下载器（8 线程） |
| `VTi\scripts\hpc_watch.py` | 作业状态轮询守护 |
| `fetch_hpc_inputs.py` | 回取远端实际提交的输入 |
| `audit_material_bindings.py` | 逐物种 (ρ,A,Z,EOS表,op表) 五元组审计 |
| `submit_msfix_all.py` | 并行上传 + 提交 |
| `msfix_download_20261018.csv` | 下载完整性汇总表 |
| `msfix_audit_20261018.csv` | 全族 ms_shld 缺陷审计表 |
| `VTi\scripts\compare_traj.py` | Ti 层轨迹/速度对照（VTi vs TiTi） |

---

## 3. 超算端位置

上传根：`~/QC/FLASH/FLASH4.8/AI/Aitemp/<场景>_<时间戳>/`
运行 objdir：`~/QC/FLASH/FLASH4.8/QC/LaserSlab_<objname>/`
完成后帧被 `mv` 到：`<上传根>/outputfiles_<时间戳>/`

| 场景 | 上传根（远端） | objdir 名 |
|---|---|---|
| TiTi1 | `Aitemp/TiTi1_20261018_152253` | `LaserSlab_TiTi1` |
| TiTi2 | `Aitemp/TiTi2_20261018_152325` | `LaserSlab_TiTi2` |
| TiTi3 | `Aitemp/TiTi3_20261018_152358` | `LaserSlab_TiTi3` |
| VCH_ml | `Aitemp/VCH_ml_20261018_152252` | `LaserSlab_VCHml`（无下划线） |
| VCH_ml_F | `Aitemp/VCH_ml_F_20261018_152253` | `LaserSlab_VCH_ml_F` |
| VTi1 | `Aitemp/VTi1_20261018_110238` | `LaserSlab_VTi1` |
| VTi2 | `Aitemp/VTi2_20261018_110440` | `LaserSlab_VTi2` |
| VTi3 | `Aitemp/VTi3_20261018_110542` | `LaserSlab_VTi3` |

---

## 4. 修正生效的物理验收

`chk_0000` 屏蔽层纯胞（13 胞/场景）实测：

| 族 | dens | pres (dyn/cm²) | 判定 |
|---|---|---|---|
| V 族（VCH_ml / VCH_ml_F / VTi1–3） | 6.110 | 3.9263e11 | 与目标 3.93e11 吻合 ✓ |
| Ti 族（TiTi1–3） | 4.540 | 1.2545e11 | 旧配置（A=6.509）应为 ≈9.2e11，即约 7× 过压已消除 ✓ |

par 实参：V 族 `ms_shldA/Z = 50.9415/23`，Ti 族 `47.867/22`，
`eos_/op_shldTableFile` 与材质一致。
