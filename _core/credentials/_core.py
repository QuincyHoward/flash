"""
Flash 凭据管理 -- 核心加密/解密
==============================
提供 CredentialManager 封装及公共辅助函数。
供其他 cred_* 模块导入使用。
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._config import DEFAULT_USER_NAME, ENTRIES, ENTRIES_BY_NAME

# ── 凭据管理器缓存 (确保同一会话内单例) ──
_CREDENTIAL_MANAGER_CACHE = None


# ── 敏感字段名: 列表展示时自动掩码 ──
_SECRET_FIELDS = {"password", "api_key", "secret", "token", "access_key", "private_key"}

_DEFAULT_PASSWORD = "123"


def get_default_password() -> str:
    """获取默认密码 (用于 SSH 账户设置提示)。"""
    return _DEFAULT_PASSWORD


def get_credential_manager():
    """获取 CredentialManager 实例 (Flash 专属存储)，会话内缓存。

    优先使用 physimx_core（加密存储），回退到内存最小实现。
    使用模块级缓存确保同一会话内返回同一实例。
    """
    global _CREDENTIAL_MANAGER_CACHE
    if _CREDENTIAL_MANAGER_CACHE is not None:
        return _CREDENTIAL_MANAGER_CACHE

    try:
        from physimx_core.credentials import CredentialManager
        # 使用 Flash 专属子目录: ~/.physimx/flash/
        _CREDENTIAL_MANAGER_CACHE = CredentialManager(subdir="flash")
    except ImportError:
        # physimx_core 未安装时，使用内存最小实现
        from ._minimal import MinimalCredentialManager
        _CREDENTIAL_MANAGER_CACHE = MinimalCredentialManager(subdir="flash")
    return _CREDENTIAL_MANAGER_CACHE


# ── 用户名字段 ──────────────────────────────────────────

def get_user_name() -> str:
    """获取用户名 (优先继承 physimx_core, fallback Flash 自己的 __meta__)。"""
    try:
        from physimx_core.credentials import get_user_name as _gun
        return _gun()
    except ImportError:
        # fallback: 从 __meta__ 读取
        try:
            cm = get_credential_manager()
            meta = cm.get("__meta__") or {}
            return meta.get("default_user_name", DEFAULT_USER_NAME)
        except Exception:
            return DEFAULT_USER_NAME


def get_user_name_source() -> str:
    """返回用户名来源: 'physimx_core' 或 'flash'。"""
    try:
        from physimx_core.credentials import get_user_name as _gun
        _gun()
        return "physimx_core"
    except ImportError:
        return "flash"


def set_user_name(name: str) -> None:
    """设置用户名。"""
    try:
        from physimx_core.credentials import set_user_name as _sun
        _sun(name)
    except ImportError:
        # fallback: 写入 __meta__
        try:
            cm = get_credential_manager()
            meta = cm.get("__meta__") or {}
            meta["default_user_name"] = name
            cm.set("__meta__", meta)
        except Exception:
            pass


def ask_one(label: str, default) -> str:
    """询问一个字段，回车返回默认值。"""
    val = input(f"  {label:12s} [{default}]: ").strip()
    return val if val else str(default)


def mask_secret(data: Dict[str, Any]) -> Dict[str, Any]:
    """对敏感字段进行掩码处理，返回安全可展示的副本。"""
    masked = dict(data)
    for k, v in masked.items():
        if k in _SECRET_FIELDS:
            if isinstance(v, str) and len(v) > 4:
                masked[k] = v[:2] + "*" * (len(v) - 4) + v[-2:]
            elif isinstance(v, str):
                masked[k] = "****"
    return masked


# ── SSH 账户辅助 ──

def collect_ssh_accounts(cm) -> List[str]:
    """收集所有 flash_ssh 开头的凭据名，排序返回。"""
    all_creds = cm._load_raw()
    return sorted([k for k in all_creds if k.startswith("flash_ssh")])


def get_primary_ssh(cm) -> str:
    """获取主 SSH 账户名。"""
    meta = cm.get("__meta__") or {}
    return meta.get("primary_ssh", "flash_ssh")


def set_primary_ssh(cm, account_name: str) -> None:
    """设置主 SSH 账户。"""
    meta = cm.get("__meta__") or {}
    meta["primary_ssh"] = account_name
    cm.set("__meta__", meta)


# ── SSH 编号工具 ──

def next_ssh_number(cm) -> int:
    """计算下一个可用的 SSH 账户编号。"""
    existing = collect_ssh_accounts(cm)
    used = set()
    for name in existing:
        if name == "flash_ssh":
            used.add(1)
        elif name.startswith("flash_ssh_"):
            try:
                used.add(int(name.split("_")[-1]))
            except ValueError:
                pass
    n = 1
    while n in used:
        n += 1
    return n


def ssh_account_name(num: int) -> str:
    """根据编号生成 SSH 账户名 (1 -> flash_ssh, 2+ -> flash_ssh_N)。"""
    return "flash_ssh" if num == 1 else f"flash_ssh_{num}"


# ── 通用凭据辅助 ──

def get_entry_def(name: str) -> Optional[Dict[str, Any]]:
    """根据名称获取凭据条目定义。"""
    return ENTRIES_BY_NAME.get(name)


def list_all_entries() -> List[Dict[str, Any]]:
    """列出所有凭据条目定义。"""
    return ENTRIES


# ── 旧接口兼容桥接 ──
#    以下函数是旧 _core/credentials.py (单文件) 中的 API，
#    供 flash_run/ 和 scenarios/flash_demo/ 等模块直接使用。
#    使用 Flash 专属存储 (get_credential_manager)。
#    =================================================

def load_ssh_credentials(name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """加载 FLASH SSH 凭据（自动解析路由）。

    返回的凭据包含 host/port/username/password 等连接所需字段。
    优先使用已缓存的 active_route，否则从预配置路由自动选择第一条。

    参数:
        name: 凭据名 (如 "flash_ssh")，为 None 时返回主账户凭据。

    返回:
        凭据字典 (含 host/port/username/password)，未找到返回 None。
    """
    try:
        cm = get_credential_manager()
    except SystemExit:
        return None
    if name is not None:
        raw = cm.get(name)
        _effective_name = name
    else:
        primary = get_primary_ssh(cm)
        raw = cm.get(primary)
        _effective_name = primary
        if raw is None:
            raw = cm.get("flash_ssh")
            _effective_name = "flash_ssh"
    if not raw:
        return None

    # 如果已有完整字段，直接返回
    if raw.get("host") and raw.get("username"):
        return dict(raw)

    # ── 路由解析 ──
    from ._config import get_ssh_routes, ENTRIES_BY_NAME
    result = dict(raw)

    # route_key: 从预配置条目中补齐
    entry = ENTRIES_BY_NAME.get(_effective_name)
    if entry and "route_key" not in result:
        rk = entry.get("route_key")
        if rk:
            result["route_key"] = rk

    # 用户名: 优先使用 raw 中的，否则从预配置获取
    if "username" not in result or not result["username"]:
        ssh_user = raw.get("ssh_username", "")
        if ssh_user:
            result["username"] = ssh_user

    # 路由: 按 active_route → 第一条 → None
    routes = get_ssh_routes(_effective_name)
    route = None
    active_idx = raw.get("active_route")
    if active_idx is not None and isinstance(active_idx, int) and 0 <= active_idx < len(routes):
        route = routes[active_idx]
    elif routes:
        route = routes[0]  # 默认第一条

    if route:
        result.setdefault("host", route["host"])
        result.setdefault("port", route["port"])

    return result


def load_all_ssh_credentials() -> Dict[str, Dict[str, Any]]:
    """加载所有超算 SSH 凭据（自动解析路由）。

    返回:
        {凭据名: 凭据字典, ...}，每个字典包含 host/port/username/password。
        仅包含可解析出 host 的有效凭据。
    """
    try:
        cm = get_credential_manager()
    except SystemExit:
        return {}
    names = collect_ssh_accounts(cm)
    result = {}
    for name in names:
        resolved = load_ssh_credentials(name)
        if resolved and resolved.get("host"):
            result[name] = resolved
    return result


def get_best_route(cred_name: str) -> Optional[Dict[str, Any]]:
    """获取凭据已缓存的最佳路由。

    参数:
        cred_name: 凭据名 (如 "flash_ssh")

    返回:
        路由字典 {"host": ..., "port": ..., "label": ...}，未缓存返回 None。
    """
    try:
        cm = get_credential_manager()
    except SystemExit:
        return None
    cred = cm.get(cred_name)
    if cred is None:
        return None
    return cred.get("best_route")
