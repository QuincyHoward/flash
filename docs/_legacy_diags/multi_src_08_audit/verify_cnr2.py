# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
# Try hypothesis: .cnr has same opacity structure but no EOS-2D blocks;
# body fields F = ntemp + ndens + [K2D]*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens
print('%-22s %5s %5s %5s %9s %9s %8s' % ('file', 'ntmp', 'ndns', 'ngrp', 'fields', 'opacity', 'K2D'))
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    ngrups = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    op = 3 * ngrups * ntemp * ndens
    rest = F - op - ntemp - ndens - (ngrups + 1)
    k2d = rest / (ntemp * ndens) if ntemp * ndens else 0
    print('%-22s %5d %5d %5d %9d %9d %8.4f' % (n, ntemp, ndens, ngrups, F, op, k2d))
