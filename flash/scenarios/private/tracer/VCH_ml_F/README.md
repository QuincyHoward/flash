# VCH_ml_F — V/CH 多薄层（关辐射变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：[VCH_ml](../VCH_ml/README.md) 的 **F 变体**——关闭辐射（RADIATION_OFF），用于隔离辐射输运对示踪层演化的影响

## 与基准场景的差异

- 几何/物种分层/激光/网格与 VCH_ml **完全一致**（shld=V 6.11 g/cm³；8 物种 12 区；0.351 µm 单光束 82 点脉冲）
- **唯一差异**：辐射关闭（F = Flux-off 变体语义，同 CHTi_F 家族约定）
- 典型用途：FL-SH / SNB 热传导对比中排除 MGD 辐射扩散通道的干扰

## 运行

```bash
python -m flash.scenarios.core.entry.cli run VCH_ml_F
```

**上级导航**：[../README.md](../../../README.md)
