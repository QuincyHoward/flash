# 超算 LaserSlab 一维仿真测试报告

- **测试日期**: 2026-08-03 07:48 ~ 07:53 (GMT+8)
- **超算账户**: flash_ssh → ParaCloud NC-E (`ssh.cn-zhongwei-1-v6.paracloud.com:2222`)
- **超算配置**: ln162.para.bscc, 24 核 / 62GB RAM, Intel oneAPI 2022.1
- **凭据**: 从 `_core/credentials/_core.py` 加载（用户: `scfa2696@NC-E`）
- **场景**: LaserSlab 1D (官方示例, Al/CH/He 三层靶)

---

## 一、测试结果总览

| 阶段 | 结果 | 耗时 |
|------|------|------|
| SSH 连接 + 凭据认证 | ✅ 成功 | <2s |
| 编译 flash4 (LaserSlab 1D, ifort 2021.5) | ✅ 成功 (12.9MB) | ~30s |
| 运行仿真 (mpirun -np 4) | ✅ 成功, 41 chk + 81 plt | ~20s |
| 下载 HDF5 到本地 | ✅ 成功 (6 chk, 1.7MB tar.gz) | <5s |
| 密度分析绘图 | ✅ 成功 (3 张 PNG) | <1s |

---

## 二、超算环境

| 项 | 值 |
|---|---|
| 主机名 | ln162.para.bscc |
| 操作系统 | Linux (NC-E 超算节点) |
| CPU | 24 核 |
| 内存 | 62 GB |
| MPI | `/public1/soft/oneAPI/2022.1/mpi/latest/bin/mpif90` (Intel MPI) |
| Fortran | **ifort 2021.5.0** (切换后) / 原 gfortran 4.8.5 (太老, 编译崩溃) |
| C | gcc 4.8.5 |
| FLASH 安装 | `~/hello/FLASH/FLASH4.8/` |
| MPICH | `/public1/soft/mpich/3.2` |
| HDF5 | `/public1/soft/hdf5/1.8.18` |
| HYPRE | `~/hello/FLASH/local/hypre/libHYPRE.a` (静态库, gcc 编译) |

---

## 三、关键问题与修复

### 问题 1: gfortran 4.8.5 编译崩溃 (Segmentation fault)

**现象**:
```
f951: internal compiler error: Segmentation fault
make: *** [gr_uhypreParamesh.o] Error 1
```

**根因**: 超算默认 MPI (`mpif90`) 包装的 Fortran 编译器是 **gfortran 4.8.5** (Red Hat 2015 版)。
FLASH 4.8 的 `gr_uhypreParamesh.F90` 包含现代 Fortran 特性 (假定类型, ALLOCATABLE 等),
gfortran 4.8.5 内部编译器崩溃 (ICEs)。

**修复**: 切换到 Intel oneAPI 的 `mpiifort` (包装 ifort 2021.5.0):

```diff
- FCOMP = /public1/soft/mpich/3.2/bin/mpif90          (gfortran 4.8.5)
+ FCOMP = /public1/soft/oneAPI/2022.1/mpi/latest/bin/mpiifort  (ifort 2021.5.0)
- CCOMP = /public1/soft/mpich/3.2/bin/mpicc
+ CCOMP = /public1/soft/oneAPI/2022.1/mpi/latest/bin/mpicc
- CPP = /public1/soft/mpich/3.2/bin/mpicxx
+ CPP = /public1/soft/oneAPI/2022.1/mpi/latest/bin/mpicxx
- LINK = /public1/soft/mpich/3.2/bin/mpif90
+ LINK = /public1/soft/oneAPI/2022.1/mpi/latest/bin/mpiifort
- FFLAGS: -fdefault-real-8 -fdefault-double-8 (gfortran)
+ FFLAGS: -r8 (ifort equivalent)
```

**结果**: ifort 编译成功, `flash4` (12.9MB) 生成 (含 2 个无关警告 `-W` 忽略)。

> 原 Makefile.h 已备份为 `Makefile.h.gfortran.bak`。

---

## 四、仿真结果

### 4.1 仿真参数 (LaserSlab 官方 example1d.par)

- **域**: `x ∈ [125, 15968.75] μm` (1496.875e-4 cm 域宽)
- **网格**: 4 块 → AMR 加密至 **36 块** (20 leaf blocks)
- **物理**: Al 靶 (t=0.1ps 2.7g/cm³) + CH 泡沫 + He 真空
- **时步**: 790 → reached max SimTime = 1.0 ns

