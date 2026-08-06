"""
Flash 凭据管理 -- 统一管理脚本
==============================
主入口菜单，可导航到各个凭据管理模块。

用法:
    python -m flash._core.credentials.manage           # 主菜单 (模块方式,推荐)
    python -m flash._core.credentials.manage setup     # 一键设置所有凭据
    python -m flash._core.credentials.manage ssh       # 直接进入 SSH 管理
    python -m flash._core.credentials.manage gitee     # 直接进入 Gitee 管理
    python -m flash._core.credentials.manage api       # 直接进入 API 管理
"""

import sys
from pathlib import Path

# =======================================================================
# 直接运行时的自动转换:
#   如果 __package__ 为 None，说明是直接运行 (python manage.py),
#   此时用 runpy 以模块方式重新运行，使相对导入能正常工作。
# =======================================================================
if __name__ == "__main__" and __package__ is None:
    _CRED_DIR = Path(__file__).resolve().parent      # .../flash/_core/credentials/
    _CORE_DIR = _CRED_DIR.parent                    # .../flash/_core/
    _FLASH_DIR = _CORE_DIR.parent                  # .../flash/
    _PARENT = _FLASH_DIR.parent                    # flash/ 的父目录

    # standalone 模式: 将 flash/ 的父目录加入 sys.path
    if str(_PARENT) not in sys.path:
        sys.path.insert(0, str(_PARENT))

    # 用 runpy 以模块方式重新运行自己
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

    import runpy
    sys.argv.insert(0, __file__)  # 保留原始 argv
    runpy.run_module("flash._core.credentials.manage", run_name="__main__")
    sys.exit(0)


# =======================================================================
# 所有导入使用相对导入 (flash 独立包模式)
# =======================================================================
from ._core import get_credential_manager, get_user_name, get_user_name_source, set_user_name
from ._config import DEFAULT_USER_NAME


def _print_header():
    """打印标题和状态。"""
    try:
        cm = get_credential_manager()
        existing = cm.list_all()
        real_keys = [k for k in existing if k != "__meta__"]
        user_name = get_user_name()
    except SystemExit:
        real_keys = []
        try:
            user_name = get_user_name()
        except Exception:
            user_name = "hello"

    print(f"\n  {'=' * 55}")
    print(f"  Flash 凭据管理中心")
    source = get_user_name_source()
    source_note = f" (继承 {source})" if source == "physimx_core" else " (独立)"
    print(f"  当前用户: {user_name}{source_note}")
    if real_keys:
        print(f"  已保存凭据: {', '.join(real_keys)}")
    else:
        print(f"  当前未保存任何凭据")
    print(f"  {'=' * 55}")


def _set_user_name() -> None:
    """设置默认用户名。"""
    current = get_user_name()
    print(f"\n  👤 设置默认用户名")
    print(f"  {'─' * 55}")
    print(f"  当前用户名: {current}")
    print(f"  {'─' * 55}")

    new_name = input(f"\n  输入新用户名 [回车保留 '{current}']: ").strip()
    if not new_name:
        print("\n  [未修改]")
        return

    set_user_name(new_name)
    print(f"\n  ✅ 用户名已设为: {new_name}")


