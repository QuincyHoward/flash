# thin_layer_sandwich_si

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：Si(0.4µm)/CH(8µm)/He 三层靶激光烧蚀（新 EOS 表；5e14 W/cm² 双束；auto = 平台自适应）

**身份**：场景名 `thin_layer_sandwich_si`（由 scene.json 位置派生，kind=engine）。整理/移动本目录无需改任何代码——身份随目录名自动跟随（见 scenarios/README「位置优先」章）。

**使用入口**：`python run.py [--tmax 1e-11]` · 统一入口 `python -m flash.scenarios.core.entry.cli run thin_layer_sandwich_si`

## 关键参数（defaults_si.py）

| 参数 | 默认值 | 说明 |
|---|---|---|
| tmax | 1.2e-9 s | 激光 1 ns 方波 + 0.1 ns 收尾 |
| 激光 | 5e14 W/cm² ×2 束（λ=0.351µm） | `DEFAULT_LASER_PULSE`；PF 乘子见下 |
| 网格 | nblockx=8 · nxb=16 · lrefine 1–8 | 域 ±450 µm |
| 初始温度 | 3500 K（九区 sim_te*/tion/trad） | 新 EOS 表低温扩散稳定性要求（290 K 会负 dt） |
| EOS/opacity | Z14/Z06-Z01/Z02 cn4（2026-07-08 版） | sim_input_si 内置 |

## 超算批量提速（2026-11-08 接入 flash_run.remote.batch）

- **适配器**：`batch_adapter.py`（实现 SceneBatchAdapter 协议；`power_factor` 缩放激光峰值，PF=1.0 → 5e14）
- **一键批量**：`python -m flash.flash_run.remote.batch.runner --adapter flash.scenarios.public.sandwich.thin_layer_sandwich.batch_adapter:ADAPTER run --overrides-json '[{"power_factor":2.0}]'`
- **方案选择**：`--plan` 显式（方案库为纯分配拓扑 p12x4/p6x8/p1x24…）；省略 = 默认单节点单任务（p1x12，seq+shared 复用整节点）
- **实测校准**（同任务 16 399 步，详见 [超算并行提速方案探索报告.md](超算并行提速方案探索报告.md)）：单任务峰 24r=87.7 步/s；最优打包 12×4=196.5 步/s（3.1× 基线）；榜单 `runs/pf_batch/leaderboard.json`
- **自动早停**：投影终值 <90%×榜单最优自动取消（`--no-early-cancel` 关闭）

**上级导航**：[../README.md](../README.md)
