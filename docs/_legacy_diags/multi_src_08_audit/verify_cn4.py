# -*- coding: utf-8 -*-
import io, os, re, math

B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
FW4 = 48          # 4*12 per full line
FW12 = 12

def parse_cn4(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    header = lines[0]
    # L1 = 2i10  -> ntemp ndens
    ntemp = int(header[0:10]); ndens = int(header[10:20])
    ngases = len(lines[1][20:].split())
    izgas = [int(x) for x in lines[1][20:].split()]
    fracs = [float(x) for x in lines[2][20:].split()]
    # L4 = i12 ngrups
    ngrups = int(lines[3][0:12])
    body = lines[4:]
    # concat all body, expect sequence of 12-char fields
    text = ''.join(body)
    # count fields via expected total
    n_EOS12 = ntemp + ndens + 12 * ntemp * ndens          # blocks 1-14 (12 2-D blocks)
    n_grp = ngrups + 1
    n_op = 3 * ngrups * ntemp * ndens
    total = n_EOS12 + n_grp + n_op
    return dict(ntemp=ntemp, ndens=ndens, ngases=ngases, izgas=izgas, fracs=fracs,
                ngrups=ngrups, total=total, textlen=len(text))

def overflow(text):
    # e12.6 overflow: 'd.dddddd-eee' or 'd.dddddd+eee' (no E)
    return re.findall(r'\d\.\d{6}[-+]\d{3}', text)

name = ['h-imx-1grp.cn4', 'al-imx-002.cn4', 'al-imx-003.cn4', 'al-imx-004.cn4',
        'he-imx-005.cn4', 'he-imx-1grp.cn4', 'polystyrene-imx-001.cn4',
        'polystyrene-imx-002.cn4', 'polystyrene-imx-008.cn4']
print('%-24s %6s %6s %6s %7s %9s %9s %7s %7s' % ('file', 'ntemp', 'ndens', 'ngrup', 'fieldsw', 'textlen', 'expect12', 'mod', 'ovf'))
for n in name:
    p = B + n
    r = parse_cn4(p)
    text = r['textlen']
    print('%-24s %6d %6d %6d %7d %9d %9d %7d %7d' %
          (n, r['ntemp'], r['ndens'], r['ngrups'], r['total'], text, r['total'] * 12,
           text % 12, len(overflow(r['text']))))
    print('        izgas=%s frac=%s' % (r['izgas'], r['fracs']))
