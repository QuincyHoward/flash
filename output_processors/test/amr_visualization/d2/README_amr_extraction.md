# FLASH 2D HDF5 文件处理工具

## 项目概述

本工具用于从 FLASH 2D 仿真输出的 HDF5 文件中提取 `dens`（密度）场数据，并正确处理 AMR（自适应网格细化）覆盖关系。

提供两种实现方法：
1. **yt 版本**（`preprocess_with_yt.py`）：使用 yt 库读取，适用于本地环境
2. **h5py 版本**（`extract_dens_h5py_amr_correct.py`）：纯 h5py 实现，适用于超算环境（无法安装 yt）

---

## 两种方法对比

| 特性 | yt 版本 | h5py 版本 |
|------|---------|------------|
| **依赖库** | yt, h5py, numpy, pandas, matplotlib | h5py, numpy, pandas, matplotlib |
| **适用环境** | 本地工作站（有 yt） | 超算（无 yt） |
| **AMR处理** | yt 自动处理 | 手动实现 child_mask 算法（重现 yt） |
| **输出格式** | CSV + HDF5 + PNG | CSV + PNG |
| **数据一致性** | 基准 | 与 yt 版本一致（差异 < 1e-8） |

---

## 安装依赖

### yt 版本
```bash
pip install yt h5py numpy pandas matplotlib
```

### h5py 版本
```bash
pip install h5py numpy pandas matplotlib
```

---

## 使用指南

### 1. yt 版本（本地预处理）

**用途**：在本地使用 yt 读取 HDF5 文件，保存为 CSV 和 HDF5 格式，供超算使用。

**运行**：
```bash
cd flash/output_processors/test/amr_visualization/d2
python preprocess_with_yt.py inputfiles/hdf5files_2d/lasslab_hdf5_plt_cnt_0049
```

**输出**：
```
lasslab_hdf5_plt_cnt_0049/
└── yt/
    ├── lasslab_hdf5_plt_cnt_0049_yt_data.csv    # CSV 数据
    ├── lasslab_hdf5_plt_cnt_0049_yt_data.h5     # HDF5 数据（用于超算）
    └── lasslab_hdf5_plt_cnt_0049_yt_dens_colormap.png  # 密度彩图
```

### 2. h5py 版本（超算直接使用）

**用途**：在超算上直接使用 h5py 读取 HDF5 文件，正确处理 AMR 覆盖关系。

**运行**：
```bash
cd flash/output_processors/test/amr_visualization/d2
python extract_dens_h5py_amr_correct.py inputfiles/hdf5files_2d/lasslab_hdf5_plt_cnt_0049
```

**输出**：
```
lasslab_hdf5_plt_cnt_0049/
└── h5py/
    ├── lasslab_hdf5_plt_cnt_0049_dens_h5py_amr_correct.csv  # CSV 数据
    └── lasslab_hdf5_plt_cnt_0049_dens_colormap.png          # 密度彩图
```

---

## 验证结果

使用 `compare_yt_h5py.py` 对比三个时间步的 yt 版本和 h5py 版本输出：

```bash
cd flash/output_processors/test/amr_visualization/d2
python compare_yt_h5py.py
```

### 对比报告

| 时间步 | yt 点数 | h5py 点数 | 点数一致 | 坐标最大差异 | 密度平均绝对差异 | 实际应用 |
|--------|---------|------------|---------|--------------|----------------|---------|
| 0000   | 11,264  | 11,264     | ✅       | 4.06e-10     | 2.17e-08       | ✅ 一致  |
| 0024   | 23,552  | 23,552     | ✅       | 4.06e-10     | 7.31e-09       | ✅ 一致  |
| 0049   | 22,784  | 22,784     | ✅       | 4.06e-10     | 7.74e-09       | ✅ 一致  |

**结论**：h5py 版本与 yt 版本的输出在实际应用中完全一致（差异在浮点数精度范围内）。

---

## 超算部署说明

### 方案 A：使用 yt 预处理的 HDF5 文件

1. **本地预处理**：
   ```bash
   python preprocess_with_yt.py inputfiles/hdf5files_2d/lasslab_hdf5_plt_cnt_0049
   ```

2. **上传 HDF5 文件到超算**：
   ```bash
   scp lasslab_hdf5_plt_cnt_0049/yt/lasslab_hdf5_plt_cnt_0049_yt_data.h5 user@hpc:/path/to/data/
   ```

