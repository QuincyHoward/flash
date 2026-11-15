# VTi — V 屏蔽 + Ti 示踪层家族（1/2/3 µm 深度三变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**V 屏蔽层** + 不同深度 Ti 示踪层）——FL-SH/SNB 热传导对比与 Ti 层预热研究的核心场景族

## 变体清单

| 变体 | Ti 示踪层位置 | scene.json |
|---|---|---|
| `VTi1`（VTi1.py） | tar1 = Ti @1 µm | scene.VTi1.json |
| `VTi2`（VTi2.py） | tar2 = Ti @2 µm | scene.VTi2.json |
| `VTi3`（VTi3.py） | tar3 = Ti @3 µm | scene.VTi3.json |

- 由 [TiTi](../TiTi/README.md)1 场景派生（2026-10-17）：**唯一物理差异是 shld 层材质 Ti → V**（V-BADGER-TOPS.cn4，ρ=6.11 g/cm³，A=50.9415，Z=23），其余（几何/物种标记/激光/辐射/Ti 示踪层深度）完全一致
- 用途：V 高 Z 屏蔽层烧蚀 + 深度分辨 Ti 示踪；VTi2um 跨模型读取需注意 FL-SH 的 `fllm` 已被覆写为 λ₃，SNB 保留自由流 `q_fs`（不可直接混用）

## SNB 版本

同构型的 SNB 热传导版本见 [SNB](../SNB/README.md) 家族（SNBVTi1um/2um/3um 及 x 域扩展变体，仅超算运行）。

## 运行

```bash
python -m flash.scenarios.core.entry.cli run VTi1    # 或 VTi2 / VTi3
```

**上级导航**：[../README.md](../../../README.md)
