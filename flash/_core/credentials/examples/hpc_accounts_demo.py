#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""hpc_accounts_demo.py — 读取 / 校验 ``hpc_accounts.json`` 的最小示例。

本脚本演示 flash 包**唯一**的超算连接信息来源::

    ~/.physimx/flash/hpc_accounts.json

包代码内不含任何超算主机 / 端口 / 用户名 / 线路定义。

运行方式
--------------------------------------------------------------------
::

    python flash/_core/credentials/examples/hpc_accounts_demo.py
    python flash/_core/credentials/examples/hpc_accounts_demo.py --probe
    python flash/_core/credentials/examples/hpc_accounts_demo.py --json

``--probe`` 会额外对每条线路做 TCP 测速并给出延迟最低者。

文件格式 (UTF-8 JSON)
--------------------------------------------------------------------

.. code-block:: json

    {
      "_comment": ["可选说明行"],
      "accounts": {
        "flash_ssh": {
          "title":        "FLASH 超算 SSH #1 (NC-E)",
          "ssh_username": "user@NC-E",
          "route_key":    "nc_e",
          "routes": [
            {"host": "ssh.example.com", "port": 22,   "label": "线路 A"},
            {"host": "ssh.example.com", "port": 2222, "label": "线路 B"}
          ]
        }
      }
    }

字段说明
    ``accounts.<name>``            账户键名, 与 ``credentials.enc`` 中的键一一对应
                                   (``flash_ssh`` / ``flash_ssh_2`` / ...)
    ``accounts.<name>.title``      人类可读标题 (仅用于菜单展示)
    ``accounts.<name>.ssh_username``  SSH 登录用户名, 可含用户自定后缀
    ``accounts.<name>.route_key``  中性集群标识, 由用户自定 (``nc_e`` / ``bscc_t6`` / 任意)
    ``accounts.<name>.routes``     线路列表, 每项 ``{host, port, label}``;
                                   自动选路时逐条 TCP 测速; 缺省 ``port`` 视为 22;
                                   缺少 ``host`` 的条目被忽略

**密码不在本文件**: 密码由 Fernet 加密存储于同目录 ``credentials.enc``。
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── standalone 引导: 使 `python <this file>` 可直接运行 ──────────────
#   examples/ -> credentials/ -> _core/ -> flash/ -> <包父目录>
if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

from flash._core.credentials.hpc_config import (  # noqa: E402
    all_routes,
    ensure_hpc_accounts_file,
    get_hpc_account,
    get_hpc_route_key,
    get_hpc_routes,
    get_hpc_ssh_username,
    hpc_accounts_file,
    list_hpc_accounts,
    load_hpc_accounts,
    write_example_file,
)

# Windows 控制台改 UTF-8, 避免中文/特殊字符输出报错
try:  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


# ── 校验 ────────────────────────────────────────────────────────────

def validate_accounts(data: Dict[str, Any]) -> List[str]:
    """校验 JSON 结构, 返回问题列表 (空列表 = 通过)。"""
    problems: List[str] = []
    if not isinstance(data, dict):
        return ["顶层结构不是 JSON 对象 (应为 {\"accounts\": {...}})"]
    accounts = data.get("accounts")
    if not isinstance(accounts, dict):
        return ["缺少 \"accounts\" 对象 (应为 {\"accounts\": {...}})"]
    if not accounts:
        problems.append("accounts 为空 — 尚无任何超算账户")
        return problems

    for name, acct in accounts.items():
        if not isinstance(acct, dict):
            problems.append(f"[{name}] 账户条目不是对象")
            continue
        if not get_hpc_ssh_username(name):
            problems.append(f"[{name}] 缺少 ssh_username (SSH 登录用户名)")
        routes = acct.get("routes")
        if not isinstance(routes, list) or not routes:
            problems.append(f"[{name}] routes 为空 — 至少需要一条线路")
            continue
        seen_endpoints: set = set()   # 仅在本账户内检测重复
        for i, r in enumerate(routes):
            if not isinstance(r, dict):
                problems.append(f"[{name}] routes[{i}] 不是对象")
                continue
            host = r.get("host")
            if not host:
                problems.append(f"[{name}] routes[{i}] 缺少 host (该条目将被忽略)")
                continue
            port = r.get("port", 22)
            try:
                port = int(port)
            except (TypeError, ValueError):
                problems.append(f"[{name}] routes[{i}] port={port!r} 不是整数")
                continue
            if not (0 < port < 65536):
                problems.append(f"[{name}] routes[{i}] port={port} 超出 1..65535")
            key = (host, port)
            if key in seen_endpoints:
                problems.append(f"[{name}] routes[{i}] 本账户内重复: {host}:{port}")
            seen_endpoints.add(key)
    return problems


