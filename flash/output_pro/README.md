# output_pro — FLASH 输出处理包

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

## 1. 职责定位

FLASH 仿真输出的通用处理三层体系：**HDF5 底层 I/O**（`hdf5pro`，AMR 块解析与派生量计算）→ **结构化加载**（`loader`，FlashDataLoader/FlashDataContainer）→ **可视化**（`plotter`，自适应 1/2/3D 绘图）。外加并行加速、提取模式注册表与 PlasmaPy 单位桥。**不含**仿真执行逻辑（在 `flash_run/`）。

## 2. 目录地图

```
output_pro/
├── __init__.py            包导出（FlashDataLoader/FlashPlotter 等统一入口）
├── hdf5pro/               核心底层 → 详见 hdf5pro/README.md
├── loader/                结构化加载 → 详见 loader/README.md
├── plotter/               可视化 → 详见 plotter/README.md
├── extraction_modes.py    提取方案模式注册表（yt-style 等）
├── parallel.py            并行处理工具（多进程批量读取）
├── plasmapy_bridge.py     PlasmaPy 适配层（方案 A 松耦合）
├── PlasmaPy/              ⚠️ vendored 外部包（PlasmaPy 2026.2.0，git tag 管理）——勿改动
├── docs/                  7 篇专题文档（workflow/usage/api/自定义变量/性能/PlasmaPy）
├── FLASH物理量说明.md      物理量字典说明（795 行）
├── inputfiles/            1d/2d/3d 数据目录（当前空）
└── test/                  测试套件（57 passed）→ 详见 test/README.md
```

## 3. 模块清单（包根级）

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `__init__.py` | 69 | 包总览与统一导出 | — |
| `extraction_modes.py` | 103 | 数据提取方案模式注册表 | `get/set/resolve_extraction_mode`、`available_extraction_modes` |
| `parallel.py` | 581 | 并行处理：按内存/文件大小自适应 worker 数 | `ParallelProcessor`、`get_optimal_workers` |
| `plasmapy_bridge.py` | 319 | PlasmaPy 单位桥（松耦合：未安装可降级） | `to_quantity`、`require_plasmapy` |
| `conftest.py` | 120 | pytest 共享 fixtures（合成测试数据自举） | `sample_h5_file` 等 |

## 4. 快速上手

```python
from flash.output_pro import FlashDataLoader, FlashPlotter

loader = FlashDataLoader("sim_output/chk_0039")
data = loader.load("dens")             # 结构化容器（含单位/派生量）

plotter = FlashPlotter()
plotter.plot(data)                     # 自适应 1/2/3D
```

```bash
python -m pytest flash/output_pro -q --ignore=flash/output_pro/PlasmaPy   # 57 passed
```

## 5. 与其他模块的关系

上游：`flash_run/modes/runner.py`（产物落盘）← **本包** → 下游：场景分析脚本（`scenarios/*/analysis`）、`docs/` 专题指南。`plasmapy_bridge` 引用 vendored `PlasmaPy/`（git tag `v2026.2.0`，仅松耦合——未安装时功能降级不崩溃）。

## 6. 测试入口

`python -m pytest flash/output_pro -q --ignore=flash/output_pro/PlasmaPy` → **57 passed**（2026-11-05 基线）。详见 [test/README.md](test/README.md)。

## 7. 已知限制 / 遗留项

- `docs/` 5 篇主文档停在 2026-07-04，早于 `plasmapy_bridge`/`extraction_modes`/`parallel` 加入——以代码为准，新增能力见各模块 docstring；
- `inputfiles/` 当前为空（运行时由场景产物填充）。

## 8. 导航

上级：[../README.md](../../README.md)（仓库根） · 子包：[hdf5pro/](hdf5pro/README.md) / [loader/](loader/README.md) / [plotter/](plotter/README.md) / [test/](test/README.md)
