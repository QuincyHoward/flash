# core/entry — 统一入口族

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：场景系统的两个命令入口。

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `cli.py` | 174 | 统一 CLI：`list / explain / run / submit` | `python -m flash.scenarios.core.entry.cli <cmd> <场景>` |
| `launcher.py` | 60 | 各场景目录 `run.py` 薄启动器的统一实现 | `run_from_dir()` |

**注意**：core 重组后旧路径 `flash.scenarios.core.entry.cli` 已失效（实测 No module named）。

**上级导航**：[../README.md](../README.md)（core）
