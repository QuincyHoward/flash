"""
Flash 凭据管理 -- FLASH SSH 账户管理 (多账户+多线路版)
======================================================
支持对多个超算 SSH 账户的增/删/改/查，以及主账户管理。
支持多线路测试与选择（自动选择最快线路）。

用法:
    python -m flash._core.credentials.flash_ssh       # 交互菜单
    python -m flash._core.credentials.flash_ssh add   # 添加新超算账户
    python -m flash._core.credentials.flash_ssh test  # 测试所有线路
"""

import sys
from pathlib import Path

# ── 直接运行时的自动转换 ─────────────────────────────
#    如果 __package__ 为 None，说明是直接运行 (python flash_ssh.py),
#    此时用 runpy 以模块方式重新运行，使相对导入能正常工作。
if __name__ == "__main__" and __package__ is None:
    _CRED_DIR = Path(__file__).resolve().parent
    _CORE_DIR = _CRED_DIR.parent
    _FLASH_DIR = _CORE_DIR.parent
    _PARENT = _FLASH_DIR.parent

    # standalone 模式: 将 flash/ 的父目录加入 sys.path
    if str(_PARENT) not in sys.path:
        sys.path.insert(0, str(_PARENT))

    import runpy
    sys.argv.insert(0, __file__)
    runpy.run_module("flash._core.credentials.flash_ssh", run_name="__main__")
    sys.exit(0)


import socket
import time
from typing import Optional, List, Dict, Any

# ── 导入 (模块方式, 统一使用相对导入) ─────────────────────────────
from ._core import (
    ask_one,
    collect_ssh_accounts,
    get_credential_manager,
    get_primary_ssh,
    get_user_name,
    get_default_password,
    mask_secret,
    next_ssh_number,
    set_primary_ssh,
    ssh_account_name,
)
from ._config import PRECONFIGURED_SSH, get_ssh_username, get_ssh_routes


# ── 线路测试 ──────────────────────────────────────────

def test_route(host: str, port: int, timeout: float = 5.0) -> Optional[float]:
    """
    测试一条 SSH 线路的连通性和延迟。

    参数:
        host: SSH 主机名
        port: SSH 端口
        timeout: 超时时间（秒）

    返回:
        延迟（秒），如果连接失败则返回 None
    """
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        latency = time.time() - start
        sock.close()
        return latency
    except (socket.timeout, socket.error, OSError):
        return None


def test_all_routes(routes: List[Dict[str, Any]], timeout: float = 5.0) -> List[Dict[str, Any]]:
    """
    测试所有线路，返回测试结果列表。

    返回:
        [{"index": 0, "host": ..., "port": ..., "label": ..., "latency": 0.123, "ok": True}, ...]
    """
    results = []
    for i, route in enumerate(routes):
        host = route["host"]
        port = route["port"]
        label = route.get("label", f"{host}:{port}")
        latency = test_route(host, port, timeout)
        results.append({
            "index": i,
            "host": host,
            "port": port,
            "label": label,
            "latency": latency,
            "ok": latency is not None,
        })
    return results


def select_best_route(routes: List[Dict[str, Any]], timeout: float = 5.0) -> int:
    """
    测试所有线路，自动选择延迟最低的线路。

    返回:
        最佳线路的索引（如果没有可用线路，返回 0）
    """
    results = test_all_routes(routes, timeout)
    ok_results = [r for r in results if r["ok"]]
    if not ok_results:
        return 0
    best = min(ok_results, key=lambda r: r["latency"])
    return best["index"]


def show_route_test_results(results: List[Dict[str, Any]]) -> None:
    """显示线路测试结果。"""
    print("\n  ─── 线路测试结果 ──────────────────────────────────")
    for r in results:
        status = f"✅ {r['latency']*1000:.1f} ms" if r["ok"] else "❌ 超时"
        print(f"    [{r['index']+1}] {r['label']:30s} {status}")
    print("  ─────────────────────────────────────────────────────")


