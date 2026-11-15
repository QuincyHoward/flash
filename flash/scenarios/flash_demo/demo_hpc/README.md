# flash_demo/demo_hpc — 超算批量运行遗留 Demo 脚本

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：LaserSlab1D 超算批量运行演示脚本集（v1.0 时期遗留，非注册场景——无 scene.json）

**状态**：⚠️ 历史遗留。其"按功率因子批量提交 + 结果对比"的思想已由
`flash/flash_run/remote/batch/`（场景无关批量模块）正式实现——新需求请直接使用：

```bash
python -m flash.flash_run.remote.batch.runner --adapter "<场景模块>:ADAPTER" \
    run --overrides-json '[{"power_factor":2.0}]'
```

**内容清单**：

| 文件 | 说明 |
|---|---|
| `laserslab1d_hpc_demo_batch.py` | 按功率因子批量提交 demo（本目录核心） |
| `laserslab1d_supercomputer_demo.py` | 单次超算运行 demo |
| `remote_ssh_helper.py` / `remote_analysis.py` / `remote_plot_script.py` | 远程执行/分析/绘图辅助 |
| `_plot_utils.py` / `com_hpc.sh` | 绘图工具与作业脚本样例 |

**上级导航**：[../README.md](../README.md)
