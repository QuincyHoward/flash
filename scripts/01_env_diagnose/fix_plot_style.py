#!/usr/bin/env python3
"""Batch-fix plotting scripts to comply with the PPT plot standard.

For every matplotlib plotting script found by check_plot_style.py:
  1. inject the plot_style bootstrap (apply_plot_style) right after the
     `import matplotlib.pyplot as plt` line,
  2. strip hardcoded fontsize < 18 arguments,
  3. bump savefig dpi 150 -> 200.

Run:  python scripts/01_env_diagnose/fix_plot_style.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent

BOOTSTRAP = '''\
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass'''

PLT_IMPORT_RE = re.compile(
    r"^(\s*import matplotlib\.pyplot as plt.*)$", re.MULTILINE)

SKIP = ("plot_style.py", "__pycache__", ".workbuddy")


def fix_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    msgs = []

    # 1) inject bootstrap after plt import
    if "apply_plot_style(" not in text:
        m = PLT_IMPORT_RE.search(text)
        if m:
            text = text[:m.end()] + "\n" + BOOTSTRAP + text[m.end():]
            msgs.append("injected apply_plot_style()")
        else:
            msgs.append("no plt import found, skipped injection")

    # 2) strip ONLY small fontsize (< 18); keep fontsize >= 18
    def _drop_small(m: re.Match) -> str:
        return "" if int(m.group(1)) < 18 else m.group(0)

    text, n_small = re.subn(r",\s*fontsize=(\d+)", _drop_small, text)
    text, n_small2 = re.subn(r"fontsize=(\d+),\s*", _drop_small, text)
    if n_small + n_small2:
        msgs.append(f"stripped {n_small + n_small2} small fontsize args")

    # 3) savefig dpi 150 -> 200
    text, n_dpi = re.subn(r"savefig\(([^)]*)dpi\s*=\s*150",
                          r"savefig(\1dpi=200", text)
    if n_dpi:
        msgs.append(f"bumped {n_dpi} savefig dpi to 200")

    if msgs:
        path.write_text(text, encoding="utf-8")
    return msgs


def main() -> None:
    n_fixed = 0
    for f in sorted(PKG_ROOT.rglob("*.py")):
        rel = f.as_posix()
        if any(s in rel for s in SKIP):
            continue
        if "matplotlib" not in f.read_text(encoding="utf-8",
                                           errors="replace"):
            continue
        msgs = fix_file(f)
        if msgs:
            n_fixed += 1
            print(f"{f.relative_to(PKG_ROOT)}: {', '.join(msgs)}")
    print(f"\nFixed {n_fixed} files.")


if __name__ == "__main__":
    sys.exit(main())
