# VCH_ml — V/CH 多薄层示踪靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（CH 基体 + **V 屏蔽层**）——tracer 多薄层家族的基准构型

## 物理构型

- 原名 `layer_tracer_CH_ml`（2026-08-30 更名 VCH_ml）；由 layer_tracer_CH 模板派生：单一示踪薄层 → 多个示踪薄层
- **shld 表面屏蔽层 = V**（V-BADGER-TOPS.cn4，ρ=6.11 g/cm³，A=50.9415，Z=23）
- 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096
- 单光束 0.351 µm 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
- **8 物种 12 区分层**：delta=0.1 µm，L1=1 µm，L2=2 µm，L3=3 µm，L4=4 µm，L6=6 µm，D=50 µm（示踪层间距均为 samp）——供 Ti Kα/X-ray 多点示踪诊断

## 运行

```bash
python -m flash.scenarios.core.entry.cli run VCH_ml    # 统一 CLI
# 或场景内直跑；WSL/hpc 由 RUN_MODE / FLASH_RUN_MODE 控制
```

## 家族关系（差异仅 shld 材质）

| 场景 | shld 材质 | 备注 |
|---|---|---|
| **本场景 VCH_ml** | V 6.11 | 基准 |
| [OneCH_ml](../OneCH_ml/README.md) | CH 1.0 | 纯 CH 靶体 |
| [OneC_ml](../OneC_ml/README.md) / [OneSi_ml](../OneSi_ml/README.md) | 纯 C / 纯 Si | 单一材料烧蚀对照 |
| `_F` 变体 | 同上 | 关辐射（RADIATION_OFF） |
| [CHTi](../CHTi/README.md) / [TiTi](../TiTi/README.md) / [VTi](../VTi/README.md) | CH / Ti / V | 另含 Ti 示踪深度 1/2/3 µm 三变体 |

**上级导航**：[../README.md](../../../README.md)
