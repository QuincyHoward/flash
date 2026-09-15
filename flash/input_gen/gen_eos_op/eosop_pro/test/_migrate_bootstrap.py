"""一次性迁移：为所有测试文件注入自举头部（使其可被裸命令行直接运行）。

策略
----
在每个 ``test_*.py`` 中，把**第一次**出现的 ``import _runner`` 行之前
插入 5 行上溯代码（若尚未存在）。幂等：已注入的跳过。

Windows 注意
-----------
必须用 ``rb``/``wb`` 显式按字节处理以保住 LF 换行
（用户铁律：``*.py`` 必须 LF）。
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # test/
MARK = "# --- path bootstrap (auto) ---"

SNIPPET = (
    "# --- path bootstrap (auto) ---\n"
    "_d = os.path.dirname(os.path.abspath(__file__))\n"
    "while _d != os.path.dirname(_d) and not os.path.isfile(\n"
    "        os.path.join(_d, \"_runner.py\")):\n"
    "    _d = os.path.dirname(_d)\n"
    "if _d not in sys.path:\n"
    "    sys.path.insert(0, _d)\n"
)


def ensure_imports(lines: list[str]) -> list[str]:
    """确保头部有 ``import os`` 与 ``import sys``（模块级、位于插入点之前）。"""
    head = "\n".join(lines)
    need_os = "import os" not in head
    need_sys = "import sys" not in head
    pre: list[str] = []
    if need_sys:
        pre.append("import sys")
    if need_os:
        pre.append("import os")
    return pre


def migrate(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")
    if MARK in text:
        return "skip(already)"
    if "import _runner" not in text:
        return "skip(no _runner)"

    lines = text.split("\n")
    idx = next(i for i, s in enumerate(lines) if s.strip().startswith("import _runner"))

    pre = ensure_imports(lines[:idx])
    block = pre + SNIPPET.split("\n")[:-1]
    # 与上一行之间留一个空行
    if idx > 0 and lines[idx - 1].strip() != "":
        block = [""] + block
    lines[idx:idx] = block

    new = "\n".join(lines)
    with open(path, "wb") as fh:
        fh.write(new.encode("utf-8"))
    return "ok"


def main() -> int:
    stats: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(HERE):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in sorted(filenames):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, HERE).replace(os.sep, "/")
            r = migrate(p)
            stats[r] = stats.get(r, 0) + 1
            print(f"{r:20s} {rel}")
    print("\n== summary ==")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
