# -*- coding: utf-8 -*-
"""Stage 2b: prove the SESAME record order and the MULTI-opacity layout by closure."""
import os, io, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_readers as ER

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xval_s2b_proof.txt')
lines = []
def P(s=''):
    lines.append(str(s))

def allnums(path, width=15, skip_first_line=False):
    s = ER.read_text(path)
    ls = [l for l in ER.split_lines(s) if l.strip()]
    if skip_first_line:
        ls = ls[1:]
    f = []
    for l in ls:
        f.extend(ER.floats_fixed(l, width))
    return f

# ==================================================================================
# 1. SESAME 201/301: header (matid, 201, ver, nr) then TWICE nr record-1 values?
# ==================================================================================
P("#" * 100)
P("# 1. SESAME 201/301 LAYOUT PROOF")
P("#" * 100)
P("""
Hypothesis H_sesame:
  numbers[0:4]      = 201 header : matid, 201, version, nr
  numbers[4:4+2*nr] = 301 header : rho grid (nr values), REPEATED TWICE (two blocks)
  then  Ntab = 3 + 3*ne + 3*nr
        [3 scalars][3*ne][3*nr]
""")
SES = [
    (r'Ta2O5\PowerLawTa2O5_EOS.SESAME', 3),
    (r'Ta2O5\PowerLawTa2O5_EOS.SESAME_', 5),
    (r'SiO2\eos_21.sesame', 43),
    (r'SiO2\eos_22.sesame', 36),
    (r'SiO2\eos_23.sesame', 75),
    (r'SiO2\eos_24.sesame', 73),
]
for rel, nr_exp in SES:
    path = os.path.join(MATTER, rel)
    if not os.path.exists(path):
        P("MISSING %s" % rel); continue
    f = allnums(path)
    N = len(f)
    P("")
    P("-" * 100)
    P("FILE %s   N=%d numbers" % (rel, N))
    P("  [0:4] = %s" % ['%.7g' % x for x in f[0:4]])
    nr = int(round(f[3]))
    P("  nr from header[3] = %d   (expected %d)  MATCH=%s" % (nr, nr_exp, nr == nr_exp))
    blk = f[4:4 + 2 * nr]
    P("  [4:4+2nr] first 6 = %s" % ['%.7g' % x for x in blk[:6]])
    P("  [4:4+2nr] last  6 = %s" % ['%.7g' % x for x in blk[-6:]])
    if len(blk) == 2 * nr:
        P("  rho_1 = blk[:nr] first6 = %s" % ['%.7g' % x for x in blk[:nr][:6]])
        P("  rho_2 = blk[nr:] first6 = %s" % ['%.7g' % x for x in blk[nr:][:6]])
        same = all(abs(a - b) < 1e-12 * max(1.0, abs(a)) for a, b in zip(blk[:nr], blk[nr:]))
        P("  rho_1 == rho_2 EXACTLY ? %s" % same)
    for Nskip in (4 + 2 * nr, 4 + nr):
        rest = f[Nskip:]
        M = len(rest)
        found = False
        for ne in range(1, 4001):
            if M == 3 + 3 * ne + 3 * nr:
                P("  CLOSURE with header_len=%d : ne=%d  (M=%d == 3+3*%d+3*%d=%d)  <== PROVEN"
                  % (Nskip, ne, M, ne, nr, 3 + 3 * ne + 3 * nr))
                P("     rest[0:3] (scalars) = %s" % ['%.7g' % x for x in rest[:3]])
                P("     rest[3:3+3] (1st deg-row, T) = %s" % ['%.7g' % x for x in rest[3:6]])
                P("     rest[3+3*ne:3+3*ne+3] (1st dens-row, T) = %s"
                  % ['%.7g' % x for x in rest[3 + 3 * ne: 6 + 3 * ne]])
                P("     rest[3+3*ne+3*nr:] leftover = %d" % len(rest[3 + 3 * ne + 3 * nr:]))
                # show structure of a few deg rows
                P("     3*ne block, first 3 rows as (a,b,c):")
                for k in range(3):
                    row = rest[3 + 3 * k: 6 + 3 * k]
                    P("        deg-row %d = %s" % (k, ['%.7g' % x for x in row]))
                P("     3*nr block, first 3 rows as (a,b,c):")
                for k in range(3):
                    row = rest[3 + 3 * ne + 3 * k: 6 + 3 * ne + 3 * k]
                    P("        den-row %d = %s" % (k, ['%.7g' % x for x in row]))
                found = True
                break
        if not found:
            P("  NO CLOSURE with header_len=%d (M=%d).  M mod 3 = %d ; M - 3 - 3*nr = %d"
              % (Nskip, M, M % 3, M - 3 - 3 * nr))

