# OneSi_ml — 纯 Si 多薄层示踪靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**纯 Si** 单一材料，无高 Z 屏蔽层）

## 物理构型

- 由 OneCH_ml 系列派生的单一材料对照场景（scene.json：纯 Si 多薄层 ML 群组）——shld 表面层材质为**硅 Si**（其余 tar*/samp 分层同族），与 Ti 示踪诊断（Si Kα 线）直接衔接，用于 warm-dense Si 的烧蚀/加热规律对照
- 几何/物种分层/激光与家族一致：域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，8 物种 12 区（delta=0.1 µm…D=50 µm），0.351 µm 单光束 82 点脉冲

## 运行

```bash
python -m flash.scenarios.core.entry.cli run OneSi_ml
```

## 家族关系

`_F` 变体（[OneSi_ml_F](../OneSi_ml_F/README.md)）关辐射；同族对照：[OneCH_ml](../OneCH_ml/README.md)、[OneC_ml](../OneC_ml/README.md)、[VCH_ml](../VCH_ml/README.md)；SNB 版见 [SNB](../SNB/README.md) 家族（SNBVTi*_ml 等）。

**上级导航**：[../README.md](../../../README.md)
