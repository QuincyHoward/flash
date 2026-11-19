"""A2 —— F3 Hyades / SESAME 解析器测试。

实测基准
* ``eos_41.dat``   L=**2004** → (44,22)；``eos_11.dat`` L=**2577** → (50,25)
* ``eos_21.dat``   L=**4743** → (43,54)
* ``opc_1031.dat`` L=**2931** → (31,46)
* ``qeos_52.dat``  L=2004

★ 两个要点
1. ``L = 2 + NR + NT + 2*NR*NT`` 的方程**并不唯一**（``L=2004`` 有 (44,22) 与 (2,400)、
   (4,222)… 共 8 组解）→ NR/NT 只能由 payload 前两个数确定，公式仅作交叉校验。
2. 部分 ``eos_*`` 文件在数组末尾**补零**凑满每行 5 字段（实测 eos_41 多 1、
   eos_11/eos_81 多 3）→ 必须显式标注 ``raw_tail``。
"""

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
from eosop_pro.parsers import hyades_eos as f3


def _p(rel):
    return f3.parse(config.MATTER(rel), rel)


def test_solve_dims_returns_all_roots():
    """方程多解 → 返回全部解；真解必在其中。"""
    sols = f3.solve_dims(2004)
    expect(len(sols) > 1, f"L=2004 应有多个解，实测 {sols}")
    expect((44, 22) in sols, f"(44,22) 应在解集，实测 {sols}")
    expect((2, 400) in sols, "短边解也应在解集内（故不能靠公式定维度）")
    expect_eq(f3.solve_dims(7), [], "过小的 L 应无解")


def test_eos_41_baseline():
    t = _p("hyades/sesame/eos_41.dat")
    expect_eq((t.table_id, t.nr, t.nt), (41, 44, 22))
    expect_eq(t.n_numbers_expected, 2004 + 1,
              "expected = L + 已记录的 1 个补零")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "seen 必须等于 expected")
    expect("P" in t.fields and "E" in t.fields, f"fields={list(t.fields)}")
    expect_eq(t.field_shape["P"], (22, 44), "(nt, nr)")


def test_eos_11_and_21_dims():
    a = _p("hyades/sesame/eos_11.dat")
    expect_eq((a.table_id, a.nr, a.nt), (11, 50, 25))
    b = _p("hyades/sesame/eos_21.dat")
    expect_eq((b.table_id, b.nr, b.nt), (21, 43, 54))


def test_opc_1031_opacity_two_arrays():
    """``opc_*`` 有**两个 (NR×NT) 数组** = [Rosseland, Planck]（SESAME 301 约定）。"""
    t = _p("hyades/Opacity/opc_1031.dat")
    expect_eq((t.table_id, t.nr, t.nt), (1031, 31, 46))
    expect_eq(t.n_numbers_expected, 2931)
    expect("Rosseland" in t.fields and "Planck" in t.fields, f"fields={list(t.fields)}")
    expect_eq(t.field_shape["Rosseland"], (46, 31))
    expect_eq(t.field_units["Rosseland"], "cm2/g")


def test_temperature_kev_to_ev():
    t = _p("hyades/sesame/eos_41.dat")
    T = t.axes["Te"]
    expect(min(T) >= 0, f"min(T)={min(T)}（该族温度网格自 0 起，允许 0）")
    expect(max(T) > 1e3, f"keV 网格应换算到 eV 量级，实测 max={max(T):.4g}")


def test_comment_line_number_is_not_payload():
    """★ 注释行的 SESAME 号/日期绝不能进入数值流。

    ``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483`` 含 3 个数字；
    本解析器从**第 2 行之后**取数，故这 3 个数字与 L=2004 的计数无关。
    """
    t = _p("hyades/sesame/eos_41.dat")
    payload_only = t.n_numbers_seen - len(t.fields.get("raw_tail", []))
    expect_eq(payload_only, 2004, f"payload 应恰为 L=2004，实测 {payload_only}")
    expect(any("SESAME" in n for n in t.notes), f"应记录注释声明，实测 {t.notes}")


def test_tail_padding_recorded_not_swallowed():
    t11 = _p("hyades/sesame/eos_11.dat")
    expect("raw_tail" in t11.fields, "eos_11 有 3 个补零")
    expect_eq(len(t11.fields["raw_tail"]), 3)
    expect(any("补零" in n or "未声明" in n for n in t11.notes), f"notes={t11.notes}")
    t41 = _p("hyades/sesame/eos_41.dat")
    expect_eq(len(t41.fields.get("raw_tail", [])), 1, "eos_41 有 1 个补零")
    t52 = _p("hyades/qeos/qeos_52.dat")
    expect("raw_tail" not in t52.fields, "qeos_52 无补零")


def test_dos_eof_marker_noted():
    t = _p("hyades/sesame/eos_41.dat")
    expect(any("EOF" in n for n in t.notes), f"应记录 \\x1a，实测 {t.notes}")


def test_header_must_have_five_numbers():
    import eosop_pro.core.text.errors as errs
    raised = False
    try:
        f3.parse_header_line("41 13 26.982 2.7568")
    except errs.ParseError:
        raised = True
    expect(raised)


def test_l_is_cross_checked_against_dims():
    """payload 读出的 (nr,nt) 必须落在 L 的可行解集中（L = expected − 补零数）。"""
    t = _p("hyades/sesame/eos_81.dat")
    L = t.n_numbers_expected - len(t.fields.get("raw_tail", []))
    sols = f3.solve_dims(L)
    expect((t.nr, t.nt) in sols or (t.nt, t.nr) in sols,
           f"(nr,nt)=({t.nr},{t.nt}) 不在 L={L} 的解集 {sols[:6]} 中")


