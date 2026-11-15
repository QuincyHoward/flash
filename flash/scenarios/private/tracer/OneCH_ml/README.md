# OneCH_ml — 纯 CH 多薄层示踪靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**纯 CH**，无 V 屏蔽层）；内置 1e-11 极短验证；`FLASH_RUN_MODE=hpc` 走超算

## 物理构型

- 由 [VCH_ml](../VCH_ml/README.md) 场景派生（2026-08-30）：结构/物种/几何完全一致，**唯一物理差异是 shld 材质 V → CH**（ρ 6.11 → 1.0 g/cm³，EOS/不透明度表 V-BADGER-TOPS → CH-QC-1-001）——靶体成为纯 CH，shld 物种标记仅用于诊断追踪该表面层
- 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096
- 单光束 0.351 µm 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
- **8 物种 12 区分层**：delta=0.1 µm，L1=1 µm，L2=2 µm，L3=3 µm，L4=4 µm，L6=6 µm，D=50 µm

## 运行

```bash
python -m flash.scenarios.core.entry.cli run OneCH_ml
# 内置 1e-11 极短验证模式；FLASH_RUN_MODE=hpc 切超算
```

## 家族关系

VCH_ml（V 屏蔽）· OneC_ml（纯 C）· OneSi_ml（纯 Si）· `_F` 关辐射变体 · CHTi/TiTi/VTi（含 Ti 示踪 1/2/3 µm 变体）——详见 [../README.md](../README.md)。

**上级导航**：[../README.md](../../../README.md)
