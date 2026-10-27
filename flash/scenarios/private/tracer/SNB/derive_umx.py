# -*- coding: utf-8 -*-
"""derive_umx.py — 从 SNBVTi{1,2,3}um 派生 SNBVTi{1,2,3}umx（域扩展变体）.

★ 唯一差别（物理/材料/激光/SNB 参数全部不变）:
    域:  -400..100 µm (500 µm) →  -600..100 µm (700 µm)
    网格: iProcs 125 × nxb 200 = 25000 格 → 175 × 200 = 35000 格
          dx 仍精确 = 0.02 µm（0.1 µm 薄层 = 5 整格）
    nblockx: 8 → 7   (rootdx = 700µm/(7×200) = 0.5 µm = 25·dx,
                      xmin=-600µm = -1200·rootdx ⇒ 域边界零吸附)
只生成 .py 场景文件；flash_input 由场景自身 --generate-only 生成。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

SNB_DIR = Path(__file__).resolve().parent

VARIANTS = [
    # (源场景, 目标场景)
    ("SNBVTi1um", "SNBVTi1umx"),
    ("SNBVTi2um", "SNBVTi2umx"),
    ("SNBVTi3um", "SNBVTi3umx"),
]

BANNER = """
## ★★★ 本文件由 {src} 程序化派生 ({date}) —— 域扩展变体 (x 场景)

    唯一差别（物理/材料/激光/SNB/辐射参数全部不变）:
      域:   -400..100 µm (500 µm)  →  **-600..100 µm (700 µm)**
      网格: iProcs 125 × nxb 200 = 25000 格  →  **175 × 200 = 35000 格**
            dx 仍精确 = 0.02 µm（0.1 µm 薄层 = 5 整格, 600µm/0.02 = 30000 ✓）
      nblockx: 8 → 7（rootdx = 700/(7×200) = 0.5 µm = 25·dx;
                      xmin = -600 µm = -1200·rootdx ⇒ align 零位移）
    NC-E 布局: 175 进程 = 4 节点（48 核/节点, 192 核, 空闲 17）。
    ★ 下文 docstring 中出现的 125/500µm/25000 等旧数值均指**母场景**,
      以本 banner 为准。

"""


def derive(src: str, dst: str) -> None:
    src_path = SNB_DIR / src / f"{src}.py"
    text = io.open(src_path, encoding="utf-8").read()

    # ── 1. 名字替换（大小写两套；先长后短防误伤）─────────────────
    for old, new in ((src, dst), (src.lower(), dst.lower())):
        text = text.replace(old, new)

    # ── 2. 几何/网格常量（逐一断言恰好替换 1 次）─────────────────
    reps = [
        ('"xmin": -0.04,', '"xmin": -0.06,'),
        ('"nblockx": 8,', '"nblockx": 7,'),
        ('"iprocs": 125,', '"iprocs": 175,'),
        ('"nprocs": 125,', '"nprocs": 175,'),
        ("UG_IPROCS_EXACT = 125", "UG_IPROCS_EXACT = 175"),
        ("UG_DOM_CM = 0.05", "UG_DOM_CM = 0.07"),
    ]
    for old, new in reps:
        n = text.count(old)
        assert n == 1, f"{dst}: {old!r} 出现 {n} 次 (期望 1)"
        text = text.replace(old, new)

    # ── 3. docstring 头部插 banner（插在首行标题之后）────────────
    lines = text.split("\n")
    assert lines[0].startswith('"""'), dst
    banner = BANNER.format(src=src, date="2026-10-27").rstrip("\n")
    text = "\n".join([lines[0], banner] + lines[1:])

    dst_dir = SNB_DIR / dst
    dst_dir.mkdir(exist_ok=True)
    out = dst_dir / f"{dst}.py"
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(f"[OK] {src} -> {out.name} ({len(text.splitlines())} 行)")


def main() -> int:
    for src, dst in VARIANTS:
        derive(src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
