"""测试套件自身的卫生检查 —— 防止"追加测试却跑不到"这类静默失效。

为什么需要它
------------
每个测试文件的末尾都有::

    if __name__ == "__main__":
        raise SystemExit(main(globals()))

如果往文件**末尾追加**新测试（``cat >> file``），新函数会落在
``main(globals())`` **之后** —— 直接跑 ``python test_x.py`` 时看不见它们
（``run_all.py`` 因为走 ``exec_module`` 之后才收 ``globals()``，反而能看见）。
这种"两种跑法结果不同"的偏差极难察觉：实测新增 4 个测试后单文件仍报
"all passed (16)"。

本文件用源码扫描把这类问题变成**会失败的测试**：

1. ``main(globals())`` 必须是文件里**最后一条可执行语句**
2. 每个自带 ``main`` 的文件必须能从 ``_runner`` 拿到它用到的断言函数
3. ``test_*.py`` 必须能被导入（无语法/导入错误）
4. 不允许出现 ``expect_*`` 的名字但没导入（NameError 只在跑到时才暴露）
"""

import ast
import importlib.util
import re
from pathlib import Path

import sys
import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import config

_TEST_DIR = Path(config.TEST_DIR)


def _test_files() -> list[Path]:
    """递归收集 ``test/`` 下全部 ``test_*.py``（含功能子包）。

    2026-09-14: ``test/`` 已按功能分为子包（core/ registry/ parsers/ ...），
    故必须是 **rglob** —— 否则子目录里的测试逃脱卫生检查，
    正是本文件要防的"静默失效"。
    """
    return sorted(
        p for p in _TEST_DIR.rglob("test_*.py")
        if "__pycache__" not in p.parts
    )


def _assert_helpers_defined_in_runner() -> set[str]:
    """``_runner.py`` 里所有模块级 ``def`` 的名字。"""
    src = (_TEST_DIR / "_runner.py").read_text(encoding="utf-8")
    return set(re.findall(r"^def (\w+)", src, re.M))


def test_runner_exposes_the_assertion_helpers():
    names = _assert_helpers_defined_in_runner()
    for n in ("expect", "expect_eq", "expect_in", "expect_almost",
              "expect_lt", "expect_gt", "run_all", "main"):
        expect_in(n, names, f"_runner 应提供 {n}")
    expect_eq(names & {"expect_in", "expect_almost", "expect_gt"},
              {"expect_in", "expect_almost", "expect_gt"},
              "断言辅助应齐全")


def test_main_guard_is_the_last_statement():
    """★ 核心断言：``raise SystemExit(main(globals()))`` 必须在文件最后。

    否则追加的测试单文件跑不到（见模块 docstring）。
    """
    bad: list[str] = []
    for p in _test_files():
        lines = p.read_text(encoding="utf-8").splitlines()
        idx = [i for i, ln in enumerate(lines)
               if "SystemExit(main(globals()))" in ln]
        if not idx:
            bad.append(f"{p.name}: 缺少 __main__ 守卫")
            continue
        last = idx[-1]
        tail = [ln for ln in lines[last + 1:] if ln.strip()]
        if tail:
            bad.append(f"{p.name}: main(globals()) 在第 {last + 1} 行，"
                       f"其后仍有 {len(tail)} 行（首行 {tail[0].strip()[:50]!r}）")
    expect(not bad, "以下测试文件的 __main__ 守卫不在末尾：\n  "
                    + "\n  ".join(bad))


def test_no_test_function_after_main_guard():
    """★ 用 AST 交叉验证：守卫之后不得再有 ``def test_*``。

    （与上一条互补：上一条查"有没有尾部内容"，这条查"尾部内容里有没有测试"。）
    """
    bad: list[str] = []
    for p in _test_files():
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        guard_line = None
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                src = ast.dump(node.test)
                if "main" in src and "__name__" in src:
                    guard_line = max(guard_line or 0, node.end_lineno or 0)
        if guard_line is None:
            continue
        later = [n.name for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name.startswith("test_")
                 and n.lineno > guard_line]
        if later:
            bad.append(f"{p.name}: 守卫（第 {guard_line} 行）之后的测试 {later}")
    expect(not bad, "守卫之后的测试跑不到：\n  " + "\n  ".join(bad))


