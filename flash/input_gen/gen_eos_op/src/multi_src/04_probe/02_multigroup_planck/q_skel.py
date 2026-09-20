# -*- coding: utf-8 -*-
"""复核：无扩展名多群不透明度表 每群是否存在"4 值骨架行"。
   对 Ce.PLANCK 与 AU_op03p 逐行 dump 前 12 行 + 行数闭合。
"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')


def dump(path, tag, nline=14):
    raw = open(path, 'rb').read().replace(b'\r\n', b'\n')
    L = [x.decode('latin-1') for x in raw.split(b'\n')]
    Ln = [l for l in L if l.strip()]
    L30 = [i for i, l in enumerate(Ln) if len(l) == 30]
    L60 = [i for i, l in enumerate(Ln) if len(l) == 60]
    other = [(i, len(l)) for i, l in enumerate(Ln) if len(l) not in (30, 60)]
    print('=' * 78)
    print('%s  (%d B)' % (tag, os.path.getsize(path)))
    print('=' * 78)
    print('  非空行 = %d   30字符行 = %d   60字符行 = %d' % (len(Ln), len(L30), len(L60)))
    print('  非 30/60 宽的行 (前10): %s' % other[:10])
    print('  前 %d 行原文:' % nline)
    for i in range(min(nline, len(Ln))):
        print('   %3d [%3d] %r' % (i, len(Ln[i]), Ln[i]))
    print('  30字符行索引 (前 6): %s' % L30[:6])
    print()


dump(os.path.join(M, 'mat_Ce', 'Ce.PLANCK'), 'Ce.PLANCK')
dump(os.path.join(M, 'mat_Au-1.0', 'AU_op03p'), 'mat_Au-1.0/AU_op03p')
dump(os.path.join(M, 'mat_Gd', 'Gd100PLANCK'), 'mat_Gd/Gd100PLANCK', 8)
dump(os.path.join(M, 'mat_Be-1.0', 'opbe'), 'mat_Be-1.0/opbe', 8)

print('=' * 78)
print('ZEFF 类文件第 2 字段（疑为 Z）实测')
print('=' * 78)
import glob
cands = []
for pat in ['mat_*/*.ZEFF', 'mat_*/*_Zeff.dat', 'mat_*/*_Z.dat', 'SNOP/*.ZEFF',
            'CELIA/*.ZEFF', 'mat_C-1.0/*zeff*', 'mat_Ce/Ce.ZEFF']:
    cands += glob.glob(os.path.join(M, pat))
seen = set()
for p in sorted(cands):
    rel = os.path.relpath(p, M)
    if rel in seen:
        continue
    seen.add(rel)
    if os.path.isdir(p):
        continue
    try:
        raw = open(p, 'rb').read(120).replace(b'\r\n', b'\n')
        l0 = raw.split(b'\n')[0].decode('latin-1')
    except OSError:
        continue
    f = [l0[j:j + 15].strip() for j in range(0, min(60, len(l0)), 15)]
    print('  %-44s %s' % (rel, f))
