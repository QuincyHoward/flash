---
name: flash-data-extract
description: 纯 h5py 提取 FLASH AMR 数据三合一：超算无 yt 时的 yt 风格块提取、压缩数据集批读提速与时间轴行对齐、float32 np.std 溢出修复。触发词：h5py 提取、yt 风格、AMR 叶块、node_type、批读、逐行慢、时间轴错位、np.std inf、float32 溢出、FlashHDF5File、FlashDataLoader、extraction_mode。
---

> 最后核对：2026-11-06 · commit 72f6428

# 纯 h5py 提取 FLASH AMR 数据（无 yt 环境）

代码锚点：
- `flash/output_pro/hdf5pro/flash_hdf5.py` — `FlashHDF5File`（yt 风格提取）
- `flash/output_pro/loader/data_loader.py` — `FlashDataLoader` / `FlashDataContainer`
- `flash/output_pro/extraction_modes.py` — 提取模式开关
- `flash/output_pro/parallel.py` — 并行读取工具

## 1. yt 风格块提取（超算无 yt 时）

### 核心原理

1. **叶节点筛选**：读 `node_type` 数据集，仅用 `node_type == 1` 的块（PARAMESH 叶节点）
2. **坐标重建**：用 `bounding box` 重建每个叶块单元中心坐标
3. **去重**：AMR 块边界单元重叠，用 `(x)` / `(x,y)` / `(x,y,z)` 元组去重
4. **坐标系自动检测**：基于 z 轴范围是否 ≈ 2π 或 ≈ 1° 判断 Cartesian/Cylindrical

### API

```python
from flash.output_pro.hdf5pro.flash_hdf5 import FlashHDF5File
ff = FlashHDF5File("plt_file")
cs = ff.coordinate_system     # "cartesian_1d" / "cylindrical_rz" / "cartesian_3d"
cl = ff.coord_labels          # {0: "x [cm]", ...}

x, dens = ff.extract_var_yt_style("dens")            # 1D → (x, data)
r, z, dens = ff.extract_var_yt_style("dens")         # 2D R-Z → (r, z, data)
x, y, z, dens = ff.extract_var_yt_style("dens")      # 3D → (x, y, z, data)
ff.close()
```

支持矩阵：`cartesian_1d` / `cylindrical_rz` / `cartesian_3d` 已实现；`cartesian_2d` / `cylindrical_1d` / `cylindrical_3d` / spherical 抛 `NotImplementedError`。新增坐标系流程：`coordinate_system` 加检测 → `coord_labels` 加标签 → 实现 `_extract_yt_Xd` → 在 `extract_var_yt_style` 的 `supported_combos` 注册 → 跑对比验证 + pytest。

### 精度基线（与 yt 对比）

1D max|diff| ≈ 2.2e-15（机器零，提速 627×）；2D ≈ 8e-12（float32 精度，提速 24×）；3D 线提取因坐标映射偏差 max|diff| ≈ 0.79。

## 2. 仓内数据读取入口（FlashDataLoader）

```python
from flash.output_pro.loader import FlashDataLoader
dl = FlashDataLoader("chk_file")
c = dl.load(compute_derived=False, extraction_mode="h5py")   # 只取叶子块
dens = c.get("dens"); unit = c.unit("dens")

FlashDataLoader.load_folder(folder, pattern="*chk*")         # 批量加载
FlashDataLoader.load_folder_parallel(folder, pattern="*chk*") # 并行批量
```

提取模式由 `flash/output_pro/extraction_modes.py` 管理：`get_extraction_mode()` / `set_extraction_mode(mode)` / `resolve_extraction_mode(mode)` / `available_extraction_modes()`。

并行工具 `flash/output_pro/parallel.py`：`get_optimal_workers()`（按 CPU/内存自适应）、`parallel_load_folder()`、`parallel_extract_fields()`（单文件多场并行）、`parallel_interpolate()`（时空插值）；模块导入时自动限制 BLAS 线程数防 OpenBLAS 内存爆炸。

## 3. 压缩数据集批读提速 + 时间轴对齐

### 性能根因

h5py 在**压缩**数据集上逐行/fancy 行访问，每次解压包含该行的整个 chunk（可达数 MB～GB）。数 GB 的 FLASH h5 文件逐行访问 371 次累计数十秒。

### 修复（两步，必做）

```python
import h5py, numpy as np
with h5py.File(path, "r") as f:
    tg = f["metadata"]["global_time_grid_s"][()] * 1e9   # s → ns
    tele = f["cases"][case]["fields"]["tele"]            # lazy dataset
    rows = np.argmin(np.abs(tg[None, :] - t[:, None]), axis=1)
    tele_all = tele[rows]      # ★ 一次性批量读入 (NT, NX)，提速 10–100 倍
```

**行对齐（正确性，不可漏）**：h5 全时间轴通常覆盖完整仿真时长，而截取后的 `t` 只有部分点。若循环用 `tele[i]`（i=0..NT-1），实际读到全时间轴前 NT 行，**错位数十行 ≈ 0.1 ns 量级**，梯度拟合/物理量会出现数量级错误。必须用 `np.argmin(np.abs(tg - t))` 算正确索引再批读。

验收：修复后物理量应与名义定义法吻合（<5%）；先修对齐再修性能，否则"快但仍错"。

## 4. float32 → float64 CV 溢出修复

FLASH 4.8 输出 HDF5 为 **float32**。`nele ~ 1e23` 时 `np.std(nele)` 内部平方达 1e46，超出 float32 上限 3.4e38 → **inf** → CV=inf → 下游 Pareto 排序崩溃。

```python
# ❌ 错误（float32 溢出）
cv = float(np.std(field) / np.mean(field))
# ✅ 正确（先转 float64 防溢出）
cv = float(np.std(field.astype(np.float64)) / np.mean(field))
```

排查：`grep -rn "np\.std\|np\.var" --include="*.py"`，所有统计调用点逐一核对输入 dtype（`np.asarray(x, dtype=np.float64)` 亦可）。

验证：

```python
print(np.std(nele[0]))                        # float32 → inf（错误）
print(np.std(nele[0].astype(np.float64)))     # float64 → 有限值（正确）
```

## 5. 排查清单

- [ ] profile 定位：`cProfile` + `pstats` 看 `dataset[...]` 是否占 >50% 时间
- [ ] 行对齐验证：打印 `tg[:5]` 与 `t[:5]`，有偏移就必须 `argmin` 对齐
- [ ] h5py 打不开 ≠ 损坏：先查字节数/传输完整性（见 skill `flash-hpc-fetch` T5）
- [ ] 所有 `np.std/np.var` 前确认 dtype 已转 float64
- [ ] 提取模式与数据维度匹配（2D Cartesian 未实现会抛错）

## 关联资源

- `flash/output_pro/README.md`、`flash/output_pro/loader/README.md`、`flash/output_pro/hdf5pro/README.md`
- skill `flash-flychk-history`（h5py 提取的消费方）、`flash-hpc-fetch`（结果下载完整性）
