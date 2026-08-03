#!/usr/bin/env python3
"""
测试 Gitee 凭证管理功能（非交互式）
"""

import sys
from pathlib import Path

# Bootstrap: find flash project root
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash._core.credentials import get_credential_manager
from flash._core.credentials._config import ENTRIES_BY_NAME


def test_gitee_entry():
    """测试 Gitee 条目定义是否存在。"""
    print("=" * 60)
    print("  测试 1: 检查 Gitee 条目定义是否存在")
    print("=" * 60)

    assert "gitee" in ENTRIES_BY_NAME, "未找到 'gitee' 条目定义"
    entry = ENTRIES_BY_NAME["gitee"]
    print(f"\n[成功] 找到 'gitee' 条目定义")
    print(f"  描述: {entry.get('title', 'N/A')}")
    fields = [f[0] for f in entry.get("fields", [])]
    print(f"  字段: {fields}")


def test_credential_manager():
    """测试 CredentialManager 是否可以正常工作。"""
    print("\n" + "=" * 60)
    print("  测试 2: 测试 CredentialManager (通过 get_credential_manager)")
    print("=" * 60)

    cm = get_credential_manager()
    print("\n[成功] CredentialManager 初始化成功")
    print(f"  类型: {type(cm).__name__}")

    # 测试读取（应该返回 None 或现有凭证）
    gitee_cred = cm.get("gitee")
    if gitee_cred:
        print("[信息] 已存在 Gitee 凭证")
        print(f"  用户名: {gitee_cred.get('username', 'N/A')}")
    else:
        print("[信息] 未找到 Gitee 凭证（首次使用）")


def test_gitee_functions():
    """测试 Gitee 相关导出函数。"""
    print("\n" + "=" * 60)
    print("  测试 3: 测试 Gitee 相关的导出函数")
    print("=" * 60)

    from flash._core.credentials import (
        get_credential_manager,
    )

    print("\n[成功] 成功导入核心函数")

    # 测试 get_credential_manager 然后获取 gitee
    cm = get_credential_manager()
    cred = cm.get("gitee")
    if cred:
        print(f"[信息] 找到 Gitee 凭证: {cred.get('username', 'N/A')}")
    else:
        print("[信息] 未找到 Gitee 凭证（这是正常的，如果还没有设置）")


def test_git_push_import():
    """测试是否可以导入统一 git_push 脚本。"""
    print("\n" + "=" * 60)
    print("  测试 4: 测试统一 git_push 导入")
    print("=" * 60)

    from flash.scripts.git_push import push_to_gitee, show_status, find_git_root

    print("\n[成功] 成功导入 git_push 核心函数:")
    print("  - push_to_gitee: 统一推送函数")
    print("  - show_status: 状态检查函数")
    print("  - find_git_root: 项目根目录查找")

    # 测试 find_git_root
    root = find_git_root(Path(__file__).parent)
    print(f"[成功] 自动检测项目根目录: {root}")


def main():
    """主函数。"""
    print("\n" + "=" * 60)
    print("  Gitee 凭证管理功能测试")
    print("  (适配模块化 _core/credentials)")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("Gitee 条目定义存在", test_gitee_entry()))
    results.append(("CredentialManager 工作", test_credential_manager()))
    results.append(("Gitee 函数工作", test_gitee_functions()))
    results.append(("git_push 导入", test_git_push_import()))

    # 总结
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)

    passed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}  {name}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 测试通过")

    if passed == len(results):
        print("\n🎉 所有测试通过！Gitee 凭证管理功能正常工作。")
        return 0
    else:
        print(f"\n⚠️  有 {len(results) - passed} 个测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
