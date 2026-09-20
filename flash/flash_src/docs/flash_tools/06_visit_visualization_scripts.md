# FLASH VisIt 可视化脚本

## 概述

VisIt 可视化脚本位于 `tools/scripts/visitScripts/`，用于批量生成 FLASH 仿真数据的可视化图像和电影。

## 文件列表

```
visitScripts/
├── movie_modular.py              # 模块化电影生成器
├── snap_camera_forvisit.py       # 简单相机快照
├── snap_camera_forwatcher.py     # 带参数相机快照
├── snap_plotfile.py              # 2D 切片快照
├── watcher_sim.py                # 自动化监控快照
└── Chombo/
    ├── dump_chombo_mesh.py       # AMR 网格可视化
    ├── dump_chombo_patches.py    # AMR 块边界可视化
    ├── run_dump_chombo_mesh.sh   # 网格可视化运行脚本
    └── run_dump_chombo_patches.sh # 块边界可视化运行脚本
```

---

## 1. movie_modular.py — 模块化电影生成器

用于批量生成 FLASH 模拟数据的电影帧图像。

### 功能

- 支持多种可视化类型组合：Pseudocolor、Vector/Hedgehog、等值面（Contour/Isosurface）、流线（Streamline）
- 摄像机路径插值（关键帧立方样条）
- 支持 AMR 细化级别选择

### 关键函数

| 函数 | 功能 |
|------|------|
| `range_intersection()` | 确定所有文件的变量公共范围（使用 `h5dump` 或 VisIt `Query`） |
| `range_union()` | 确定所有文件变量的并集范围 |
| `snap()` | 遍历文件列表并生成图像 |
| `set_plots_ops_1()` | 添加 Pseudocolor 和 Vector 图 |
| `set_plots_ops_2()` | 添加 Contour 图 |
| `set_ref_level()` | 选择 AMR 细化级别 |

### 使用方式

直接编辑脚本中的硬编码参数后运行：

```bash
python movie_modular.py
```

**需配置参数**:
- 数据库位置（文件路径前缀）
- 变量名
- 摄像机向量和位置
- 关键帧定义

---

## 2. snap_camera_forvisit.py — 简单相机快照

生成单个 FLASH plot 文件的 PNG 图像。

### 功能

- Contour 图 + IndexSelect 操作符（快速低分辨率渲染）
- 3D 视角控制
- 支持多 plot 文件批处理

### 使用方式

```bash
visit -cli -nowin -s snap_camera_forvisit.py
```

需编辑脚本硬编码变量名、文件名、相机向量等参数。

---

## 3. snap_camera_forwatcher.py — 带参数相机快照

与 `snap_camera_forvisit.py` 类似，但支持命令行参数，适合自动化和外部脚本调用。

### 使用方式

```bash
visit -cli -nowin -default_format FLASH -s snap_camera_forwatcher.py \
  --pfname <plotfile> --vname <var> --ifname <image> --camvec x y z
```

### 参数

| 参数 | 说明 |
|------|------|
| `--pfname` | plot 文件路径 |
| `--vname` | 可视化变量名 |
| `--ifname` | 输出图像文件名 |
| `--camvec` | 摄像机向量 (x y z) |

---

## 4. snap_plotfile.py — 2D 切片快照

生成 FLASH 数据的 2D 切片 PNG 图像（Pseudocolor + Slice 操作符）。

### 使用方式

```bash
visit -cli -nowin -default_format FLASH -s snap_plotfile.py \
  -fn <plotfile> -vn <varname> -in <imagefilename>
```

### 三个必需参数

| 参数 | 说明 |
|------|------|
| `-fn` | plot 文件路径 |
| `-vn` | 变量名 |
| `-in` | 输出图像文件名 |

---

## 5. watcher_sim.py — 自动化监控快照

模拟 Bob Fisher 的"watcher"脚本，自动对一组 plot 文件调用 `snap_camera_forwatcher.py` 生成 PNG。

### 使用方式

编辑脚本中的硬编码文件列表和参数，直接运行：

```bash
python watcher_sim.py
```

### 工作流

1. 定义 plot 文件列表
2. 对每个文件调用 VisIt CLI
3. 生成 PNG 快照

---

## 6. Chombo 子目录 — AMR 网格可视化

### 6.1 dump_chombo_mesh.py

生成 AMR 网格（Mesh）+ 密度（Pseudocolor）叠加的 PNG 图像。

```bash
visit -cli -nowin -s dump_chombo_mesh.py
```

### 6.2 dump_chombo_patches.py

类似 `dump_chombo_mesh.py`，但额外绘制网格块边界（粗黑线 Subset 图），便于可视化 AMR 块分解。

```bash
visit -cli -nowin -s dump_chombo_patches.py
```

### 6.3 Shell 运行脚本

```bash
bash run_dump_chombo_mesh.sh
bash run_dump_chombo_patches.sh
```

---

## 依赖

所有脚本依赖 **VisIt CLI**:
- 安装 VisIt 后确保 `visit` 命令在 PATH 中
- 使用 `-cli` 模式运行 Python 脚本
- 使用 `-nowin` 关闭窗口（批处理模式）
- 使用 `-default_format FLASH` 设置文件格式

---

## 快速开始示例

### 单文件快照

```bash
# 生成 2D 切片
visit -cli -nowin -default_format FLASH -s snap_plotfile.py \
  -fn sedov_hdf5_plt_cnt_0010 -vn dens -in density_slice.png

# 生成 3D 快照
visit -cli -nowin -default_format FLASH -s snap_camera_forwatcher.py \
  --pfname sedov_hdf5_chk_0010 --vname dens --ifname dens_3d.png \
  --camvec 0.577 0.577 0.577
```

### 批量生成电影帧

1. 编辑 `movie_modular.py` 设置文件列表、变量和相机路径
2. 运行生成帧图像
3. 用 ffmpeg 等工具编码为电影

### Chombo 网格可视化

```bash
# 生成网格密度叠加图
visit -cli -nowin -s dump_chombo_mesh.py

# 生成带块边界的网格图
visit -cli -nowin -s dump_chombo_patches.py
```
