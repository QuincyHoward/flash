"""
Flash 凭据管理 -- PyPI 发布令牌
=================================
管理 PyPI (pypi.org) 与 TestPyPI (test.pypi.org) 的 API Token,
凭据加密存储在 ~/.physimx/flash/credentials.json (与 Gitee/SSH 同体系)。

用法:
    python -m flash._core.credentials.pypi              # 交互设置 (pypi + testpypi)
    python -m flash._core.credentials.pypi setup        # 同交互设置
    python -m flash._core.credentials.pypi show         # 查看 (脱敏)
    python -m flash._core.credentials.pypi write-pypirc # 生成 ~/.pypirc (twine 用)

发布:
    python scripts/03_git_publish/publish_pypi.py --test               # 试发 TestPyPI
    python scripts/03_git_publish/publish_pypi.py                      # 正式发布 PyPI
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

from ._core import get_credential_manager, mask_secret

# 索引 → (名称, 标题, 上传地址)
ENTRY_TITLES: Dict[str, str] = {
    "pypi": "PyPI 发布令牌 (pypi.org)",
    "testpypi": "TestPyPI 发布令牌 (test.pypi.org)",
}
INDEX_URLS: Dict[str, str] = {
    "pypi": "https://upload.pypi.org/legacy/",
    "testpypi": "https://test.pypi.org/legacy/",
}


def _entry_def(name: str):
    """从 _config.ENTRIES 取条目定义 (供字段默认值)。"""
    from ._config import ENTRIES_BY_NAME

    return ENTRIES_BY_NAME.get(name)


def setup_pypi(index: Optional[str] = None) -> bool:
    """交互式设置 PyPI / TestPyPI token。"""
    cm = get_credential_manager()
    targets = [index] if index else list(ENTRY_TITLES)

    print(f"\n  📦 PyPI 发布令牌设置")
    print(f"  {'─' * 55}")
    print(f"  请先在对应网站创建 API Token (Scope 选整个账户):")
    print(f"    - PyPI:      https://pypi.org/manage/account/token/")
    print(f"    - TestPyPI:  https://test.pypi.org/manage/account/token/")
    print(f"  Token 形如 pypi-xxxxxxxxxxxx, 创建后仅显示一次。")
    print(f"  {'─' * 55}\n")

    for name in targets:
        entry = _entry_def(name)
        title = ENTRY_TITLES.get(name, name)
        existing = cm.get(name) or {}
        has = "✅ 已设置" if existing.get("token") else "⬜ 未设置"
        print(f"  [{name}] {title}  [{has}]")
        default = entry["fields"][0][2] if entry else ""
        token = input(f"    token (留空保留当前): ").strip()
        if not token and existing.get("token"):
            token = existing["token"]
        if not token:
            print(f"    ⚠️  跳过 {name} (未提供 token)\n")
            continue
        cm.set(name, {"token": token, "username": "__token__"})
        print(f"    ✅ {name} 已保存\n")

    # 自动生成 ~/.pypirc (twine 可直接使用)
    pypirc = write_pypirc()
    print(f"  📄 已生成 {pypirc} (twine 发布用)")
    print(f"  ✅ PyPI 令牌设置完成!")
    return True


def get_pypi_config(index: str = "pypi") -> Optional[Dict[str, str]]:
    """读取 PyPI token 配置 (twine 上传用)。

    返回 {"username": "__token__", "password": token} 或 None (未配置)。
    """
    cm = get_credential_manager()
    data = cm.get(index)
    if not data or not data.get("token"):
        return None
    return {"username": data.get("username") or "__token__", "password": data["token"]}


def write_pypirc(pypirc: Optional[Path] = None) -> Path:
    """生成 ~/.pypirc 配置文件 (twine 的 --config-file 默认位置)。

    若 token 未配置, 对应段落密码留空 (twine 会提示输入)。
    """
    pypirc = pypirc or Path.home() / ".pypirc"
    lines = ["[distutils]", "index-servers =", "  pypi", "  testpypi", ""]
    for name in ("pypi", "testpypi"):
        cfg = get_pypi_config(name)
        url = INDEX_URLS[name]
        pw = cfg["password"] if cfg else ""
        lines += [
            f"[{name}]",
            f"repository = {url}",
            "username = __token__",
            f"password = {pw}",
            "",
        ]
    pypirc.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return pypirc


def show_pypi(raw: bool = False) -> None:
    """查看 PyPI / TestPyPI 令牌配置状态 (脱敏)。"""
    print(f"\n  {'─' * 55}")
    for name, title in ENTRY_TITLES.items():
        cfg = get_pypi_config(name)
        if cfg:
            shown = cfg["password"] if raw else mask_secret({"token": cfg["password"]}).get("token", "***")
            print(f"  [{name}] {title}")
            print(f"      username: {cfg['username']}")
            print(f"      token:    {shown}")
        else:
            print(f"  [{name}] {title}  ⬜ 未配置")
    print(f"  {'─' * 55}\n")


def main() -> None:
    """CLI 入口。"""
    args = sys.argv[1:]
    if args and args[0] in ("setup", "set"):
        setup_pypi(args[1] if len(args) > 1 else None)
    elif args and args[0] == "show":
        show_pypi(raw="--raw" in args)
    elif args and args[0] == "write-pypirc":
        p = write_pypirc()
        print(f"  ✅ 已生成 {p}")
    else:
        setup_pypi()


if __name__ == "__main__":
    main()
