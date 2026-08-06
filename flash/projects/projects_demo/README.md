# projects_demo — 用户项目演示包

> 演示如何在 flash-sim 框架之上快速构建自己的仿真对比项目。
> 本项目包结构与 flash-sim 解耦, 可直接复制为自定义项目的起点。

## 目录结构

```
projects/projects_demo/
├── __init__.py
├── README.md                  ← 本文档
└── ch_center_demo/            ← ch_center 双密度对比演示
    ├── __init__.py
    ├── run_compare.py         ← 双密度 WSL 仿真运行器
    ├── plot_compare.py        ← 对比绘图
    ├── runs_ch_center_compare/ ← 仿真输出 (自动生成)
    └── compare_plots/          ← 对比图 (自动生成)
```

## 演示内容: ch_center 双密度对比

对 `ch_center` (CH 靶中心演化) 场景, 用**两种不同的 CH 靶密度** `sim_rhoTarg`
在本地 WSL 中分别运行 FLASH 仿真, 对比密度演化差异。

| 方案 | CH 靶密度 (sim_rhoTarg) | 物理含义 |
|------|------------------------|----------|
| 低密度 | 0.5 g/cm³ | 低密度 CH 靶, 压缩更易发生 |
| 高密度 | 2.0 g/cm³ | 高密度 CH 靶, 惯性更强 |

> ch_center 场景默认 `sim_rhoTarg=1.0 g/cm³`; 其余参数沿用场景默认值
> (5e14 W/cm² 激光, 1.2ns 仿真, 30μm 靶厚)。

## 快速开始

### 1. 前置条件

- 本地 WSL 已安装 FLASH 4.8 (见 `scenarios/flash_demo/hello_flash/README.md`)
- Python ≥ 3.10, 已安装 `numpy`, `h5py`, `matplotlib`
- 已安装 `pytest` (可选, 用于验证)

### 2. 运行双密度仿真 (WSL)

```bash
cd projects/projects_demo/ch_center_demo

# 完整运行 (双密度, 实际执行 FLASH)
python run_compare.py

# 仅生成输入文件, 不运行 FLASH (快速验证流程)
python run_compare.py --dry-run

# 自定义密度
python run_compare.py --dens 0.3,1.5,3.0
```

首次运行会编译 FLASH (ch_center 场景, LaserSlab1D_new), 后续复用缓存, 较快。

### 3. 对比绘图

```bash
python plot_compare.py
```

生成 3 张对比图到 `compare_plots/`:

| 图 | 内容 |
|----|------|
| `compare_dens_profile.png` | 末时刻密度空间剖面 (低/高密度对比) |
| `compare_dens_time.png` | 中心点密度时间演化对比 |
| `compare_dens_heatmap.png` | x-t 密度热图并排对比 |

## 运行摘要

每次运行在 `runs_ch_center_compare/compare_summary.json` 生成结构化摘要,
供 plot_compare.py 与后续分析使用:

```json
{
  "scenario": "ch_center",
  "densities": [0.5, 2.0],
  "results": [
    {"run_id": "000001", "dens": 0.5, "success": true, ...},
    {"run_id": "000002", "dens": 2.0, "success": true, ...}
  ]
}
```

## 扩展指南

- **更多密度**: `python run_compare.py --dens 0.1,0.5,1.0,2.0,5.0`
- **其他参数对比**: 修改 `run_compare.py` 中的 `params_override`,
  例如同时覆盖 `sim_targetHeight_um`, `laser_powers` 等。
- **自定义场景**: 参考 `scenarios/center_evolution/ch_center/` 创建新场景,
  再仿照本包写对比逻辑。
