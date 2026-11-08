# scenarios/public/sandwich

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：多层 sandwich 靶场景族（1D 激光烧蚀，公开可分享）

## 场景清单

| 场景 | 物理构型 | 说明 |
|---|---|---|
| [thin_layer_sandwich_si](thin_layer_sandwich/README.md) | Si(0.4µm)/CH(8µm)/He，5e14 W/cm² 双束 | 新 EOS 表；**已接入批量提速**（batch_adapter + PF；实测最优打包 12×4=196.5 步/s，见其[探索报告](thin_layer_sandwich/超算并行提速方案探索报告.md)） |
| [grad_dens_sandwich](grad_dens_sandwich/README.md) | HE-CH-Si-CH-HE 渐变密度 CH 靶 | 超高斯脉冲 |

## 快速使用

```bash
# 单次运行（WSL 本地或超算，auto = 平台自适应）
python <场景目录>/run.py --tmax 1e-11        # 极短验证
python -m flash.scenarios.core.entry.cli run thin_layer_sandwich_si

# 超算批量提速（功率因子扫描；方案缺省 = 单节点单任务）
python -m flash.flash_run.remote.batch.runner \
    --adapter flash.scenarios.public.sandwich.thin_layer_sandwich.batch_adapter:ADAPTER \
    run --overrides-json '[{"power_factor":1.0},{"power_factor":2.0}]'
```

运行产物：各场景 `runs*/`（本仓库内）与远端共享盘 `flash_output/<场景名>/`。

**上级导航**：[../README.md](../README.md)
