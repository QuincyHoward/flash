# scenarios/public

> 最后核对：2026-11-11 · commit d767384

**一句话职责**：public 公开场景区——官方可分享的一键场景（私有科研场景不在本区，见 `../private/`，此处不做介绍）

## 场景族清单

| 目录 | 场景 | 说明 |
|---|---|---|
| [LaserCompression_twoside/](LaserCompression_twoside/README.md) | thin_layer_sandwich_si · grad_dens_sandwich · ch_center · ch_center_t | 双面激光压缩族：sandwich（多层靶）+ center_evolution（中心演化） |
| [Fusion/laserfusion/](Fusion/laserfusion/README.md) | hohlraum_auch · direct_drive_ch · hybrid_hohlraum · dci_double_cone | 间接/直接/混合驱动与双锥对撞四构型几何验证（2D rz） |
| [Fusion/zpinch/](Fusion/README.md) | zpinch_beliner | Be-liner 圆柱 Z 箍缩 MHD 几何验证（1D 圆柱） |
| [LaserAblation_oneside/](LaserAblation_oneside/README.md) | — | 单面激光烧蚀（占位 / 规划中） |
| [UltraLaser/](UltraLaser/README.md) | — | 超强激光（占位 / 规划中） |
| `SimulationMain/` | — | 规划中（暂空目录） |

## 快速开始

```bash
python <场景目录>/run.py                     # 一键运行（缺省 --mode auto）
python -m flash.scenarios.core.entry.cli run <场景名>   # 统一入口
python -m flash.scenarios.core.entry.cli list            # 列出可用场景
```

超算批量提速、新建/整理场景等完整工作流见 [../README.md](../README.md)。

**上级导航**：[../README.md](../README.md)
