# -*- coding: utf-8 -*-
"""独立裁定：不透明度表 T 轴 10× 悬案。
   读 Ce.INPUT / Ce.PLANCK / Ce.ROSS / Ce.EPS / Cerium.PAR.log，
   并把 log10(T) 网格反解回 eV 与 keV。
"""
import os, glob

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')

print('=' * 78)
print('1. mat_Ce 目录全部文件')
print('=' * 78)
for f in sorted(os.listdir(os.path.join(M, 'mat_Ce'))):
    p = os.path.join(M, 'mat_Ce', f)
    print('   %-40s %10d' % (f, os.path.getsize(p)))

print()
print('=' * 78)
print('2. Ce.INPUT 全文')
print('=' * 78)
for cand in ['Ce.INPUT', 'Cerium.INPUT']:
    p = os.path.join(M, 'mat_Ce', cand)
    if os.path.exists(p):
        raw = open(p, 'rb').read()
        for enc in ('utf-8', 'latin-1'):
            try:
                t = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        for i, l in enumerate(t.split('\n'), 1):
            print('%4d | %s' % (i, l.rstrip()))

print()
print('=' * 78)
print('3. mat_Ce 各表头部（前 4 行原文）')
print('=' * 78)
for name in ['Ce.PLANCK', 'Ce.ROSS', 'Ce.EPS', 'Ce.ZEFF']:
    p = os.path.join(M, 'mat_Ce', name)
    if not os.path.exists(p):
        print('   [missing]', name)
        continue
    raw = open(p, 'rb').read(400).replace(b'\r\n', b'\n')
    L = [x.decode('latin-1') for x in raw.split(b'\n')]
    print('--- %s  (%d B)' % (name, os.path.getsize(p)))
    for i in range(min(4, len(L))):
        print('   %d| %r' % (i, L[i][:100]))

print()
print('=' * 78)
print('4. 解析 Ce.PLANCK：NR/NT + log10(T) 网格 -> eV / keV')
print('=' * 78)
FIX = os.path.join(ROOT, '.workbuddy', 'tmp', '_fixfloat.py')
p = os.path.join(M, 'mat_Ce', 'Ce.PLANCK')
raw = open(p, 'rb').read().replace(b'\r\n', b'\n')
L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
hdr = L[0]
f = [hdr[j:j + 15] for j in range(0, 60, 15)]
print('   hdr fields =', f)
table = f[0].strip()
kind = f[1].strip()
NR = int(float(f[2]))
NT = int(float(f[3]))
print('   table=%s kind=%r NR=%d NT=%d' % (table, kind, NR, NT))

# 第一群：2 值行 + 4 值骨架行 + 数据区
vals30 = [i for i, l in enumerate(L) if len(l) == 30]
print('   30-char rows (群数) =', len(vals30))


def nums(line):
    o = []
    for j in range(0, len(line) - 14, 15):
        tok = line[j:j + 15]
        try:
            o.append(float(tok))
        except ValueError:
            o.append(None)
    return o


s = vals30[0]
band = nums(L[s])
print('   第 1 群带界 (原文) =', repr(L[s]))
print('   第 1 群带界 (eV)   =', band)

# 数据区
body = []
e = vals30[1] if len(vals30) > 1 else len(L)
for l in L[s + 2:e]:
    body.extend([v for v in nums(l) if v is not None])
n = NR + NT + NR * NT
print('   数据区值数 = %d  (期望 %d)  %s' % (len(body), n, 'OK' if len(body) == n else 'MISMATCH'))

lr = body[0:NR]
lt = body[NR:NR + NT]
print('   log10(rho) 首/末 = %r / %r' % (lr[0], lr[-1]))
print('   log10(T)   首/末 = %r / %r' % (lt[0], lt[-1]))
T = [10 ** v for v in lt]
print('   T[eV]  = %s ... %s' % (['%.6g' % v for v in T[:4]], ['%.6g' % v for v in T[-4:]]))
print('   T[keV] = %.6g ... %.6g' % (T[0] / 1000, T[-1] / 1000))
RHO = [10 ** v for v in lr]
print('   rho    = %s ... %s' % (['%.6g' % v for v in RHO[:3]], ['%.6g' % v for v in RHO[-3:]]))

print()
print('   >>> 与 Ce.INPUT 的 T1/T2、RHO1/RHO2 对照 <<<')
