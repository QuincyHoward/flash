# -*- coding: utf-8 -*-
import io, itertools
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
rows = []
for n in cnr:
    with io.open(B + n, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    ngrups = int(lines[3].split()[-1])
    F = len(''.join(lines[4:])) // 12
    rows.append((n, ntemp, ndens, ngrups, F))

# Hypothesis A: pure opacity file, no EOS at all: F = ngrups+1 + 3*ngrups*ntemp*ndens  (too small?)
# Hypothesis B: F = ntemp+ndens+ n2d*ntemp*ndens + (ngrups+1)+ 3*ngrups*ntemp*ndens  -> solve n2d
print('HYP-A pure-opacity:', 'F - (ngrups+1) - 3*ng*nt*nd')
for n, nt, nd, ng, F in rows:
    print('  %-22s F=%-8d base=%-8d diff=%-8d /(nt*nd)=%.4f' % (n, F, (ng + 1) + 3 * ng * nt * nd, F - (ng + 1) - 3 * ng * nt * nd, (F - (ng + 1) - 3 * ng * nt * nd) / (nt * nd)))
print()
print('HYP-C: F = ntemp+ndens+ntrad + n2d*(ntemp*ndens + ntrad*ndens) + (ng+1) + 3*ng*nt*nd')
# solve for small integer n2d, and ntrad>=0: resid = F - ntemp - ndens - (ng+1) - 3*ng*nt*nd - n2d*nt*nd  must be divisible structure
for n, nt, nd, ng, F in rows:
    base = nt + nd + (ng + 1) + 3 * ng * nt * nd
    r = F - base
    best = []
    for n2d in range(0, 20):
        rem = r - n2d * nt * nd
        # rem should be ntrad + n2d*ntrad*nd = ntrad*(1+n2d*nd)
        for ntrad in range(0, 60):
            if rem == ntrad * (1 + n2d * nd):
                best.append((n2d, ntrad))
    print('  %-22s r=%-8d sols=%s' % (n, r, best[:6]))
