"""
Flash 凭据管理 -- 配置定义
============================
定义所有凭据模板及其默认值。

★ 超算账户基础信息的唯一来源
---------------------------------------------------------------
本包 **不再以任何形式硬编码超算主机 / 端口 / 线路 / 用户名**。
SSH 连接所需的全部基础信息在运行时从下列明文 JSON 读取:

    ~/.physimx/flash/hpc_accounts.json

文件格式 (UTF-8, JSON, 由 hpc_config.py 读写)::

    {
      "_comment": ["说明行...", "..."],
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
        "flash_ssh_2": { "title": "...", "ssh_username": "...",
                         "route_key": "...", "routes": [ ... ] }
      }
    }

字段含义:
  accounts.<name>                账户键名, 与加密库 credentials.enc 的键一一对应
                                 (flash_ssh / flash_ssh_2 / ...);
  accounts.<name>.title          人类可读标题 (仅用于菜单展示);
  accounts.<name>.ssh_username   SSH 登录用户名 (可含用户自定后缀, 如 user@NC-E);
  accounts.<name>.route_key      中性集群标识, 由用户自定 (nc_e / bscc_t6 / 任意);
  accounts.<name>.routes         线路列表, 每项 {host, port, label};
                                 自动选路时逐条做 TCP 测速; 缺省 port 视为 22;
                                 缺少 host 的条目被忽略。

**密码不在本文件**: 密码由 Fernet 对称加密存储于同目录 credentials.enc。

本模块对外暴露的读取 API (均为 JSON 优先且唯一来源):
  ``get_ssh_username(name)``  -> str         账户 SSH 用户名 (未配置返回 "")
  ``get_ssh_routes(name)``    -> List[dict]  账户线路列表 (未配置返回 [])
  ``PRECONFIGURED_SSH``                      导入期快照, 供交互菜单展示

完整格式规范与示例见 ``hpc_config.py`` 模块 docstring 及同目录
``hpc_accounts.example.json`` / ``examples/hpc_accounts_demo.py``。
"""

from typing import Any, Dict, List, Tuple

# 字段类型: (key, label, default)
FieldDef = Tuple[str, str, Any]

# 凭据条目类型
EntryDef = Dict[str, Any]

# 默认值
DEFAULT_USER_NAME = "hello"
DEFAULT_PASSWORD = "123"

# ── 凭据条目定义 ──────────────────────────────────

# 说明: 超算主机/端口/线路/用户名的**具体取值**一律不在本文件出现 —
#       它们只存在于 ~/.physimx/flash/hpc_accounts.json (见 hpc_config.py)。
#       此处 ENTRIES 仅保留"凭据条目结构"与非敏感的字段占位默认值。

