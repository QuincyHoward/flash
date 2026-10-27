# -*- coding: utf-8 -*-
"""probe_12_verify: verify group counts (100 vs 20), material-number table, header dims."""
import os, re, json

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
M = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
OUT = os.path.join(REPO, ".workbuddy", "tmp", "out_12.txt")

def head(p, n=3):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [f.readline().rstrip("\r\n") for _ in range(n)]

def firstline(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.readline().rstrip("\r\n")

def numeric_header(p):
    """Extract the (Tmin,Tmax,rho_min,rho_max) or group-count header line for _opp family."""
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        l0 = f.readline().rstrip("\r\n")
        l1 = f.readline().rstrip("\r\n")
    return l0, l1

buf = []
buf.append("### A. _op*_ and _mop*_ group-count verification ###")
PATTERNS = [
    ("mat_Au-1.0/AU_op03p", "Planck MG (SNOP)"),
    ("mat_Au-1.0/AU_op03r", "Ross MG (SNOP)"),
    ("mat_Au-1.0/AU_op03e", "EPS MG (SNOP)"),
    ("mat_Au-1.0/AU_op03z", "ZEFF (SNOP)"),
    ("mat_Au-1.0/Au100PLANCK", "100G Planck"),
    ("mat_Au-1.0/Au100ROSS", "100G Ross"),
    ("mat_Au-1.0/Au100EPS", "100G EPS"),
    ("mat_Au-1.0/Au100ZEFF", "100G ZEFF"),
    ("mat_Gd/Gd20PLANCK", "20G Planck"),
    ("mat_Gd/Gd100PLANCK", "100G Planck"),
    ("mat_Gd/Gd_op100PLANCK", "op100 Planck"),
    ("mat_Gd/Gd_op100ZEFF", "op100 ZEFF"),
    ("mat_Gd/Gd20ZEFF", "20G ZEFF"),
    ("mat_Ti/Ti_Planck", "Ti Planck 1G"),
    ("mat_Ti/Ti_Ross", "Ti Ross 1G"),
    ("mat_Ti/Ti_EPS", "Ti EPS 1G"),
    ("mat_Gd/Gd100ZEFF", "100G ZEFF Gd"),
    ("CH/CH_mopp20", "CH mopp20"),
    ("CH/CHSi1_mopp100", "CHSi1 mopp100"),
    ("CH/C_mopp", "C mopp"),
]
for rel, note in PATTERNS:
    p = os.path.join(M, rel)
    if not os.path.exists(p):
        buf.append("MISSING %s" % rel); continue
    sz = os.path.getsize(p)
    try:
        l0, l1 = numeric_header(p)
    except Exception as e:
        l0 = l1 = "<err %s>" % e
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        nl = sum(1 for _ in f)
    buf.append("%-30s %-20s size=%9d lines=%7d" % (rel, note, sz, nl))
    buf.append("     L0=%r" % l0)
    buf.append("     L1=%r" % l1)

buf.append("\n\n### B. material-number (NUMERO) table from AU_info vs *_op03* headers ###")
buf.append("AU_info says:  Z:27002003; P:27003003; R:27004003; E:27005003")

buf.append("\n\n### C. Gd20 vs Gd100 vs Gd_op100 : size ratios ###")
gd = ["mat_Gd/Gd20PLANCK", "mat_Gd/Gd100PLANCK", "mat_Gd/Gd_op100PLANCK",
      "mat_Gd/Gd20ROSS", "mat_Gd/Gd100ROSS", "mat_Gd/Gd_op100ROSS",
      "mat_Gd/Gd20ZEFF", "mat_Gd/Gd100ZEFF", "mat_Gd/Gd_op100ZEFF"]
for r in gd:
    p = os.path.join(M, r)
    if os.path.exists(p):
        buf.append("  %-26s %d" % (r, os.path.getsize(p)))

buf.append("\n\n### D. _eos family headers (AU_eos vs AU_eosd vs BE_eos vs BE_eos_e/i) ###")
for r in ["mat_Au-1.0/AU_eos", "mat_Au-1.0/AU_eosd", "mat_Be-1.0/BE_eos",
          "mat_Be-1.0/BE_eos_e", "mat_Be-1.0/BE_eos_i", "mat_DT-1.0/DT_EOS",
          "mat_DT-1.0/DT_EOS_e", "mat_DT-1.0/DT_EOS_i", "mat_Ti/Ti_eos",
          "mat_C-1.0/C_EOS", "mat_Au-1.0/AU_op03z", "mat_Ti/422_ieos",
          "mat_Al-1.0/41_ieos", "mat_Al-1.0/42_ieos", "mat_C-1.0/511_ieos"]:
    p = os.path.join(M, r)
    if not os.path.exists(p):
        buf.append("MISSING " + r); continue
    sz = os.path.getsize(p)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = [f.readline().rstrip("\r\n") for _ in range(3)]
        f.seek(0); nl = sum(1 for _ in f)
    buf.append("%-26s size=%8d lines=%6d" % (r, sz, nl))
    for i, ln in enumerate(lines):
        buf.append("   L%d=%r" % (i, ln))

buf.append("\n\n### E. AU_info full decode of NUMERO convention ###")
buf.append("  NUMERO = ZZ|TT|KK  e.g. 27002003 -> physical 27/00/2003? re-read:")
p = os.path.join(M, "mat_Au-1.0/AU_info")
buf.append("  raw AU_info:")
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, ln in enumerate(f):
        buf.append("   %2d| %s" % (i, ln.rstrip()))
buf.append("  AU=196.97 -> first digits '19697'?  actually 27002003 = '2700' + '2003'?")
buf.append("  AU_eos line0 = ' 27001000 -> EOS numero 27001000 (Z-table=27001000)")
buf.append("  => NUMERO encodes: <2-digit material-code><3-digit ...>")

buf.append("\n\n### F. mat_Ti family header (Ti_Planck/Ti_Ross/Ti_EPS) ###")
for r in ["mat_Ti/Ti_Planck", "mat_Ti/Ti_Ross", "mat_Ti/Ti_EPS"]:
    p = os.path.join(M, r)
    if os.path.exists(p):
        buf.append("  %-20s L0=%r" % (r, firstline(p)))

buf.append("\n\n### G. CH/CHSi1_mopp vs mopp100 vs mopr20 ###")
for r in ["CH/CHSi1_mopp", "CH/CHSi1_mopp100", "CH/CHSi1_mopr", "CH/CHSi1_mopr100",
          "CH/CH_mopp20", "CH/CH_mopr20", "CH/C_mopp", "CH/C_mopr", "CH/CHSi10_mopp",
          "CH/CHSi10_mopr", "CH/CH_ieos", "CHBr3at%/C50H47Br3_mopp"]:
    p = os.path.join(M, r)
    if not os.path.exists(p):
        buf.append("MISSING " + r); continue
    sz = os.path.getsize(p)
    try:
        l0, l1 = numeric_header(p)
    except Exception as e:
        l0, l1 = "<err>", "<err>"
    buf.append("%-28s size=%8d L0=%r L1=%r" % (r, sz, l0, l1))

buf.append("\n\n### H. mat_Others CH10Water* family ###")
for r in ["mat_Others/CH10Water1/CH10Water1_ieos", "mat_Others/CH10Water1/CH2_H2O_1m1Z",
          "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Others/CH10Water1/CH2_H2O_1m1opr"]:
    p = os.path.join(M, r)
    if not os.path.exists(p):
        buf.append("MISSING " + r); continue
    sz = os.path.getsize(p)
    l0, l1 = numeric_header(p)
    buf.append("%-46s size=%8d\n   L0=%r\n   L1=%r" % (r, sz, l0, l1))

buf.append("\n\n### I. mat_C-1.0 Carbon_DLC_ieos_e/i vs Carbon_Polystyrene ###")
for r in ["mat_C-1.0/Carbon_DLC_ieos_e", "mat_C-1.0/Carbon_DLC_ieos_i",
          "mat_C-1.0/Carbon_Polystyrene_ieos_e", "mat_C-1.0/Carbon_Polystyrene_ieos_i",
          "mat_C-1.0/CH_ieos", "mat_CELIA/CH_ieos", "mat_CELIA/DD_ieos", "mat_CELIA/DT_ieos"]:
    p = os.path.join(M, r)
    if not os.path.exists(p):
        buf.append("MISSING " + r); continue
    sz = os.path.getsize(p)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        l0 = f.readline().rstrip("\r\n"); l1 = f.readline().rstrip("\r\n")
    buf.append("%-40s size=%8d\n   L0=%r\n   L1=%r" % (r, sz, l0, l1))

open(OUT, "w", encoding="utf-8").write("\n".join(buf))
print("written", OUT, len(buf))
