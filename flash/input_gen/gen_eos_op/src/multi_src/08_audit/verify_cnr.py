# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
print('%-22s %5s %5s %5s %10s %10s %5s %5s' % ('file', 'ntmp', 'ndns', 'ngrp', 'bodylen', 'L4len', 'mod12', 'mod48'))
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    izgas = [int(x) for x in lines[1][20:].split()]
    L4 = lines[3]
    tok = L4.split()
    ngrups = int(tok[-1]) if tok else -1
    print('%-22s %5d %5d %5d %10d %10d %5d %5d  izgas=%s L4=%r' %
          (n, ntemp, ndens, ngrups, len(''.join(lines[4:])), len(L4), len(''.join(lines[4:])) % 12, len(''.join(lines[4:])) % 48, izgas, L4))