# ==================================================================================
# 2. MULTI bare-name opacity: header identity
# ==================================================================================
P("")
P("#" * 100)
P("# 2. MULTI BARE-NAME OPACITY LAYOUT PROOF   (PLANCK / ROSS / EPS / ZEFF)")
P("#" * 100)
P("""
Hypothesis H_op:
  line0 : <tableid(8)><6 sp><CATEGORY><sp><M|1|4>  then  nr  nt    <- NR and NT ARE THE
          TWO NUMBERS ON LINE 0
  line1 : x1 x2  (normalisation / axis scaling for the two axes, NOT grid values)
  then  rho[NR] (log10) , T[NT] (log10) , values[NR*NT] (log10)
  count after line1 = NR + NT + NR*NT
""")
def op_header(path, nvals_hint):
    s = ER.read_text(path)
    ls = [l.rstrip('\n') for l in ER.split_lines(s) if l.strip()]
    l0, l1 = ls[0], ls[1]
    # header numbers on line0: from col 14 on, 15-wide
    h = [float(c) for c in ER.nums_fixed(l0[14:], 15)]
    body = []
    for l in ls[2:]:
        body.extend(ER.floats_fixed(l, 15))
    return l0, l1, h, body, len(ls)

BARE_FILE = [
    (r'mat_Ce\Ce.PLANCK', None), (r'mat_Ce\Ce.ROSS', None), (r'mat_Ce\Ce.EPS', None),
    (r'mat_Ce\Ce.ZEFF', None),
    (r'mat_C-1.0\C_1G.PLANCK', None), (r'mat_C-1.0\C_20GSNOP.PLANCK', None),
    (r'mat_C-1.0\C_20GSNOP.ZEFF', None), (r'mat_C-1.0\C_Z.dat', None),
    (r'mat_Ti\Ti_Planck', None), (r'mat_Ti\SNOP_NLTE.PLANCK', None),
]
for rel, _ in BARE_FILE:
    path = os.path.join(MATTER, rel)
    if not os.path.exists(path):
        P("MISSING %s" % rel); continue
    P("")
    P("-" * 100)
    P("FILE %s" % rel)
    try:
        l0, l1, h, body, nlines = op_header(path, None)
    except Exception as e:
        P("  err %r" % e); continue
    P("  line0 = |%s|" % l0)
    P("  line1 = |%s|" % l1)
    P("  line0 hdr nums (from col14) = %s" % ['%g' % x for x in h])
    P("  n_body = %d   nlines=%d" % (len(body), nlines))
    ok = False
    if len(h) >= 2:
        a, b = int(round(h[0])), int(round(h[1]))
        for nm, nr, nt in (('h0=NR,h1=NT', a, b), ('h0=NT,h1=NR', b, a)):
            need = nr + nt + nr * nt
            diff = len(body) - need
            mark = '  <== CLOSES EXACTLY' if diff == 0 else ''
            P("    %-14s NR=%3d NT=%3d  need=NR+NT+NR*NT=%6d  n_body=%6d  diff=%6d%s"
              % (nm, nr, nt, need, len(body), diff, mark))
            if diff == 0:
                ok = True
        if ok:
            # figure out which of a,b is NR by looking at the first block monotonic run
            nr, nt = (a, b)
            if nr + nt + nr * nt != len(body):
                nr, nt = (b, a)
            rho_log = body[:nr]
            T_log = body[nr:nr + nt]
            P("    -> NR=%d (rho grid), NT=%d (T grid)" % (nr, nt))
            P("       rho_log10 first6 = %s   last=%s" % (['%.6g' % x for x in rho_log[:6]],
                                                          ['%.6g' % x for x in rho_log[-3:]]))
            P("       T_log10   first6 = %s   last=%s" % (['%.6g' % x for x in T_log[:6]],
                                                          ['%.6g' % x for x in T_log[-3:]]))
            P("       rho = %s .. %s g/cc" % ('%.4g' % 10 ** rho_log[0], '%.4g' % 10 ** rho_log[-1]))
            P("       T   = %s .. %s erg (10^x erg)" % ('%.4g' % 10 ** T_log[0], '%.4g' % 10 ** T_log[-1]))
    if not ok:
        P("    NO CLOSURE.  trying structured guesses:")
        for nr in (20, 30, 50, 100, 200, 250, 500, 1000):
            for nt in (20, 30, 50, 100, 200, 250, 500, 1000):
                if len(body) == nr + nt + nr * nt:
                    P("      CLOSES with NR=%d NT=%d" % (nr, nt))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
