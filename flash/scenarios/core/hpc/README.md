# core/hpc — 超算提交族

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：场景超算提交的声明与胶水。

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `hpc_job.py` | 246 | 场景超算提交声明表（内置表 + manifest `hpc` 节按字段合并；路径按 manifest 物理位置动态校正） | `list_scene_hpc_jobs` |
| `submit_cli.py` | 361 | `cli submit` 的提交胶水（本地生成 + 上传 + sbatch；input_rel_dir/gen_script 仓库根相对） | — |

**上级导航**：[../README.md](../README.md)（core）
