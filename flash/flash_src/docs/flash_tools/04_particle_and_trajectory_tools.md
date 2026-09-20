# FLASH 粒子与轨迹工具

## 概述

FLASH 提供两套粒子数据处理工具：
1. **particleTools/** — 粒子排序、读取、写入和可视化
2. **trajectoryFile/** — 粒子轨迹聚合与切片

---

## 1. particleTools — 粒子数据处理

### 目录结构

```
particleTools/
├── Makefile                  # 构建配置
├── README                    # 使用说明
├── flash_ptio.h              # 粒子 I/O 头文件
├── readFlashParticles.c      # 粒子文件读取器
├── sortParticles.c            # 粒子排序工具
├── writeFlashParticles.c     # 粒子写入器（二进制/TXT）
├── writeFlashParticlesHDF5.c # 粒子写入器（HDF5）
├── particles.py              # 粒子可视化 GUI
└── radius.py                 # 粒子半径分析
```

### 1.1 粒子排序 (readFlashParticles.c + sortParticles.c)

根据模板文件（通常是仿真第一个粒子文件）中的模式，为 FLASH 粒子输出文件提供一致的排序顺序。

**编译**:
```bash
cd tools/particleTools
make
```

**用法**:
```bash
mpirun -np N partSort <filename_base> <template_number> <first_file> <last_file>
```

**示例**:
```bash
mpirun -np 4 partSort driventurb_hdf5_part_ 0 1 4
# 使用文件 0 作为模板，排序文件 1~4
```

### 1.2 粒子读取/写入 (C 库)

**`readFlashParticles.c`** — 读取 FLASH 粒子文件（HDF5 或二进制格式），解析粒子属性、标签和块位置。

**`writeFlashParticles.c`** — 将粒子数据写入文本或二进制格式。支持自定义输出字段和格式。

**`writeFlashParticlesHDF5.c`** — 将粒子数据写入 HDF5 格式，保持 FLASH HDF5 文件兼容性。

**`flash_ptio.h`** — 共享头文件，定义粒子 I/O 结构体、常量和函数原型：
- `PARTICLE_TAG`, `PARTICLE_BLK` 等粒子属性常量
- 粒子文件格式定义

### 1.3 粒子可视化 (particles.py)

基于 Tkinter 的粒子动画查看器，支持二进制粒子文件的实时动画播放。

**用法**:
```bash
python particles.py <particle_file> <num_particles>
```

**功能**:
- 动画播放粒子运动
- 轨迹跟踪模式（trace on/off）
- 滚动条支持大尺度场景
- 控制按钮：Run（播放动画）、Exit（退出）

**技术细节**:
- 读取二进制双精度数据
- 支持多时间步回放
- 坐标映射到屏幕坐标

### 1.4 粒子半径分析 (radius.py)

分析粒子位置半径分布。

**功能**:
- 计算粒子距原点的径向距离
- 支持径向统计（平均、方差等）
- 按半径分仓统计粒子数

---

## 2. trajectoryFile — 粒子轨迹工具

### 功能

将 FLASH 粒子跟踪数据聚合为统一的轨迹文件格式，便于后处理分析。轨迹文件将多个时间步的粒子数据合并为一个高效访问的文件。

### 目录结构

```
trajectoryFile/
├── Makefile              # 构建配置
├── Makefile.*            # 各平台 Makefile
├── README.txt            # 使用说明
├── trajectoryFileNotes.txt # 轨迹文件格式说明
├── trajectory.c          # 轨迹转换主程序
├── trajectory.h          # 轨迹数据结构
├── readFlashParticles.c  # 粒子文件读取器
├── sortParticles.c/.h    # 粒子排序
├── writeTrajectoryFile.c # 轨迹文件写入
├── getOptions.c/.h       # 命令行选项
├── flash_ptio.h          # 粒子 I/O 头文件
└── trajSlice/            # 轨迹切片子工具
    ├── Makefile / Makefile.eureka
    ├── README
    ├── slice.c / slice.h
    ├── writeTrajectoryFile.c
    ├── getOptions.c / getOptions.h
    └── flash_ptio.h
```

### 2.1 轨迹转换 (trajectory.c)

将一系列 FLASH 粒子文件聚合为单一轨迹文件。

**用法**:
```bash
trajectoryConvert [options] <file_basename> <start_number> <end_number>
```

**参数**:
- `file_basename` — FLASH 文件名（不含编号，如 `sod_hdf5_part_`）
- `start_number` — 起始文件编号（通常 0000）
- `end_number` — 结束文件编号

**支持**: 标准 FLASH 粒子文件，暂不直接支持 Split 文件。

### 2.2 轨迹文件格式

根据 `trajectoryFileNotes.txt`:

```
字段:
  Simulation info     — 仿真信息（同 FLASH 输出）
  Simulation time    — 时间序列（每个粒子文件对应一个时间点）
  Particle names     — 粒子属性名
  Particles          — NPROPS x nTimeSteps x numParticles

  粒子数据按 tag 编号组织:
    Particle_NNNN    — 特定粒子的所有时间步数据
```

**尺寸估计**:
- 初始运行: 10K 粒子 × 20 属性 × 10K 文件 ≈ 16 GB
- 全规模: 1M 粒子需要格式扩展

**备注**: 离开域的粒子写入 `-1.0` 占位。排序器不修改粒子数据本身。

### 2.3 轨迹切片 (trajSlice)

从轨迹文件中提取指定时间步或粒子子集的切片数据。

**用法**:
```bash
cd trajSlice
make
./slice <input_traj_file> <output_file> [options]
```

**功能**:
- 按时间步过滤
- 按粒子标签过滤
- 按空间区域过滤

### 2.4 编译

```bash
cd tools/trajectoryFile
make                           # Linux
make -f Makefile.eureka        # Eureka 集群
# 其他平台参考 Makefile.*
cd trajSlice
make                           # 编译切片工具
```