def _setup_ssh_presconfigured() -> None:
    """设置预配置 SSH 账户（带路由测试）。"""
    from ._config import ENTRIES, ENTRIES_BY_NAME
    from .flash_ssh import _get_ssh_username, test_all_routes, test_route
    from ._core import get_credential_manager, ask_one, set_primary_ssh, collect_ssh_accounts

    cm = get_credential_manager()

    # 收集预配置账号
    presconfigured = []
    for entry in ENTRIES:
        if not entry["name"].startswith("flash_ssh"):
            continue
        name = entry["name"]
        title = entry.get("title", name)
        ssh_user = _get_ssh_username(name)
        presconfigured.append((name, title, ssh_user, entry))

    if not presconfigured:
        print("\n  [提示] 未找到预配置 SSH 账户。")
        return

    # 显示预配置账号
    print(f"\n  📋 预配置 SSH 账户:")
    for i, (name, title, ssh_user, entry) in enumerate(presconfigured, 1):
        existing = cm.get(name)
        status = "✅ 已配置" if existing else "⬜ 未配置"
        print(f"    [{i}] {title}")
        print(f"        账号: {ssh_user}  [{status}]")

    print(f"\n  选项:")
    print(f"    [1-{len(presconfigured)}] 设置对应的预配置账号")
    print(f"    [A] 设置所有预配置账号")
    print(f"    [0] 跳过")

    choice = input(f"\n  请选择: ").strip().lower()

    if choice == "0":
        print("\n  [已跳过]")
        return
    elif choice == "a":
        # 设置所有预配置账号
        accounts = collect_ssh_accounts(cm)

        # 先进行路由测试
        print(f"\n  🔍 进行路由测试...")
        try:
            results = test_all_routes()
            if results:
                print(f"\n  {'─' * 60}")
                print(f"  路由测试结果 (延迟越低越好)")
                print(f"  {'─' * 60}")
                sorted_results = sorted(results.items(), key=lambda x: x[1][1])
                for name, (ok, delay, host, port, title) in sorted_results:
                    status = f"✅ {delay:.3f}s" if ok else f"❌ 超时"
                    print(f"    {title}")
                    print(f"      {host}:{port} → {status}")

                # 自动选择延迟最低的作为主账户
                if accounts:
                    best_name = sorted_results[0][0]
                    set_primary_ssh(cm, best_name)
                    print(f"\n  ✅ 已自动选择延迟最低的账号作为主账户: {best_name}")
        except Exception as e:
            print(f"\n  ⚠️  路由测试失败: {e}")

        # 依次设置每个预配置账号
        for name, title, ssh_user, entry in presconfigured:
            print(f"\n  {'=' * 60}")
            print(f"  📝 设置: {title}")
            print(f"  {'=' * 60}")
            print(f"  账号: {ssh_user}")
            print(f"  {'─' * 60}")

            data = {}
            for key, label, default in entry.get("fields", []):
                if key == "password":
                    print(f"\n  ⚠️  请为账号 {ssh_user} 设置密码")
                data[key] = ask_one(label, default)

            # 如果连接模式是 manual，询问额外字段
            if data.get("connection_mode") == "manual":
                print("\n  [手动模式] 需要额外信息:")
                for key, label, default in entry.get("manual_fields", []):
                    data[key] = ask_one(label, default)

            cm.set(name, data)
            print(f"\n  ✅ {title} 已保存。")

        print(f"\n  ✅ 所有预配置 SSH 账号设置完成！")
    elif choice.isdigit() and 1 <= int(choice) <= len(presconfigured):
        idx = int(choice) - 1
        name, title, ssh_user, entry = presconfigured[idx]

        print(f"\n  📝 设置: {title}")
        print(f"  {'─' * 50}")
        print(f"  账号: {ssh_user}")
        print(f"  {'─' * 50}")

        # 先进行路由测试
        try:
            results = test_all_routes()
            if name in results:
                ok, delay, host, port, _ = results[name]
                status = f"✅ {delay:.3f}s" if ok else f"❌ 超时"
                print(f"\n  🔍 路由测试: {host}:{port} → {status}")
        except Exception:
            pass

        data = {}
        for key, label, default in entry.get("fields", []):
            if key == "password":
                print(f"\n  ⚠️  请为账号 {ssh_user} 设置密码")
            data[key] = ask_one(label, default)

        if data.get("connection_mode") == "manual":
            print("\n  [手动模式] 需要额外信息:")
            for key, label, default in entry.get("manual_fields", []):
                data[key] = ask_one(label, default)

        cm.set(name, data)
        print(f"\n  ✅ {title} 已保存。")

        # 如果是第一个账户，设为主账户
        accounts = collect_ssh_accounts(cm)
        if len(accounts) == 1:
            set_primary_ssh(cm, name)
            print(f"  ✅ 已设为默认主账户。")
    else:
        print("\n  [无效选择]")


