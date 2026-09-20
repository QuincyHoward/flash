# -*- coding: utf-8 -*-
import io, os, re

base = 'src/Multi1D++Portable20241128/matter++/hyades/'

def scan(path, tag):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        lines = f.read().splitlines()
    print('=' * 90)
    print('SCAN', tag, 'lines', len(lines))
    # look for lines that are not 5-token numeric
    bad = []
    for i, ln in enumerate(lines[2:], 3):
        t = ln.split()
        if len(t) != 5:
            bad.append((i, len(t), ln[:100]))
        else:
            for x in t:
                try:
                    float(x)
                except Exception:
                    bad.append((i, 'nonnum:' + x, ln[:100]))
                    break
    print('  suspicious lines:', len(bad))
    for b in bad[:25]:
        print('   ', b)
    # E12.6 style overflow regex
    txt = '\n'.join(lines)
    pat = re.compile(r'(\d\.\d{6,7})([-+]\d{3})(?![\dEe])')
    hits = pat.findall(txt)
    print('  E12.6-style overflow candidates:', len(hits), hits[:8])

scan(base + 'sesame/eos_41.dat', 'eos_41')
scan(base + 'qeos/qeos_115.dat', 'qeos_115')
scan(base + 'qeos/qeos_391.dat', 'qeos_391')
scan(base + 'qeos/qeos_52.dat', 'qeos_52')
scan(base + 'Opacity/opc_1121.dat', 'opc_1121')
scan(base + 'sesame/eos_2051.dat', 'eos_2051')
