# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'

def analyze(p):
    with io.open(B + p, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    head = ''.join(lines[0:2])
    v = [float(head[i:i + 15]) for i in range(0, 300, 15)]
    NR = int(round(v[1])) - 1; NT = int(round(v[2])) - 1; Nel = int(round(v[3])) - 1
    nch = len(txt.replace('\n', '').replace('\r', ''))
    headf = 20 + 3 * (Nel + 1) + (NR + 1) + (NT + 1)
    per = (nch / 15.0 - headf) / ((NR + 1) * (NT + 1))
    return NR, NT, Nel, headf, nch, per

print('hypothesis: fields = 20 + 3*(Nel+1) + (NR+1) + (NT+1) + (18+Nel)*(NR+1)*(NT+1)')
print('%-22s %4s %4s %4s %12s %12s %8s' % ('file', 'NR', 'NT', 'Nel', 'predict_ch', 'actual_ch', 'delta'))
for p in ['mat_Al-1.0/Al.feos', 'mat_B/B.feos', 'Ta2O5/Ta2O5.feos',
          'mat_Others/SiO2.feos', 'mat_Ba/Ba.feos', 'mat_Ce/Cerium.feos']:
    NR, NT, Nel, headf, nch, per = analyze(p)
    pred = (20 + 3 * (Nel + 1) + (NR + 1) + (NT + 1) + (18 + Nel) * (NR + 1) * (NT + 1)) * 15
    print('%-22s %4d %4d %4d %12d %12d %8d  per=%.4f' % (os.path.basename(p), NR, NT, Nel, pred, nch, nch - pred, per))
