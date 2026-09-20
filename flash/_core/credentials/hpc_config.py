"""
Flash 凭据管理 -- 超算账户明文配置 (hpc_accounts.json)
======================================================

``~/.physimx/flash/hpc_accounts.json`` 是 **本包唯一的超算连接信息来源**。
包代码内不再硬编码任何主机名 / 端口 / 线路 / SSH 用户名。

安全设计 (配置 / 密码分离)
---------------------------------------------------------------
  * **非敏感基础信息** (SSH 用户名、主机、端口、线路列表) 存放于明文 JSON,
    用户可直接编辑以增删账户 / 调整端口 / 重排线路, 无需改代码::

        ~/.physimx/flash/hpc_accounts.json

  * **密码** 仍按原方法 Fernet 加密存储于同目录 ``credentials.enc``,
    绝不出现于本 JSON。
  * 包随 PyPI 分发时不携带任何用户账户信息。

文件格式 (UTF-8 / JSON)
---------------------------------------------------------------

.. code-block:: json

    {
      "_comment": ["FLASH 超算账户明文配置 (可手工编辑)", "..."],
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

字段说明
~~~~~~~~

+-----------------------------------+--------------------------------------------+
| 键                                | 含义                                       |
+===================================+============================================+
| ``_comment``                      | 任意说明字符串数组 (可删除, 仅作文档)      |
+-----------------------------------+--------------------------------------------+
| ``accounts``                      | ``{账户键名: 账户基础信息}``               |
+-----------------------------------+--------------------------------------------+
| ``accounts.<name>``               | 账户键名, 与 ``credentials.enc`` 中的键    |
|                                   | 一一对应 (``flash_ssh`` / ``flash_ssh_2``) |
+-----------------------------------+--------------------------------------------+
| ``accounts.<name>.title``         | 人类可读标题 (仅用于菜单展示)              |
+-----------------------------------+--------------------------------------------+
| ``accounts.<name>.ssh_username``  | SSH 登录用户名, 可含自定后缀 (``user@NC-E``)|
+-----------------------------------+--------------------------------------------+
| ``accounts.<name>.route_key``     | 中性集群标识, 用户自定 (``nc_e``/``bscc_t6``|
|                                   | /任意值); 仅作路由分组用途                 |
+-----------------------------------+--------------------------------------------+
| ``accounts.<name>.routes``        | 线路列表, 每项 ``{host, port, label}``;    |
|                                   | 自动选路时逐条 TCP 测速; 缺省 port 视为 22;|
|                                   | 缺少 host 的条目被忽略                     |
+-----------------------------------+--------------------------------------------+

读写 API (供其它模块调用)
~~~~~~~~~~~~~~~~~~~~~~~~~
* :func:`load_hpc_accounts` / :func:`save_hpc_accounts` — 整体读写
* :func:`get_hpc_account` — 单账户基础信息
* :func:`get_hpc_ssh_username` / :func:`get_hpc_routes` — 单账户字段
* :func:`list_hpc_accounts` — 全部账户键名
* :func:`set_hpc_account_basics` — 写入 (仅非敏感字段)

生命周期
---------------------------------------------------------------
  1. 首次使用时 :func:`ensure_hpc_accounts_file` 生成可编辑骨架 (空账户模板);
  2. 升级迁移 :func:`extract_accounts_from_storage` 把加密库中已有的
     ``ssh_username`` 与旧条目 title/route_key 合并进 JSON
     (★ 线路不再由包提供, 完全由用户维护);
  3. 交互式设置 (``flash_ssh`` 菜单) 在 JSON 缺失用户名/线路时提示补全,
     并回写本 JSON (密码除外)。

用法 (CLI)
---------------------------------------------------------------
::

    python -m flash._core.credentials.hpc_config            # 状态 + 自动补骨架
    python -m flash._core.credentials.hpc_config show       # 打印当前配置
    python -m flash._core.credentials.hpc_config extract    # 从加密库提取用户名
    python -m flash._core.credentials.hpc_config example    # 输出格式示例文件

可直接运行的最小示例见 ``examples/hpc_accounts_demo.py``,
模板见 ``hpc_accounts.example.json``。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# 与 credentials.enc 同目录 (~/.physimx/flash/), 不在 flash 包内
_HPC_CONFIG_FILE = Path.home() / ".physimx" / "flash" / "hpc_accounts.json"

# 旧包内配置的兼容映射 (历史 route_key → 中性 key, 供读取旧数据时归一化)
_LEGACY_ROUTE_KEY = {"scfa2696": "nc_e", "sch0348": "bscc_t6"}

# ── 生成文件时写入的说明头 (同时也是格式速查) ─────────────
_HEADER_COMMENT = [
    "FLASH 超算账户明文配置 (可手工编辑) — 超算连接信息的唯一来源",
    "",
    "格式 (UTF-8 JSON):",
    "  accounts.<name>.title        : 人类可读标题 (菜单展示用)",
    "  accounts.<name>.ssh_username : SSH 登录用户名, 如 \"user@NC-E\"",
    "  accounts.<name>.route_key    : 中性集群标识, 用户自定 (如 nc_e / bscc_t6)",
    "  accounts.<name>.routes       : [{host, port, label}, ...]; 自动选路逐条 TCP 测速",
    "",
    "示例:",
    "  {\"accounts\": {\"flash_ssh\": {",
    "      \"title\": \"NC-E\", \"ssh_username\": \"user@NC-E\", \"route_key\": \"nc_e\",",
    "      \"routes\": [{\"host\": \"ssh.example.com\", \"port\": 22, \"label\": \"线路 A\"}]",
    "  }}}",
    "",
    "- 密码不在此文件: 由 Fernet 加密存储于同目录 credentials.enc",
    "- 删除 accounts 中某条目即移除该账户基础信息 (加密库中的密码不受影响)",
    "- 包代码内不含任何超算主机/端口/用户名, 全部由本文件驱动",
]

# ── 格式示例 (CLI `example` 命令输出, 亦作为模板) ─────────
HPC_ACCOUNTS_TEMPLATE: Dict[str, Any] = {
    "_comment": _HEADER_COMMENT,
    "accounts": {
        "flash_ssh": {
            "title": "示例账户 #1 (请改成真实集群名)",
            "ssh_username": "user@CLUSTER-A",
            "route_key": "cluster_a",
            "routes": [
                {"host": "ssh.example-a.com", "port": 22,   "label": "线路 1"},
                {"host": "ssh.example-a.com", "port": 2222, "label": "线路 2"},
            ],
        },
        "flash_ssh_2": {
            "title": "示例账户 #2 (可选, 多账户时使用)",
            "ssh_username": "user@CLUSTER-B",
            "route_key": "cluster_b",
            "routes": [
                {"host": "ssh.example-b.com", "port": 8443, "label": "线路 1"},
            ],
        },
    },
}


# ── 路径与整体读写 ─────────────────────────────────────────

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


def write_example_file(path: Optional[Path] = None) -> Path:
    """写出格式示例文件 (默认 ``hpc_accounts.example.json``, 与配置同目录)。

    仅用于文档/参考, **不会**被程序读取; 便于用户照抄格式后填入真实信息。
    """
    target = path or (_HPC_CONFIG_FILE.with_name("hpc_accounts.example.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(HPC_ACCOUNTS_TEMPLATE, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


# ── 单账户读取 (hpc_accounts.json 是唯一来源) ──────────────

def list_hpc_accounts() -> List[str]:
    """返回全部已配置账户键名 (按 JSON 中的顺序)。"""
    return list(load_hpc_accounts().get("accounts", {}).keys())


def get_hpc_account(name: str) -> Optional[Dict[str, Any]]:
    """获取某账户的基础信息 (明文, 无密码字段)。"""
    return load_hpc_accounts()["accounts"].get(name)


def get_hpc_ssh_username(name: str) -> str:
    """获取 SSH 用户名 (JSON 优先); 未配置返回空串。"""
    acct = get_hpc_account(name) or {}
    return acct.get("ssh_username", "") or ""


def get_hpc_routes(name: str) -> List[Dict[str, Any]]:
    """获取 SSH 线路列表 (JSON 优先); 未配置返回空列表。

    返回项已**归一化** (下游连接逻辑可直接使用):
      * ``port`` 一定是 1..65535 的整数 (缺省按 22 处理);
      * ``host`` 一定非空;
      * ``label`` 缺失时自动补为 ``host:port``。

    缺少 ``host`` 或 ``port`` 非法的条目被**静默忽略** (不抛异常,
    配置问题由 ``examples/hpc_accounts_demo.py`` 的校验功能报告)。
    """
    acct = get_hpc_account(name) or {}
    routes = acct.get("routes") or []
    out: List[Dict[str, Any]] = []
    for r in routes:
        if not isinstance(r, dict) or not r.get("host"):
            continue
        try:
            port = int(r.get("port", 22))
        except (TypeError, ValueError):
            continue
        if not (0 < port < 65536):
            continue
        out.append({
            "host": r["host"],
            "port": port,
            "label": r.get("label") or f"{r['host']}:{port}",
        })
    return out


def get_hpc_route_key(name: str, default: str = "") -> str:
    """获取账户的中性集群标识 (历史 scfa2696/sch0348 自动归一化)。"""
    acct = get_hpc_account(name) or {}
    rk = acct.get("route_key", "") or default
    return _LEGACY_ROUTE_KEY.get(rk, rk)


def all_routes() -> List[Dict[str, Any]]:
    """汇总全部账户的线路 (按 host:port 去重), 便于"任一线路可达即认为网络可用"的探活。

    每条记录附 ``account`` 字段标明来源账户键名。
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    for name in list_hpc_accounts():
        for r in get_hpc_routes(name):
            key = (r["host"], r["port"])
            if key in seen:
                continue
            seen.add(key)
            out.append({"account": name, **r})
    return out


