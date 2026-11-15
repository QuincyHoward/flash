# CHTi_F — CH 屏蔽 + Ti 示踪层家族（关辐射变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：[CHTi](../CHTi/README.md) 家族的 **F 变体**（关辐射 RADIATION_OFF=True）

## 变体清单

| 变体 | 与 CHTi 的关系 |
|---|---|
| `CHTi1_F` | CHTi1（Ti @1 µm）关辐射 |
| `CHTi2_F` | CHTi2（Ti @2 µm）关辐射 |
| `CHTi3_F` | CHTi3（Ti @3 µm）关辐射 |

- 物理（几何/物种/激光/Ti 深度）与对应 CHTi 场景完全一致，唯一差异是辐射关闭——用于隔离 MGD 辐射扩散对 Ti 示踪层预热与 Kα 线强的影响
- 由 OneCH_ml 系列派生（2026-08-31，与 CHTi 同批）

## 运行

```bash
python -m flash.scenarios.core.entry.cli run CHTi1_F    # 或 CHTi2_F / CHTi3_F
```

**上级导航**：[../README.md](../../../README.md)
