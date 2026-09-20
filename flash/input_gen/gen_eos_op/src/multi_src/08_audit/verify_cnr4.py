# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
cn4 = ['h-imx-1grp.cn4', 'al-imx-002.cn4', 'al-imx-003.cn4', 'al-imx-004.cn4',
       'he-imx-005.cn4', 'he-imx-1grp.cn4', 'polystyrene-imx-001.cn4',
       'polystyrene-imx-002.cn4', 'polystyrene-imx-008.cn4']
print('#### .cnr exactly-closing check:  F == ntemp+ndens+4*ntemp*ndens+(ngrups+1)+3*ngrups*ntemp*ndens')
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    nt = int(lines[0][0:10]); nd = int(lines[0][10:20]); ng = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    exp = nt + nd + 4 * nt * nd + (ng + 1) + 3 * ng * nt * nd
    print('  %-22s nt=%-3d nd=%-3d ng=%-4d F=%-8d exp=%-8d delta=%d' % (n, nt, nd, ng, F, exp, F - exp))
print()
print('#### .cn4 exactly-closing check:  F == ntemp+ndens+12*ntemp*ndens+(ngrups+1)+3*ngrups*ntemp*ndens')
for n in cn4:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    nt = int(lines[0][0:10]); nd = int(lines[0][10:20]); ng = int(lines[3][0:12])
    F = len(''.join(lines[4:])) // 12
    exp = nt + nd + 12 * nt * nd + (ng + 1) + 3 * ng * nt * nd
    print('  %-24s nt=%-3d nd=%-3d ng=%-4d F=%-8d exp=%-8d delta=%d' % (n, nt, nd, ng, F, exp, F - exp))
