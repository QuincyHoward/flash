"""A2 —— F6c Hugoniot（``*.hug``）解析器测试。

实测 ``hyades/sesame/eos_41.hug`` 第 0 行（注释）本身就把列名与单位写在方括号里::

    # Rho[g/cm^3]  T [eV]   P [Mbar]  E [erg/g]  Us [km/s]  Up [km/s]

→ 「注释即证据」的又一处：直接解析为轴/场的单位。
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
from eosop_pro.parsers import hugoniot as hu

_HDR = "# Rho[g/cm^3]  T [eV]   P [Mbar]  E [erg/g]   Us [km/s]   Up [km/s]"


def test_column_header_regex():
    cols = hu.parse_column_header(_HDR)
    names = [c[0] for c in cols]
    units = [c[1] for c in cols]
    expect("Rho" in names and "T" in names and "Us" in names, f"names={names}")
    expect("g/cm^3" in units, f"units={units}")
    expect("eV" in units, f"units={units}")
    expect("km/s" in units, f"units={units}")


def test_eos_41_hug_parsed():
    t = hu.parse(config.MATTER("hyades/sesame/eos_41.hug"), "hyades/sesame/eos_41.hug")
    expect_eq(t.kind, "HUGONIOT")
    expect(t.n_numbers_seen > 100, f"应有数据行，实测 {t.n_numbers_seen}")
    expect("declared:inline" in t.unit_source, f"unit_source={t.unit_source}")


def test_units_applied_to_fields():
    t = hu.parse(config.MATTER("hyades/sesame/eos_41.hug"), "hyades/sesame/eos_41.hug")
    units = set(t.field_units.values()) | set(t.axis_units.values())
    expect("eV" in units, f"应含 eV，实测 units={units}")
    expect(any("km/s" in u for u in units), f"应含 km/s，实测 units={units}")


def test_all_hug_files():
    """全树 ``.hug`` 逐个尝试。

    实测 ``mat_Au-1.0/AU_eos.hug`` **只有 1 行表头、无数据** → 解析器正确抛
    ``ParseError``（这是"拒绝为空文件编造数据"的正确行为），故本测试允许有
    少量此类退化文件，但要求**多数可解析**。
    """
    import os
    from eosop_pro import config as cfg
    found = []
    for root, _d, files in os.walk(cfg.MATTER_DIR):
        for f in files:
            if f.lower().endswith(".hug"):
                found.append(os.path.join(root, f))
    expect(len(found) >= 4, f"应有 >=4 个 .hug，实测 {len(found)}")

    ok, empty = 0, []
    for p in found:
        try:
            t = hu.parse(p, os.path.basename(p))
            expect(t.n_numbers_seen > 0, f"{p} 应有数据")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            empty.append(f"{os.path.basename(p)}: {exc}")
    expect(ok >= len(found) - 2, f"多数应可解析，实测 ok={ok}/{len(found)} 失败={empty}")


def test_scaled_unit_header_variant():
    """``Al.feos.hug`` 的表头带缩放因子：``Rho [1.000000e+000 g/cm^3]``。

    必须剥离数字、保留单位，并把缩放因子记在单位串里（不丢失信息）。
    """
    hdr = ("# Rho [1.000000e+000 g/cm^3]  T [1.000000e+000 eV]  "
           "P [1.000000e+012 dyne/cm^2]")
    cols = dict(hu.parse_column_header(hdr))
    expect("Rho" in cols, f"cols={cols}")
    expect("g/cm^3" in cols["Rho"], f"应剥离缩放因子保留单位，实测 {cols['Rho']!r}")
    expect("x1.000000e+000" in cols["Rho"] or "x1" in cols["Rho"],
           f"缩放因子应被保留，实测 {cols['Rho']!r}")
    expect("dyne/cm^2" in cols.get("P", ""), f"实测 {cols.get('P')!r}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
