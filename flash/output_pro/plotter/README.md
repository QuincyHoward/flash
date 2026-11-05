# output_pro/plotter — 可视化层

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：FLASH 数据的自适应维度绘图（1/2/3D 自动识别）与统一 PPT 友好风格。

## 文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `__init__.py` | 9 | 子包声明 |
| `plot_generator.py` | 702 | `FlashPlotter`（14 方法）：自适应 1/2/3D 绘图、线提取、多帧 |
| `plot_style.py` | 241 | 统一绘图风格（`apply_plot_style`/`new_figure`/中英文标签处理） |

## 使用入口

```python
from flash.output_pro.plotter import FlashPlotter
plotter = FlashPlotter()
plotter.plot(data)          # 数据来自 loader 或 FlashHDF5File
```

**上级导航**：[../README.md](../README.md)