# ── SSH 账户操作 ──────────────────────────────────────────

def _get_ssh_username(name: str) -> str:
    """获取 SSH 用户名（从配置中读取）。"""
    return get_ssh_username(name)


def _get_routes(name: str) -> List[Dict[str, Any]]:
    """获取账户的线路列表（从配置中读取）。"""
    return get_ssh_routes(name)


def add_account(cm, number: int = None, interactive: bool = False) -> None:
    """添加/修改 SSH 账户。"""
    if number is None:
        number = next_ssh_number(cm)
    name = ssh_account_name(number)
    
    # 尝试从预配置获取
    ssh_username = get_ssh_username(name)
    routes = get_ssh_routes(name)
    
    # 如果是手动添加（不在预配置中），询问用户名
    if ssh_username == name:
        print(f"\n  --- {'添加新' if not cm.get(name) else '修改'} SSH 账户: {name} ---")
        ssh_username = ask_one("  SSH 用户名", name)
        routes = []
    else:
        print(f"\n  --- {'添加新' if not cm.get(name) else '修改'} SSH 账户: {name} ---")
        print(f"  SSH 用户名: {ssh_username}")

    # 设置密码
    default_pwd = get_default_password()
    password = ask_one("  密码", default_pwd)
    data = {
        "ssh_username": ssh_username,
        "password": password,
        "active_route": 0,
    }
    cm.set(name, data)

    # 测试线路
    if routes:
        print(f"\n  📡 测试所有线路...")
        results = test_all_routes(routes)
        show_route_test_results(results)

        # 自动选择最快线路
        ok_results = [r for r in results if r["ok"]]
        if ok_results:
            best = min(ok_results, key=lambda r: r["latency"])
            data["active_route"] = best["index"]
            cm.set(name, data)
            print(f"  ✅ 自动选择线路: [{best['index']+1}] {best['label']} ({best['latency']*1000:.1f} ms)")
        else:
            print("\n  [警告] 所有线路均不可达，请检查网络。")

    print(f"\n  ✅ 已保存账户: {name}")

    # 如果是第一个账户，设为主账户
    if number == 1 or not get_primary_ssh(cm):
        set_primary_ssh(cm, name)
        print(f"  ✅ 已设为主账户: {name}")


def delete_account(cm) -> None:
    """删除 SSH 账户。"""
    accounts = collect_ssh_accounts(cm)
    name = _pick_account(cm, accounts)
    if not name:
        return
    primary = get_primary_ssh(cm)
    if name == primary:
        print("\n  [警告] 正在删除主账户！")
        confirm = input("  确认删除? [y/N]: ").strip().lower()
        if confirm != "y":
            print("\n  已取消。")
            return

    cm.delete(name)
    print(f"\n  ✅ 已删除账户: {name}")

    # 如果删除了主账户，重新设置
    if name == primary and collect_ssh_accounts(cm):
        new_primary = collect_ssh_accounts(cm)[0]
        set_primary_ssh(cm, new_primary)
        print(f"  ✅ 新主账户: {new_primary}")


def show_account(cm) -> None:
    """查看 SSH 账户详情。"""
    accounts = collect_ssh_accounts(cm)
    name = _pick_account(cm, accounts)
    if not name:
        return
    data = cm.get(name)
    if not data:
        print(f"\n  [错误] 账户不存在: {name}")
        return

    primary = get_primary_ssh(cm)
    routes = _get_routes(name)
    active = data.get("active_route", 0)

    print(f"\n  --- SSH 账户: {name}{' [主]' if name == primary else ''} ---")
    print(f"    ssh_username: {data.get('ssh_username', '(未设置)')}")
    print(f"    password:     {'*' * 8}")
    if routes:
        print(f"    可用线路:   {len(routes)} 条")
        print(f"    当前线路:   [{active+1}] {routes[active].get('label', routes[active]['host'])}")


