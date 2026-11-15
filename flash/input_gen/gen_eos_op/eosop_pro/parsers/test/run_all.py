"""parsers/test 独立汇总 runner —— 产物核查套件（不接入 eosop_pro/test/run_all.py）。

用法::

    cd <gen_eos_op>
    python eosop_pro/parsers/test/run_all.py          # 全量
    python eosop_pro/parsers/test/test_cn4_io.py      # 单文件裸跑

退出码 = 失败测试数；全量运行时把整段 console 输出写入 ``_out/test_log.txt``。
本套件与 ``eosop_pro/test/parsers/``（纯断言测试）的分工见 README.md。
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import _bootstrap  # noqa: F401,E402 —— 注入 test/与包根路径

OUT_LOG = os.path.join(_HERE, "_out", "test_log.txt")


def _discover() -> list[str]:
    """收集本目录全部 test_*.py（不含 _out/，按名排序）。"""
    out = []
    for f in sorted(os.listdir(_HERE)):
        if f.startswith("test_") and f.endswith(".py"):
            out.append(os.path.join(_HERE, f))
    return out


def _load(path: str):
    """加载测试模块（唯一模块名前缀 wbpt_，避免与 test/parsers/ 同名冲突）。"""
    name = "wbpt_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)
    files = _discover()
    buf = io.StringIO()
    total_fail = 0
    with redirect_stdout(buf):
        print(f"=== parsers/test 产物核查套件 : {len(files)} 文件 ===\n")
        for path in files:
            mod = _load(path)
            label = os.path.basename(path)
            ns = vars(mod)
            tests = [(k, v) for k, v in ns.items()
                     if k.startswith("test_") and callable(v)]
            tests.sort(key=lambda kv: kv[0])
            if not tests:
                print(f"--- {label} : no tests found ---\n")
                continue
            nfail = 0
            print(f"\n=== {label} : {len(tests)} tests ===")
            for tname, fn in tests:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    nfail += 1
                    import traceback
                    print(f"  FAIL {tname}")
                    for line in traceback.format_exc().rstrip().splitlines()[-6:]:
                        print(f"        {line}")
                else:
                    print(f"  PASS {tname}")
            total_fail += nfail
            print(f"  --> {'FAILED ' + str(nfail) if nfail else 'all passed'}\n")
        print("=" * 60)
        print(f"TOTAL: {'ALL PASSED' if total_fail == 0 else f'{total_fail} FAILED'}"
              f" across {len(files)} file(s)")
        print("=" * 60)

    text = buf.getvalue()
    print(text, end="")
    with open(OUT_LOG, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"[log] {OUT_LOG}")
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
