# OneC_ml_F — 纯 C 多薄层（关辐射变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：[OneC_ml](../OneC_ml/README.md) 的 **F 变体**——关闭辐射（RADIATION_OFF），隔离辐射输运通道

- 几何/物种分层/激光与 OneC_ml 完全一致（纯 C 多薄层）
- 唯一差异：辐射关闭——与 OneCH_ml_F/OneSi_ml_F/VCH_ml_F 构成完整的"纯材料 × 关辐射"对照矩阵
- 典型用途：热传导模型（FL-SH / SNB）对比时排除 MGD 辐射扩散

```bash
python -m flash.scenarios.core.entry.cli run OneC_ml_F
```

**上级导航**：[../README.md](../../../README.md)