def test_routes(cm) -> None:
    """测试指定账户的所有线路。"""
    accounts = collect_ssh_accounts(cm)
    name = _pick_account(cm, accounts)
    if not name:
        return

    routes = _get_routes(name)
    if not routes:
        print("\n  [提示] 该账户没有配置线路。")
        return

    print(f"\n  📡 测试账户 {name} 的所有线路...")
    results = test_all_routes(routes)
    show_route_test_results(results)

    # 询问是否选择最佳线路
    ok_results = [r for r in results if r["ok"]]
    if ok_results:
        best = min(ok_results, key=lambda r: r["latency"])
        choice = input(f"\n  选择最佳线路 [{best['index']+1}]? [Y/n]: ").strip().lower()
        if choice != "n":
            data = cm.get(name) or {}
            data["active_route"] = best["index"]
            cm.set(name, data)
            print(f"  ✅ 已选择线路: [{best['index']+1}] {best['label']}")


def select_route(cm) -> None:
    """手动选择线路。"""
    accounts = collect_ssh_accounts(cm)
    name = _pick_account(cm, accounts)
    if not name:
        return

    routes = _get_routes(name)
    if not routes:
        print("\n  [提示] 该账户没有配置线路。")
        return

    print(f"\n  --- 选择 {name} 的线路 ---")
    for i, route in enumerate(routes):
        label = route.get("label", f"{route['host']}:{route['port']}")
        print(f"    [{i+1}] {label}")

    try:
        idx = int(input(f"\n  请选择 [1-{len(routes)}, 0=自动测试]: ").strip()) - 1
        if idx == -1:
            # 自动测试
            best_idx = select_best_route(routes)
            data = cm.get(name) or {}
            data["active_route"] = best_idx
            cm.set(name, data)
            print(f"  ✅ 已自动选择: [{best_idx+1}] {routes[best_idx].get('label', '')}")
        elif 0 <= idx < len(routes):
            data = cm.get(name) or {}
            data["active_route"] = idx
            cm.set(name, data)
            print(f"  ✅ 已选择线路: [{idx+1}] {routes[idx].get('label', '')}")
        else:
            print("\n  [错误] 无效选择。")
    except ValueError:
        print("\n  [错误] 无效输入。")


def _pick_account(cm, accounts=None) -> Optional[str]:
    """让用户选择一个 SSH 账户，返回账户名。"""
    if accounts is None:
        accounts = collect_ssh_accounts(cm)
    if not accounts:
        print("\n  [提示] 尚未添加任何 SSH 账户。")
        return None
    if len(accounts) == 1:
        return accounts[0]
    print("\n  请选择 SSH 账户:")
    for i, n in enumerate(accounts):
        primary = get_primary_ssh(cm)
        tag = " [主]" if n == primary else ""
        print(f"    [{i+1}] {n}{tag}")
    try:
        idx = int(input("\n  请选择 [1-{}]: ".format(len(accounts)))) - 1
        if 0 <= idx < len(accounts):
            return accounts[idx]
    except ValueError:
        pass
    print("\n  [错误] 无效选择。")
    return None


def _add_preconfigured(cm, idx: int) -> None:
    """添加预配置 SSH 账户（只需输入密码）。"""
    if idx < 0 or idx >= len(PRECONFIGURED_SSH):
        print("\n  [错误] 无效选择。")
        return

    pre = PRECONFIGURED_SSH[idx]
    name = pre["name"]
    title = pre["title"]
    ssh_username = pre["ssh_username"]
    routes = pre["routes"]

    print(f"\n  ─── 添加预配置账户: {title} ──────────────────")
    print(f"  SSH 用户名: {ssh_username}")
    print(f"  可用线路: {len(routes)} 条")
    print()

    default_pwd = get_default_password()
    password = ask_one("  密码", default_pwd)

    data = {
        "ssh_username": ssh_username,
        "password": password,
        "active_route": 0,
    }

    cm.set(name, data)
    print(f"\n  ✅ 已添加账户: {name}")
    print(f"      SSH 用户名: {ssh_username}")
    print(f"      密码: {mask_secret(password)}")

    # 测试线路
    print(f"\n  📡 测试所有线路...")
    results = test_all_routes(routes)
    show_route_test_results(results)

    ok_results = [r for r in results if r["ok"]]
    if ok_results:
        best = min(ok_results, key=lambda r: r["latency"])
        data["active_route"] = best["index"]
        cm.set(name, data)
        print(f"  ✅ 自动选择线路: [{best['index']+1}] {best['label']} ({best['latency']*1000:.1f} ms)")
    else:
        print(f"\n  [警告] 所有线路均不可达，请检查网络。")