def test_expect_helpers_used_are_imported():
    """★ ``expect_in`` 这类名字若没导入，只在**跑到那一行**时才 NameError。

        实测踩过两次（``test_declared_types`` / ``test_plots``）：加断言时随手写了
    ``expect_in`` 但文件头只 import 了 ``expect, expect_eq`` ——
    于是新测试"失败"的报错是 ``NameError`` 而不是断言内容，很难一眼看出。

    ⚠️ 匹配范围限定为 ``_runner`` 实际导出的断言函数名（``expect``，
    ``expect_eq``，``expect_in``，``expect_close`` …），**不能**用
    ``expect\\w*`` 通配 —— 否则像 ``expected_number_count(...)`` 这种
    合法的业务函数名会被误判为"未导入的断言函数"。
    """
    bad: list[str] = []
    helper_names = _assert_helpers_defined_in_runner() - {"_x"}
    helper_pat = re.compile(
        r"\b(" + "|".join(re.escape(h) for h in sorted(helper_names, key=len, reverse=True))
        + r")\s*\("
    ) if helper_names else None
    for p in _test_files():
        text = p.read_text(encoding="utf-8")
        imported = set()
        for m in re.finditer(r"from _runner import \(?([^)\n]+)\)?", text):
            imported |= {s.strip() for s in m.group(1).split(",") if s.strip()}
        for m in re.finditer(r"from _runner import ((?:\s*\w+,?\s*)+)", text):
            imported |= {s.strip() for s in m.group(1).split(",") if s.strip()}
        if helper_pat is None:
            continue
        used = set(helper_pat.findall(text))
        missing = sorted(u for u in used
                         if u not in imported
                         and f"def {u}" not in text)
        if missing:
            bad.append(f"{p.name}: 使用了但未导入 {missing}")
    expect(not bad, "断言函数未导入（会在运行时 NameError）：\n  "
                    + "\n  ".join(bad))


def test_every_test_file_imports_runner_first():
    """约定：头两行固定 ``import _runner`` + ``from _runner import ...``。

    原因：``python test/test_x.py`` 会把 ``test/`` 放进 ``sys.path[0]``，
    ``import _runner`` 一定成功；而 ``_runner`` 在被导入时把**项目根**插进
    ``sys.path``，于是之后 ``from eosop_pro import ...`` 才能成功。
    """
    bad = []
    for p in _test_files():
        text = p.read_text(encoding="utf-8")
        expect_in("import _runner", text, f"{p.name} 应 import _runner")
        expect_in("from _runner import", text, f"{p.name} 应从 _runner 导入")
    expect(not bad, str(bad))


