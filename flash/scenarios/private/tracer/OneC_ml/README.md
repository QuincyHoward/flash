# OneC_ml — 纯 C 多薄层示踪靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**纯 C** 单一材料，无高 Z 屏蔽层）

## 物理构型

- 由 OneCH_ml 系列派生的单一材料对照场景（scene.json：纯 C 多薄层 ML 群组）——shld 表面层材质为**碳 C**（其余 tar*/samp 分层同族），用于与 V/CH/Si 屏蔽场景对照烧蚀与示踪层加热规律
- 几何/物种分层/激光与家族一致：域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，8 物种 12 区（delta=0.1 µm…D=50 µm），0.351 µm 单光束 82 点脉冲

## 运行

```bash
python -m flash.scenarios.core.entry.cli run OneC_ml
```

## 家族关系

`_F` 变体（[OneC_ml_F](../OneC_ml_F/README.md)）关辐射；同族对照：[OneCH_ml](../OneCH_ml/README.md)（纯 CH）、[OneSi_ml](../OneSi_ml/README.md)（纯 Si）、[VCH_ml](../VCH_ml/README.md)（V 屏蔽基准）。

**上级导航**：[../README.md](../../../README.md)
