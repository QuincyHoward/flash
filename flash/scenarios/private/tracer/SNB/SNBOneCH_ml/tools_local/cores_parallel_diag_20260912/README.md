# cores_parallel_diag_20260912

2026-09-12 NC-E 核数短时测试（131/192/256 三作业并行）的一次性诊断脚本归档。

> ★ 原始副本仍在 `C:\Users\Administrator\`（未删除，沙箱阻断 unlink）。

| 脚本 | 用途 |
|---|---|
| `_layout_probe.py` | 勘察 FLASH `+ug` chk 的 HDF5 布局（发现 `coordinates` 是块中心） |
| `_topo_probe.py` | 验证块拓扑: 块宽均匀、`refine level` 全为 1 |
| `_analyze_cores2.py` | **修正版**健康判据分析器（质量守恒 1e-16~1e-15） |
| `_perf5.py` | 逐步日志稳健解析（按 `|` 切分，不用大正则） |
| `_timing_final.py` | 由 sacct Elapsed 推导 s/step 与到 tmax 的剩余成本 |
| `_sacct2/3/4.py` | 查询 SLURM 计时与部署目录时间戳 |
| `_make_plot.py` | 生成 PPT 级性能图（6 面板 + 剖面图） |
