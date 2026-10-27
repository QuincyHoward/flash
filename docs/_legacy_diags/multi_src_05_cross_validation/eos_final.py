# -*- coding: utf-8 -*-
"""FINAL readers for the three target families, with structure-aware closure.

All layouts below were DERIVED EMPIRICALLY (see xval_s2b_proof.txt, xval_s4.txt).
"""
import os, io, sys, math, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')

NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')

def read_text(path):
    with open(path, 'rb') as fh:
        b = fh.read()
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def lines_of(path):
    s = read_text(path).replace('\r\n', '\n').replace('\r', '\n')
    return [l.rstrip('\n') for l in s.split('\n')]

def nums_fixed(s, width=15):
    out = []
    for i in range(0, len(s), width):
        c = s[i:i + width].strip()
        if c:
            out.append(c)
    return out

def floats_fixed(s, width=15):
    """Split into `width` cells and pull every float-looking token.  Glued
    wide fields (2-digit mantissa+3-digit exponent) are recovered because the
    regex scans inside the cell."""
    res = []
    for c in nums_fixed(s, width):
        try:
            res.append(float(c.replace('D', 'E').replace('d', 'e')))
        except ValueError:
            toks = NUMRE.findall(c)
            if not toks:
                continue
            mv = re.search(r'[eEdD][-+]?\d+$', c)
            exp = ''
            if mv and len(toks) > 1:
                exp = c[mv.start():mv.end()]
                toks = toks[:-1]
            for t in toks:
                try:
                    res.append(float(t))
                except ValueError:
                    pass
            if exp:
                res[-1] = float(('%g' % res[-1]) + exp.replace('D', 'E').replace('d', 'e'))
    return res

def floats_any(s):
    return [float(t.replace('D', 'E').replace('d', 'e')) for t in NUMRE.findall(s)]

# ==================================================================================
# R1 CORRECTED : SESAME 201/301
# ==================================================================================
# PROVEN layout (see proof log):
#   nums[0:4]            = 201 record  : [matid, 201, version, ntab]
#   then ntab records, each prefixed by its table number:
#       record 1 : tabno=301, then 3 numbers [ne, nr, ?], then body of
#                  length 3 + 3*ne + 3*nr
#     -> body(3)          = 3 scalars
#     -> body[3:3+3*ne]   = ne rows x 3 : (T, P, E) at ONE density, sweeping energy
#     -> body[3+3*ne:...] = nr rows x 3 : (T, P, E) at ONE energy, sweeping density
#   The 'de' energy grid is NOT stored in these tables -- the energy grid is the
#   ENERGY COLUMN of the first block.  Hence the document's formula
#   n = 4 + 2*nr + ne + 2*nr*ne is WRONG for this family.

def read_sesame301(path):
    s = read_text(path)
    ls = [l for l in lines_of(path) if l.strip()]
    f = []
    for l in ls:
        f.extend(floats_fixed(l, 15))
    N = len(f)
    h201 = f[0:4]
    ntab = int(round(h201[3]))
    recs = []
    idx = 4
    ok = True
    for k in range(ntab):
        if idx + 4 > N:
            ok = False
            break
        tabno = int(round(f[idx])); a = f[idx + 1]; b = f[idx + 2]; c = f[idx + 3]
        idx += 4
        # try (a,b) as (ne,nr)
        ne, nr = int(round(a)), int(round(b))
        need = 3 + 3 * ne + 3 * nr
        if idx + need <= N:
            body = f[idx:idx + need]
            idx += need
            recs.append({'tabno': tabno, 'ne': ne, 'nr': nr, 'c': c,
                         'a': a, 'b': b, 'body': body,
                         'closure': 'OK', 'start': idx - need})
        else:
            recs.append({'tabno': tabno, 'ne': ne, 'nr': nr, 'c': c,
                         'a': a, 'b': b, 'closure': 'NO_ROOM', 'start': idx})
            ok = False
    return {'kind': 'sesame301', 'file': os.path.basename(path), 'N': N,
            'h201': h201, 'ntab': ntab, 'records': recs,
            'consumed': idx, 'leftover': N - idx, 'all_closed': ok}

def sesame301_grid(rec):
    """Extract rho grid, T grid, P table from a 301 record.
    Returns (rho[nr], T_of_rho[nr], P_2d[i_e][i_d]) derived from the two blocks."""
    b = rec['body']; ne = rec['ne']; nr = rec['nr']
    # first block: ne rows of 3, each row = one density, sweeping energy
    eblk = [b[3 + 3 * k: 6 + 3 * k] for k in range(ne)]
    dblk = [b[3 + 3 * ne + 3 * k: 6 + 3 * ne + 3 * k] for k in range(nr)]
    # In the SESAME 301 convention the columns are (T, P, E).
    # rho grid = the DENSITY column of dblk (column 2 of the 3-scalar block? no)
    return {'eblk': eblk, 'dblk': dblk}

