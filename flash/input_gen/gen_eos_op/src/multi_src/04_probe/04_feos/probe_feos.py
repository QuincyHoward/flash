# -*- coding: utf-8 -*-
import io, os
def show(path, n, enc='cp936'):
    print('=' * 100); print('FILE:', path, os.path.getsize(path) if os.path.exists(path) else 'MISSING')
    if not os.path.exists(path): return
    with io.open(path, 'r', encoding=enc, errors='replace') as f:
        for i in range(n):
            ln = f.readline()
            if not ln: break
            s = ln.rstrip('\r\n'); print('  L%-3d len=%-4d |%s|' % (i + 1, len(s), s))
B = 'src/Multi1D++Portable20241128/matter++/'
show(B + 'mat_Al-1.0/FEOS/Al.feos.301', 8)
show(B + 'mat_Al-1.0/FEOS/Al.feos.304', 6)
show(B + 'mat_Al-1.0/FEOS/Al.feos.305', 6)
show(B + 'mat_Al-1.0/FEOS/Al.feos', 12)
show(B + 'mat_B/B.301', 4)
show(B + 'mat_Au-1.0/Au.301', 4)
show(B + 'mat_Al-1.0/Al.feos.par', 60)
