# -*- coding: utf-8 -*-
"""1) 找全部 SNOP 输入卡（.INPUT/.SNOP/.inhalt）并 dump 关键参数
   2) 对每个无扩展名 PLANCK 族文件，从第 1 群解出 rho/T 网格，与输入卡对照
   3) 打印 SNOP 手册中关于 T1/T2/单位 的原文
"""
import os, glob, re

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
SRC = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128')
M = os.path.join(SRC, 'matter++')


def readtext(p, n=None):
    raw = open(p, 'rb').read(n)
    for enc in ('utf-8', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1', 'replace')


print('=' * 78)
print('1. 全部 SNOP 输入卡')
print('=' * 78)
cards = []
for pat in ['**/*.INPUT', '**/*.SNOP', '**/*.inhalt', '**/*.input']:
    cards += glob.glob(os.path.join(M, pat), recursive=True)
cards = sorted(set(cards))
for p in cards:
    if os.path.isdir(p):
        continue
    t = readtext(p)
    rel = os.path.relpath(p, M)
    keys = {}
    for k in ['NT', 'NR', 'NG', 'NP', 'RHO1', 'RHO2', 'T1', 'T2', 'X1', 'X2',
              'NPLA', 'NROSS', 'NEPS', 'NZ', 'Z', 'AW', 'Z_element', 'EQ', 'F0', 'F1']:
        m = re.search(r'(?<![\w])%s\s*=\s*([^,\n/]+)' % k, t)
        if m:
            keys[k] = m.group(1).strip()
    fg = re.search(r'FG\(1\)\s*=\s*([^\n]+)', t)
    if fg:
        v = [x.strip() for x in fg.group(1).rstrip(',').split(',') if x.strip()]
        keys['FG(1)'] = '%d 值: %s ... %s' % (len(v), v[0], v[-1])
    print('--- %s  (%d B)' % (rel, os.path.getsize(p)))
    for k, v in keys.items():
        print('      %-8s = %s' % (k, v))
print()

print('=' * 78)
print('2. 无扩展名 PLANCK 族第 1 群网格解码')
print('=' * 78)
names = []
for pat in ['**/*PLANCK*', '**/*PLANCK', '**/op*', '**/*_mopp*', '**/*.PLANCK', '**/*.ROSS', '**/*.EPS']:
    names += glob.glob(os.path.join(M, pat), recursive=True)
names = sorted(set(p for p in names if os.path.isfile(p)))
seen = set()
for p in names:
    rel = os.path.relpath(p, M)
    base = os.path.basename(p)
    if rel in seen:
        continue
    seen.add(rel)
    try:
        raw = open(p, 'rb').read(3000).replace(b'\r\n', b'\n')
        L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    except OSError:
        continue
    if not L or len(L[0]) != 60:
        continue
    hdr = L[0]
    f = [hdr[j:j + 15].strip() for j in range(0, 60, 15)]
    try:
        NR, NT = int(float(f[2])), int(float(f[3]))
    except ValueError:
        continue
    if len(L) < 3 or len(L[1]) != 30:
        continue
    band = [float(L[1][j:j + 15]) for j in (0, 15)]
    D = -(-(NR + NT + NR * NT) // 4)
    vals = []
    for l in L[2:2 + D]:
        for j in range(0, len(l) - 14, 15):
            try:
                vals.append(float(l[j:j + 15]))
            except ValueError:
                vals.append(None)
    rho = vals[0:NR]
    T = vals[NR:NR + NT]
    def rng(g):
        g2 = [x for x in g if x is not None]
        if not g2:
            return 'n/a'
        return 'log10 %.4f..%.4f -> %.6g .. %.6g' % (g2[0], g2[-1], 10**g2[0], 10**g2[-1])
    print('%-38s %-18s NR=%d NT=%d D=%d' % (rel, '%s%s' % (f[0], ''), NR, NT, D))
    print('      band(eV)=%s' % band)
    print('      rho : %s' % rng(rho))
    print('      T   : %s' % rng(T))
print()

print('=' * 78)
print('3. SNOP 手册中与单位/温度范围相关的原文')
print('=' * 78)
p = os.path.join(SRC, 'doc', 'SNOP.MANUAL')
if os.path.exists(p):
    t = readtext(p)
    for i, l in enumerate(t.split('\n'), 1):
        if re.search(r'keV|eV|Kelvin|temperature|T1|T2|RHO', l):
            print('%4d | %s' % (i, l.rstrip()[:120]))
else:
    print('  [missing]', p)
