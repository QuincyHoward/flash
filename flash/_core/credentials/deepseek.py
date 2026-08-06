"""
Flash 凭据管理 -- DeepSeek API 管理
==========================================
管理 DeepSeek API 密钥 (太极网关)。

用法:
    python -m flash._core.credentials.deepseek          # 交互菜单
    python -m flash._core.credentials.deepseek setup   # 设置 DeepSeek API
    python -m flash._core.credentials.deepseek show    # 查看 DeepSeek API
"""

import sys
from pathlib import Path

# ── 直接运行时的自动转换 ────────────────────────────
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
    runpy.run_module("flash._core.credentials.deepseek", run_name="__main__")
    sys.exit(0)


# ── 导入 (模块方式, 统一使用相对导入) ─────────────────────────────
from ._core import (
    ask_one,
    get_credential_manager,
    mask_secret,
)


# ── 设置 DeepSeek API 凭据 ─────────────────────────────────────

def setup_deepseek(cm, silent: bool = False) -> None:
    """设置/修改 DeepSeek API 凭据。"""
    data = cm.get("deepseek_api") or {}

    current_url = data.get("base_url", "")
    current_key = data.get("api_key", "")

    if not silent:
        print("\n  DeepSeek API (太极网关)")
        print("  (直接回车使用默认值)\n")

    # API 地址
    default_url = "https://gateway.taichuai.cn/modelhub/api/v1"
    if current_url:
        default_url = current_url

    if not silent:
        url = ask_one("  API 地址", default_url)
    else:
        url = default_url

    # API Key
    default_key = "(隐藏)"
    if current_key:
        default_key = "(已保存)"

    if not silent:
        key = ask_one("  API Key", default_key)
        if key == "(隐藏)" or key == "(已保存)":
            key = current_key
    else:
        # 用户输入了新 key
        pass

    if not key or key == "(隐藏)" or key == "(已保存)":
        key = current_key

    if not key:
        print("\n  [错误] API Key 不能为空。")
        return

    data = {"base_url": url, "api_key": key}
    cm.set("deepseek_api", data)

    if not silent:
        print(f"\n  ✅ DeepSeek API 凭据已保存。")
        print(f"     API 地址: {url}")
        print(f"     API Key:  {mask_secret(key)}")


# ── 查看 DeepSeek API 凭据 ─────────────────────────────────────

def show_deepseek(cm) -> None:
    """查看 DeepSeek API 凭据。"""
    data = cm.get("deepseek_api")

    print("\n" + "=" * 50)
    print("  DeepSeek API 凭据")
    print("=" * 50)

    if not data:
        print("\n  [提示] 尚未设置 DeepSeek API 凭据。\n")
        return

    print(f"\n  API 地址: {data.get('base_url', '(未设置)')}")
    key = data.get("api_key", "")
    if key:
        print(f"  API Key:  {mask_secret(key)}")
    else:
        print(f"  API Key:  (未设置)")

    print()


# ── 删除 DeepSeek API 凭据 ─────────────────────────────────────

def delete_deepseek(cm) -> None:
    """删除 DeepSeek API 凭据。"""
    data = cm.get("deepseek_api")
    if not data:
        print("\n  [提示] 尚未设置 DeepSeek API 凭据。")
        return

    show_deepseek(cm)

    try:
        confirm = input("\n  确认删除 DeepSeek API 凭据? [y/N]: ").strip().lower()
    except EOFError:
        confirm = "n"

    if confirm == "y":
        cm.delete("deepseek_api")
        print("\n  ✅ DeepSeek API 凭据已删除。")
    else:
        print("\n  [提示] 已取消。")


# ── 交互菜单 ─────────────────────────────────────────

def interactive_menu(cm) -> None:
    """DeepSeek API 管理交互菜单。"""
    while True:
        print("\n" + "=" * 50)
        print("  DeepSeek API 管理")
        print("=" * 50)
        print("  [1] 设置/修改 DeepSeek API")
        print("  [2] 查看 DeepSeek API")
        print("  [3] 删除 DeepSeek API")
        print("  [0] 返回")
        print("=" * 50)

        try:
            choice = input("\n  请选择 [0-3]: ").strip()
        except EOFError:
            break

        if choice == "1":
            setup_deepseek(cm)
        elif choice == "2":
            show_deepseek(cm)
        elif choice == "3":
            delete_deepseek(cm)
        elif choice == "0":
            break
        else:
            print("\n  [错误] 无效选择。")


# ── 直接运行 ─────────────────────────────────────

if __name__ == "__main__":
    cm = get_credential_manager()

    if len(__import__("sys").argv) > 1:
        arg = __import__("sys").argv[1].lower()
        if arg in {"setup", "set"}:
            setup_deepseek(cm)
        elif arg in {"show", "view"}:
            show_deepseek(cm)
        elif arg in {"delete", "del", "remove"}:
            delete_deepseek(cm)
        else:
            print(f"\n  [错误] 未知参数: {arg}")
            print("  支持: setup, show, delete")
    else:
        interactive_menu(cm)
