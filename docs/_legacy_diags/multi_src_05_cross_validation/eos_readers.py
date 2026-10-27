# -*- coding: utf-8 -*-
"""
eos_readers.py  --  VERIFIED readers for the EOS/opacity families in matter++/

Every layout below was proven by exact arithmetic closure on real files
(see xval_s2b_proof.txt, xval_s4.txt, xval_s13.txt).

Normalisation used everywhere:
  rho : g/cm^3
  T   : eV            (1 eV = 11604.519 K)
  P   : Mbar          (1 Mbar = 1e12 dyne/cm^2)
  E   : Mbar*cm^3/g   (= 1e12 erg/g)
"""
import os, re, math

EV_PER_K = 1.0 / 11604.519
K_PER_EV = 11604.519
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')

# ------------------------------------------------------------------ text helpers
def read_text(path):
    with open(path, 'rb') as fh:
        b = fh.read()
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def lines_of(path):
    s = read_text(path).replace('\r\n', '\n').replace('\r', '\n')
    return [l.rstrip('\n') for l in s.split('\n')]

def floats_fixed(s, width=15):
    """Split into `width` cells, parse each.  Handles the 2-digit-mantissa +
    3-digit-exponent overflow (e.g. '12345678901234-3.39996293e+09') that occurs
    wherever a value has one char too many: the exponent is recovered from the
    cell's own trailing exponent token and re-attached to the BARE mantissa."""
    out = []
    for i in range(0, len(s), width):
        c = s[i:i + width].strip()
        if not c:
            continue
        try:
            out.append(float(c.replace('D', 'E').replace('d', 'e')))
            continue
        except ValueError:
            pass
        mv = re.search(r'(?<![eEdD])[-+]?\d*\.?\d+[eEdD][-+]?\d+$', c)
        if mv:
            exp = c[mv.start():]
            head = c[:mv.start()]
            toks = NUMRE.findall(head)
            for t in toks[:-1] if len(toks) > 1 else toks:
                out.append(float(t.replace('D', 'E').replace('d', 'e')))
            if toks:
                mant = toks[-1].lstrip('+')
                try:
                    out.append(float(mant + exp.replace('D', 'E').replace('d', 'e')))
                except ValueError:
                    out.append(float(toks[-1]))
            continue
        for t in NUMRE.findall(c):
            out.append(float(t.replace('D', 'E').replace('d', 'e')))
    return out

def floats_any(s):
    return [float(t.replace('D', 'E').replace('d', 'e')) for t in NUMRE.findall(s)]

# ==================================================================================
# R6/R10 : MULTI opacity family   (*.PLANCK/*.ROSS/*.EPS/*.ZEFF, bare names,
#          and the .sesame_PLANCK / .sesame_ROSSELAND variants)
# ==================================================================================
# PROVEN record layout (112 lines for NR=NT=20):
#   line 0 : <tableid 8 chars> <spaces> <CATEGORY> [flag]  NR  NT
#            flag is 'M' (multi-group) / '1' (one-group) / absent (ZEFF, or
#            ZERO-table).  For ZEFF and the bare 'ZERO' variant there are THREE
#            numbers: (Z, NR, NT).
#   line 1 : T_lo  T_hi      <- the temperature energy BAND of this record, in eV
#            (for the ONE-record variants, e.g. Ce.ZEFF / C_1G.PLANCK, line 1 is
#             already the rho grid and the file is truncated at 111 lines.)
#   then   : rho[NR] (log10 of rho/[0.001 g/cc] over [1e-1, 1e5])
#            T[NT]   (log10 of T/[10 eV]        over [1e-5, 1e2])
#            values[NR*NT] (log10 of opacity)      <- count = NR+NT+NR*NT
#   => a file with K records has 2 + K*(1 + ceil((NR+NT+NR*NT)/4)) lines
#      (dedicated category files are NOT contiguous grid dumps)