# ── 单账户写入 ─────────────────────────────────────────────

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


# ── 升级迁移 ───────────────────────────────────────────────

def extract_accounts_from_storage() -> Dict[str, Any]:
    """一次性提取: 把加密存储中的 ssh_username 与包内旧条目的
    title / route_key 合并进明文 JSON (升级用)。

    ★ 线路 (``routes``) **不再由本包提供**: 完全由用户在 JSON 中维护。
      已有配置的 routes 会被原样保留; 此前未配置的账户得到空列表,
      需用户自行补全 (见模块 docstring 的格式说明)。
    """
    from ._config import ENTRIES_BY_NAME

    existing = load_hpc_accounts()

    # 从加密存储读取各 flash_ssh* 账户的 ssh_username (非密码)
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

    data: Dict[str, Any] = {
        "_comment": _HEADER_COMMENT,
        "accounts": dict(existing.get("accounts", {})),
    }
    for name, entry in ENTRIES_BY_NAME.items():
        if not name.startswith("flash_ssh"):
            continue
        prev = data["accounts"].get(name, {}) or {}
        data["accounts"][name] = {
            "title": prev.get("title") or entry.get("title", name),
            "ssh_username": (cm_usernames.get(name)
                             or prev.get("ssh_username", "")),
            "route_key": _LEGACY_ROUTE_KEY.get(
                prev.get("route_key") or entry.get("route_key", ""),
                prev.get("route_key") or entry.get("route_key", "")),
            # ★ 线路不在包内定义; 仅保留用户已在 JSON 中配置的条目
            "routes": [dict(r) for r in (prev.get("routes") or [])],
        }
    save_hpc_accounts(data)
    return data


