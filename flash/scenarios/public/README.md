# scenarios/public

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：public 公开场景区——官方可分享的一键场景（私有科研场景不在本区，见 `../private/`，此处不做介绍）

## 场景族清单

| 目录 | 场景 | 说明 |
|---|---|---|
| [sandwich/](sandwich/README.md) | thin_layer_sandwich_si · grad_dens_sandwich | 多层靶 1D 激光烧蚀；thin_layer 已接入**超算批量提速** |
| [center_evolution/](center_evolution/README.md) | ch_center · ch_center_t | 中心演化专题（1D LaserSlab CH 中心层） |
| [Fusion/laserfusion/](Fusion/laserfusion/README.md) | hohlraum_auch · direct_drive_ch · hybrid_hohlraum · dci_double_cone | 间接/直接/混合驱动与双锥对撞四构型几何验证（2D rz） |
| [Fusion/zpinch/](Fusion/README.md) | zpinch_beliner | Be-liner 圆柱 Z 箍缩 MHD 几何验证（1D 圆柱） |
| `runs_*/` | — | 各场景运行产物目录（非场景） |

## 快速开始

```bash
python <场景目录>/run.py                     # 一键运行（缺省 --mode auto）
python -m flash.scenarios.core.entry.cli run <场景名>   # 统一入口
python -m flash.scenarios.core.entry.cli list            # 列出可用场景
```

超算批量提速、新建/整理场景等完整工作流见 [../README.md](../README.md)。

**上级导航**：[../README.md](../README.md)
