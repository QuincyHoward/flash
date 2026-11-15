# scenarios/public/Fusion/laserfusion

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：激光聚变专题公开场景族（四种驱动构型几何验证）

**内容导航**（编组层，场景见各自 README）：
- `IndirectDrive/`：Hohlraum_AuCH 间接驱动黑腔几何验证（`hohlraum_auch`，已验证）
- `DirectDrive/`：CH_Capsule 直接驱动自由靶丸几何验证（`direct_drive_ch`，已验证）
- `HybridDrive/`：Hohlraum_Spherical 混合驱动球腔几何验证（`hybrid_hohlraum`，已验证）
- `DoubleConeIgnition/`：DCI_DoubleCone 双锥对撞点火几何验证（`dci_double_cone`，已验证）

四个场景统一 2D rz 柱坐标 + tmax=1e-13 s 极短运行 + MGD 10 群同源 EOS 表
（He/CH/Au，`gen_hohlraum10.py` 生成），几何判据由各自 runner 自动定量核对。

**上级导航**：[../../README.md](../../README.md)
