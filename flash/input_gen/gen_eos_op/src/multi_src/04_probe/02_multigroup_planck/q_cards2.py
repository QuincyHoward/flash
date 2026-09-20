# -*- coding: utf-8 -*-
"""聚焦：opbe 的 80 个群界是否 = 两个 40 群序列拼接；SNOP 手册单位原文；
   以及各无扩展名 PLANCK 文件的网格极值汇总（紧凑表）。"""
import os, glob, re

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
SRC = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128')
M = os.path.join(SRC, 'matter++')
OUT = os.path.join(ROOT, '.workbuddy', 'tmp', 'q_cards2_out.txt')
buf = []
A = buf.append


def readtext(p, n=None):
    raw = open(p, 'rb').read(n)
    for enc in ('utf-8', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1', 'replace')


# ── opbe 群界 ────────────────────────────────────────────────
A('=' * 78)
A('A. opbe 的 80 个群界（看是否为两遍拼接）')
A('=' * 78)
p = os.path.join(M, 'mat_Be-1.0', 'opbe')
Ln = [x.decode('latin-1') for x in
      open(p, 'rb').read().replace(b'\r\n', b'\n').split(b'\n') if x.strip()]
bands = []
for i, l in enumerate(Ln):
    if len(l) == 30:
        bands.append((i, float(l[0:15]), float(l[15:30])))
A('  群数 = %d' % len(bands))
for k, (i, lo, hi) in enumerate(bands):
    A('   %2d  idx=%4d  [%10.4g, %10.4g]' % (k + 1, i, lo, hi))
A('')
if len(bands) == 80:
    b1 = [(lo, hi) for _, lo, hi in bands[:40]]
    b2 = [(lo, hi) for _, lo, hi in bands[40:]]
    A('  前 40 与后 40 群界是否逐位相同: %s' % (b1 == b2))
    A('  差异(前10): %s' % [(a, b) for a, b in zip(b1, b2) if a != b][:10])
A('')
A('  行数核对: 79×112 + 111 = %d ; 实测非空行 = %d' % (79 * 112 + 111, len(Ln)))
A('  2×40 群满编 = 80×112 = %d ; 实测 = %d ; 差 = %d'
  % (80 * 112, len(Ln), len(Ln) - 80 * 112))
A('')

# ── SNOP 手册单位 ────────────────────────────────────────────
A('=' * 78)
A('B. SNOP.MANUAL 中与单位/温度/密度范围相关的原文')
A('=' * 78)
pm = os.path.join(SRC, 'doc', 'SNOP.MANUAL')
if os.path.exists(pm):
    t = readtext(pm)
    for i, l in enumerate(t.split('\n'), 1):
        if re.search(r'keV|eV|Kelvin|[Tt]emperatur|^.{0,20}T1|^.{0,20}T2|RHO|Densit', l):
            A('%4d | %s' % (i, l.rstrip()[:130]))
else:
    A('  [missing] ' + pm)
A('')

# ── 各 PLANCK 文件网格极值 ───────────────────────────────────
A('=' * 78)
A('C. 无扩展名多群表：第 1 群网格极值 + 公式闭合')
A('=' * 78)
pats = ['**/*PLANCK*', '**/op*', '**/*_mopp*', '**/*.PLANCK', '**/*.ROSS', '**/*.EPS']
files = []
for pat in pats:
    files += glob.glob(os.path.join(M, pat), recursive=True)
files = sorted(set(x for x in files if os.path.isfile(x)))
A('%-40s %-9s %4s %4s %5s %6s %6s  %s' %
  ('file', 'table', 'NR', 'NT', 'D', 'rows', 'pred', 'rho_range|T_range(eV)'))
for p in files:
    rel = os.path.relpath(p, M)
    try:
        raw = open(p, 'rb').read(4000).replace(b'\r\n', b'\n')
        L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    except OSError:
        continue
    if not L or len(L[0]) != 60 or len(L) < 3 or len(L[1]) != 30:
        continue
    f = [L[0][j:j + 15].strip() for j in range(0, 60, 15)]
    try:
        NR, NT = int(float(f[2])), int(float(f[3]))
    except ValueError:
        continue
    D = -(-(NR + NT + NR * NT) // 4)
    # 群数
    try:
        full = [x.decode('latin-1') for x in
                open(p, 'rb').read().replace(b'\r\n', b'\n').split(b'\n') if x.strip()]
    except OSError:
        continue
    K = sum(1 for l in full if len(l) == 30)
    pred = K * (2 + D)
    vals = []
    for l in L[2:2 + D]:
        for j in range(0, len(l) - 14, 15):
            try:
                vals.append(float(l[j:j + 15]))
            except ValueError:
                vals.append(None)
    r = [x for x in vals[0:NR] if x is not None]
    T = [x for x in vals[NR:NR + NT] if x is not None]
    rr = '%.4g..%.4g' % (10**r[0], 10**r[-1]) if r else 'n/a'
    TT = '%.4g..%.4g' % (10**T[0], 10**T[-1]) if T else 'n/a'
    A('%-40s %-9s %4d %4d %5d %6d %6d  %s | %s  %s'
      % (rel, f[0], NR, NT, D, len(full), pred, rr, TT,
         'OK' if pred == len(full) else 'DIFF(%+d)' % (len(full) - pred)))

open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(buf))
print('written', OUT, len(buf), 'lines')
