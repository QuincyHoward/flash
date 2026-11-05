# core/engine — 引擎运行族

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：场景声明的执行引擎与共享计算。

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `simulator.py` | 1235 | `FlashSimulatorEngine` 全管线引擎（WSL 执行 + 插值 + 输出管线；本地/远程目标裁决提示） | — |
| `base.py` | 69 | `SimulationScenario` 声明式场景数据类（钩子：build_par / build_grid / interpolate） | — |
| `interpolator.py` | 169 | 共享时空网格插值 | — |
| `hints.py` | 71 | 极短验证提示 | — |

**上级导航**：[../README.md](../README.md)（core）