# ── 2026-11-15 sesame/ 全量审计后的加固测试（审计脚本 parsers/test/audit_sesame_dat.py）──

def test_csi25_variant_13char_lowercase_e():
    """13 字符/字段 + 小写 e 变体（fn.extract_numbers 正则与宽度无关）。"""
    t = _p("hyades/sesame/CSi2.5_eos.dat")
    expect_eq((t.table_id, t.nr, t.nt), (1214, 57, 44))
    expect_eq(t.n_numbers_seen, 5119, "L=5119 计数闭合")
    expect("P" in t.fields and "E" in t.fields, f"fields={list(t.fields)}")


def test_mixed_material_header_note():
    """混合材料非标头（无 SESAME#/QEOS 模式）→ notes 显式登记，不静默。"""
    t = _p("hyades/sesame/EOS_Al10Au3.DAT")
    expect_eq((t.table_id, t.nr, t.nt), (1, 50, 50))
    expect(any("no SESAME#/QEOS pattern" in n for n in t.notes),
           f"应登记注释行无模式，实测 {t.notes[-2:]}")


def test_truncated_exponent_token_rejected():
    """★ eos_332 末行 ` 7.4E`：计数守恒但末值错 13 个量级 → 必须显式拒绝
    （用户裁定：忽略 + 告警；分派层冻结清单 see declared_types._KNOWN_CORRUPT）。"""
    import eosop_pro.core.text.errors as errs
    raised = None
    try:
        _p("hyades/sesame/eos_332.dat")
    except errs.ParseError as exc:
        raised = str(exc)
    expect(raised is not None, "eos_332 必须抛 ParseError（防静默错值）")
    expect("truncated" in (raised or ""), f"消息应含 truncated，实测 {raised!r}")


def test_empty_file_rejected():
    import eosop_pro.core.text.errors as errs
    raised = None
    try:
        _p("hyades/sesame/CSi2.5_from_lililing")
    except errs.ParseError as exc:
        raised = str(exc)
    expect(raised is not None and "empty" in raised,
           f"空文件应报 empty，实测 {raised!r}")


def test_flow_id_semantics():
    """编号约定（Hyades 数据格式说明.doc）：2001-2999 电子流 / 3001-3999 离子流。"""
    te = _p("hyades/sesame/eos_2044.dat")
    expect_eq(te.kind, "EOS_ELECTRON", f"2044 电子流，实测 {te.kind}")
    ti = _p("hyades/sesame/eos_3044.dat")
    expect_eq(ti.kind, "EOS_ION", f"3044 离子流，实测 {ti.kind}")
    ts = _p("hyades/sesame/eos_41.dat")
    expect_eq(ts.kind, "EOS_TOTAL", "id<998 保持 EOS_TOTAL")
    expect(any("编号约定" in n for n in te.notes), f"notes 应登记约定，实测 {te.notes[-2:]}")


def test_three_array_variant_x3():
    """F3b 三数组变体：L = 2+nr+nt+3*nr*nt；第三数组以 X3 中性登记（语义未定）。"""
    t = _p("hyades/sesame/eos_31.dat")
    expect_eq((t.nr, t.nt), (65, 32))
    expect_eq(t.n_numbers_seen - len(t.fields.get("raw_tail", [])), 6339)
    expect("X3" in t.fields, f"fields={list(t.fields)}")
    expect_eq(t.field_units["X3"], "unknown")
    expect("3*nr*nt" in t.layout_rule, f"layout_rule={t.layout_rule}")
    expect(any("语义未定" in n for n in t.notes), "notes 应登记语义未定")


def test_single_temperature_degenerate_table():
    """eos_541：nt=1 退化表（L=204=2+67+1+2*67*1），维度闸门放宽至 nt>=1。"""
    t = _p("hyades/sesame/eos_541.dat")
    expect_eq((t.nr, t.nt), (67, 1))
    expect_eq(len(t.axes["Te"]), 1)
    expect(any("nt=1" in n for n in t.notes), f"notes 应登记退化，实测 {t.notes[-2:]}")


#: 全量扫 97 文件的冻结分类（与审计 JSON 同步；清单外任何失败 = FAIL）
#: 依据：parsers/test/_out/sesame_audit.json（2026-11-15）
_KNOWN_SKIP = ("eos_332.dat", "csi2.5_from_lililing")
_KNOWN_F3_ERROR = ("eos_32.hug", "eos_41.hug", "eos_41.dat.par")  # 非 F3 直调对象


def test_sesame_folder_full_sweep():
    """97 文件全量：要么 F3 解析成功，要么命中冻结清单（审计结果固化）。"""
    import eosop_pro.core.text.errors as errs
    d = config.MATTER_DIR / "hyades" / "sesame"
    files = sorted(d.iterdir())
    expect_eq(len(files), 97, f"目录文件数应为 97，实测 {len(files)}")
    n_ok = 0
    for p in files:
        if p.name.lower() in _KNOWN_SKIP or p.name.lower() in _KNOWN_F3_ERROR:
            continue
        try:
            tables = f3.parse_all(p, f"hyades/sesame/{p.name}")
        except (errs.ParseError, errs.CountMismatch) as exc:
            raise AssertionError(f"清单外解析失败: {p.name}: {exc}") from exc
        expect(len(tables) >= 1, f"{p.name} 应至少解析出 1 张表")
        n_ok += 1
    expect_eq(n_ok, 92, f"应恰有 92 个文件解析成功（97 - 2 skip - 3 非 F3 直调），"
                        f"实测 {n_ok}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
