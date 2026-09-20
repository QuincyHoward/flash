# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
print('FINAL LAW A: F = 4*nt*nd + (ng+1) + 3*ng*nt*nd')
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    nt = int(lines[0][0:10]); nd = int(lines[0][10:20]); ng = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    exp = 4 * nt * nd + (ng + 1) + 3 * ng * nt * nd
    print('  %-22s nt=%-3d nd=%-3d ng=%-4d F=%-8d exp=%-8d delta=%d' % (n, nt, nd, ng, F, exp, F - exp))
print()
print('FINAL LAW B (alt, includes ntrad): F = nt+nd+ntrad + 4*nt*nd + ntrad*nd*K + (ng+1)+3*ng*nt*nd')
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    nt = int(lines[0][0:10]); nd = int(lines[0][10:20]); ng = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    base = 4 * nt * nd + (ng + 1) + 3 * ng * nt * nd
    print('  %-22s F-base = %d   (=nt+nd? %s)' % (n, F - base, F - base == nt + nd))
