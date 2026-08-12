"""
Flash 凭据管理 -- 配置定义
============================
定义所有凭据模板及其默认值。
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

# 所有 ParaCloud 可用线路 (host, port)
ROUTES_ALL: List[Dict[str, Any]] = [
    {"host": "ssh.cn-zhongwei-1.paracloud.com",      "port": 8443, "label": "中卫-1 :8443"},
    {"host": "ssh.cn-hongkong-1.paracloud.com",       "port": 22,   "label": "香港-1 :22"},
    {"host": "ssh.cn-zhongwei-1.paracloud.com",       "port": 22,   "label": "中卫-1 :22"},
    {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",    "port": 22,   "label": "中卫-1 v6 :22"},
    {"host": "ssh.cn-zhongwei-1.paracloud.com",       "port": 2222, "label": "中卫-1 :2222"},
    {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",    "port": 2222, "label": "中卫-1 v6 :2222"},
    {"host": "ssh.cn-zhongwei-cstnet.paracloud.com",  "port": 22,   "label": "中卫 cstnet :22"},
    {"host": "ssh.cn-zhongwei-cstnet-v6.paracloud.com","port": 22,   "label": "中卫 cstnet v6 :22"},
    {"host": "ssh.paracloud.com",                     "port": 2222, "label": "paracloud :2222"},
]

ENTRIES: List[EntryDef] = [
    # FLASH SSH 账户（支持多个）
    {
        "name": "flash_ssh",
        "title": "FLASH 超算 SSH #1 (ParaCloud 中卫 NC-E)",
        "fields": [
            ("connection_mode", "连接模式 [auto/manual]", "auto"),
            ("password", "密码", "123"),
        ],
        "route_key": "scfa2696",
        "manual_fields": [
            ("host",     "SSH 主机", "ssh.cn-zhongwei-1.paracloud.com"),
            ("port",     "SSH 端口", 22),
            ("username", "用户名",   "scfa2696@NC-E"),
        ],
        "routes": ROUTES_ALL,
    },
    {
        "name": "flash_ssh_2",
        "title": "FLASH 超算 SSH #2 (ParaCloud 中卫 BSCC-T6)",
        "fields": [
            ("connection_mode", "连接模式 [auto/manual]", "auto"),
            ("password", "密码", "123"),
        ],
        "route_key": "sch0348",
        "manual_fields": [
            ("host",     "SSH 主机", "ssh.cn-zhongwei-1.paracloud.com"),
            ("port",     "SSH 端口", 22),
            ("username", "用户名",   "sch0348@BSCC-T6"),
        ],
        "routes": ROUTES_ALL,
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


# ── SSH 预配置辅助 ──────────────────────────────────

def _get_field(entry: EntryDef, key: str, default=None):
    """从 entry 的 fields/manual_fields 里取默认值。"""
    for k, _, v in entry.get("fields", []):
        if k == key:
            return v
    for k, _, v in entry.get("manual_fields", []):
        if k == key:
            return v
    return default


def get_ssh_username(name: str) -> str:
    """获取 SSH 账户的用户名 (从预配置读取, 未找到则返回 name 本身)。"""
    entry = ENTRIES_BY_NAME.get(name)
    if entry:
        return _get_field(entry, "username", name)
    return name


def get_ssh_routes(name: str) -> List[Dict[str, Any]]:
    """获取 SSH 账户的线路列表 (从预配置读取)。"""
    entry = ENTRIES_BY_NAME.get(name)
    if not entry:
        return []
    # 优先使用 entry 的 routes 字段（多线路）
    routes = entry.get("routes")
    if routes:
        return list(routes)
    # fallback: 从 manual_fields 构建单条线路
    host = _get_field(entry, "host")
    port = _get_field(entry, "port", 22)
    if not host:
        return []
    label = entry.get("title", f"{host}:{port}")
    return [{"host": host, "port": int(port), "label": label}]


# PRECONFIGURED_SSH: 从 ENTRES 自动构建
PRECONFIGURED_SSH: List[Dict[str, Any]] = [
    {
        "name": e["name"],
        "title": e["title"],
        "ssh_username": get_ssh_username(e["name"]),
        "routes": get_ssh_routes(e["name"]),
    }
    for e in ENTRIES if e["name"].startswith("flash_ssh")
]
