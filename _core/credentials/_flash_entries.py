"""
Flash 包 -- 凭据条目定义
========================

这是 flash 包自己的凭据配置。
在 flash/_core/credentials/_config.py 中注册。

注意: SSH 线路定义在 _config.py 中 (共享基础设施)。
"""

# ── 导入 register 函数 (兼容直接运行和模块运行) ─────────────────────
try:
    # 相对导入 (作为包的一部分运行时)
    from ._config import register_entries, register_ssh_accounts
except (ImportError, ValueError):
    # 绝对导入 (直接运行时)
    from flash._core.credentials._config import register_entries, register_ssh_accounts


# ── 预配置 SSH 账户 ───────────────────────────────

register_ssh_accounts([
    {
        "name": "flash_ssh",
        "title": "FLASH 超算 SSH #1 (ParaCloud 中卫 NC-E)",
        "ssh_username": "scfa2696@NC-E",
        "routes": [
            {"host": "ssh.cn-zhongwei-1.paracloud.com",     "port": 8443, "label": "中卫-1 (8443)"},
            {"host": "ssh.cn-hongkong-1.paracloud.com",     "port": 22,   "label": "香港-1 (22)"},
            {"host": "ssh.cn-zhongwei-1.paracloud.com",      "port": 22,   "label": "中卫-1 (22)"},
            {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",  "port": 22,   "label": "中卫-1-v6 (22)"},
            {"host": "ssh.cn-zhongwei-1.paracloud.com",      "port": 2222, "label": "中卫-1 (2222)"},
            {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",  "port": 2222, "label": "中卫-1-v6 (2222)"},
            {"host": "ssh.cn-zhongwei-cstnet.paracloud.com", "port": 22,   "label": "中卫-cstnet (22)"},
            {"host": "ssh.cn-zhongwei-cstnet-v6.paracloud.com","port": 22, "label": "中卫-cstnet-v6 (22)"},
            {"host": "ssh.paracloud.com",                    "port": 2222, "label": "ParaCloud (2222)"},
        ],
    },
    {
        "name": "flash_ssh_2",
        "title": "FLASH 超算 SSH #2 (ParaCloud 中卫 BSCC-T6)",
        "ssh_username": "sch0348@BSCC-T6",
        "routes": [
            {"host": "ssh.cn-zhongwei-1.paracloud.com",     "port": 8443, "label": "中卫-1 (8443)"},
            {"host": "ssh.cn-hongkong-1.paracloud.com",     "port": 22,   "label": "香港-1 (22)"},
            {"host": "ssh.cn-zhongwei-1.paracloud.com",      "port": 22,   "label": "中卫-1 (22)"},
            {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",  "port": 22,   "label": "中卫-1-v6 (22)"},
            {"host": "ssh.cn-zhongwei-1.paracloud.com",      "port": 2222, "label": "中卫-1 (2222)"},
            {"host": "ssh.cn-zhongwei-1-v6.paracloud.com",  "port": 2222, "label": "中卫-1-v6 (2222)"},
            {"host": "ssh.cn-zhongwei-cstnet.paracloud.com", "port": 22,   "label": "中卫-cstnet (22)"},
            {"host": "ssh.cn-zhongwei-cstnet-v6.paracloud.com","port": 22, "label": "中卫-cstnet-v6 (22)"},
            {"host": "ssh.paracloud.com",                    "port": 2222, "label": "ParaCloud (2222)"},
        ],
    },
])


# ── 普通凭据条目 ──────────────────────────────────

register_entries([
    # Gitee 凭据
    {
        "name": "gitee",
        "type": "gitee",
        "title": "Gitee 访问令牌",
        "fields": [
            ("token",    "访问令牌 (Personal Access Token)", "123"),
            ("username", "用户名",                                 "hello"),
            ("repo_url", "仓库 URL (可选)",                      "https://gitee.com/physimx/flash.git"),
        ],
    },

    # DeepSeek API
    {
        "name": "deepseek_api",
        "type": "api",
        "title": "DeepSeek API (太极网关)",
        "fields": [
            ("base_url", "API 地址", "https://gateway.taichuai.cn/modelhub/api/v1"),
            ("api_key",  "API Key", "123"),
        ],
    },
])
