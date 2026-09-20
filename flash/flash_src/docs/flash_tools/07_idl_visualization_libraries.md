# FLASH IDL 可视化库

FLASH 提供两套完整的 IDL（Interactive Data Language）可视化库，用于 FLASH HDF5 输出数据的后处理和可视化。

| 库 | 路径 | 文件数 | 特点 |
|----|------|--------|------|
| **fidlr3.0** | `tools/fidlr3.0/` | 79 | FLASH IDL 读取器 v3.0，轻量级 |
| **idlamrlib** | `tools/idlamrlib/` | 97 | IDL-AMR 可视化库，功能更全面 |

---

## 1. FIDL (FLASH IDL Reader) v3.0

### 概述

FIDL 是 FLASH 的 IDL 数据读取和可视化工具集，使用 IDL 5.6+ 原生 HDF5 支持。

**重要**: 仅支持 HDF5（HDF v4.x 支持已移除）。需要 IDL 5.6+。

**支持**:
- HDF5 格式的 checkpoint/plot 文件
- NetCDF 格式（2003-09-09 后添加）
- 粒子数据（2D Cartesian，NetCDF/HDF5）
- 二维球面几何的初步支持

### 文件统计

- 77 个 `.pro` IDL 源文件
- 1 个颜色表文件 `flash_colors.tbl`
- 1 个 README

### 核心程序

| 程序 | 文件 | 功能 |
|------|------|------|
| **xflash3** | `xflash3.pro` (73KB) | 主可视化程序，FLASH 3D 数据浏览 |
| **xplot1d_amr** | `xplot1d_amr.pro` (18KB) | 1D AMR 数据绘图 |
| **xplot2d_amr** | `xplot2d_amr.pro` (48KB) | 2D AMR 数据绘图 |
| **xplot2d_amr_diff** | `xplot2d_amr_diff.pro` (33KB) | 2D AMR 差异绘图 |
| **xplot3d_amr** | `xplot3d_amr.pro` (35KB) | 3D AMR 数据绘图 |
| **data_browse** | `data_browse.pro` (22KB) | 数据浏览工具 |
| **merge_amr** | `merge_amr.pro` (21KB) | AMR 数据合并 |
| **read_amr** | `read_amr.pro` (23KB) | AMR 数据读取器 |
| **read_fisher** | `read_fisher.pro` (73KB) | Fisher 格式数据读取 |
| **merge_polar** | `merge_polar.pro` (14KB) | 极坐标数据合并 |
| **xcontour** | `xcontour.pro` (11KB) | 等值线绘图 |
| **vectorplot** | `vectorplot.pro` (11KB) | 矢量场绘图 |
| **xvector** | `xvector.pro` (6KB) | 矢量场绘图（2D） |
| **xvector3d** | `xvector3d.pro` (6KB) | 矢量场绘图（3D） |
| **xparticle** | `xparticle.pro` (12KB) | 粒子数据绘图 |
| **tvimage** | `tvimage.pro` (27KB) | 图像显示工具 |
| **xlabel** | `xlabel.pro` (17KB) | 标签工具 |
| **xflash_defaults** | `xflash_defaults.pro` (16KB) | 默认参数设置 |
| **hist / hist_driver** | `hist.pro` / `hist_driver.pro` | 直方图工具 |
| **partvelvec** | `partvelvec.pro` (16KB) | 粒子速度矢量图 |

### 辅助模块

| 文件 | 功能 |
|------|------|
| `file_information.pro` | 文件元数据查询 |
| `determine_file_*.pro` | 文件特性检测（维度、精度、类型、版本） |
| `determine_flash_version.pro` | FLASH 版本检测 |
| `determine_geometry.pro` | 几何类型检测 |
| `extract_line.pro / extract_line_polar.pro` | 沿线数据提取 |
| `radial_average.pro / radial_average_polar.pro` | 径向平均 |
| `draw_blocks.pro / draw_blocks_polar.pro` | 块结构绘制 |
| `query.pro` | 数据查询工具 |
| `readtab.pro` | 表格数据读取 |
| `color*.pro` | 颜色管理 |
| `scale*.pro` | 缩放与颜色缩放 |

### 快速开始

```idl
; 在 IDL 中
IDL> .compile xflash3
IDL> xflash3
```

### 配置

颜色表文件: `flash_colors.tbl`

---

## 2. IDL-AMR 可视化库 (idlamrlib)

### 概述

IDL-AMR 可视化库（IDLAMRVis）提供更全面的 FLASH AMR 数据可视化功能，支持交互式 3D 数据探索。

### 文件统计

- 83 个 `.pro` IDL 源文件
- 3 个 `.txt` 文档（MANUAL.TXT, README.txt, plotting.txt）
- 1 个 `license.txt`（15KB）
- 1 个 `movie_inputs.txt`
- 1 个 `smartframelinker.tar`
- 3 个示例图像

### 快速开始

```bash
cd idlamrlib
idl
```

在 IDL 中:

```idl
IDL> .com idlamrvis    ; 加载所有函数（注意: 用 .com 不是 .compile）
IDL> idlamrvis          ; 启动程序
```

启动后出现文件选择对话框 → 选择 FLASH plot 文件 → 自动加载密度（density）数据。

### 核心程序

| 程序 | 功能 |
|------|------|
| **idlamrvis.pro** (64KB) | 主交互式可视化程序 |
| **get_amrcomponent_flash.pro** (20KB) | AMR 组件提取器 |
| **merge_amr.pro** (21KB，与 fidlr 共享) | AMR 数据合并 |
| **column_amr.pro** (21KB) | 柱密度计算 |
| **get_ppv_amr.pro** (14KB) | PPV（位置-位置-速度）数据 |
| **raster_amr.pro** (18KB) | 光栅化 AMR 数据 |

### 可视化模式

根据 `README.txt`，IDLAMRVis 支持三种可视化模式:

#### 3.1 柱密度 (Column-Density)
- 沿指定轴积分密度
- 支持旋转滑块控制视角
- 适用于快速整体数据浏览

#### 3.2 切片 (Slice)
- 标量范围窗口
- 切片几何窗口
- 渲染区域交互

#### 3.3 线 (Line)
- 沿指定线提取数据
- 1D X vs Y 绘图

### 命令行访问

以下函数可直接在 IDL 命令行调用:

| 函数 | 说明 |
|------|------|
| `COLUMN_ANY` | 基础级柱密度计算 |
| `COL_ANY_FRAME` | 高级柱密度工具 |
| 轴对齐切片 | 沿坐标轴的切片 |
| 任意角度切片 | 沿任意角度的切片 |
| 沿线提取 | 沿指定线的数据提取 |

### 电影制作

1. 渲染帧: 使用命令行工具批量生成帧图像
2. 编码电影: 使用外部工具将帧编码为视频格式
3. 支持时变电影（随时间演化的数据）

### 文档

| 文件 | 内容 |
|------|------|
| `README.txt` (17KB) | 快速入门指南，详细操作说明 |
| `MANUAL.TXT` (11KB) | 完整用户手册 |
| `plotting.txt` (7KB) | 绘图配置说明 |
| `license.txt` (15KB) | 许可证信息 |
| `movie_inputs.txt` | 电影参数配置 |

### 依赖

- IDL 6.0+
- 建议 3 键鼠标（左=MB0, 中=MB1, 右=MB2）
- 支持所有 FLASH HDF5 格式

### 恢复运行

如果程序崩溃或出错:

1. 点击 IDLAMRVis 窗口标题栏的 'X'
2. 在 IDL 命令行输入:
```idl
IDL> idlamrvis
```