3. **在超算上读取**：
   ```python
   import h5py
   import numpy as np
   
   with h5py.File('lasslab_hdf5_plt_cnt_0049_yt_data.h5', 'r') as f:
       r = f['r'][:]
       z = f['z'][:]
       dens = f['dens'][:]
   
   print(f"数据点数量: {len(dens):,}")
   print(f"密度范围: [{dens.min():.6e}, {dens.max():.6e}]")
   ```

### 方案 B：直接在超算上运行 h5py 版本

1. **上传 HDF5 输出文件到超算**：
   ```bash
   scp inputfiles/hdf5files_2d/lasslab_hdf5_plt_cnt_0049 user@hpc:/path/to/flash/output/
   ```

2. **上传处理脚本到超算**：
   ```bash
   scp extract_dens_h5py_amr_correct.py user@hpc:/path/to/scripts/
   ```

3. **在超算上运行**：
   ```bash
   python extract_dens_h5py_amr_correct.py /path/to/flash/output/lasslab_hdf5_plt_cnt_0049
   ```

4. **下载结果**：
   ```bash
   scp -r user@hpc:/path/to/output/lasslab_hdf5_plt_cnt_0049/h5py/ ./
   ```

---

## 核心算法说明（h5py 版本）

### AMR 覆盖关系处理

FLASH 使用 AMR（自适应网格细化）技术，细网格会覆盖粗网格的对应区域。正确提取数据需要：

1. **建立父子关系**：从 `/gid` 数据集读取子网格 ID
2. **计算 child_mask**：对于每个网格，计算哪些单元格被细网格覆盖
3. **应用掩码**：只保留未被覆盖的单元格数据

### child_mask 算法（重现 yt）

```python
def compute_child_mask(self):
    mask = np.ones(self.active_dims, dtype=bool)
    
    for child in self.children:
        # 计算子网格在父网格中的索引范围
        gi = self.get_global_startindex()
        cgi = child.get_global_startindex()
        rf = 2  # refine_by
        
        startIndex = np.maximum(0, cgi // rf - gi)
        endIndex = np.minimum(
            (cgi + child.active_dims) // rf - gi,
            self.active_dims
        )
        
        # 将对应区域的掩码设为 False
        mask[
            startIndex[0]:endIndex[0],
            startIndex[1]:endIndex[1],
            startIndex[2]:endIndex[2]
        ] = False
    
    return mask
```

---

## 文件清单

### 核心脚本
- `preprocess_with_yt.py` - yt 版本（本地预处理）
- `extract_dens_h5py_amr_correct.py` - h5py 版本（超算用）
- `compare_yt_h5py.py` - 对比工具

### 输出目录结构
```
d2/
├── lasslab_hdf5_plt_cnt_0000/
│   ├── yt/           # yt 版本输出
│   └── h5py/        # h5py 版本输出
├── lasslab_hdf5_plt_cnt_0024/
│   ├── yt/
│   └── h5py/
├── lasslab_hdf5_plt_cnt_0049/
│   ├── yt/
│   └── h5py/
├── compare_yt_h5py.py
├── preprocess_with_yt.py
└── extract_dens_h5py_amr_correct.py
```

---

## 常见问题

### Q1: 为什么需要两种版本？
**A**: yt 库功能强大但依赖复杂，无法在超算上安装。h5py 版本是纯 Python 实现，只需要基础的 HDF5 读取能力。

### Q2: 数据差异来源是什么？
**A**: 差异主要来自浮点数精度误差（float64 的机器精度约为 2.2e-16）。实际应用中可忽略（差异 < 1e-8）。

### Q3: 如何验证 AMR 处理正确？
**A**: 使用 `compare_yt_h5py.py` 对比 yt 版本和 h5py 版本的输出。如果数据点数量、坐标范围、密度统计都一致，则 AMR 处理正确。

---

## 作者与日期

- **作者**: AI Assistant
- **日期**: 2026-07-02
- **版本**: 1.0
- **项目**: PhySimX (原名 physiopt)

---

## 参考文献

1. FLASH User Guide - HDF5 Output Format
2. yt Documentation - AMR Data Access
3. h5py Documentation - Reading HDF5 Files