def test_all_test_files_are_importable():
    """★ 每个测试文件都必须能被导入（无语法错 / 导入错）。"""
    bad: list[str] = []
    for p in _test_files():
        spec = importlib.util.spec_from_file_location("hyg_" + p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:                             # noqa: BLE001
            bad.append(f"{p.name}: {type(exc).__name__}: {exc}")
    expect(not bad, "以下测试文件导入失败：\n  " + "\n  ".join(bad))


def test_test_count_is_nonzero_per_file():
    """每个 ``test_*.py`` 至少要有一个 ``def test_``。"""
    empty = []
    for p in _test_files():
        n = len(re.findall(r"^def test_", p.read_text(encoding="utf-8"), re.M))
        if n == 0:
            empty.append(p.name)
    expect(not empty, f"以下文件没有测试：{empty}")


def test_docstring_documents_each_file():
    """每个测试文件都应有一句说明"测什么"（模块 docstring）。"""
    bad = []
    for p in _test_files():
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        doc = ast.get_docstring(tree) or ""
        if len(doc.strip()) < 30:
            bad.append(f"{p.name}: docstring 过短（{len(doc.strip())} 字符）")
    expect(not bad, "以下文件缺少说明性 docstring：\n  " + "\n  ".join(bad))


def test_run_all_discovers_every_test_file():
    """``run_all.py`` 的发现规则应覆盖 ``test_*.py`` 全集（含子包）。"""
    discovered = sorted(str(p.relative_to(_TEST_DIR)).replace("\\", "/")
                        for p in _test_files())
    expect(len(discovered) >= 30, f"测试文件数偏少：{len(discovered)}")
    src = (_TEST_DIR / "run_all.py").read_text(encoding="utf-8")
    # 必须是递归发现，否则子包里的测试会被漏掉
    expect_in("os.walk", src, "run_all 应递归发现（os.walk）")
    expect_in('startswith("test_")', src, "应过滤 test_ 前缀")
    expect_in('.endswith(".py")', src, "应过滤 .py 后缀")
    # 子包确实存在，且发现结果里含斜杠路径
    expect(any("/" in d for d in discovered),
           f"应发现子包内测试，实测 {discovered[:4]}")


# ══════════════════════════════════════════════════════════════
# ★ Windows .bat 启动器的硬约束
# ══════════════════════════════════════════════════════════════
def _bats() -> list[Path]:
    return sorted(Path(config.SCRIPTS_DIR).glob("*.bat"))


def test_bats_use_crlf():
    """★ ``.bat`` **必须 CRLF** —— cmd.exe 对多行 ``if ( … )`` 块在纯 LF 下会解析异常。

    实测踩过：用 MSYS 的 ``sed -i`` 改 bat 时，**sed 把 CRLF 归一成了 LF**
    （同时还吞掉了反斜杠）。所以这条必须由测试守住，不能靠"我写的时候用了 CRLF"。
    """
    bad = []
    for p in _bats():
        raw = p.read_bytes()
        if b"\r\n" not in raw:
            bad.append(f"{p.name}: 没有 CRLF")
        elif raw.replace(b"\r\n", b"").count(b"\n"):
            bad.append(f"{p.name}: 混有裸 LF")
    expect(not bad, ".bat 换行符不合规：\n  " + "\n  ".join(bad))


def test_bats_are_pure_ascii():
    """★ 全 ASCII —— cmd 按 GBK 解码，中文会变乱码（实测踩过）。"""
    bad = []
    for p in _bats():
        raw = p.read_bytes()
        non = sorted({b for b in raw if b > 127})
        if non:
            bad.append(f"{p.name}: 非 ASCII 字节 {non[:6]}")
    expect(not bad, ".bat 含非 ASCII：\n  " + "\n  ".join(bad))


def test_bats_have_single_backslash_venv_path():
    """★ venv 路径必须是**单反斜杠**。

    实测两次踩坑：
    * ``C:////Users////…``（Python 转义多写了斜杠）
    * ``C://Users//…``（MSYS sed 把 ``\\`` 按 Unix 路径规则转换）
    两者都能"看起来像路径"，所以用值断言而不是目视。
    """
    bs = chr(92)
    want = bs.join(["C:", "Users", "Administrator", ".workbuddy",
                    "binaries", "python", "envs", "default"])
    bad = []
    for p in _bats():
        lines = [ln for ln in p.read_bytes().decode("ascii").splitlines()
                 if ln.startswith("set VENV=")]
        if not lines:
            bad.append(f"{p.name}: 没有 `set VENV=`")
        elif lines[0] != f"set VENV={want}":
            bad.append(f"{p.name}: {lines[0]!r}")
    expect(not bad, f"venv 路径不规范（应为 set VENV={want}）：\n  "
                    + "\n  ".join(bad))


def test_bats_guard_missing_venv():
    """每个 bat 都应在 venv 缺失时给出提示并退出，而不是抛一堆 ImportError。"""
    bad = [p.name for p in _bats() if b"if not exist" not in p.read_bytes()]
    expect(not bad, f"缺少 venv 存在性检查：{bad}")


def test_bats_reference_existing_scripts():
    """bat 里引用的 ``scripts/*.py`` 必须真的存在。"""
    import re

    scripts_dir = Path(config.SCRIPTS_DIR)
    bad = []
    for p in _bats():
        text = p.read_bytes().decode("ascii")
        for m in re.finditer(r"scripts[\\/]+([0-9A-Za-z_]+\.py)", text):
            target = scripts_dir / m.group(1)
            if not target.exists():
                bad.append(f"{p.name} → {m.group(1)} 不存在")
    expect(not bad, "bat 引用了不存在的脚本：\n  " + "\n  ".join(bad))


def test_wrappers_reference_existing_cli_subcommands():
    """``scripts/*.py`` 的 ``main([[...]])`` 子命令必须都在 cli 里注册。"""
    import re

    from eosop_pro import cli as mcli

    src = Path(mcli.__file__).read_text(encoding="utf-8")
    registered = set(re.findall(r'add_parser\(\s*"([a-z-]+)"', src))
    expect(registered, "应解析出已注册子命令")
    for w in sorted(Path(config.SCRIPTS_DIR).glob("*.py")):
        for name in re.findall(r'main\(\[\["([a-z-]+)"', w.read_text(encoding="utf-8")):
            expect_in(name, registered, f"{w.name} 调用了未注册的 {name!r}")


def test_python_sources_do_not_contain_crlf():
    """★ 反向约束：``.py`` / ``.md`` / ``.json`` 一律 **LF**。

    理由：同一套脚本要在 WSL / 超算 Linux 上跑；
    CRLF 会破坏 shebang（``/bin/bash^M``）与行解析。
    （``.bat`` 是唯一例外，由 ``test_bats_use_crlf`` 单独守。）

    ⚠️ 豁免：``**/source_data/`` 下的文件是**外部原始数据的逐字节副本**
    （2026-09-15 用户规约：原始 eosop 数据随图复制到 ``<type>/_out/
    source_data/`` 供人工核查对照）—— 逐字节保真优先，源文件若本身是
    CRLF 就原样保留，不属于项目产出文本（且 ``test/**/_out/`` 已
    gitignore，不会经 git 上 Linux）。
    """
    crlf = bytes([13, 10])          # b"\r\n"，避开源码里写字面转义
    bad = []
    exts = {".py", ".md", ".json", ".txt", ".yaml", ".yml"}
    roots = (Path(config.PACKAGE_ROOT), Path(config.SCRIPTS_DIR), _TEST_DIR,
             Path(config.PROJECT_ROOT) / "docs")
    for root in roots:
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            if "source_data" in p.parts:
                continue
            if crlf in p.read_bytes():
                bad.append(str(p.relative_to(config.PROJECT_ROOT)).replace("\\", "/"))
    expect(not bad, f"以下文本文件含 CRLF（应为 LF）：\n  " + "\n  ".join(bad[:10]))


if __name__ == "__main__":
    raise SystemExit(main(globals()))
