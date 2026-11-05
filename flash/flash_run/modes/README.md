# flash_run/modes — 运行模式执行体

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

**一句话职责**：三种运行模式（wsl / hpc-remote / hpc-insitu）的执行体唯一归属——场景层只声明「怎么跑」，本包实现「真的跑」。

## 文件清单

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `__init__.py` | 14 | 子包声明（2026-10-22 自 scenarios 迁入） | — |
| `runner.py` | 1051 | **统一场景运行器**：WSL 执行体（WslSpec）与超算远程执行体（HpcRunner/HpcSpec）唯一归属；模式归一化与平台探测 | `resolve_run_mode`、`HpcRunner`、CLI |
| `hpc_insitu.py` | 237 | hpc-insitu 模式编排（登录节点判定、就地收集） | `run_insitu`、`is_hpc_login_node`、`collect_local` |

## 使用入口

本包不直接调用——由执行契约 `flash_run/execution.py` 与场景层（`scenarios/core/engine.simulator`）经 `scenarios/core/runner.py` 兼容壳调度。运行入口见上级 [../README.md](../README.md) §快速开始。

## 已知边界

- `is_hpc_login_node()` 与 `probe_insitu` 仍为两份实现，待合一；
- wsl 模式的工程铁律（wsl.exe 命令串拆分、ext4 工作目录）见上级 README §工程铁律。

**上级导航**：[../README.md](../README.md)
