"""parsers/test 共享工具 —— 产物目录、summary 写出、安全绘图。

产物落 ``parsers/test/_out/<解析器名>/``（与 formats/ 文档、test_*.py 同名同序），
便于人工逐解析器核查。**不复用** ``eosopdata._samples.tmp_dir()``——
其用 ``inspect.stack()[1]`` 取调用者目录，经本模块包装会错位。
"""

from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
OUT_ROOT = _HERE / "_out"


def out_dir(name: str) -> Path:
    """返回 ``_out/<name>/`` 并自动创建（幂等）。"""
    d = OUT_ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_summary(name: str, lines: list[str]) -> Path:
    """把解析统计写入 ``_out/<name>/summary.txt``（统一 LF）。"""
    p = out_dir(name) / "summary.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return p


def log(msg: str = "") -> None:
    """打印一行（run_all.py 会把整段 console 输出捕获进 _out/test_log.txt）。"""
    print(msg)


def sample_or_skip(path):
    """样例惰性发现语义：``find_parseable`` 返回 None 时打印 SKIP 并返回 False。"""
    if path is None:
        log("  SKIP: matter++/eos_op_data 中未找到可解析样例")
        return False
    return True


def try_plot(fn, out_path: Path, name: str) -> bool:
    """安全绘图：matplotlib 缺失或绘图异常 → 记 SKIP 返回 False，不让测试 FAIL。"""
    try:
        fn()
        if Path(out_path).exists():
            log(f"  plot: {Path(out_path).name}")
            return True
        log(f"  SKIP-plot: {name} 未产出文件")
        return False
    except Exception as exc:  # noqa: BLE001 —— 产物核查套件绘图失败只降级
        log(f"  SKIP-plot: {name} -> {type(exc).__name__}: {exc}")
        return False


def table_stats(path, tables) -> list[str]:
    """从 (path, tables) 提取人工核查关心的解析统计行。"""
    lines = [f"sample : {path}"]
    for i, t in enumerate(tables):
        lines.append(f"table[{i}] kind={getattr(t, 'kind', '?')} "
                     f"family={getattr(t, 'family', '?')}")
        axes = getattr(t, "axes", None)
        if isinstance(axes, dict):
            for k, v in axes.items():
                lines.append(f"  axis {k}: n={len(v) if v is not None else 0}")
        fu = getattr(t, "field_units", None)
        if isinstance(fu, dict) and fu:
            for k in sorted(fu):
                lines.append(f"  field {k}: [{fu.get(k, '?')}]")
        notes = getattr(t, "notes", None)
        if notes:
            for n in notes[:6]:
                lines.append(f"  note: {n}")
    return lines
