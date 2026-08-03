"""
Flash 凭据管理 -- 包导出
============================
导出核心函数，方便其他模块导入。
"""

from ._core import (
    get_credential_manager,
    get_user_name,
    set_user_name,
    mask_secret,
    # SSH 辅助
    collect_ssh_accounts,
    get_primary_ssh,
    set_primary_ssh,
    next_ssh_number,
    ssh_account_name,
    # 旧接口桥接
    load_ssh_credentials,
    load_all_ssh_credentials,
    get_best_route,
)
# 导入统一管理菜单
from .manage import main as interactive_menu

# 版本
__version__ = "1.0.0"

# 公开 API
__all__ = [
    "get_credential_manager",
    "get_user_name",
    "set_user_name",
    "mask_secret",
    "collect_ssh_accounts",
    "get_primary_ssh",
    "set_primary_ssh",
    "next_ssh_number",
    "ssh_account_name",
    "load_ssh_credentials",
    "load_all_ssh_credentials",
    "get_best_route",
    "interactive_menu",
]