def parse_op_header(l0):
    cat = None
    for c in ('PLANCK', 'ROSSELAND', 'EPS', 'ZEFF'):
        if c in l0:
            cat = c; break
    pos = l0.find(cat) if cat else -1
    flag = None
    if pos >= 0:
        m = l0[pos + len(cat):].lstrip()
        if m and not m[0].isdigit() and m[0] not in '+-.':
            flag = m[0]
    tail = l0[26:] if cat else l0[14:]
    nums = floats_any(tail)
    return {'tableid': l0[:8].strip(), 'category': cat, 'flag': flag, 'nums': nums}

def read_opacity(path):
    """Parse a MULTI opacity file.  Returns one entry per record plus the grids."""
    ls = [l for l in lines_of(path) if l.strip()]
    nlines = len(ls)
    h0 = parse_op_header(ls[0])
    nums = h0['nums']
    if h0['category'] == 'ZEFF' or len(nums) >= 3:
        NR = int(round(nums[-2])); NT = int(round(nums[-1]))
    else:
        NR = int(round(nums[0])); NT = int(round(nums[1]))
    per = NR + NT + NR * NT
    rec_lines = 2 + (per + 3) // 4
    nrec = nlines // rec_lines
    truncated = (nlines % rec_lines) != 0
    out = {'kind': 'multi_opacity', 'file': os.path.basename(path),
           'nr': NR, 'nt': NT, 'per_record_values': per,
           'rec_lines': rec_lines, 'nlines': nlines,
           'n_records': nrec if not truncated else nrec + 1,
           'truncated_last': truncated, 'records': []}
    for k in range(nrec + (1 if truncated else 0)):
        i = k * rec_lines
        if i >= nlines:
            break
        hh = parse_op_header(ls[i])
        # record i+1 on line 1 = the T band, unless this is the truncated one-record file
        if i + 1 < nlines and (nrec > 0):
            band = floats_any(ls[i + 1])
        else:
            band = None
        body = []
        start = i + 2 if (nrec > 0 or not truncated) else i + 1
        if truncated and nrec == 0:
            start = i + 1
            band = None
        for l in ls[start:start + rec_lines]:
            body.extend(floats_fixed(l, 15))
        if len(body) < per:
            # truncated (1-record) file: line 1 was the rho grid
            body = []
            for l in ls[i + 1: i + 1 + rec_lines]:
                body.extend(floats_fixed(l, 15))
            band = None
        rhoL = body[:NR]; TL = body[NR:NR + NT]; vals = body[NR + NT:NR + NT + NR * NT]
        out['records'].append({'idx': k, 'header': hh, 'band_eV': band,
                               'rho_log10': rhoL, 'T_log10': TL, 'vals': vals})
    # a representative record for grid questions
    if out['records']:
        r = out['records'][0]
        out['rho_log10'] = r['rho_log10']
        out['T_log10'] = r['T_log10']
        out['rho_grid'] = [10 ** (x - 3) for x in r['rho_log10']]     # g/cc
        out['T_grid'] = [10 ** (x + 1) for x in r['T_log10']]         # eV
    return out

def read_opacity_sesame(path):
    """Same family but with a sentinel '0.1234567E+000' glued to the category."""
    ls = [l for l in lines_of(path) if l.strip()]
    l0 = ls[0]
    i = l0.find('0.1234567E+000')
    stripped = l0[:i] + l0[i + len('0.1234567E+000'):]
    return {'kind': 'sesame_opacity', 'file': os.path.basename(path),
            'line0': l0, 'line0_stripped': stripped, 'nlines': len(ls),
            'ls_head': ls[:4]}

# ==================================================================================
# R1 : SESAME 201/301
# ==================================================================================
# PROVEN: nums[0:4] = [matid, 201, version, ntab]
#         then ntab records: [tabno, a, b, c] followed by (3 + 3*ne + 3*nr) values
#         where for the 301 record ne = a, nr = b.
#   body = [3 scalars][ne rows of 3][nr rows of 3]