# ── CLI ────────────────────────────────────────────────────

def _main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "example":
        p = write_example_file()
        print(f"[OK] 已写出格式示例: {p}")
        print("     (示例仅供参考, 程序不会读取它; 请把真实信息写入 "
              f"{hpc_accounts_file()})")
        return 0

    if cmd == "extract":
        data = extract_accounts_from_storage()
        n = len(data["accounts"])
        print(f"[OK] 已提取 {n} 个超算账户基础信息 -> {hpc_accounts_file()}")
        for name, acct in data["accounts"].items():
            n_routes = len(acct.get("routes") or [])
            warn = "" if n_routes else "   ← 无线路, 请手工补全 routes"
            print(f"  [{name}] ssh_username={acct['ssh_username'] or '(空)'}"
                  f"  routes={n_routes}{warn}")
        return 0

    ensure_hpc_accounts_file()
    data = load_hpc_accounts()
    print(f"配置文件: {hpc_accounts_file()}")
    if not data["accounts"]:
        print("  (无账户条目; 可手工编辑本文件, 或运行交互式设置自动补全)")
        print("  (格式说明: 见本模块 docstring; 示例: "
              "python -m flash._core.credentials.hpc_config example)")
        return 0
    for name, acct in data["accounts"].items():
        print(f"  [{name}] {acct.get('title', '')}")
        print(f"    ssh_username: {acct.get('ssh_username', '') or '(空)'}")
        print(f"    route_key:    {acct.get('route_key', '') or '(空)'}")
        routes = acct.get("routes") or []
        if not routes:
            print("      (无线路 — 请在 routes 中补充 {host, port, label})")
        for r in routes:
            print(f"      - {r.get('label', '')}  {r.get('host')}:{r.get('port')}")
    print("  (本文件为明文可编辑; 密码加密存于同目录 credentials.enc)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
