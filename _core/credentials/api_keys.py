"""
Flash 凭据管理 -- API 密钥管理
====================================
管理各种 AI API 密钥 (DeepSeek、OpenAI、Claude、Gemini 等)。

用法:
    python -m flash._core.credentials.api_keys           # 交互菜单
    python -m flash._core.credentials.api_keys setup     # 设置 API 密钥
    python -m flash._core.credentials.api_keys list      # 列出所有 API 凭据
"""

import sys
from typing import Dict, Any, Optional, List

from ._core import (
    ask_one,
    get_credential_manager,
    mask_secret,
)
from ._config import ENTRIES, ENTRIES_BY_NAME, DEFAULT_PASSWORD


# API 类型的凭据名识别: 名称以 _api 结尾
def _is_api_entry(entry: Dict[str, Any]) -> bool:
    """判断是否为 API 类型的凭据。"""
    return entry["name"].endswith("_api")


def _get_api_entries() -> List[Dict[str, Any]]:
    """获取所有 API 类型的凭据定义。"""
    return [e for e in ENTRIES if _is_api_entry(e)]


def setup_api(name: str) -> bool:
    """设置指定 API 的凭据。"""
    cm = get_credential_manager()

    entry_def = ENTRIES_BY_NAME.get(name)
    if entry_def is None:
        print(f"\n  [错误] 未找到 API 定义: {name}")
        return False

    print(f"\n  📝 设置 {entry_def['title']}")
    print(f"  {'─' * 50}")

    data = {}
    for key, label, default in entry_def["fields"]:
        # 使用全局默认值
        if default == "123":
            default = DEFAULT_PASSWORD
        data[key] = ask_one(label, default)

    cm.set(name, data)
    print(f"\n  ✅ {entry_def['title']} 凭据已保存。")
    return True


def show_api(name: str, raw: bool = False) -> None:
    """查看指定 API 的凭据。"""
    cm = get_credential_manager()
    data = cm.get(name)

    if not data:
        entry_def = ENTRIES_BY_NAME.get(name)
        title = entry_def["title"] if entry_def else name
        print(f"\n  [提示] 尚未设置: {title}")
        return

    entry_def = ENTRIES_BY_NAME.get(name)
    title = entry_def["title"] if entry_def else name

    print(f"\n  {'─' * 50}")
    print(f"  {title}")
    print(f"  {'─' * 50}")

    display = data if raw else mask_secret(data)
    for k, v in display.items():
        print(f"    {k:12s}: {v}")
    print(f"  {'─' * 50}")
    if not raw:
        print(f"  💡 使用 --raw 查看原始密钥")


def list_all_api() -> None:
    """列出所有 API 凭据。"""
    cm = get_credential_manager()
    api_entries = _get_api_entries()

    print(f"\n  {'─' * 50}")
    print(f"  API 凭据列表")
    print(f"  {'─' * 50}")

    found = False
    for entry_def in api_entries:
        name = entry_def["name"]
        data = cm.get(name)
        if data:
            found = True
            title = entry_def["title"]
            print(f"\n  [{name}]")
            print(f"    名称: {title}")
            masked = mask_secret(data)
            for k, v in masked.items():
                print(f"    {k:12s}: {v}")

    if not found:
        print("\n  [提示] 尚未设置任何 API 凭据。")
    print(f"\n  {'─' * 50}")


def delete_api(name: str) -> bool:
    """删除指定 API 的凭据。"""
    cm = get_credential_manager()

    if not cm.get(name):
        entry_def = ENTRIES_BY_NAME.get(name)
        title = entry_def["title"] if entry_def else name
        print(f"\n  [提示] 尚未设置: {title}")
        return False

    confirm = input(f"\n  确认删除 {name} 凭据? [y/N]: ").strip().lower()
    if confirm != "y":
        print("\n  [已取消]")
        return False

    try:
        cm.delete(name)
        print(f"\n  ✅ {name} 凭据已删除。")
        return True
    except Exception as e:
        print(f"\n  ❌ 删除失败: {e}")
        return False


def interactive_menu() -> None:
    """交互式菜单。"""
    while True:
        api_entries = _get_api_entries()

        print(f"\n  {'=' * 50}")
        print(f"  API 密钥管理")
        print(f"  {'=' * 50}")
        print("  [1] 设置 API 密钥")
        print("  [2] 查看所有 API 凭据")
        print("  [3] 删除 API 凭据")
        print("  [0] 返回")

        choice = input("\n  请选择 [0-3]: ").strip()

        if choice == "1":
            _setup_menu(api_entries)
        elif choice == "2":
            list_all_api()
        elif choice == "3":
            _delete_menu()
        elif choice == "0":
            break
        else:
            print("  [无效选择]")


def _setup_menu(api_entries: List[Dict[str, Any]]) -> None:
    """选择要设置的 API。"""
    if not api_entries:
        print("\n  [提示] 尚未定义任何 API 类型。")
        return

    print("\n  可选 API:")
    for i, entry in enumerate(api_entries, 1):
        print(f"    [{i}] {entry['title']}")

    choice = input(f"\n  选择要设置的 API [1-{len(api_entries)}, 0=取消]: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(api_entries):
            setup_api(api_entries[idx]["name"])
    except ValueError:
        pass


def _delete_menu() -> None:
    """删除菜单（选择要删除的 API）。"""
    cm = get_credential_manager()
    api_entries = _get_api_entries()

    # 只显示已设置的
    existing = [(e["name"], e["title"]) for e in api_entries if cm.get(e["name"])]

    if not existing:
        print("\n  [提示] 尚未设置任何 API 凭据。")
        return

    print("\n  可选 API 凭据:")
    for i, (name, title) in enumerate(existing, 1):
        print(f"    [{i}] {title}")

    choice = input(f"\n  选择要删除的编号 [1-{len(existing)}, 0=取消]: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(existing):
            delete_api(existing[idx][0])
    except ValueError:
        pass


if __name__ == "__main__":
    main_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if main_arg == "setup":
        name = sys.argv[2] if len(sys.argv) > 2 else "deepseek_api"
        setup_api(name)
    elif main_arg == "show":
        name = sys.argv[2] if len(sys.argv) > 2 else "deepseek_api"
        raw = "--raw" in sys.argv
        show_api(name, raw)
    elif main_arg == "list":
        list_all_api()
    elif main_arg == "del":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        if name:
            delete_api(name)
        else:
            _delete_menu()
    else:
        interactive_menu()
