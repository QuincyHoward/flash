# flash/_core — 内置迷你核心层

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

## 1. 职责定位

flash 包的**基础层**：仿真器抽象契约、dataclass 仿真数据模式、模拟器注册表、全库路径/身份解析唯一入口、运行配置（FlashConfig）与凭据管理。全部只依赖 stdlib（Fernet 为凭据可选依赖），自包含、可被 `deploy/` 独立脚本直接导入。**不包含**任何仿真执行逻辑（执行在 `flash_run/`，场景在 `scenarios/`）。

## 2. 目录地图

```
_core/
├── __init__.py           包导出：契约 + schema + 凭据 + FlashConfig
├── config.py             FlashConfig 运行配置（local/ssh 模式、超算硬件参数）
├── interface.py          BaseSimulator 抽象契约
├── schema.py             SimulationRequest/Result 等 dataclass（免 pydantic）
├── registry.py           极简模拟器注册表
├── paths.py              ★ 全库统一路径/身份解析入口（硬编码唯一收纳处）
├── credentials_legacy.py ⚠️ 旧单体凭据实现（不可达遗留，勿 import）
├── config.py 的落盘位置：~/.physimx/flash_config.json（用户目录，不入库）
└── credentials/          凭据管理子包 → 详见 credentials/README.md
```

## 3. 模块清单

| 文件 | 行数 | 职责 | 关键入口 | 备注 |
|---|---|---|---|---|
| `__init__.py` | 40 | 包导出 | `BaseSimulator`、`FlashConfig`、凭据 API | |
| `config.py` | 115 | 运行配置（FlashConfig dataclass：mode/ssh_*/nodes/ppn/walltime/flash_exe_path） | `get_default_config()`、`FlashConfig.load/save`、`main()`（`flash-setup` 入口） | 2026-11-05 自原 config/ 包迁入；超算主机权威来源是 hpc_accounts.json（见 credentials/README §4），本模块 ssh_* 字段仅为临时覆盖 |
| `interface.py` | 89 | `BaseSimulator` 抽象基类（run/capabilities 契约） | `BaseSimulator` | |
| `schema.py` | 117 | 仿真请求/结果/能力卡 dataclass | `SimulationRequest`、`SimulationResult`、`CapabilityCard` | 免 pydantic |
| `registry.py` | 35 | 模拟器注册表（名字→实例） | `register`、`get_simulator` | |
| `paths.py` | 191 | 全库统一路径/身份解析（用户名/家目录/WSL/超算目录），解析顺序 env→~/.physimx→探测→显式报错 | `repo_root()`、`hpc_ssh_username()`、`hpc_target_dirs()` | 2026-10-27 新增；新代码禁止再写死路径 |
| `credentials_legacy.py` | 1126 | 旧单体凭据实现（被 credentials/ 包取代） | — | **不可达遗留，勿 import**；无文档示例 |
| `credentials/`（13 模块） | ~3400 | 凭据管理（API key/SSH/加密存储） | `interactive_menu` | → [credentials/README.md](credentials/README.md) |

## 4. 快速上手

```python
from flash._core import (
    FlashConfig,          # 运行配置
    BaseSimulator,        # 仿真器契约
    SimulationRequest, SimulationResult,   # 仿真数据模式
    get_credential_manager, mask_secret,   # 凭据
)

cfg = FlashConfig.load()          # 缺省文件时返回默认配置
print(cfg)                        # FlashConfig(mode='local', ssh=N/A)
```

```bash
python -m flash._core.config      # 查看并保存当前配置（flash-setup 入口）
python -m flash._core.credentials.manage   # 凭据统一菜单（flash-cred）
```

## 5. 与其他模块的关系

```
scenarios/core/engine.simulator ──实现──> interface.BaseSimulator
flash_run/remote.session        ──读取──> credentials/hpc_config（超算连接唯一来源）
deploy/ 独立脚本                ──导入──> paths.repo_root()/hpc_target_dirs()
flash/__init__.py               ──再导出──> FlashConfig/get_default_config（顶层 API 不变）
```

## 6. 测试入口

本层随仓库基线主套验证（`pytest test/`，313 passed 基线的一部分）；无专属测试目录。

## 7. 已知限制 / 遗留项

- `credentials_legacy.py`（1126 行）为不可达遗留，**勿 import、勿新增依赖**；
- `config.py` 的 `ssh_*` 字段与 hpc_accounts.json 的权威关系见 [credentials/README.md §4](credentials/README.md)；建议 ssh_* 留空走 JSON。

## 8. 导航

上级：[../../README.md](../../README.md)（仓库根 README） · 子包：[credentials/README.md](credentials/README.md) · 下游：[../flash_run/README.md](../flash_run/README.md)、[../scenarios/README.md](../scenarios/README.md)
