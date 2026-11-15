# core/hpc — 超算提交族

> 最后核对：2026-11-11

**一句话职责**：场景超算提交的声明与胶水。

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `hpc_job.py` | ~200 | 场景超算提交声明（唯一事实源 = 各场景 `scene.json` 的 `hpc` 节，`./` 相对路径随场景目录移动自动跟随；本模块仅做 manifest 并表 + 别名回退查询，内置表已清零） | `list_scene_hpc_jobs` |
| `submit_cli.py` | 361 | `cli submit` 的提交胶水（本地生成 + 上传 + sbatch；input_rel_dir/gen_script 仓库根相对） | — |

**上级导航**：[../README.md](../README.md)（core）
