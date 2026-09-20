# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
print('%-22s %4s %4s %5s %8s %8s %7s' % ('file', 'nt', 'nd', 'ng', 'delta', 'nt+nd+ng', 'cnt'))
rows = []
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    nt = int(lines[0][0:10]); nd = int(lines[0][10:20]); ng = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    exp = nt + nd + 4 * nt * nd + (ng + 1) + 3 * ng * nt * nd
    rows.append((n, nt, nd, ng, F - exp))
    print('%-22s %4d %4d %5d %8d %8d %7d' % (n, nt, nd, ng, F - exp, nt + nd + ng, 2 * (nt + nd) + ng))
print()
# try: delta = -(nt+nd) - ng + c
print('check delta + (nt+nd) + ng = const?')
for n, nt, nd, ng, d in rows:
    print('  %-22s  delta+(nt+nd)+ng = %d' % (n, d + nt + nd + ng))
print()
print('check delta + (nt+nd) = const?')
for n, nt, nd, ng, d in rows:
    print('  %-22s  delta+(nt+nd) = %d' % (n, d + nt + nd))
