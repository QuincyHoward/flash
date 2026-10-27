# -*- coding: utf-8 -*-
"""ZEFF 式表（第 2 字段为数值）的结构与闭合；以及 opbe 尾段确认。"""
import os, glob

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')

print('=' * 74)
print('ZEFF 式表结构与闭合')
print('=' * 74)
pats = ['**/*ZEFF*', '**/*Zeff*', '**/*_Z.dat', '**/*.Zeff', '**/*opbe*', '**/*_Z_*']
files = []
for pat in pats:
    files += glob.glob(os.path.join(M, pat), recursive=True)
files = sorted(set(x for x in files if os.path.isfile(x)))
print('%-46s %-9s %4s %4s %6s %6s %s' % ('file', 'id', 'NR', 'NT', 'lines', 'pred', 'note'))
for p in files:
    rel = os.path.relpath(p, M)
    raw = open(p, 'rb').read()
    Ln = [x.decode('latin-1') for x in raw.replace(b'\r\n', b'\n').split(b'\n') if x.strip()]
    if not Ln:
        continue
    l0 = Ln[0]
    if len(l0) != 60:
        print('%-46s  [first line %d chars: %r]' % (rel, len(l0), l0[:60]))
        continue
    f = [l0[j:j + 15].strip() for j in range(0, 60, 15)]
    def isnum(s):
        try:
            float(s); return True
        except ValueError:
            return False
    if not (isnum(f[2]) and isnum(f[3])):
        print('%-46s  [hdr fields: %s]' % (rel, f))
        continue
    NR, NT = int(float(f[2])), int(float(f[3]))
    n30 = sum(1 for l in Ln if len(l) == 30)
    D = -(-(NR + NT + NR * NT) // 4)
    pred1 = 1 + D                     # 单表：1 表头 + D 数据
    predk = n30 * (2 + D)
    note = ''
    if len(Ln) == pred1:
        note = 'Z 式单表 OK'
    elif n30 and len(Ln) == predk:
        note = 'Z 式多表 OK (K=%d)' % n30
    else:
        note = 'DIFF len1=%d lenK=%d' % (pred1, predk)
    print('%-46s %-9s %4d %4d %6d %6d %s' % (rel, f[0], NR, NT, len(Ln), pred1, note))

print()
print('=' * 74)
print('Ce.ZEFF 逐行 dump 前 4 行 + 行数')
print('=' * 74)
p = os.path.join(M, 'mat_Ce', 'Ce.ZEFF')
raw = open(p, 'rb').read()
print('  bytes =', len(raw), ' CRLF count =', raw.count(b'\r\n'), ' LF =', raw.count(b'\n'))
Ln = [x.decode('latin-1') for x in raw.replace(b'\r\n', b'\n').split(b'\n') if x.strip()]
print('  非空行 =', len(Ln))
for i in range(min(4, len(Ln))):
    print('   %3d [%3d] %r' % (i, len(Ln[i]), Ln[i][:70]))
print('  最后 2 行:')
for i in range(max(0, len(Ln) - 2), len(Ln)):
    print('   %3d [%3d] %r' % (i, len(Ln[i]), Ln[i][:70]))
vals = []
for l in Ln[1:]:
    for j in range(0, len(l) - 14, 15):
        try:
            vals.append(float(l[j:j + 15]))
        except ValueError:
            pass
print('  数据值数 = %d ; 期望 NR+NT+NR*NT = %d + %d + %d = %d  %s'
      % (len(vals), 20, 20, 400, 440, 'OK' if len(vals) == 440 else 'MISMATCH'))

print()
print('=' * 74)
print('opbe 尾段（ZEFF 表）确认')
print('=' * 74)
p = os.path.join(M, 'mat_Be-1.0', 'opbe')
Ln = [x.decode('latin-1') for x in
      open(p, 'rb').read().replace(b'\r\n', b'\n').split(b'\n') if x.strip()]
tail = Ln[8961:]
print('  tail 行数 = %d' % len(tail))
for i in range(min(3, len(tail))):
    print('   %3d [%3d] %r' % (i, len(tail[i]), tail[i][:70]))
print('   tail 30字符行数 =', sum(1 for l in tail if len(l) == 30))
print('   tail 60字符行数 =', sum(1 for l in tail if len(l) == 60))
