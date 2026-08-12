#!/usr/bin/env python3
"""Plot-style compliance checker for the flash-sim package.

Scans every Python file in the package that uses matplotlib and reports
violations of the PPT-friendly plotting standard (see
`docs/flash_operation_standard.md` section 1.1):

  1. MUST import and call `apply_plot_style()` from
     `output_processors.plotter.plot_style` (fonts >= 18, English, dpi=200).
  2. MUST NOT hardcode small fonts (fontsize < 18).
  3. MUST NOT contain CJK characters in plot text
     (titles, labels, legends, colorbar labels, annotations).
  4. MUST save with dpi >= 200.

Usage:
  python scripts/01_env_diagnose/check_plot_style.py                 # scan whole package
  python scripts/01_env_diagnose/check_plot_style.py path/to/file.py # scan one file
  python scripts/01_env_diagnose/check_plot_style.py --strict        # exit 1 on violations

Exit codes:
  0  all compliant (or only warnings)
  1  violations found (with --strict)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── Package root: flash/ ───────────────────────────────────
HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent

# ── Patterns ───────────────────────────────────────────────
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SMALL_FONT_RE = re.compile(r"fontsize\s*=\s*(\d{1,2})\b")
PLOT_TEXT_RE = re.compile(
    r"(?:set_title|set_xlabel|set_ylabel|set_label|legend|annotate"
    r"|text|suptitle|colorbar)\s*\(",
    re.IGNORECASE,
)
STRING_RE = re.compile(r"\"([^\"]*)\"|'([^']*)'")

# Directories / files to skip (third-party, generated, private, tests utils)
SKIP_PATTERNS = (
    "__pycache__",
    ".workbuddy",
    "plot_style.py",          # the spec module itself
    "test/amr_visualization",  # low-level AMR tests
    "compare_h5py_vs_yt.py",   # comparison harness
    "flash_run/remote/ssh_check.py",
    "scenarios/simulator.py",  # engine (does not produce figures directly)
)


def is_skipped(path: Path) -> bool:
    rel = path.as_posix()
    return any(p in rel for p in SKIP_PATTERNS)


def is_plotting_script(text: str) -> bool:
    """Heuristic: does this file actually produce figures?

    A file only needs the plot standard if it uses plotting APIs:
    plt.subplots / plt.plot / savefig / pcolormesh / imshow / ax.plot ...
    Files that merely `import matplotlib` (e.g. to set backend) are skipped.
    """
    PLOT_APIS = re.compile(
        r"(plt\.(subplots|plot|figure|savefig|pcolormesh|imshow|scatter|"
        r"contour|contourf|colorbar|bar|hist|errorbar|semilogy|semilogx|"
        r"loglog|fill_between|tricontour|tricontourf|quiver|streamplot)|"
        r"ax\.(plot|pcolormesh|imshow|scatter|contour|contourf|bar|hist|"
        r"semilogy|semilogx|loglog|fill_between|quiver|errorbar)|"
        r"fig\.(savefig|colorbar|suptitle)|"
        r"matplotlib\.pyplot|pyplot\.show)",
        re.IGNORECASE,
    )
    return bool(PLOT_APIS.search(text))


def scan_file(path: Path) -> list[str]:
    """Return list of violation messages for one file."""
    violations: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    # Only plotting scripts are subject to the standard
    if not is_plotting_script(text):
        return violations

    has_plot_style_import = (
        "from output_processors.plotter.plot_style" in text
        or "import plot_style" in text
    )
    has_apply = "apply_plot_style(" in text

    # Rule 1: must call apply_plot_style
    if not has_apply:
        violations.append("  [MISS] apply_plot_style() not called "
                          "(add: from output_processors.plotter.plot_style "
                          "import apply_plot_style; apply_plot_style())")

    # Rule 2: no small fonts
    for m in SMALL_FONT_RE.finditer(text):
        size = int(m.group(1))
        if size < 18:
            line_no = text[: m.start()].count("\n") + 1
            violations.append(
                f"  [FONT] line {line_no}: fontsize={size} < 18 "
                f"(remove hardcoded fontsize; rely on apply_plot_style)")

    # Rule 3: no CJK in plot-text context (best effort)
    for m in PLOT_TEXT_RE.finditer(text):
        start = m.end()
        seg = text[start:start + 600]
        # find string literals inside this call
        for sm in STRING_RE.finditer(seg[:200]):
            s = sm.group(1) or sm.group(2) or ""
            if CJK_RE.search(s):
                line_no = text[: m.start() + sm.start()].count("\n") + 1
                violations.append(
                    f"  [CJK ] line {line_no}: CJK in plot text: {s!r} "
                    f"(use english() from plot_style)")
                break

    # Rule 4: savefig dpi >= 200
    for m in re.finditer(r"savefig\([^)]*dpi\s*=\s*(\d+)", text):
        dpi = int(m.group(1))
        if dpi < 200:
            line_no = text[: m.start()].count("\n") + 1
            violations.append(
                f"  [DPI ] line {line_no}: savefig dpi={dpi} < 200 "
                f"(use save_figure() or dpi>=200)")

    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="*", help="files/dirs to scan "
                                              "(default: whole package)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when violations are found")
    args = ap.parse_args()

    if args.targets:
        files = [Path(t) for t in args.targets]
    else:
        files = sorted(PKG_ROOT.rglob("*.py"))

    n_files = 0
    n_violations = 0
    for f in files:
        if f.is_dir():
            continue
        if not f.name.endswith(".py"):
            continue
        if is_skipped(f):
            continue
        v = scan_file(f)
        if v:
            n_files += 1
            n_violations += len(v)
            print(f"{f.relative_to(PKG_ROOT)}:")
            print("\n".join(v))
            print()

    total_scanned = sum(
        1 for f in files if f.is_file() and f.name.endswith(".py")
        and not is_skipped(f))
    print(f"Scanned {total_scanned} Python files: "
          f"{n_files} non-compliant, {n_violations} violations.")
    if args.strict and n_violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
