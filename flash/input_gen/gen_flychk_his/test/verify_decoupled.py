#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_decoupled.py — 解耦验证 (机械化证明)
===========================================

证明 `gen_flychk_his` **完全不依赖外部 FLYCHK Python 包**，可随 flash-sim
独立分发。做法:

1. 在 `sys.meta_path` 头部插入拦截器，任何对 ``flychk`` / ``flychk.*`` 的
   import 立即抛 `ImportError`（而非静默回退），并把已加载的此类模块从
   `sys.modules` 清除、把指向 flychk-sim 的 `sys.path` 条目移除；
2. 在该"敌对环境"下运行完整测试套件（pytest）；
3. 再跑一次真实端到端生成（合成数据 → 多区域 zip + manifest），断言
   写出与自检全部通过；
4. 静态扫描发布包源码，确认无外部包导入/路径搜索字符串。

用法::

    python flash/input_gen/gen_flychk_his/test/verify_decoupled.py

退出码: 0 = 完全解耦; 1 = 发现耦合或测试失败。
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

_HERE = Path(__file__).resolve().parent
_PKG = _HERE.parent
_ROOT = _HERE.parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 外部包名 (需被严密封锁的)
EXTERNAL_PREFIX = "flychk"
FORBIDDEN_STRINGS = (
    "import flychk", "flychk.input_gen", "flychk_root", "FLYCHK_SIM_ROOT",
    "candidate_flychk_roots", "resolve_flychk_generator", "compare_backends",
    "allow_fallback",
)


class _BlockExternal:
    """meta_path 拦截器: 禁止导入外部 FLYCHK 包 (抛错而非回退)。"""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.blocked: List[str] = []

    def find_spec(self, fullname, path=None, target=None):   # noqa: D102
        if fullname == self.prefix or fullname.startswith(self.prefix + "."):
            self.blocked.append(fullname)
            raise ImportError(
                f"[解耦验证] 禁止导入外部包 '{fullname}' —— 该包必须自包含"
            )
        return None


def install_blocker() -> _BlockExternal:
    blocker = _BlockExternal(EXTERNAL_PREFIX)
    # 清除已加载的外部模块与指向其仓库的 sys.path 条目
    for name in [m for m in list(sys.modules)
                 if m == EXTERNAL_PREFIX or m.startswith(EXTERNAL_PREFIX + ".")]:
        sys.modules.pop(name, None)
    sys.path[:] = [p for p in sys.path
                   if "flychk-sim" not in str(p).replace("\\", "/")]
    sys.meta_path.insert(0, blocker)
    return blocker


def scan_sources() -> List[str]:
    """静态扫描发布包源码 (顶层模块, 不含 test/)。"""
    hits: List[str] = []
    for py in sorted(_PKG.glob("*.py")):
        txt = py.read_text(encoding="utf-8")
        hits += [f"{py.name}: {s}" for s in FORBIDDEN_STRINGS if s in txt]
    if (_PKG / "backend.py").exists():
        hits.append("backend.py: 外部后端解析模块仍然存在")
    return hits


def run_pytest() -> int:
    import pytest
    return int(pytest.main([str(_HERE), "-q", "--no-header",
                            "-p", "no:cacheprovider"]))


def run_end_to_end() -> Tuple[bool, str]:
    """在封锁环境下跑一次真实生成。"""
    from flash.input_gen.gen_flychk_his import FlychkHistoryGenerator

    with tempfile.TemporaryDirectory(prefix="decoupled_e2e_") as tmp:
        gen = FlychkHistoryGenerator(element="Ti", agg="mass", n_time_max=4,
                                     dens_cut=1e-6)
        rep = gen.generate(source=None,
                           region=["whole", "label:matid=2", "x:-40..0um"],
                           output_dir=str(Path(tmp) / "out"),
                           self_check=True, verbose=False)
        ok = rep.ok and rep.integrity_ok is True and len(rep.zip_paths) == 3
        detail = (f"zip={len(rep.zip_paths)}, 自检={rep.integrity_ok}, "
                  f"manifest={'ok' if rep.manifest_path else 'missing'}")
        return bool(ok), detail


def main(argv=None) -> int:
    print("=" * 74)
    print("gen_flychk_his 解耦验证")
    print("=" * 74)

    # 1) 静态: 源码级
    hits = scan_sources()
    print(f"[1/3] 发布包源码外部引用扫描: {'PASS' if not hits else 'FAIL'}")
    for h in hits:
        print(f"      ! {h}")

    # 2) 封锁外部包
    blocker = install_blocker()
    print(f"[2/3] 已封锁外部包 '{EXTERNAL_PREFIX}*' 导入 "
          f"(meta_path 拦截, 不会静默回退)")

    # 3) 敌对环境端到端
    e2e_ok, e2e_detail = run_end_to_end()
    print(f"[3/3] 封锁环境下端到端生成: {'PASS' if e2e_ok else 'FAIL'} ({e2e_detail})")

    # 4) 敌对环境下全量测试
    print("-" * 74)
    rc = run_pytest()
    print("-" * 74)
    print(f"[pytest] exit={rc}; 外部包导入被拦截 {len(blocker.blocked)} 次")
    print(f"[源码扫描] {'PASS' if not hits else 'FAIL'}; "
          f"[端到端] {'PASS' if e2e_ok else 'FAIL'}; "
          f"[测试] {'PASS' if rc == 0 else 'FAIL'}")
    all_ok = (not hits) and e2e_ok and rc == 0
    print("=" * 74)
    print("结论: " + ("完全解耦 (可随 flash-sim 独立分发)"
                    if all_ok else "发现耦合或失败, 见上"))
    return 0 if all_ok else 1


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
