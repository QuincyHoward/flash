# hpc_accounts.json — 超算连接信息的唯一来源

flash 包**不硬编码任何**超算主机 / 端口 / 线路 / SSH 用户名。
所有 SSH 连接所需的基础信息在运行时从下面这个明文 JSON 读取：

```
~/.physimx/flash/hpc_accounts.json      # 与 credentials.enc 同目录（不在包内）
```

> 密码**不在**此文件。密码由 Fernet 对称加密存储于同目录 `credentials.enc`。

---

## 1. 文件格式（UTF-8 JSON）

```json
{
  "_comment": ["可选的说明行", "..."],
  "accounts": {
    "flash_ssh": {
      "title":        "FLASH 超算 SSH #1 (NC-E)",
      "ssh_username": "user@NC-E",
      "route_key":    "nc_e",
      "routes": [
        {"host": "ssh.example.com", "port": 22,   "label": "线路 A"},
        {"host": "ssh.example.com", "port": 2222, "label": "线路 B"}
      ]
    },
    "flash_ssh_2": {
      "title":        "FLASH 超算 SSH #2 (BSCC-T6)",
      "ssh_username": "user2@BSCC-T6",
      "route_key":    "bscc_t6",
      "routes": [
        {"host": "ssh.example.com", "port": 8443, "label": "线路 A"}
      ]
    }
  }
}
```

### 字段

| 键 | 类型 | 说明 |
|---|---|---|
| `_comment` | `string[]` | 任意说明，仅作文档，可删 |
| `accounts` | `object` | `{账户键名: 账户基础信息}` |
| `accounts.<name>` | `object` | 账户键名，与 `credentials.enc` 中的键一一对应（`flash_ssh` / `flash_ssh_2`） |
| `.title` | `string` | 人类可读标题，仅用于菜单展示 |
| `.ssh_username` | `string` | SSH 登录用户名，可含用户自定后缀（如 `user@NC-E`） |
| `.route_key` | `string` | 中性集群标识，由用户自定（`nc_e` / `bscc_t6` / 任意值），仅作路由分组 |
| `.routes` | `object[]` | 线路列表，每项 `{host, port, label}`；自动选路时逐条 TCP 测速；缺省 `port` 视为 `22`；缺少 `host` 的条目被忽略 |

模板文件见 [`hpc_accounts.example.json`](hpc_accounts.example.json)。

---

## 2. 读取示例（推荐路径）

```python
from flash._core.credentials.hpc_config import (
    hpc_accounts_file,   # -> Path
    load_hpc_accounts,   # -> dict
    list_hpc_accounts,   # -> ["flash_ssh", "flash_ssh_2"]
    get_hpc_account,     # 单账户基础信息
    get_hpc_ssh_username,# -> "user@NC-E"
    get_hpc_routes,      # -> [{"host":..., "port":..., "label":...}, ...]
    all_routes,          # 全部账户线路汇总（去重）
)

# 方式一：高层 API（等价于 _config.get_ssh_routes，JSON 为唯一来源）
for r in get_hpc_routes("flash_ssh"):
    print(r["host"], r["port"], r.get("label", ""))

# 方式二：原始读取
data = load_hpc_accounts()
print(data["accounts"]["flash_ssh"]["ssh_username"])
```

完整可运行示例脚本：**[`examples/hpc_accounts_demo.py`](examples/hpc_accounts_demo.py)**

```bash
python flash/_core/credentials/examples/hpc_accounts_demo.py            # 打印 + 校验
python flash/_core/credentials/examples/hpc_accounts_demo.py --probe    # 附带 TCP 测速
python flash/_core/credentials/examples/hpc_accounts_demo.py --example  # 写出格式示例
python flash/_core/credentials/examples/hpc_accounts_demo.py --init     # 生成空骨架
```

---

## 3. 命令行工具

```bash
# 查看状态（缺失自动补骨架）
python -m flash._core.credentials.hpc_config

# 打印当前配置
python -m flash._core.credentials.hpc_config show

# 从加密库提取已存的 ssh_username 到 JSON（升级用；线路需自行维护）
python -m flash._core.credentials.hpc_config extract

# 输出格式示例文件
python -m flash._core.credentials.hpc_config example

# 交互式增删账户 / 测试线路（交互流程在 JSON 缺字段时会提示补录并回写）
python -m flash._core.credentials.manage
# 或安装后使用入口脚本：
flash-cred
```

---

## 4. 相关模块

| 模块 | 职责 |
|---|---|
| `hpc_config.py` | 本 JSON 的读写实现（**唯一**入口）；模块 docstring 含完整格式规范 |
| `_config.py` | `get_ssh_username` / `get_ssh_routes`，均直接委托给 `hpc_config` |
| `flash_ssh.py` | 多账户 / 多线路交互管理；缺字段时提示补录并回写 JSON |
| `manage.py` | 统一凭据管理菜单 |
| `examples/hpc_accounts_demo.py` | 最小读取 / 校验示例脚本 |

> 代码中如需获取路由，请统一调用
> `flash._core.credentials.hpc_config.get_hpc_routes()`，
> 不要在任何模块内新增硬编码的主机 / 端口表。
