# flash/_core/credentials — 凭据管理包

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

## 1. 职责定位

flash 包全部凭据的存储与交互管理：AI API 密钥（DeepSeek/Gitee/PyPI 等）、超算 SSH 多账户多线路、用户名与 Fernet 加密密文。**安全总原则：明文 JSON 只放非敏感基础信息，密码/令牌一律 Fernet 加密存 `credentials.enc`；PyPI 分发不携带任何用户账户信息。**

## 2. 目录地图

```
credentials/
├── __init__.py           包导出（get_credential_manager/mask_secret/interactive_menu 等 13 项）
├── _config.py            凭据模板与默认值；get_ssh_username/get_ssh_routes（委托 hpc_config）
├── _core.py              CredentialManager 封装 + 加解密公共辅助（供各 cred_* 模块导入）
├── _minimal.py           MinimalCredentialManager（Fernet 最小实现，credentials.enc 唯一读写层）
├── _flash_entries.py     （已停用的条目占位，仅 10 行）
├── manage.py             ★ 统一入口菜单（flash-cred 命令的实现）
├── hpc_config.py         ★ hpc_accounts.json 读写唯一入口（见 §4 权威声明）
├── flash_ssh.py          超算 SSH 多账户/多线路交互管理（增删改查/测速选路）
├── api_keys.py           AI API 密钥管理（DeepSeek/OpenAI/Claude/Gemini 条目）
├── deepseek.py           DeepSeek（太极网关）专用管理
├── gitee.py              Gitee 访问令牌管理
├── pypi.py               PyPI/TestPyPI API Token 管理（写 ~/.pypirc）
└── examples/
    └── hpc_accounts_demo.py   hpc_accounts.json 读取/校验/生成示例（可运行）
```

## 3. 模块清单

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `__init__.py` | 45 | 包导出与版本 | `interactive_menu`、`get_credential_manager` |
| `_config.py` | 217 | 凭据模板/默认值；SSH 基础信息查询 | `get_ssh_username`、`get_ssh_routes` |
| `_core.py` | 261 | 加解密公共辅助与 CredentialManager 封装 | `get_user_name`、`mask_secret`、`get_best_route` |
| `_minimal.py` | 137 | Fernet 最小凭据存储 | `MinimalCredentialManager` |
| `_flash_entries.py` | 10 | 已停用占位 | — |
| `manage.py` | 430 | 统一管理菜单（主入口） | `main()` → `flash-cred` |
| `hpc_config.py` | 406 | hpc_accounts.json 读写（唯一入口） | `load_hpc_accounts`、`get_hpc_routes`、`list_hpc_accounts` |
| `flash_ssh.py` | 548 | SSH 多账户/多线路交互管理 | `test_all_routes`、交互式菜单（CLI） |
| `api_keys.py` | 226 | AI API 密钥条目管理 | `setup_api`、`show_api`（CLI） |
| `deepseek.py` | 188 | DeepSeek 太极网关专用 | `setup_deepseek`（CLI） |
| `gitee.py` | 273 | Gitee 令牌管理 | `setup_gitee`（CLI） |
| `pypi.py` | 145 | PyPI Token 管理 | `main()`、`write_pypirc` |
| `examples/hpc_accounts_demo.py` | 254 | hpc_accounts.json 可运行示例 | `main()`（`--probe/--example/--init`） |

## 4. 超算连接信息权威声明（全包唯一出处）

**`~/.physimx/flash/hpc_accounts.json` 是全仓超算主机/端口/线路/SSH 用户名的唯一来源**（`flash_run/remote` 等消费方一律经 `hpc_config.get_hpc_routes()` 读取，不另行声明）。密码不在该 JSON——由 Fernet 加密存同目录 `credentials.enc`。

```bash
python -m flash._core.credentials.hpc_config show        # 打印当前配置
python -m flash._core.credentials.hpc_config example     # 输出格式示例
python -m flash._core.credentials.hpc_config extract     # 从加密库提取 ssh_username
python flash/_core/credentials/examples/hpc_accounts_demo.py --probe   # 读取+TCP 测速
```

JSON 格式字段说明与完整读取示例见 `hpc_config.py` 模块 docstring 与 `examples/hpc_accounts_demo.py`。

## 5. 敏感信息边界（铁律）

- 本 README 与任何文档**只允许**出现 `ssh.example.com`、`user@NC-E` 等占位符；真实主机/IP/账号/令牌禁止入档；
- 仓库内禁止出现 `hpc_accounts.json` 实体文件（在用户家目录，不入库）；格式示例用 `hpc_config example` 命令现生成；
- `scripts/08_docs/check_docs.py` 会对文档做敏感信息启发式扫描（`sk-`/`password=`/明文 IPv4）。

## 6. 快速上手

```bash
# 统一菜单（管理全部凭据类别）
python -m flash._core.credentials.manage        # 或安装后: flash-cred
```

```python
from flash._core.credentials import (
    get_credential_manager,   # CredentialManager 实例
    mask_secret,              # 脱敏展示
    get_primary_ssh,          # 主 SSH 账户
    interactive_menu,         # 统一菜单入口
)
```

## 7. 测试入口

本包未纳入仓库基线 pytest 主套；`examples/hpc_accounts_demo.py`（无 `--probe`）可作只读自检。基线命令见仓库根 README §测试。

## 8. 已知限制 / 遗留项

- `_flash_entries.py` 已停用（保留占位）；`_core/credentials_legacy.py` 为旧单体实现（1126 行），**不可达遗留，勿 import**；
- 旧接口 `load_ssh_credentials`/`get_best_route` 由 `_core.py` 桥接保留，新代码请用 `hpc_config` API。

## 9. 导航

上级：[../README.md](../README.md)（flash/_core） · 消费方：[../../flash_run/remote/README.md](../../flash_run/remote/README.md)
