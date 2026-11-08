# TiTi — Ti 屏蔽 + Ti 示踪层家族（1/2/3 µm 深度三变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**Ti 屏蔽层** + 不同深度 Ti 示踪层——屏蔽层与示踪层同材质）

## 变体清单

| 变体 | Ti 示踪层位置 | scene.json |
|---|---|---|
| `TiTi1`（TiTi1.py） | tar1 = Ti @1 µm | scene.TiTi1.json |
| `TiTi2`（TiTi2.py） | tar2 = Ti @2 µm | scene.TiTi2.json |
| `TiTi3`（TiTi3.py） | tar3 = Ti @3 µm | scene.TiTi3.json |

- 由 [CHTi](../CHTi/README.md)1 场景派生（2026-09-08）：**唯一物理差异是 shld 层材质 CH → Ti**（Ti-BADGER-TOPS.cn4，ρ=4.54 g/cm³，A=47.867，Z=22——与 Ti 示踪层同材质同密度），其余（几何/物种标记/激光/辐射）完全一致
- 用途：高 Z 全 Ti 靶的烧蚀规律 + 深度分辨示踪——shld 层本身也是 Ti 示踪介质

## 关联

无独立 _F 变体；V 屏蔽对照见 [VTi](../VTi/README.md)，CH 屏蔽对照见 [CHTi](../CHTi/README.md)。

## 运行

```bash
python -m flash.scenarios.core.entry.cli run TiTi1    # 或 TiTi2 / TiTi3
```

**上级导航**：[../README.md](../../../README.md)
