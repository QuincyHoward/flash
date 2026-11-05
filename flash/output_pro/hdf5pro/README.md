# output_pro/hdf5pro — HDF5 核心底层 I/O

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：FLASH HDF5 输出文件的底层读取与解析——AMR 块结构、坐标系统、单位、派生量计算（`DataCalculator`）的唯一实现。

## 文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `__init__.py` | 35 | 子包声明 |
| `flash_hdf5.py` | 1440 | `FlashHDF5File`（46 方法）：叶节点筛选、`extract_var_yt_style()` 纯 h5py yt 风格提取（1/2/3D）、6 种坐标系统自动检测、`DataCalculator` 派生量（如标长 gradient scale length） |

## 使用入口

```python
from flash.output_pro.hdf5pro import FlashHDF5File
f = FlashHDF5File("sim_output/chk_0039")
dens, units = f.read_var("dens")
```

**详细文档**：[../docs/api_reference.md](../docs/api_reference.md)、[../FLASH物理量说明.md](../FLASH物理量说明.md)

**上级导航**：[../README.md](../README.md)
