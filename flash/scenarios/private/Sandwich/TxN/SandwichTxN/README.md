# sandwich_txn — CH/Si/CH 三明治靶（FL-SH 基线场景）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：CH(50µm)/Si(10µm)/CH(50µm) 三明治靶 + 极低密度 He 填充（1D，5×10¹⁴ W/cm²；auto = 平台自适应）——FL-SH/SNB 热传导对比与超算批量提速能力的**首验证场景**

## 物理构型

- 1D 笛卡尔域 ±450 µm；Si 芯（ρ=2.33）两侧致密 CH（1.0 g/cm³）+ 泡沫 CH 层；He 低密度填充
- 双束 0.351 µm 激光（3.183×10¹⁴ W/cm² 峰值/束）；lrefine 1–10（Si 区最小格距 ~0.014 µm）
- 关键诊断位：烧蚀前沿 x_a、临界密度面 x_c（n_c≈9.05×10²¹ cm⁻³）、激波前沿 x_s

## 使用入口

```bash
# 场景自带 CLI（自包含单文件 sandwich_txn.py）
python sandwich_txn.py gen --force                 # 生成输入（带释义 par + 预诊断图）
python sandwich_txn.py gen --pf 2.0                # 功率因子 PF=2.0（I0 = PF×3.183e14）
SANDWICH_TXN_TMAX=1e-11 python sandwich_txn.py run --mode wsl --nproc 4   # 极短验证

# 统一 CLI
python -m flash.scenarios.core.entry.cli run sandwich_txn
```

## 超算批量提速（首个落地场景）

- **薄壳**：`scripts/hpc_pf_batch.py`（plan/upload/submit/poll/collect/calc + `--plan` 可选）——委托 `flash_run/remote/batch`；适配器 `scripts/batch_adapter.py`
- **批次数据**：`runs/pf_batch/<batch_id>/`（manifest/stats/download）+ `leaderboard.json`（实测节点价值榜）
- **校准结论**（E1/E2 实测，2026-11-08）：单任务峰 32r=55.4 步/s；最优打包 12×4=120.3 步/s（3.3× 基线）

## 文档与产物

- [docs/超算并行提速方案计划.md](docs/超算并行提速方案计划.md)（改造点定义）/ [docs/超算并行仿真提速报告.md](docs/超算并行仿真提速报告.md)（五轮搜索 + E1/E2 全量实录）
- `scripts/`：prediag / si_history / analyze_output / plot_refine_levels 等分析脚本
- 历史归档：`temp_delete/`（旧版批量脚本 .orig）

**上级导航**：[../README.md](../../../../README.md)
