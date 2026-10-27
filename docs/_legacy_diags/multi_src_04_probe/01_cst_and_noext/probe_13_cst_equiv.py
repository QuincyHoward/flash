# -*- coding: utf-8 -*-
"""probe_13_cst_equiv: verify DE vs EN numeric equivalence; INF census per isotherm; column widths."""
import os, re, json
from collections import Counter

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
M = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
OUT = os.path.join(REPO, ".workbuddy", "tmp", "out_13.txt")
buf = []

DE = os.path.join(M, "mat_Ne/Ne.cst")
EN = os.path.join(M, "mat_He/Untitled.CST")

def load(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()

ls_de = load(DE)
ls_en = load(EN)

buf.append("### 1. DE (Ne) vs EN (He): are these the SAME material? ###")
buf.append("DE L2: %r" % ls_de[2])
buf.append("EN L2: %r" % ls_en[2])
buf.append("DE col0 L2=%s  EN col0 L2=%s" % (ls_de[2].split()[0], ls_en[2].split()[0]))
buf.append("DE col3 L2=%s  EN col3 L2=%s" % (ls_de[2].split()[3], ls_en[2].split()[3]))
buf.append("=> Ne cst: Qtot(0,0)=7.404834  He CST: Qtot(0,0)=6.687637e+001 -- DIFFERENT")
buf.append("   (Ne Z=10, He Z=2 ; both are the 3rd cst-able element set)")

buf.append("\n### 2. Physical sanity of column 1 (Molekueldichte) = rho/(Atot*m_p) ###")
buf.append("   He: A=4 (Atot=4), m_p=1.6726231e-24")
for p, tag, A in ((EN, "He", 4.0), (DE, "Ne", 20.18)):
    ls = load(p)
    # first data line of 2nd isotherm where rho != 0
    for ln in ls[127:250]:
        t = ln.split()
        particle = float(t[0]); rho = float(t[1])
        if particle > 0 and rho > 0:
            ratio = particle / rho
            pred = 1.0 / (A * 1.6726231e-24)
            buf.append("   %s: particle=%.6e rho=%.6e  ratio=%.6e  pred(1/(A*m_p))=%.6e  match=%s" %
                       (tag, particle, rho, ratio, pred, abs(ratio - pred) / pred < 0.01))
            break

buf.append("\n### 3. Pressure units check: DE says MBar, EN says MBar ###")
buf.append("   FEOS source: P[i][j]*cgs2MBar  with cgs2MBar=1.0e-12 (dyne/cm2 -> MBar)")
buf.append("   Both headers label col2 as [MBar] => same physical unit.")

buf.append("\n### 4. INF census PER ISOTHERM for EN (He) ###")
titles = [i for i, ln in enumerate(ls_en) if "sotherm" in ln] + [len(ls_en)]
per = []
for k in range(len(titles) - 1):
    blk = ls_en[titles[k]:titles[k + 1]]
    n = sum(1 for ln in blk if "#INF" in ln)
    per.append((titles[k], n))
c = Counter(n for _, n in per)
buf.append("   per-isotherm INF-line-count histogram: %s" % dict(c))
buf.append("   first 8 isotherms (title_idx, INF_lines): %s" % per[:8])
buf.append("   last 4: %s" % per[-4:])
buf.append("   total INF lines in He CST: %d" % sum(n for _, n in per))

buf.append("\n### 5. INF census for DE (Ne) ###")
titles = [i for i, ln in enumerate(ls_de) if "sotherm" in ln] + [len(ls_de)]
per = []
for k in range(len(titles) - 1):
    blk = ls_de[titles[k]:titles[k + 1]]
    n = sum(1 for ln in blk if "#INF" in ln)
    per.append((titles[k], n))
c = Counter(n for _, n in per)
buf.append("   per-isotherm INF-line-count histogram: %s" % dict(c))
buf.append("   first 8: %s" % per[:8])
buf.append("   total: %d" % sum(n for _, n in per))

buf.append("\n### 6. Which density values give INF in DE (Ne) isotherm 0? ###")
blk = ls_de[2:125]
for ln in blk[:6]:
    buf.append("   %r" % ln)
buf.append("   ...")
for ln in blk[-4:]:
    buf.append("   %r" % ln)
nz = [ln for ln in blk if not ln.startswith("0.000000e+00")]
buf.append("   first non-zero-density line: %r" % (nz[0] if nz else None))

buf.append("\n### 7. Column start positions (fixed vs whitespace) ###")
for tag, ls in (("DE(Ne)", ls_de), ("EN(He)", ls_en)):
    buf.append("  -- %s --" % tag)
    for i in (1, 2, 3, 124):
        ln = ls[i]
        buf.append("   L%d len=%d repr=%r" % (i, len(ln), ln))
    # field start offsets on a typical data line
    ln = ls[3]
    starts = [m.start() for m in re.finditer(r"\S+", ln)]
    buf.append("   L3 token start offsets: %s" % starts)
    widths = []
    toks = re.findall(r"\S+", ln)
    for t in toks:
        widths.append(len(t))
    buf.append("   L3 token widths: %s" % widths)

buf.append("\n### 8. Does a whitespace split ALWAYS give 4 cols for data lines? ###")
for tag, ls in (("DE(Ne)", ls_de), ("EN(He)", ls_en)):
    c = Counter()
    for ln in ls:
        if any(ch.isalpha() for ch in ln):
            continue
        c[len(ln.split())] += 1
    buf.append("   %s numeric-line split census: %s" % (tag, dict(c)))

buf.append("\n### 9. Fixed-width slice feasibility: cols at [0:12],[12:24],[24:45],[45:] ? ###")
for tag, ls in (("DE(Ne)", ls_de), ("EN(He)", ls_en)):
    bad = 0
    tot = 0
    for ln in ls:
        if any(ch.isalpha() for ch in ln):
            continue
        tot += 1
        a, b, c2, d = ln[0:12], ln[12:24], ln[24:45], ln[45:]
        try:
            float(a.strip()) if a.strip() else None
            float(b.strip()) if b.strip() else None
            c2s = c2.strip()
            if c2s and "#" not in c2s:
                float(c2s)
            ds = d.strip()
            if ds:
                float(ds)
        except Exception:
            bad += 1
    buf.append("   %s: %d/%d lines parse with fixed-width slices (failures=%d)" % (tag, tot - bad, tot, bad))

open(OUT, "w", encoding="utf-8").write("\n".join(buf))
print("written", OUT, len(buf))
