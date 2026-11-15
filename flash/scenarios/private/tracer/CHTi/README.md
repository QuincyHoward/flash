# CHTi — CH 屏蔽 + Ti 示踪层家族（1/2/3 µm 深度三变体）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（纯 CH 基体，**不同深度单独埋 Ti 示踪层**）——Ti Kα 示踪诊断的主力场景族

## 变体清单（每深度一个脚本）

| 变体 | Ti 示踪层位置 | scene.json |
|---|---|---|
| `CHTi1`（CHTi1.py） | tar1 = Ti @1 µm | scene.CHTi1.json |
| `CHTi2`（CHTi2.py） | tar2 = Ti @2 µm | scene.CHTi2.json |
| `CHTi3`（CHTi3.py） | tar3 = Ti @3 µm | scene.CHTi3.json |

- 由 [OneCH_ml](../OneCH_ml/README.md) 派生（2026-08-31）：shld 为 CH（无 V 屏蔽层），tar* 中指定深度层改为 **Ti 示踪层**（Ti-BADGER-TOPS.cn4，ρ=4.54 g/cm³），其余 tar*/samp 仍为 CH
- 几何/物种分层/激光与 tracer 多薄层家族一致（8 物种 12 区，0.351 µm 单光束 82 点脉冲）

## 关辐射变体

[CHTi_F](../CHTi_F/README.md)：CHTi1_F/CHTi2_F/CHTi3_F 对应关辐射变体（RADIATION_OFF=True）。

## 运行

```bash
python -m flash.scenarios.core.entry.cli run CHTi1    # 或 CHTi2 / CHTi3
```

**上级导航**：[../README.md](../../../README.md)
