"""``eosop_pro.prune`` 测试 —— 报告目录保留策略。

为什么值得单独测
----------------
这个模块**删文件**。删错的代价是"证据没了"，而且不会有任何报错。
所以三条纪律必须由测试守住：

1. **永远保留最新一批**（哪怕 ``keep=0`` 也要当成 1）
2. **固定名报告永不删**（``zeff_inventory.*`` / ``type_conflict.*``）
3. **一次运行的 csv/json/md 同进同出**（共享时间戳 → 不能被拆开）

另外验证"只动报告、不碰 h5/plots/logs"。
"""

import tempfile
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

from eosop_pro import config, prune
from eosop_pro import cli as mcli


def _mk(tmp: Path, name: str) -> Path:
    p = tmp / name
    p.write_text("x", encoding="utf-8", newline="\n")
    return p


def _tree(tmp: Path, *names: str) -> None:
    for n in names:
        _mk(tmp, n)


# ══════════════════════════════════════════════════════════════
def test_report_prefixes_are_timestamped_kinds_only():
    """固定名报告（无时间戳）不应出现在前缀表里 —— 它们每次覆盖，无需清理。"""
    for pre in prune.REPORT_PREFIXES:
        expect(pre.endswith("."), f"{pre} 应为 `<kind>.` 形式")
        expect("zeff_inventory" not in pre, "zeff_inventory 是固定名，不参与")
        expect("type_conflict" not in pre, "type_conflict 是固定名，不参与")


def test_list_batches_groups_by_timestamp():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "audit_all.20260101T000000.csv", "audit_all.20260101T000000.json",
              "audit_all.20260101T000000.md",
              "audit_all.20260202T000000.csv", "audit_all.20260202T000000.json",
              "audit_all.20260202T000000.md",
              "zeff_inventory.md", "notes.txt")
        b = prune.list_report_batches(d)
        expect_in("audit_all", b)
        expect_eq(len(b["audit_all"]), 2, f"应识别 2 批，实测 {b}")
        # 同批三份在一起
        expect_eq(len(b["audit_all"][0]), 3)
        # 固定名不进批次表
        expect_eq(sorted(b), ["audit_all"], f"只应有 audit_all，实测 {sorted(b)}")


def test_prune_keeps_latest_batch_and_removes_older():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d,
              "audit_all.20260101T000000.csv", "audit_all.20260101T000000.json",
              "audit_all.20260101T000000.md",
              "audit_all.20260202T000000.csv", "audit_all.20260202T000000.json",
              "audit_all.20260202T000000.md")
        r = prune.prune_reports(outdir=d, keep=1)
        expect_eq(len(r["audit_all"]["removed"]), 3)
        expect_eq(len(r["audit_all"]["kept"]), 3)
        left = sorted(p.name for p in d.iterdir())
        expect_eq(left, ["audit_all.20260202T000000.csv",
                         "audit_all.20260202T000000.json",
                         "audit_all.20260202T000000.md"],
                  f"应只剩最新一批，实测 {left}")


def test_prune_never_deletes_the_latest_even_with_keep_zero():
    """★ ``keep=0`` 也当 1 —— 绝不把"最新一批"删掉。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "plot_all.20260101T000000.md", "plot_all.20260202T000000.md")
        r = prune.prune_reports(outdir=d, keep=0)
        expect_eq(len(r["plot_all"]["kept"]), 1)
        expect_eq(len(r["plot_all"]["removed"]), 1)
        expect((d / "plot_all.20260202T000000.md").exists(), "最新一批必须留着")


def test_prune_never_touches_fixed_name_reports():
    """★ 固定名报告（每次覆盖的那类）必须原样保留。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "zeff_inventory.csv", "zeff_inventory.md",
              "type_conflict.csv", "type_conflict.md",
              "identify.20260101T000000.md", "identify.20260202T000000.md")
        prune.prune_reports(outdir=d, keep=1)
        left = sorted(p.name for p in d.iterdir())
        for must in ("zeff_inventory.csv", "zeff_inventory.md",
                     "type_conflict.csv", "type_conflict.md",
                     "identify.20260202T000000.md"):
            expect_in(must, left, f"{must} 不该被删")
        expect("identify.20260101T000000.md" not in left, "旧的批次报告应被删")


def test_prune_dry_run_changes_nothing():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "audit_all.20260101T000000.md", "audit_all.20260202T000000.md")
        before = sorted(p.name for p in d.iterdir())
        r = prune.prune_reports(outdir=d, keep=1, dry_run=True)
        after = sorted(p.name for p in d.iterdir())
        expect_eq(before, after, "dry-run 不得删除任何文件")
        expect_eq(len(r["audit_all"]["removed"]), 1,
                  "但应报告将会删什么（dry-run 只列不删）")


def test_prune_multiple_kinds_independently():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d,
              "audit_all.20260101T000000.md", "audit_all.20260202T000000.md",
              "convert_all.20260101T000000.md", "convert_all.20260202T000000.md",
              "convert_all.20260303T000000.md")
        r = prune.prune_reports(outdir=d, keep=1)
        expect_eq(len(r["audit_all"]["removed"]), 1)
        expect_eq(len(r["convert_all"]["removed"]), 2)
        left = sorted(p.name for p in d.iterdir())
        expect_eq(left, ["audit_all.20260202T000000.md",
                         "convert_all.20260303T000000.md"])


def test_prune_ignores_non_report_extensions_and_dirs():
    """只处理 ``csv/json/md``；``.h5`` / ``.png`` / 子目录一律不动。"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "audit_all.20260101T000000.md", "audit_all.20260202T000000.md",
              "audit_all.20260101T000000.h5", "audit_all.20260101T000000.png")
        (d / "inference_reports").mkdir()
        _mk(d / "inference_reports", "x.md")
        prune.prune_reports(outdir=d, keep=1)
        expect((d / "audit_all.20260101T000000.h5").exists(), "h5 不该被删")
        expect((d / "audit_all.20260101T000000.png").exists(), "png 不该被删")
        expect((d / "inference_reports").is_dir(), "子目录不该被删")
        expect((d / "inference_reports" / "x.md").exists())


def test_prune_empty_and_missing_dir_is_safe():
    with tempfile.TemporaryDirectory() as td:
        expect_eq(prune.prune_reports(outdir=Path(td)), {})
        expect_eq(prune.prune_reports(outdir=Path(td) / "nope"), {})
        expect_eq(prune.list_report_batches(Path(td) / "nope"), {})


def test_cli_prune_reports_dispatch():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _tree(d, "plot_all.20260101T000000.md", "plot_all.20260202T000000.md")
        expect_eq(mcli.main(["prune-reports", "--outdir", str(d)]), 0)
        expect_eq(sorted(p.name for p in d.iterdir()),
                  ["plot_all.20260202T000000.md"])
        # --dry-run
        _tree(d, "plot_all.20260303T000000.md")
        expect_eq(mcli.main(["prune-reports", "--outdir", str(d),
                             "--keep", "2", "--dry-run"]), 0)
        expect_eq(len(list(d.iterdir())), 2, "dry-run 不应删文件")


def test_cli_exposes_prune_reports_subcommand():
    import re

    src = Path(mcli.__file__).read_text(encoding="utf-8")
    expect_in('"prune-reports"', src)
    expect_in("cmd_prune_reports", src)
    reg = set(re.findall(r'add_parser\(\s*"([a-z-]+)"', src))
    expect_in("prune-reports", reg)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
