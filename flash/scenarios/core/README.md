# scenarios/core — 场景框架层

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文

## 1. 职责定位

场景系统的框架层：全树发现（discovery）→ 声明式注册（registry）→ 可执行目录（catalog）→ 统一入口（cli/launcher）→ 引擎执行（simulator）→ 超算提交（hpc_job/submit_cli）。**2026-11-05 功能化重组为 4 子包**；兼容壳与地基原地保留。

## 2. 目录地图

```
core/
├── __init__.py            布局地图 docstring
├── runner.py              兼容壳 → flash_run.modes.runner（125 处引用，勿删）
├── insitu_runner.py       兼容壳 → flash_run.modes.hpc_insitu
├── scene_paths.py         地基：repo_root()/scenarios_root() 官方根定位
├── anchors.py             地基：跨场景数据锚点（_scene_anchors.json）
├── scene_reg/             发现注册族 → README.md
├── entry/                 入口族 → README.md
├── engine/                引擎运行族 → README.md
└── hpc/                   超算提交族 → README.md
```

## 3. 模块清单

| 文件 | 行数 | 职责 | 备注 |
|---|---|---|---|
| `runner.py` | 44 | re-export `flash_run.modes.runner` | 125 处外部引用的兼容壳 |
| `insitu_runner.py` | 29 | re-export `flash_run.modes.hpc_insitu` | 兼容壳 |
| `scene_paths.py` | 62 | 仓库根/包根定位唯一入口 | 取代场景脚本 parents[N] |
| `anchors.py` | 72 | 数据文件逻辑锚点解析 | 表：`flash/scenarios/_scene_anchors.json` |

## 4. 快速上手

```bash
python -m flash.scenarios.core.entry.cli list          # 场景清单
python -m flash.scenarios.core.entry.cli run <场景>     # 执行
```

## 5. 测试入口

`pytest test/scenarios/`（discovery/registry/catalog 等单元测试）+ `test/scenarios/tools/`（工具链门禁）。

## 6. 导航

上级：[../README.md](../README.md) · 子包：[scene_reg/](scene_reg/README.md) / [entry/](entry/README.md) / [engine/](engine/README.md) / [hpc/](hpc/README.md)