def _setup_all() -> None:
    """一键设置所有凭据。"""
    user_name = get_user_name()
    print(f"\n  🚀 一键设置所有凭据")
    print(f"  {'─' * 55}")
    print(f"  默认值: 用户名={user_name}, 密码=123")
    print(f"  {'─' * 55}\n")

    # 1. FLASH SSH
    print("  [1/4] FLASH SSH 凭据")
    print(f"  {'─' * 55}")
    _setup_ssh_presconfigured()

    # 2. Gitee
    print(f"\n  [2/4] Gitee 凭据")
    print(f"  {'─' * 55}")
    from .gitee import setup_gitee
    setup_gitee()

    # 3. DeepSeek API
    print(f"\n  [3/4] DeepSeek API 凭据")
    print(f"  {'─' * 55}")
    from .api_keys import setup_api
    setup_api("deepseek_api")

    print(f"\n  ✅ 所有凭据设置完成！")


def main():
    """主入口。"""
    args = sys.argv[1:]

    # 命令行模式
    if args:
        if args[0] in ("setup", "all"):
            force = "--force" in args or "-f" in args
            _setup_all()
            return
        elif args[0] == "ssh":
            from .flash_ssh import interactive_menu
            cm = get_credential_manager()
            interactive_menu(cm)
            return
        elif args[0] == "gitee":
            from .gitee import interactive_menu
            interactive_menu()
            return
        elif args[0] == "api":
            from .api_keys import interactive_menu
            interactive_menu()
            return
        elif args[0] in ("pypi", "py"):
            from .pypi import setup_pypi, show_pypi
            if "--show" in args:
                show_pypi()
            else:
                setup_pypi(args[1] if len(args) > 1 and not args[1].startswith("-") else None)
            return

    # 交互模式
    try:
        get_credential_manager()
    except SystemExit:
        return

    while True:
        _print_header()
        print("  [1] 一键设置所有凭据")
        print("  [2] FLASH SSH 账户管理     (增/删/改)")
        print("  [3] Gitee 访问令牌管理   (设置/查看/删除)")
        print("  [4] API 密钥管理          (AI API)")
        print("  [5] PyPI 发布令牌管理     (pypi.org / test.pypi.org)")
        print("  [6] 查看所有已保存凭据")
        print("  [7] 设置默认用户名        (当前: {}, 默认: {})".format(get_user_name(), DEFAULT_USER_NAME))
        print("  [0] 退出")

        choice = input("\n  请选择 [0-7]: ").strip()

        if choice == "1":
            _setup_all()
        elif choice == "2":
            from .flash_ssh import interactive_menu
            cm = get_credential_manager()
            interactive_menu(cm)
        elif choice == "3":
            from .gitee import interactive_menu
            interactive_menu()
        elif choice == "4":
            from .api_keys import interactive_menu
            interactive_menu()
        elif choice == "5":
            from .pypi import setup_pypi, show_pypi
            print("\n  [P] 设置令牌")
            print("  [V] 查看状态")
            sub = input("  请选择 [P/V]: ").strip().lower()
            if sub in ("v", "view"):
                show_pypi()
            else:
                setup_pypi()
        elif choice == "6":
            cm = get_credential_manager()
            existing = cm.list_all()
            real_keys = [k for k in existing if k != "__meta__"]
            if not real_keys:
                print("\n  当前没有保存任何凭据。")
            else:
                print(f"\n  {'─' * 55}")
                print(f"  已保存凭据 ({len(real_keys)} 组)")
                print(f"  {'─' * 55}")
                for name, data in existing.items():
                    if name == "__meta__":
                        continue
                    print(f"\n  [{name}]")
                    for k, v in data.items():
                        print(f"    {k:12s}: {v}")
                print(f"\n  {'─' * 55}")
                # 显示 Flash 专属存储位置
                try:
                    storage_dir = cm._cred_dir
                except AttributeError:
                    # 兼容旧版（无 subdir 支持）
                    from pathlib import Path
                    storage_dir = Path.home() / ".physimx" / "flash"
                print(f"  存储位置: {storage_dir}/")
            input("\n  按回车返回...")
        elif choice == "7":
            _set_user_name()
        elif choice == "0":
            print("\n  再见!\n")
            break
        else:
            print("  [无效选择]")


if __name__ == "__main__":
    main()