### 4.2 HDF5 输出

| 类型 | 数量 | 范围 |
|------|------|------|
| checkpoint (`lasslab_hdf5_chk_*`) | **41** | 0000 ~ 0040 |
| plot file (`lasslab_hdf5_plt_cnt_*`) | **80** | 0000 ~ 0079 |
| final forced plot | 1 | forced_hdf5_plt_cnt_0000 |

### 4.3 下载到本地的样本 (用于绘图)

| chk | 时间 (ps) | dens 范围 (g/cm³) | 网格单元 |
|------|----------|-------------------|----------|
| 0001 | 0.057 | [1e-6, 2.70] | 160 |
| 0005 | 137.8 | [1e-6, 2.70] | 160 |
| 0010 | 391.5 | [1e-6, 3.11] | 192 |
| 0020 | 604.9 | [1e-6, 3.58] | 240 |
| 0030 | 805.9 | [1e-6, 4.31] | 272 |
| 0039 | 990.2 | [1e-6, 4.21] | 272 |

---

## 五、分析绘图

基于下载的 6 个 checkpoint, 生成 3 张分析图 (`outputfiles/plotsfrom_ssh1/`):

1. **`density_vs_x_evolution.png`** (260KB) — 全部时间步 dens vs x 曲线 (viridis 色带)
2. **`density_heatmap_and_stats.png`** (90KB) — x-t 密度谱 + max/mean(dens) 时间统计
3. **`density_snapshots.png`** (80KB) — 首/中/末时间步密度对比快照

### 关键物理结论

| 指标 | 值 |
|------|-----|
| 时间跨度 | 0.057 ~ 990.164 ps (~1 ns) |
| max(dens) 变化 | 2.70 → 4.21 g/cm³ (↑56%) |
| mean(dens) 变化 | 0.82 → 0.50 g/cm³ (↓39%) |
| 物理过程 | **压缩波从右边界 (x≈16000 μm) 向左传播**, 物质被压缩到前沿 |

---

## 六、流程产物清单

### 新增脚本

| 文件 | 用途 |
|------|------|
| `scripts/02_hpc/hpc_laserslab_test.py` | 一键编译 + 运行 + 报告 |
| `scripts/02_hpc/hpc_run_laserslab.sh` | 上传到超算的运行脚本 |
| `scripts/02_hpc/hpc_run_uploader.py` | 脚本上传 + 执行器 |
| `scripts/02_hpc/hpc_download_results.py` | SFTP 打包下载 HDF5 |

### 远程改动

- 超算 `~/hello/FLASH/FLASH4.8/Makefile.h` 切换至 ifort (`Makefile.h.gfortran.bak` 已备份)

### 输出文件

| 路径 | 内容 |
|------|------|
| `scenarios/flash_demo/hello_flash/outputfiles/hdf5filesfrom_ssh1/laserslab1d/` | 6 个 chk (本地副本) |
| `scenarios/flash_demo/hello_flash/outputfiles/plotsfrom_ssh1/` | 3 张密度分析图 |
| 超算 `~/hello/FLASH/run_laserslab_hpc_test/` | 完整仿真产物 (41 chk + 81 plt) |

---

## 七、复现方式

```bash
# 1. 编译 + 运行 (ifort)
python scripts/02_hpc/hpc_laserslab_test.py
# 或分步:
python scripts/02_hpc/hpc_run_uploader.py    # 需先确保 ifort 配置

# 2. 下载结果
python scripts/02_hpc/hpc_download_results.py

# 3. 绘图分析
cd scenarios/flash_demo/hello_flash
FLASH_SOURCE_SUFFIX=from_ssh1 python analyze_density.py
```

---

## 八、经验与建议

1. **超算 nc-e 默认编译器太老**: `gfortran 4.8.5` 无法编译 FLASH 4.8, 必须切换到 ifort (oneAPI 2022.1)。
2. **静态库无 ABI 问题**: HYPRE 是 gcc 编译的 C 静态库, 链接时用 ifort 不受影响。
3. **Intel MPI + ifort 组合 (`mpiifort`)**: 超算性能最佳的 FLASH 编译路径。
4. **下载策略**: 6 个代表性 chk (打压缩包) 比下载全部 41 个更高效 (1.7MB vs ~12MB)。

---

*报告生成: 2026-08-03 07:55 GMT+8*