def interactive_menu(cm) -> None:
    """交互菜单。"""
    # 确保预配置账户已加载
    try:
        from ._config import autodiscover_configs
        autodiscover_configs()
    except (ImportError, ValueError):
        pass

    while True:
        accounts = collect_ssh_accounts(cm)
        primary = get_primary_ssh(cm)
        print("\n" + "=" * 50)
        print("  FLASH SSH 账户管理")
        if accounts:
            print(f"  主账户: {primary}")
            print(f"  全部账户: {', '.join(accounts)}")
        else:
            print("  当前未添加任何 SSH 账户")
            if PRECONFIGURED_SSH:
                print(f"  (预配置账户: {', '.join([p['title'] for p in PRECONFIGURED_SSH])})")
        print("=" * 50)

        if not accounts and PRECONFIGURED_SSH:
            # 显示预配置账户选项
            print("\n  请选择:")
            print("  [1] 添加预配置账户 (只需输入密码)")
            print("  [2] 手动添加新账户")
            print("  [0] 返回")
            print("=" * 50)
            try:
                choice = input("\n  请选择 [0-2]: ").strip()
            except EOFError:
                break

            if choice == "1":
                print(f"\n  请选择预配置账户:")
                for i, p in enumerate(PRECONFIGURED_SSH):
                    print(f"    [{i+1}] {p['title']}")
                try:
                    idx = int(input(f"\n  请选择 [1-{len(PRECONFIGURED_SSH)}]: ").strip()) - 1
                    _add_preconfigured(cm, idx)
                except ValueError:
                    print("\n  [错误] 无效选择。")
            elif choice == "2":
                add_account(cm)
            elif choice == "0":
                break
            else:
                print("\n  [错误] 无效选择。")
        else:
            # 正常菜单
            print("  [1] 添加/修改 SSH 账户")
            print("  [2] 删除 SSH 账户")
            print("  [3] 查看 SSH 账户详情")
            print("  [4] 测试所有线路")
            print("  [5] 手动选择线路")
            print("  [6] 设置主 SSH 账户")
            print("  [0] 返回")
            print("=" * 50)
            try:
                choice = input("\n  请选择 [0-6]: ").strip()
            except EOFError:
                break

            if choice == "1":
                add_account(cm)
            elif choice == "2":
                delete_account(cm)
            elif choice == "3":
                show_account(cm)
            elif choice == "4":
                test_routes(cm)
            elif choice == "5":
                select_route(cm)
            elif choice == "6":
                accounts = collect_ssh_accounts(cm)
                if not accounts:
                    print("\n  [提示] 尚未添加任何 SSH 账户。")
                    continue
                print("\n  请选择新的主账户:")
                for i, n in enumerate(accounts):
                    print(f"    [{i+1}] {n}")
                try:
                    idx = int(input("\n  请选择 [1-{}]: ".format(len(accounts)))) - 1
                    if 0 <= idx < len(accounts):
                        set_primary_ssh(cm, accounts[idx])
                        print(f"\n  ✅ 已设为主账户: {accounts[idx]}")
                except ValueError:
                    print("\n  [错误] 无效选择。")
            elif choice == "0":
                break
            else:
                print("\n  [错误] 无效选择。")


if __name__ == "__main__":
    cm = get_credential_manager()
    interactive_menu(cm)