ENTRIES: List[EntryDef] = [
    # FLASH SSH 账户（支持多个）
    {
        "name": "flash_ssh",
        "title": "FLASH 超算 SSH #1 (ParaCloud 中卫 NC-E)",
        "fields": [
            ("connection_mode", "连接模式 [auto/manual]", "auto"),
            ("password", "密码", "123"),
        ],
        "route_key": "nc_e",
        "manual_fields": [
            ("host",     "SSH 主机", ""),
            ("port",     "SSH 端口", 22),
            ("username", "用户名",   ""),
        ],
    },
    {
        "name": "flash_ssh_2",
        "title": "FLASH 超算 SSH #2 (ParaCloud 中卫 BSCC-T6)",
        "fields": [
            ("connection_mode", "连接模式 [auto/manual]", "auto"),
            ("password", "密码", "123"),
        ],
        "route_key": "bscc_t6",
        "manual_fields": [
            ("host",     "SSH 主机", ""),
            ("port",     "SSH 端口", 22),
            ("username", "用户名",   ""),
        ],
    },

    # Gitee 凭据
    {
        "name": "gitee",
        "title": "Gitee 访问令牌",
        "fields": [
            ("token",       "访问令牌 (Personal Access Token)", "123"),
            ("username",    "用户名",                                 DEFAULT_USER_NAME),
            ("repo_url",   "仓库 URL (可选)",                      "https://gitee.com/physimx/flash.git"),
        ],
    },

    # PyPI 发布令牌 (pypi.org / test.pypi.org)
    {
        "name": "pypi",
        "title": "PyPI 发布令牌 (pypi.org)",
        "fields": [
            ("token",    "PyPI API Token (pypi-xxx)", ""),
            ("username", "用户名",                      "__token__"),
        ],
    },
    {
        "name": "testpypi",
        "title": "TestPyPI 发布令牌 (test.pypi.org)",
        "fields": [
            ("token",    "TestPyPI API Token (pypi-xxx)", ""),
            ("username", "用户名",                          "__token__"),
        ],
    },

    # API 密钥 -- AI 服务 (可扩展)
    {
        "name": "deepseek_api",
        "title": "DeepSeek API (太极网关)",
        "fields": [
            ("base_url", "API 地址", "https://gateway.taichuai.cn/modelhub/api/v1"),
            ("api_key",  "API Key", "123"),
        ],
    },
    # 可扩展：添加更多 AI API 凭据
    # {
    #     "name": "openai_api",
    #     "title": "OpenAI API",
    #     "fields": [
    #         ("api_key", "API Key", "123"),
    #         ("base_url", "API 地址 (可选)", ""),
    #     ],
    # },
    # {
    #     "name": "claude_api",
    #     "title": "Claude API (Anthropic)",
    #     "fields": [
    #         ("api_key", "API Key", "123"),
    #         ("base_url", "API 地址 (可选)", ""),
    #     ],
    # },
    # {
    #     "name": "gemini_api",
    #     "title": "Gemini API (Google)",
    #     "fields": [
    #         ("api_key", "API Key", "123"),
    #     ],
    # },
    # {
    #     "name": "qwen_api",
    #     "title": "通义千问 API (阿里云)",
    #     "fields": [
    #         ("api_key", "API Key", "123"),
    #         ("base_url", "API 地址 (可选)", ""),
    #     ],
    # },
]

# 按名称索引
ENTRIES_BY_NAME: Dict[str, EntryDef] = {e["name"]: e for e in ENTRIES}


# ── SSH 账户基础信息读取 (唯一来源: hpc_accounts.json) ──────

def get_ssh_username(name: str) -> str:
    """获取 SSH 账户的登录用户名。

    ★ 唯一来源是 ``~/.physimx/flash/hpc_accounts.json``
      (``accounts.<name>.ssh_username``)。

    未在该 JSON 中配置时返回空字符串 —— 代码内不做任何回退或默认值分发。
    """
    from .hpc_config import get_hpc_ssh_username
    return get_hpc_ssh_username(name) or ""


def get_ssh_routes(name: str) -> List[Dict[str, Any]]:
    """获取 SSH 账户的线路列表。

    ★ 唯一来源是 ``~/.physimx/flash/hpc_accounts.json``
      (``accounts.<name>.routes``)。

    返回 ``[{"host": ..., "port": ..., "label": ...}, ...]``;
    未配置时返回空列表 (无包内回退线路)。
    """
    from .hpc_config import get_hpc_routes
    return get_hpc_routes(name)


# PRECONFIGURED_SSH: 从 ENTRIES + hpc_accounts.json 动态构建
# (注意: 这里是模块导入期快照; 交互流程中应改用 get_ssh_username/get_ssh_routes
#  实时读取, 以反映用户对 JSON 的手工编辑)
PRECONFIGURED_SSH: List[Dict[str, Any]] = [
    {
        "name": e["name"],
        "title": e["title"],
        "ssh_username": get_ssh_username(e["name"]),
        "routes": get_ssh_routes(e["name"]),
    }
    for e in ENTRIES if e["name"].startswith("flash_ssh")
]
