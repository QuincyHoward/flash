"""B1 —— 通用识别与提取层测试（行剖面 / 列剖面 / 反演 / 包络）。

★ 本文件是**阶段 B 的门禁**：**禁用家族先验**的情况下，
通用路径必须能反演出下列文件的正确维数：
``AL_eos`` (66,74)、``eos_41.dat`` (44,22)、``Al.feos.301`` (192,69)、
``BE_eos`` (101,50)、``C_EOS`` (101,23)、``opc_1031.dat`` (31,46)

并且：**故意破坏一个数字后必须落 ambiguous/unrecognized，不得静默成功**。
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
from _runner import expect, expect_eq, main

from eosop_pro import config
from eosop_pro.core import columnprofile as cp
from eosop_pro.core import fortran_numbers as fn
from eosop_pro.core import lineprofile as lp
from eosop_pro.core.envelope import DEFAULT_ENVELOPE, Envelope, check_values
from eosop_pro.core.inference import TEMPLATES, infer_file, infer_layout


# ── ② 行剖面 ───────────────────────────────────────────────────
def test_lineprofile_payload_line_is_not_header():
    """★ payload 行含指数 ``E`` → 剔除数值后无字母残留，才判为 payload。

    这里用 ``modal_only=False`` —— 合成的三行宽度不一（51/75/60），
    众数过滤会剔除少数派；该过滤的行为由下面的真实文件用例覆盖。
    """
    p = lp.profile_lines([
        "ALUMINUM    LANL SESAME #3711 DATED: 22581 11483",
        "     41     1.30000000E+01 2.69820000E+01 2.75681460E+00    2004",
        "-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01",
    ], modal_only=False)
    expect_eq(p.payload_flags[0], False, "注释行不是 payload")
    expect_eq(p.payload_flags[1], True, "纯数字表头行本身也算 payload")
    expect_eq(p.payload_flags[2], True, "紧邻负数行是 payload")


def test_lineprofile_header_end_for_textual_comment():
    """有文本注释头时，``header_end`` 应把它排除。"""
    p = lp.profile_lines([
        "ALUMINUM    LANL SESAME #3711 DATED: 22581 11483",
        " 4.40000000E+01 2.20000000E+01 0.00000000E+00 2.75681460E-04",
        " 5.93937702E-04 8.71781324E-04 1.27959999E-03 1.87819593E-03",
    ])
    expect_eq(p.header_end, 1, "注释行应被排除在 payload 之外")
    expect(p.n_payload >= 2, p.describe())


def test_lineprofile_real_file_modal_length():
    p = lp.profile_file(config.MATTER("mat_Al-1.0/AL_eos"))
    expect_eq(p.modal_length, 60, "AL_eos 众数行宽应为 60（4×15）")
    expect_eq(p.n_blank, 0, "AL_eos 无空行")


def test_lineprofile_detects_payload_interruption():
    """payload 区被**含字母的行**打断 → 应记录中断。

    这是发现拼接文件（如 ``opbe`` 里多张表串在一起）与"格式误判"的关键信号：
    真正的 payload 行不会含字母，一旦出现就是结构性异常。
    """
    p = lp.profile_lines([
        "1.0 2.0 3.0 4.0",
        "5.0 6.0 7.0 8.0",
        "*** comment ***",
        "another note line",
        "yet another note",
        "1.0 2.0 3.0 4.0",
        "5.0 6.0 7.0 8.0",
    ], modal_only=False)
    expect(any("中断" in n for n in p.notes), f"应记录中断，实测 {p.notes}")
    expect(p.n_payload == 4, f"只应识别 4 行 payload，实测 {p.n_payload}")


# ── ③ 列剖面 ───────────────────────────────────────────────────
def test_columnprofile_realistic_width():
    """定宽字段（右对齐）→ 应得 W=15。

    实测教训：``/`` 右对齐字段的**散碎前导空白**会让「空白列间距众数」偏小，
    故长度法（``行长 // token 数``）被定为**主判据**，空白列法仅作佐证。
    两者不一致时必须**记录冲突**而不是静默选一个。
    """
    lines = [f"{i:.6e}".rjust(15) + f"{i * 2:.6e}".rjust(15)
             + f"{i * 3:.6e}".rjust(15) for i in range(1, 12)]
    p = cp.profile_columns(lines)
    expect_eq(p.width, 15, f"应得 W=15，实测 {p.describe()}")
    expect("line-length" in p.rule, f"主判据应为长度法，实测 {p.rule}")
    expect(any("长度法" in c for c in p.conflicts),
           f"两法不一致时应记录冲突，实测 {p.conflicts}")


def test_columnprofile_packed_negatives_falls_back():
    """★ 字段紧邻（负号吃掉前导空格）→ 无空白列 → 必须**退化并声明**。"""
    line = "-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01"
    p = cp.profile_columns([line] * 5)
    expect_eq(p.blank_columns, [], "紧邻负数字段不应有空白列")
    expect(any("退化" in c or "空白列" in c for c in p.conflicts),
           f"应声明退化，实测 {p.conflicts}")
    expect(p.width in (15, 16, 20, p.width_from_length or 15),
           f"宽度应落在合理集合，实测 {p.width}")


def test_columnprofile_real_files():
    from eosop_pro.core import textio
    for rel, expected in (("mat_Al-1.0/FEOS/Al.feos.301", 15),
                          ("mat_He/Untitled.304", 16)):
        d = textio.read_text(config.MATTER(rel))
        payload = [ln for ln in d.lines[1:] if ln.strip()]
        p = cp.profile_columns(payload)
        expect(p.width == expected, f"{rel} 应得 W={expected}，实测 {p.width} ({p.rule})")


# ── ④ 反演（禁用先验的硬门禁）──────────────────────────────────
def test_templates_registered():
    names = {t.name for t in TEMPLATES}
    for n in ("f1_with_e0", "f1_no_e0", "f2_gray", "f2_multigroup",
              "hyades_eos", "mpqeos"):
        expect(n in names, f"模板应含 {n}，实测 {names}")


def test_inference_solves_without_family_priors():
    """★ 阶段 B 门禁：**不给任何家族先验**也要解对维数。"""
    cases = {
        "mat_Al-1.0/AL_eos": (66, 74),
        "hyades/sesame/eos_41.dat": (44, 22),
        "mat_Al-1.0/FEOS/Al.feos.301": (192, 69),
        "mat_Be-1.0/BE_eos": (101, 50),
        "mat_C-1.0/C_EOS": (101, 23),
        "hyades/Opacity/opc_1031.dat": (31, 46),
    }
    for rel, dims in cases.items():
        r = infer_file(config.MATTER(rel))
        expect(r.status == "ok", f"{rel} 应为 ok，实测 {r.status}")
        expect_eq(r.best.dims, dims, f"{rel} 维数")


def test_inference_ambiguous_lists_all_candidates():
    """多解时必须**列出全部并列候选**，而不是挑一个。"""
    r = infer_file(config.MATTER("mat_Al-1.0/1041_ROSS"))
    if r.status == "ambiguous":
        expect(len(r.candidates) >= 2, f"应列出 >=2 个候选，实测 {len(r.candidates)}")
        expect(any("并列候选" in n for n in r.notes), f"notes={r.notes}")
    else:
        expect(r.status == "ok", f"实测 {r.status}")


def test_broken_file_never_silently_succeeds():
    """★ 故意破坏一个数字 → 必须 ambiguous/unrecognized。"""
    src = config.MATTER("mat_Al-1.0/AL_eos").read_text(encoding="utf-8", errors="replace")
    broken = src.rstrip()
    broken = broken[: broken.rfind(" ")].rstrip()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "broken_eos"
        p.write_text(broken, encoding="utf-8")
        r = infer_file(p)
        expect(r.status in ("ambiguous", "unrecognized"),
               f"破坏后不应静默成功，实测 {r.status}")
        expect(r.best is None, "破坏后不应给出 best")


def test_garbage_is_unrecognized():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "noise.dat"
        p.write_text("hello world\nthis is not data\n", encoding="utf-8")
        r = infer_file(p)
        expect_eq(r.status, "unrecognized")


def test_report_is_produced():
    r = infer_file(config.MATTER("mat_Al-1.0/1041_ROSS"))
    rep = r.report()
    for token in ("通用布局反演报告", "行剖面", "维度候选", "自洽候选"):
        expect(token in rep, f"报告应含 {token!r}")


# ── ⑤ 包络 ─────────────────────────────────────────────────────
def test_envelope_rejects_absurd_magnitudes():
    c = check_values({"rho": [1e-6, 2.7, 100.0]})
    expect(c.ok, f"正常密度应通过，实测 {c.describe()}")
    c2 = check_values({"rho": [1.0, 1e30]})
    expect(not c2.ok, "1e30 g/cm³ 应被判越界")
    expect(c2.n_outside >= 1, c2.describe())


def test_envelope_is_configurable_and_reported():
    env = Envelope(rho_max=1e3)
    c = check_values({"rho": [1e4]}, envelope=env)
    expect(not c.ok, "自定义包络应生效")
    expect(any("包络" in n for n in c.notes), f"必须打印所用包络，实测 {c.notes}")
    expect(DEFAULT_ENVELOPE.describe().count("e") > 0)


def test_envelope_log10_flags():
    """以 log10 存储的量应先还原再比。"""
    c = check_values({"rho": [-6.0, 0.0, 2.0]}, log10_flags={"rho": True})
    expect(c.ok, f"log10 密度应通过，实测 {c.describe()}")
    c2 = check_values({"rho": [500.0]}, log10_flags={"rho": True})
    expect(not c2.ok, "10^500 应越界")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