def read_sesame201(path):
    ls = [l for l in lines_of(path) if l.strip()]
    f = []
    for l in ls:
        f.extend(floats_fixed(l, 15))
    N = len(f)
    h201 = f[0:4]
    ntab = int(round(h201[3]))
    recs = []
    idx = 4
    for k in range(ntab):
        if idx + 4 > N:
            recs.append({'ok': False, 'why': 'ran out of numbers', 'idx': idx}); break
        tabno = int(round(f[idx])); a = f[idx + 1]; b = f[idx + 2]; c = f[idx + 3]
        idx += 4
        ne, nr = int(round(a)), int(round(b))
        need = 3 + 3 * ne + 3 * nr
        if ne > 0 and nr > 0 and idx + need <= N:
            body = f[idx:idx + need]
            recs.append({'ok': True, 'tabno': tabno, 'a': a, 'b': b, 'c': c,
                         'ne': ne, 'nr': nr, 'body': body, 'idx': idx})
            idx += need
        else:
            recs.append({'ok': False, 'why': 'header out of range', 'tabno': tabno,
                         'a': a, 'b': b, 'c': c, 'idx': idx})
            break
    return {'kind': 'sesame201', 'file': os.path.basename(path), 'N': N,
            'h201': h201, 'ntab': ntab, 'records': recs,
            'consumed': idx, 'leftover': N - idx}

# ==================================================================================
# R2 : FEOS  (.feos)
# ==================================================================================
def read_feos_header(path):
    ls = [l for l in lines_of(path) if l.strip()]
    h0 = floats_fixed(ls[0], 15)
    h1 = floats_fixed(ls[1], 15)
    return {'kind': 'feos', 'file': os.path.basename(path), 'h0': h0, 'h1': h1,
            'h0raw': ls[0], 'h1raw': ls[1], 'nlines': len(ls),
            'NRho': int(round(h0[1])) if len(h0) > 1 else None,
            'NT': int(round(h0[2])) if len(h0) > 2 else None,
            'Atot': h1[7] if len(h1) > 7 else None,
            'Ztot': h1[8] if len(h1) > 8 else None}

# ==================================================================================
# R5 : .cst  (Rostock)  -- T = 0 K isotherm
# ==================================================================================
def read_cst(path):
    ls = lines_of(path)
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
    return {'kind': 'cst', 'file': os.path.basename(path),
            'title': ls[0].strip() if ls else '', 'n_rows': len(rows), 'rows': rows,
            'numdens': [r[0] for r in rows], 'rho': [r[1] for r in rows],
            'P': [r[2] for r in rows], 'Q': [r[3] for r in rows]}

# ==================================================================================
# interpolation
# ==================================================================================
def interp1_loglog(g, v, x):
    """1-D linear interpolation of v(g) at x, in log10-log10 if possible."""
    import bisect
    gg = list(g)
    logg = all(a > 0 for a in gg) and x > 0
    X = math.log10(x) if logg else x
    G = [math.log10(a) for a in gg] if logg else gg
    if X <= G[0]:
        return v[0]
    if X >= G[-1]:
        return v[-1]
    i = max(0, min(bisect.bisect_right(G, X) - 1, len(G) - 2))
    t = (X - G[i]) / (G[i + 1] - G[i])
    return v[i] + (v[i + 1] - v[i]) * t

def P_on_grid(rho, T, P2d, rho_q, T_q):
    """P2d[i_T][i_rho], Mbar.  Bilinear in log10(rho)-log10(T), falling back to
    log10 in only the axis that is positive."""
    def ip(axis, val):
        import bisect
        g = list(axis)
        use_log = all(a > 0 for a in g) and val > 0
        G = [math.log10(a) for a in g] if use_log else g
        V = math.log10(val) if use_log else val
        if V <= G[0]:
            return 0, 0.0
        if V >= G[-1]:
            return len(G) - 2, 1.0
        i = max(0, min(bisect.bisect_right(G, V) - 1, len(G) - 2))
        t = (V - G[i]) / (G[i + 1] - G[i])
        return i, t
    i, tx = ip(rho, rho_q)
    j, ty = ip(T, T_q)
    z00 = P2d[j][i]; z01 = P2d[j][i + 1]
    z10 = P2d[j + 1][i]; z11 = P2d[j + 1][i + 1]
    a = z00 + (z01 - z00) * tx
    b = z10 + (z11 - z10) * tx
    return a + (b - a) * ty
