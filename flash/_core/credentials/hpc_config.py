"""
Flash 凭据管理 -- 超算账户明文配置 (hpc_accounts.json)
======================================================

安全性设计 (配置/密码分离):
  - **非敏感基础信息** (SSH 用户名、主机、端口、线路列表) 存放于明文 JSON:
      ``~/.physimx/flash/hpc_accounts.json`` (与 credentials.enc 同目录, 不在包内)
      用户可直接编辑此文件调整账户/端口/线路, 无需改代码。
  - **密码** 仍按原方法 Fernet 加密存储于 ``~/.physimx/flash/credentials.enc``,
      绝不出现在本 JSON 中。
  - flash 包代码内不再硬编码任何超算账号; 包随 PyPI 分发时不携带用户账户信息。

生命周期:
  1. 首次使用时 ``ensure_hpc_accounts_file()`` 生成可编辑骨架 (空账户模板);
  2. 旧版本升级时 ``extract_accounts_from_storage()`` 可把包内旧硬编码 +
     加密存储中的 ssh_username 一次性提取进 JSON (本 CLI 的 ``extract`` 命令);
  3. 交互式设置 (flash_ssh 菜单) 在 JSON 缺失用户名/线路时提示补全,
     并回写本 JSON (密码除外)。

用法 (CLI):
    python -m flash._core.credentials.hpc_config            # 状态 + 自动补齐骨架
    python -m flash._core.credentials.hpc_config extract    # 从旧配置一次性提取
    python -m flash._core.credentials.hpc_config show
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# 与 credentials.enc 同目录 (~/.physimx/flash/), 不在 flash 包内
_HPC_CONFIG_FILE = Path.home() / ".physimx" / "flash" / "hpc_accounts.json"

# 旧包内配置的兼容映射 (历史 route_key → 中性 key, 供读取旧数据时归一化)
_LEGACY_ROUTE_KEY = {"scfa2696": "nc_e", "sch0348": "bscc_t6"}

_HEADER_COMMENT = [
    "FLASH 超算账户明文配置 (可手工编辑)",
    "- 密码不在此文件: 密码由 Fernet 加密存储于同目录 credentials.enc",
    "- accounts.<name>.ssh_username: SSH 登录用户名 (如 user@集群)",
    "- accounts.<name>.routes: SSH 线路列表 (host/port/label), 自动选路时逐条测试",
    "- accounts.<name>.route_key: 中性集群标识 (nc_e / bscc_t6 / 自定义)",
    "- 删除 accounts 中某条目即移除该账户的基础信息 (加密库中的密码不受影响)",
]


def hpc_accounts_file() -> Path:
    """返回明文配置文件路径 (~/.physimx/flash/hpc_accounts.json)。"""
    return _HPC_CONFIG_FILE


def load_hpc_accounts() -> Dict[str, Any]:
    """读取明文配置; 文件缺失/损坏时返回空结构。"""
    if not _HPC_CONFIG_FILE.exists():
        return {"_comment": _HEADER_COMMENT, "accounts": {}}
    try:
        data = json.loads(_HPC_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"_comment": _HEADER_COMMENT, "accounts": {}}
    if not isinstance(data, dict) or "accounts" not in data:
        return {"_comment": _HEADER_COMMENT, "accounts": {}}
    data.setdefault("_comment", _HEADER_COMMENT)
    data.setdefault("accounts", {})
    return data


def save_hpc_accounts(data: Dict[str, Any]) -> Path:
    """保存明文配置 (UTF-8, 缩进 2, 便于手工编辑/diff)。"""
    _HPC_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("_comment", _HEADER_COMMENT)
    tmp = _HPC_CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(_HPC_CONFIG_FILE)
    return _HPC_CONFIG_FILE


def ensure_hpc_accounts_file() -> Path:
    """确保明文配置文件存在; 缺失时写入空账户骨架 (幂等)。"""
    if _HPC_CONFIG_FILE.exists():
        return _HPC_CONFIG_FILE
    return save_hpc_accounts({"_comment": _HEADER_COMMENT, "accounts": {}})


def get_hpc_account(name: str) -> Optional[Dict[str, Any]]:
    """获取某账户的基础信息 (明文, 无密码字段)。"""
    return load_hpc_accounts()["accounts"].get(name)


def get_hpc_ssh_username(name: str) -> str:
    """获取 SSH 用户名 (JSON 优先); 未配置返回空串。"""
    acct = get_hpc_account(name) or {}
    return acct.get("ssh_username", "") or ""


def get_hpc_routes(name: str) -> List[Dict[str, Any]]:
    """获取 SSH 线路列表 (JSON 优先); 未配置返回空列表。"""
    acct = get_hpc_account(name) or {}
    routes = acct.get("routes") or []
    return [dict(r) for r in routes if isinstance(r, dict) and r.get("host")]


def get_hpc_route_key(name: str, default: str = "") -> str:
    """获取账户的中性集群标识 (历史 scfa2696/sch0348 自动归一化)。"""
    acct = get_hpc_account(name) or {}
    rk = acct.get("route_key", "") or default
    return _LEGACY_ROUTE_KEY.get(rk, rk)


def set_hpc_account_basics(
    name: str,
    title: Optional[str] = None,
    ssh_username: Optional[str] = None,
    routes: Optional[List[Dict[str, Any]]] = None,
    route_key: Optional[str] = None,
) -> Path:
    """写入/更新某账户的基础信息 (仅非敏感字段, 密码不经过此函数)。"""
    data = load_hpc_accounts()
    acct = data["accounts"].setdefault(name, {})
    if title:
        acct["title"] = title
    if ssh_username is not None:
        acct["ssh_username"] = ssh_username
    if routes is not None:
        acct["routes"] = routes
    if route_key is not None:
        acct["route_key"] = _LEGACY_ROUTE_KEY.get(route_key, route_key)
    return save_hpc_accounts(data)


def extract_accounts_from_storage() -> Dict[str, Any]:
    """一次性提取: 从加密存储 + 包内旧预配置构建明文 JSON (升级用)。

    提取内容 (均非密码):
      - 加密凭据中的 ssh_username (各 flash_ssh* 账户)
      - 包内旧 _config.ENTRIES 的 title / route_key
      - 包内旧 ROUTES_ALL 线路表
    """
    from ._config import ENTRIES_BY_NAME, LEGACY_PACKAGE_ROUTES

    cm_usernames: Dict[str, str] = {}
    try:
        from ._core import get_credential_manager, collect_ssh_accounts
        cm = get_credential_manager()
        for cred_name in collect_ssh_accounts(cm):
            cred = cm.get(cred_name) or {}
            if cred.get("ssh_username"):
                cm_usernames[cred_name] = cred["ssh_username"]
    except Exception:  # noqa: BLE001
        pass

    data: Dict[str, Any] = {"_comment": _HEADER_COMMENT, "accounts": {}}
    for name, entry in ENTRIES_BY_NAME.items():
        if not name.startswith("flash_ssh"):
            continue
        data["accounts"][name] = {
            "title": entry.get("title", name),
            "ssh_username": cm_usernames.get(name, ""),
            "route_key": _LEGACY_ROUTE_KEY.get(entry.get("route_key", ""),
                                               entry.get("route_key", "")),
            "routes": [dict(r) for r in LEGACY_PACKAGE_ROUTES],
        }
    save_hpc_accounts(data)
    return data


def _main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "extract":
        data = extract_accounts_from_storage()
        n = len(data["accounts"])
        print(f"[OK] 已提取 {n} 个超算账户基础信息 -> {hpc_accounts_file()}")
        for name, acct in data["accounts"].items():
            print(f"  [{name}] ssh_username={acct['ssh_username'] or '(空)'}"
                  f"  routes={len(acct['routes'])}")
        return 0

    ensure_hpc_accounts_file()
    data = load_hpc_accounts()
    print(f"配置文件: {hpc_accounts_file()}")
    if not data["accounts"]:
        print("  (无账户条目; 可手工编辑本文件, 或运行交互式设置自动补全)")
        return 0
    for name, acct in data["accounts"].items():
        print(f"  [{name}] {acct.get('title', '')}")
        print(f"    ssh_username: {acct.get('ssh_username', '') or '(空)'}")
        print(f"    route_key:    {acct.get('route_key', '') or '(空)'}")
        for r in acct.get("routes", []):
            print(f"      - {r.get('label', '')}  {r.get('host')}:{r.get('port')}")
    print("  (本文件为明文可编辑; 密码加密存于同目录 credentials.enc)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