# ==================================================================================
# R6 CORRECTED : MULTI bare-name opacity
# ==================================================================================
# PROVEN header variants:
#   V_name  : ' 27003000      PLANCK M        2.00000000e+01 2.00000000e+01'
#             -> tableid 8 chars, 6 spaces, CATEGORY, 1 space, FLAG, then NR NT
#   V_name2 : ' 0.28603000e+04PLANCK M      ...'  (Ti)  -> tableid is a FLOAT
#   V_bare  : ' 27002000      0.60000000E+01 2.00000000e+01 2.00000000e+01'  (ZEFF)
#             -> tableid, then Z, NR, NT     (ZEFF is written with 3 numbers)
#   V_plain : '00000000        0.60000000E+01 4.3000000e+001 4.3000000e+001' (C_Z.dat)
#   line 1  : [x1 x2] = axis normalisation constants (NOT grid values)
#   payload : rho[NR] (log10) , T[NT] (log10) , values[NR*NT] (log10)
#             => count = NR + NT + NR*NT

def read_multi_opacity(path):
    ls = [l for l in lines_of(path) if l.strip()]
    l0, l1 = ls[0], ls[1]
    cat = None
    for c in ('PLANCK', 'ROSSELAND', 'EPS', 'ZEFF'):
        if c in l0:
            cat = c; break
    tail = l0[26:] if cat else l0[14:]
    l0n = floats_any(tail)
    body = []
    for l in ls[2:]:
        body.extend(floats_fixed(l, 15))
    N = len(body)
    out = {'file': os.path.basename(path), 'category': cat, 'line0': l0,
           'line1': l1, 'l0nums': l0n, 'line1nums': floats_any(l1),
           'n_body': N, 'nlines': len(ls), 'tableid': l0[:8].strip()}
    # candidate (NR,NT)
    cands = []
    if cat == 'ZEFF' and len(l0n) >= 3:
        cands.append(('ZEFF:Z,NR,NT', int(round(l0n[1])), int(round(l0n[2]))))
    if len(l0n) >= 2:
        cands.append(('n0,n1', int(round(l0n[0])), int(round(l0n[1]))))
    if len(l0n) >= 3:
        cands.append(('n1,n2', int(round(l0n[1])), int(round(l0n[2]))))
    hit = None
    for nm, NR, NT in cands:
        if NR < 2 or NT < 2:
            continue
        if N == NR + NT + NR * NT:
            hit = (nm, NR, NT, 'NR+NT+NR*NT')
            break
        if N == (NR + 1) + NT + NR * NT:
            hit = (nm, NR, NT, '(NR+1)+NT+NR*NT')
            break
    if not hit and cat == 'ZEFF':
        # ZEFF has no 'M' flag; sometimes only (NR,NT) present
        for NR in (20, 30, 50, 100, 200):
            for NT in (20, 30, 50, 100, 200):
                if N == (NR + 1) + NT + NR * NT:
                    hit = ('scan', NR, NT, '(NR+1)+NT+NR*NT'); break
            if hit: break
    out['candidates'] = [(nm, NR, NT, N - (NR + NT + NR * NT)) for nm, NR, NT in cands]
    if not hit:
        out['closure'] = 'FAILED'
        return out
    nm, NR, NT, form = hit
    out.update({'closure': 'OK', 'how': nm, 'form': form, 'nr': NR, 'nt': NT})
    if form == 'NR+NT+NR*NT':
        rhoL = body[:NR]; TL = body[NR:NR + NT]; vals = body[NR + NT:]
    else:
        rhoL = body[:NR]; TL = body[NR:NR + NT]; vals = body[NR + NT + 1:]
    out['rho_log10'] = rhoL
    out['T_log10'] = TL
    out['vals'] = vals
    out['rho_grid'] = [10 ** x for x in rhoL]
    if len(vals) == NR * NT:
        out['vals_2d'] = [vals[i * NT:(i + 1) * NT] for i in range(NR)]
    return out

# ==================================================================================
# R7-ish : cst
# ==================================================================================
def read_cst(path):
    ls = lines_of(path)
    title = ls[0].strip()
    rows = []
    for l in ls:
        t = l.strip()
        if not t or 'Molek' in t or 'Massendichte' in t or t.lower().startswith('isotherm'):
            continue
        v = floats_any(t)
        if len(v) == 4:
            rows.append(v)
        elif len(v) > 4 and len(v) % 4 == 0:
            for i in range(0, len(v), 4):
                rows.append(v[i:i + 4])
    return {'file': os.path.basename(path), 'title': title, 'n_rows': len(rows),
            'rows': rows,
            'numdens': [r[0] for r in rows], 'rho': [r[1] for r in rows],
            'P': [r[2] for r in rows], 'Q': [r[3] for r in rows]}

# ==================================================================================
# FEOS
# ==================================================================================
def read_feos_hdr(path):
    ls = [l for l in lines_of(path) if l.strip()]
    h0 = floats_fixed(ls[0], 15)
    h1 = floats_fixed(ls[1], 15)
    return {'file': os.path.basename(path), 'h0': h0, 'h1': h1,
            'h0raw': ls[0], 'h1raw': ls[1], 'nlines': len(ls)}

# ==================================================================================
# 301 mexport  (matid+tabno glued in the first 12 chars)
# ==================================================================================
def read_mexport301(path):
    ls = [l for l in lines_of(path) if l.strip()]
    l0 = ls[0]
    hd = l0[:12]
    rest0 = floats_any(l0[12:])
    body = []
    for l in ls[1:]:
        body.extend(floats_fixed(l, 15))
    return {'file': os.path.basename(path), 'head12': hd, 'l0rest': rest0,
            'n_body': len(body), 'body_head': body[:30], 'linewidths': [len(x) for x in ls[:5]]}