# ── 线路测速 (可选) ──────────────────────────────────────────────────

def tcp_ms(host: str, port: int, timeout: float = 5.0) -> Optional[float]:
    """TCP connect 延迟 (ms); 不可达返回 None。"""
    import time
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return (time.time() - t0) * 1000.0
    except OSError:
        return None


def probe_best(account: str, timeout: float = 5.0) -> Optional[Tuple[str, int, float]]:
    """对该账户所有线路 TCP 测速, 返回 (host, port, ms) 中延迟最低者。"""
    best: Optional[Tuple[str, int, float]] = None
    for r in get_hpc_routes(account):
        ms = tcp_ms(r["host"], int(r.get("port", 22)), timeout)
        tag = f"{ms:7.1f} ms" if ms is not None else "   unreachable"
        print(f"      {r.get('label', ''):22s} {r['host']}:{r.get('port', 22):<6}"
              f" {tag}")
        if ms is not None and (best is None or ms < best[2]):
            best = (r["host"], int(r.get("port", 22)), ms)
    return best


# ── 主流程 ──────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="读取并校验 ~/.physimx/flash/hpc_accounts.json (超算连接信息唯一来源)")
    ap.add_argument("--probe", action="store_true",
                    help="对每条线路做 TCP 测速并给出最低延迟线路")
    ap.add_argument("--json", action="store_true",
                    help="以原始 JSON 形式打印当前配置")
    ap.add_argument("--init", action="store_true",
                    help="若配置文件不存在则创建空骨架")
    ap.add_argument("--example", action="store_true",
                    help="写出格式示例文件 hpc_accounts.example.json")
    ap.add_argument("--timeout", type=float, default=5.0, help="TCP 测速超时 (秒)")
    args = ap.parse_args()

    path = hpc_accounts_file()

    if args.example:
        p = write_example_file()
        print(f"[OK] 格式示例已写出: {p}")
        return 0

    if args.init:
        ensure_hpc_accounts_file()

    print("=" * 66)
    print("  hpc_accounts.json — flash 超算连接信息的唯一来源")
    print("=" * 66)
    print(f"  路径: {path}")
    print(f"  存在: {'是' if path.exists() else '否 (读取将返回空配置)'}")
    print("-" * 66)

    data = load_hpc_accounts()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    names = list_hpc_accounts()
    print(f"  账户数: {len(names)}")
    if not names:
        print("  (无账户) 先运行 `--init` 生成骨架, 或运行 `--example` 查看格式示例。")
        return 0

    for name in names:
        acct = get_hpc_account(name) or {}
        print(f"\n  [{name}] {acct.get('title', '')}")
        print(f"    ssh_username : {get_hpc_ssh_username(name) or '(未配置)'}")
        print(f"    route_key    : {get_hpc_route_key(name) or '(未配置)'}")
        routes = get_hpc_routes(name)
        print(f"    routes       : {len(routes)} 条")
        for r in routes:
            print(f"      - {r.get('label', ''):22s} "
                  f"{r['host']}:{r.get('port', 22)}")
        if args.probe:
            if not routes:
                print("      (无线路, 跳过测速)")
            else:
                print("      TCP 测速:")
                best = probe_best(name, args.timeout)
                if best:
                    print(f"      -> 最低延迟: {best[0]}:{best[1]}  ({best[2]:.1f} ms)")
                else:
                    print("      -> 所有线路均不可达")

    # ── 校验 ──
    print("\n" + "-" * 66)
    problems = validate_accounts(data)
    if problems:
        print(f"  ⚠ 校验发现 {len(problems)} 个问题:")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  ✓ 校验通过 (accounts / ssh_username / routes 均合法)")

    flat = all_routes()
    uniq = {(r["host"], r["port"]) for r in flat}
    print(f"  去重后线路总数: {len(uniq)} (跨 {len(names)} 个账户)")

    print("\n" + "=" * 66)
    print("  提示: 密码不在本 JSON; 由 Fernet 加密存储于同目录 credentials.enc")
    print("  格式规范: flash/_core/credentials/hpc_config.py 模块 docstring")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
