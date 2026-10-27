# -*- coding: utf-8 -*-
import io, os, traceback
B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
p = B + 'h-imx-1grp.cn4'
with io.open(p, 'r', encoding='cp936', errors='replace') as f:
    raw = f.read().replace('\x1a', '')
lines = raw.splitlines()
for i in range(6):
    print(i + 1, repr(lines[i]))
try:
    print('slice0', repr(lines[0][0:10]), repr(lines[0][10:20]))
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    print('ntemp ndens', ntemp, ndens)
    print('L2 [20:]', repr(lines[1][20:]), lines[1][20:].split())
    print('L3 [20:]', repr(lines[2][20:]))
    ngrups = int(lines[3][0:12]); print('ngrups', ngrups)
    text = ''.join(lines[4:])
    print('textlen', len(text), 'mod12', len(text) % 12)
    n = ntemp + ndens + 12 * ntemp * ndens + (ngrups + 1) + 3 * ngrups * ntemp * ndens
    print('expect total fields', n, '=> chars', n * 12)
except Exception:
    traceback.print_exc()
