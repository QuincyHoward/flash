# output_pro/loader — 结构化数据加载层

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：把 FLASH HDF5 原始数据加载为结构化容器（`FlashDataContainer`），提供多文件/多变量批量加载与元数据管理。

## 文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `__init__.py` | 8 | 子包声明 |
| `data_loader.py` | 460 | `FlashDataLoader`（批量 load_folder/load_folders）、`FlashDataContainer`（refine_level/bbox/单位）；支持 use_cell_centers/return_global_coords |

## 使用入口

```python
from flash.output_pro.loader import FlashDataLoader
loader = FlashDataLoader("sim_output/chk_0039")
data = loader.load(["dens", "tele"])
```

**详细文档**：[../docs/output_processors_usage.md](../docs/output_processors_usage.md)

**上级导航**：[../README.md](../README.md)
