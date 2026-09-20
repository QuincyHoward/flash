# -*- coding: utf-8 -*-
import io, os, re

B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
ovf_pat = re.compile(r'\d\.\d{6}[-+]\d{3}')

def head4(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    return lines, raw

cn4 = ['h-imx-1grp.cn4', 'al-imx-002.cn4', 'al-imx-003.cn4', 'al-imx-004.cn4',
       'he-imx-005.cn4', 'he-imx-1grp.cn4', 'polystyrene-imx-001.cn4',
       'polystyrene-imx-002.cn4', 'polystyrene-imx-008.cn4']
print('#### .cn4 verification  (expect fields = ntemp+ndens+12*ntemp*ndens+(ngrups+1)+3*ngrups*ntemp*ndens)')
print('%-24s %5s %5s %5s %8s %9s %9s %5s %6s' % ('file', 'ntmp', 'ndns', 'ngrp', 'expect', 'chars/12', 'len%12', 'ztot', 'ovf'))
for n in cn4:
    lines, raw = head4(B + n)
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    izgas = [int(x) for x in lines[1][20:].split()]
    ngrups = int(lines[3][0:12])
    text = ''.join(lines[4:])
    exp = ntemp + ndens + 12 * ntemp * ndens + (ngrups + 1) + 3 * ngrups * ntemp * ndens
    ov = len(ovf_pat.findall(text))
    print('%-24s %5d %5d %5d %8d %9d %9d %5d %6d' % (n, ntemp, ndens, ngrups, exp, len(text) // 12, len(text) % 12, sum(izgas), ov))

print()
print('#### .cnr  header probe + reverse-solve ntrad from remainder')
cnr = ['al-imx-001.cnr', 'helium-imx-002.cnr', 'be-100grp-lte.cnr',
       'h-100grp-lte.cnr', 'n-100grp-lte.cnr', 'o-100grp-lte.cnr',
       'xe-005grp-lte.cnr', 'xe-100grp-lte.cnr']
for n in cnr:
    lines, raw = head4(B + n)
    ntemp = int(lines[0][0:10]); ndens = int(lines[0][10:20])
    izgas = [int(x) for x in lines[1][20:].split()]
    L4 = lines[3]
    ngrups = int(L4[60:72]) if len(L4) >= 72 else int(L4[60:].split()[-1])
    text = ''.join(lines[4:])
    # unknown ntrad: fields = ntemp+ndens+12*ntemp*ndens+(ngrups+1)+3*ngrups*ntemp*ndens + ??? 
    # .cnr: no EOS blocks; unknown structure. print raw info
    print('%-22s ntemp=%-4d ndens=%-4d ngrups=%-4d bodylen=%-8d mod12=%-3d L4=%r' %
          (n, ntemp, ndens, ngrups, len(text), len(text) % 12, L4))
