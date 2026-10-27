# -*- coding: utf-8 -*-
import io, os, re
B = 'src/Multi1D++Portable20241128/matter++/'
for p in ['mat_Others/SiO2.feos', 'mat_Al-1.0/Al.feos', 'mat_B/B.feos', 'Ta2O5/Ta2O5.feos',
          'mat_Ba/Ba.feos', 'mat_Ce/Cerium.feos']:
    with io.open(B + p, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    e3 = re.findall(r'\d\.\d{8}[eE][-+]\d{3}', txt)
    e2 = re.findall(r'\d\.\d{8}[eE][-+]\d{2}\b', txt)
    # short (no leading space) fields
    short = len(re.findall(r'(?<![0-9eE])-?\d\.\d{8}[eE][-+]\d{2}(?![0-9])', txt))
    print('%-24s e3=%-6d e2=%-8d shortnostart=%d lines=%d' % (os.path.basename(p), len(e3), len(e2), short, txt.count('\n')))
    if e3: print('     e3 sample:', e3[:4])
