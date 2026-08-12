"""
Flash 凭据管理 -- Gitee 凭据管理
=====================================
管理 Gitee 访问令牌。

用法:
    python -m flash._core.credentials.gitee          # 交互菜单
    python -m flash._core.credentials.gitee setup   # 设置 Gitee 凭据
    python -m flash._core.credentials.gitee show    # 查看 Gitee 凭据
"""

import sys
from typing import Optional

from ._core import (
    ask_one,
    get_credential_manager,
    mask_secret,
)
from ._config import DEFAULT_USER_NAME, DEFAULT_PASSWORD


def setup_gitee() -> bool:
    """设置 Gitee 凭据。"""
    cm = get_credential_manager()

    print(f"\n  📝 设置 Gitee 凭据")
    print(f"  {'─' * 50}")

    # 获取默认值
    entry_def = next((e for e in __import__("_config", fromlist=["ENTRIES"]).ENTRIES if e["name"] == "gitee"), None)
    if entry_def is None:
        print("\n  ❌ 未找到 Gitee 配置定义。")
        return False

    data = {}
    for key, label, default in entry_def["fields"]:
        # 使用全局默认值
        if key == "username" and default == "hello":
            default = DEFAULT_USER_NAME
        elif key == "token" and default == "123":
            default = DEFAULT_PASSWORD
        data[key] = ask_one(label, default)

    cm.set("gitee", data)

    # 自动补存 login (登录名): git 无交互直连认证必须用 login, 显示名会 403
    login = _query_gitee_login(data.get("token", ""))
    if login:
        data["login"] = login
        cm.set("gitee", data)
        print(f"  ✅ 已自动获取登录名: {login}")
    else:
        print(f"  ⚠ 未能获取登录名 (token 可能无效或网络问题), "
              f"无交互直连需手动补充 login 字段")

    print(f"\n  ✅ Gitee 凭据已保存。")
    return True


def _query_gitee_login(token: str) -> str:
    """通过 Gitee API 查询 token 对应的登录名 (login)。

    用于 git 无交互直连: https://login:token@gitee.com/...
    返回空串表示查询失败。
    """
    if not token:
        return ""
    import json
    import urllib.error
    import urllib.request
    try:
        url = f"https://gitee.com/api/v5/user?access_token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            user_info = json.loads(resp.read().decode("utf-8"))
        return str(user_info.get("login", ""))
    except Exception:
        return ""


def show_gitee(raw: bool = False) -> None:
    """查看 Gitee 凭据。"""
    cm = get_credential_manager()
    data = cm.get("gitee")

    if not data:
        print("\n  [提示] 尚未设置 Gitee 凭据。")
        return

    print(f"\n  {'─' * 50}")
    print(f"  Gitee 凭据")
    print(f"  {'─' * 50}")

    display = data if raw else mask_secret(data)
    for k, v in display.items():
        print(f"    {k:12s}: {v}")
    print(f"  {'─' * 50}")
    if not raw:
        print(f"  💡 使用 --raw 查看原始 token")


def delete_gitee() -> bool:
    """删除 Gitee 凭据。"""
    cm = get_credential_manager()

    if not cm.get("gitee"):
        print("\n  [提示] 尚未设置 Gitee 凭据。")
        return False

    confirm = input("\n  确认删除 Gitee 凭据? [y/N]: ").strip().lower()
    if confirm != "y":
        print("\n  [已取消]")
        return False

    try:
        cm.delete("gitee")
        print("\n  ✅ Gitee 凭据已删除。")
        return True
    except Exception as e:
        print(f"\n  ❌ 删除失败: {e}")
        return False


def test_gitee() -> bool:
    """测试 Gitee 连接。"""
    cm = get_credential_manager()
    data = cm.get("gitee")

    if not data:
        print("\n  [提示] 尚未设置 Gitee 凭据。")
        return False

    token = data.get("token")
    username = data.get("username")
    repo_url = data.get("repo_url", "")

    print(f"\n  🔧 测试 Gitee 连接...")
    print(f"  用户名: {username}")
    print(f"  仓库: {repo_url}")

    # 解析仓库 owner 和 repo name
    import re
    match = re.search(r"gitee\.com[:/]([^/]+)/([^/.]+)", repo_url)
    if not match:
        print(f"\n  ⚠️  无法解析仓库 URL: {repo_url}")
        print(f"  请确保 URL 格式类似: https://gitee.com/owner/repo.git")
        return False

    owner, repo = match.group(1), match.group(2).rstrip(".git")

    # 测试 1: 验证 token (获取用户信息)
    print(f"\n  [1/2] 验证访问令牌...")
    import urllib.request
    import urllib.error
    import json

    try:
        # 获取用户信息
        url = f"https://gitee.com/api/v5/user?access_token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            user_info = json.loads(resp.read().decode("utf-8"))

        if "login" in user_info:
            print(f"  ✅ Token 有效 (用户: {user_info.get('login')})")
        else:
            print(f"  ❌ Token 验证失败: {user_info}")
            return False

    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"  ❌ Token 验证失败 (HTTP {e.code}): {error_msg}")
        return False
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

    # 测试 2: 验证仓库访问
    print(f"\n  [2/2] 验证仓库访问...")
    try:
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}?access_token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            repo_info = json.loads(resp.read().decode("utf-8"))

        if "name" in repo_info:
            print(f"  ✅ 仓库可访问: {repo_info.get('name')}")
            print(f"  仓库 URL: {repo_info.get('html_url', repo_url)}")
        else:
            print(f"  ⚠️  仓库访问异常: {repo_info}")
            return False

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  ⚠️  仓库不存在或无访问权限: {owner}/{repo}")
            print(f"  请检查仓库 URL 是否正确，以及 token 是否有访问权限")
        else:
            error_msg = e.read().decode("utf-8")
            print(f"  ❌ 仓库访问失败 (HTTP {e.code}): {error_msg}")
        return False
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

    print(f"\n  ✅ Gitee 连接测试通过！")
    return True


def interactive_menu() -> None:
    """交互式菜单。"""
    while True:
        print(f"\n  {'=' * 50}")
        print(f"  Gitee 凭据管理")
        print(f"  {'=' * 50}")
        print("  [1] 设置/修改 Gitee 凭据")
        print("  [2] 查看 Gitee 凭据")
        print("  [3] 删除 Gitee 凭据")
        print("  [4] 测试 Gitee 连接")
        print("  [0] 返回")

        choice = input("\n  请选择 [0-4]: ").strip()

        if choice == "1":
            setup_gitee()
        elif choice == "2":
            raw = input("  显示原始 token? [y/N]: ").strip().lower() == "y"
            show_gitee(raw)
        elif choice == "3":
            delete_gitee()
        elif choice == "4":
            test_gitee()
        elif choice == "0":
            break
        else:
            print("  [无效选择]")


if __name__ == "__main__":
    main_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if main_arg == "setup":
        setup_gitee()
    elif main_arg == "show":
        raw = "--raw" in sys.argv
        show_gitee(raw)
    elif main_arg == "del":
        delete_gitee()
    elif main_arg == "test":
        test_gitee()
    else:
        interactive_menu()
