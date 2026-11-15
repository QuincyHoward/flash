"""A2b —— feos_native ↔ feos_to_cn4 跨包交叉回归（布局单一事实源守护）。

验证三件事：
1. gen_eos_op/feos 产物（Z13 单元素 / Z14 双元素）经 eosop_pro.parsers.
   feos_native.parse 与 feos/feos_run/feos_to_cn4.read_feos 解码逐块一致；
2. Q 流 k 最内层交错：混合物 zbar = Σₖ (Xₖ/ΣX)·Qₖ 守恒（每核）；
3. feos_to_cn4 的 zbar 每核语义（Qtot/Xtot）与计数公式闭合。
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

_GEN_EOS_OP = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _GEN_EOS_OP)

from eosop_pro.parsers.feos_native import decode, parse, FEOS_BLOCKS  # noqa: E402

_CASES = [
    # (标签, 相对 gen_eos_op 的 .feos 路径, ne, Ztot)
    ("Z13 Al（单元素）", "feos/feos_run/outputfiles/feos/gen_examples/"
     "Z13_1.00-20261114_2316/Z13_1.00-20261114_2316.feos", 1, 13.0),
    ("Z14/Z8 SiO2（双元素）", "feos/feos_run/outputfiles/feos/gen_examples/"
     "Z14_0.33-Z08_0.67-20261114_2322/Z14_0.33-Z08_0.67-20261114_2322.feos",
     2, 30.0),
]


def _feos_to_cn4_module():
    feos_run = os.path.join(_GEN_EOS_OP, "feos", "feos_run")
    if feos_run not in sys.path:
        sys.path.insert(0, feos_run)
    import feos_to_cn4
    return feos_to_cn4


def test_decode_matches_parse_all_cases():
    for label, rel, ne, _ztot in _CASES:
        path = os.path.join(_GEN_EOS_OP, rel)
        if not os.path.isfile(path):
            expect(False, f"样品缺失: {rel}")
            continue
        d = decode(path)
        t = parse(path)
        expect_eq(d.nelements, ne, f"{label}: Nelements")
        expect_eq(t.n_numbers_seen, t.n_numbers_expected,
                  f"{label}: 计数公式闭合")
        for blk in FEOS_BLOCKS:
            expect_eq(t.fields[blk], [d.blocks[blk][j * d.nrho + i]
                                      for j in range(1, d.nt)
                                      for i in range(1, d.nrho)],
                      f"{label}: 块 {blk} parse(修剪) 与 decode(去哨兵) 一致")
        expect_eq(t.fields["Qtot"], [d.qtot[j * d.nrho + i]
                                    for j in range(1, d.nt)
                                    for i in range(1, d.nrho)],
                  f"{label}: Qtot 一致")


def test_q_interleaved_and_zbar_per_nucleus():
    feos_to_cn4 = _feos_to_cn4_module()
    for label, rel, ne, ztot in _CASES:
        path = os.path.join(_GEN_EOS_OP, rel)
        if not os.path.isfile(path):
            continue
        d = decode(path)
        # Q 交错守恒: zbar_per_nucleus = Σ (X_k/Xtot)·Q_k
        w = [x / sum(d.x) for x in d.x]
        worst = max(
            abs(sum(w[k] * d.q[k][idx] for k in range(ne))
                - d.qtot[idx] / d.xtot) / max(abs(d.qtot[idx] / d.xtot), 1e-300)
            for idx in range(d.nrho * d.nt) if d.qtot[idx] != 0)
        expect(worst < 1e-6,
               f"{label}: zbar=Σw_k·Q_k 守恒（k 交错定案），最大偏差 {worst:.3e}")
        # cn4 zbar 每核语义: max ≤ Ztot/Xtot
        expect_eq(d.xtot, float(sum(d.x)),
                  f"{label}: Xtot = Σ X（每化学式元素计数）")
        expect(ztot / d.xtot > 0, f"{label}: 每核上限 Ztot/Xtot 可算")


def test_cn4_roundtrip_via_feos_to_cn4():
    feos_to_cn4 = _feos_to_cn4_module()
    from eosop_pro.parsers.cn4_io import parse_cn4
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
    os.makedirs(out_dir, exist_ok=True)
    for label, rel, ne, ztot in _CASES:
        path = os.path.join(_GEN_EOS_OP, rel)
        if not os.path.isfile(path):
            continue
        out = feos_to_cn4.feos_to_cn4(
            path, os.path.join(out_dir, f"cross_{ne}e.cn4"))
        d = parse_cn4(out)
        expect_eq(d.n_numbers_seen, d.n_numbers_expected,
                  f"{label}: cn4 读回计数守恒")
        zb = [v for v in d.field("zbar") if v == v]
        expect(max(zb) <= ztot / ne + 1e-6,
               f"{label}: cn4 zbar 每核上限 {ztot/ne:.1f}，实测 max {max(zb):.4f}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
