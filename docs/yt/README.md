# yt — FLASH 可视化与分析工具

> yt (https://yt-project.org) 是一个开源的宇宙学和天体物理仿真数据分析与可视化工具包，原生支持 FLASH AMR HDF5 输出格式。

---

## 1. 概述

本集群（NC-E / BSCC-T6）上 yt 的安装与使用说明。由于超算环境限制，**推荐优先使用纯 h5py 方案** 进行 FLASH 数据处理（详见本文档第 5 节）。

### 核心依赖

| 包 | 版本要求 | 用途 |
|----|----------|------|
| `unyt` | >= 2.9 | 带单位物理量 |
| `cmyt` | >= 2.0 | yt 色图 |
| `toml` | >= 0.10 | 配置文件 (yt < 4.1) |
| `tomli` | >= 2.0 | 配置文件 (yt >= 4.1) |
| `ewah-bool-utils` | >= 1.0 | 位图压缩 (yt >= 4.2) |
| `more-itertools` | >= 8.0 | 迭代器工具 |
| `matplotlib` | >= 3.5 | 绘图 |

---

## 2. HPC 安装

### 2.1 安装位置

所有文件安装在用户空间：
```
~/QC/FLASH/local/yt/
├── lib/python3.9/site-packages/    # yt 及依赖
├── bin/                             # 命令行工具
└── modulefiles/yt/4.0.2            # modulefile
```

### 2.2 离线安装 (从预编译 wheel)

由于超算计算节点无外网访问，采用 **本地下载 + SCP 上传 + 离线 pip 安装** 流程：

```bash
# 1. 本地下载 cp39 manylinux wheels
pip download --only-binary=:all: --platform manylinux2014_x86_64 \
  --python-version 3.9 --implementation cp --abi cp39 \
  --dest ./yt_wheels \
  yt==4.0.2 unyt cmyt toml more-itertools ewah-bool-utils

# 2. 打包上传到超算
tar czf yt_wheels.tar.gz *.whl
scp yt_wheels.tar.gz scfa2696@ssh.cn-zhongwei-1.paracloud.com:~/AI/AItemp/

# 3. 超算端安装
module load python/3.9.6
cd ~/AI/AItemp/yt_wheels && tar xzf ../yt_wheels.tar.gz
pip install --no-index --find-links . --prefix ~/QC/FLASH/local/yt \
  yt unyt cmyt toml more-itertools ewah-bool-utils
```

> ⚠ **wheel 兼容性问题**: yt 4.x 的预编译 manylinux wheel 在 NC-E 上 `import yt` 时 segfault (exit code 139)。
> 原因: glibc 2.17 + Haswell CPU 与最新 manylinux 二进制存在 ABI 不兼容。
>
> 尝试过的版本: 4.0.2, 4.3.0 — 全部 segfault。

### 2.3 Module 加载

```bash
module use ~/QC/FLASH/local/yt/modulefiles
module load yt/4.0.2
```

**作用**: 添加 yt 的 `site-packages` 到 `PYTHONPATH`，添加 `bin` 目录到 `PATH`。

---

## 3. yt vs h5py 数据对比验证

### 3.1 测试条件

- **测试文件**: `test/hdf5ploter_easy/lasslab_hdf5_plt_cnt_0066`
- **本地环境**: Windows x86_64, Python 3.14, yt 4.x
- **对比方法**:
  - **yt**: `ds.ray(domain_left_edge, domain_right_edge)` → 单元格中心采样
  - **h5py**: `dens[:,0,0,:]` + `bbox[:,0,:]` → 单元格中心坐标重建 + 拼合 + 排序 + 去重

### 3.2 定量对比结果

| 指标 | yt ray | h5py cell-center |
|------|--------|-------------------|
| 数据点数 | 272 | 480 |
| x 范围 | 1.250e-4 ~ 1.597e-2 cm | 1.250e-4 ~ 1.597e-2 cm |
| 密度范围 | 1.0e-6 ~ 4.33 g/cm³ | 1.0e-6 ~ 4.33 g/cm³ |
| 一致率 (500点插值) | **440/500 (88%)** 完全一致 | 基线 |

### 3.3 差异分析

两方法在 **88% 的点上完全一致**（相对误差 < 1e-12）。差异仅出现在 **AMR 块边界** 处：

- yt 的 ray 采样点数更少（272 vs 480），因为 yt 对每个唯一单元格只采样 1 个点
- yt 在块边界处可能使用不同的插值策略
- 最大绝对差异 `max|diff| = 0.50 g/cm³` 出现在密度梯度最大的区域
- 两种方法得到的 **密度峰值完全相同** (`4.328 g/cm³`)

### 3.4 对比图

![yt vs h5py 对比图](../test/hdf5ploter_easy/output/hpc_comparison/yt_vs_h5py_comparison.png)

---

## 4. 本地使用 (Windows/WSL)

本地不需要离线安装，直接 pip 安装即可：

```bash
pip install yt
```

### 本地使用示例

```python
import yt
yt.funcs.mylog.setLevel(50)  # 抑制 yt 日志

# 加载 FLASH HDF5
ds = yt.load("lasslab_hdf5_plt_cnt_0066")

# 沿 x 方向 ray 采样 (1D)
ray = ds.ray(ds.domain_left_edge, ds.domain_right_edge)
x = ray[("index", "x")].to("cm").d
dens = ray[("flash", "dens")].to("g/cm**3").d

# 排序
import numpy as np
idx = np.argsort(x)
x, dens = x[idx], dens[idx]

# 绘图
import matplotlib.pyplot as plt
plt.plot(x, dens)
plt.xlabel("x [cm]")
plt.ylabel(r"Density [g/cm$^3$]")
plt.show()
```

---

## 5. 推荐方案：纯 h5py 提取 (无需 yt)

鉴于 yt 在超算上不可用且本地安装较重量级，**推荐使用纯 h5py 方案**，这也是本项目中所有 Demo 的统一做法。

### 5.1 核心算法

```python
import h5py
import numpy as np

with h5py.File("output.h5", "r") as f:
    raw = f["dens"][:]          # (nblocks, 1, 1, nx)
    bbox = f["bounding box"][:] # (nblocks, 3, 2)

nblocks, nz, ny, nx = raw.shape
dense = raw[:, 0, 0, :]  # (nblocks, nx)

x_list, d_list = [], []
for b in range(nblocks):
    xmin = float(bbox[b, 0, 0])
    xmax = float(bbox[b, 0, 1])
    dx = (xmax - xmin) / nx
    xs = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
    x_list.append(xs)
    d_list.append(dense[b, :])

x_all = np.concatenate(x_list)
d_all = np.concatenate(d_list)

# 稳定排序 + 去重 (AMR 块边界处 x 可能重复)
idx = np.argsort(x_all, kind="mergesort")
x_sorted = x_all[idx]
d_sorted = d_all[idx]

unique_x, inverse = np.unique(x_sorted, return_inverse=True)
if len(unique_x) < len(x_sorted):
    d_unique = np.zeros_like(unique_x)
    np.add.at(d_unique, inverse, d_sorted)
    d_unique /= np.bincount(inverse)
    x_final, d_final = unique_x, d_unique
else:
    x_final, d_final = x_sorted, d_sorted
```

### 5.2 已集成的工具函数

| 函数 | 位置 | 功能 |
|------|------|------|
| `extract_1d_profile()` | `scenarios/flash_demo/demo_hpc/_plot_utils.py` | 提取 1D 剖面 (任何变量) |
| `extract_center_value()` | `scenarios/flash_demo/demo_hpc/_plot_utils.py` | 提取中心值 + 仿真时间 |
| `save_density_plot()` | `scenarios/flash_demo/demo_hpc/_plot_utils.py` | 保存密度图 |
| `plot_dens_easy_hpc.py` | `test/hdf5ploter_easy/` | 跨平台 HDF5→CSV+绘图 独立脚本 |

### 5.3 已集成的 Demo

| Demo | 位置 | 说明 |
|------|------|------|
| `laserslab1d_supercomputer_demo.py` | `scenarios/flash_demo/demo_hpc/` | 超算一键运行 + 超算端绘图 |
| `laserslab1d_hpc_demo_batch.py` | `scenarios/flash_demo/demo_hpc/` | 多功率批量对比 + 远程分析 |
| `remote_plot_script.py` | `scenarios/flash_demo/demo_hpc/` | 超算端绘图脚本 |
| `remote_analysis.py` | `scenarios/flash_demo/demo_hpc/` | 超算端分析脚本 |

---

## 6. 安装排查记录

### 6.1 问题: pip install 需要网络

**症状**: `pip install yt` 在超算上失败 — `Name or service not known`

**解决**: 在本地下载 wheel，上传到超算，用 `--no-index --find-links` 离线安装。

### 6.2 问题: manylinux wheel 标签不兼容

**症状**: `yt-4.3.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl is not a supported wheel`

**原因**: pip 22.3.1 不识别双 manylinux 标签格式。yt >= 4.1 的 wheel 使用 `{glibc_ver}.{rhel_ver}` 双标签。

**解决**: 复制 wheel 并重命名，移除多余标签后缀：
```bash
cp yt-4.3.0-cp39-...manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
   yt-4.3.0-cp39-cp39-manylinux2014_x86_64.whl
```

### 6.3 问题: import yt 段错误 (SIGSEGV)

**症状**: `import yt` 返回 exit code 139，无 Python traceback

**诊断**:
- glibc: `ldd --version` → 2.17 (CentOS 7)
- CPU: Intel Xeon E5-2678 v3 (Haswell, 2014)
- 无缺失共享库 (`ldd *.so` 全部 OK)
- C 扩展全部可通过 `ctypes.CDLL` 加载

**结论**: 二进制不兼容。yt 4.x 的 manylinux wheel 使用较新的编译工具链，生成的机器码在 glibc 2.17 + Haswell 上运行时 SIGSEGV。

**尝试方案** (均失败):
- yt 4.3.0 (最新) → segfault
- yt 4.0.2 (最老的 cp39 版本) → segfault
- 从源码编译 (`pip install --no-build-isolation`) → 缺少 `ewah_bool_utils` 构建依赖

### 6.4 问题: real scalars compound dataset 遍历

**症状**: 从 `real scalars` 读取时间始终返回 0.0

**原因**: `for name_arr, val_arr in rs:` 对 numpy 结构化数组不适用 — `name_arr[0]` 返回 int 而非字符串。

**解决**: 使用 dict-style 访问:
```python
for rec in rs:
    name = rec["name"].decode("utf-8").strip()
    if name == "time":
        time = float(rec["value"])
        break
```

---

## 7. 注意事项

1. **超算上不要依赖 yt**: yt 的 C 扩展在 NC-E 上 segfault。所有超算端绘图已改用纯 h5py。
2. **跨平台 CSV 对比**: 由于 Windows/Linux 浮点数格式化存在 ~1e-13 差异，CSV 文件比较应使用数值容差 (`np.allclose`) 而非 SHA256。
3. **单元格中心坐标**: FLASH 数据存储在单元格中心，需用 `xmin + dx/2` 到 `xmax - dx/2` 的 linspace，而非 `xmin` 到 `xmax`。
4. **AMR 块排序**: 不同平台的 `np.argsort` 在平局时行为不同，必须用 `kind="mergesort"` 保证跨平台确定性。
5. **临时目录**: 超算上的 `~/AI/AItemp/` 用于存放临时文件，运行完 `pip install` 后可清理 `~ /AI/AItemp/yt_wheels/`。

---

*文档版本: v1.0 | 最后更新: 2026-06-30*
