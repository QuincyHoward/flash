# -*- coding: utf-8 -*-
import io, os
def show(path, n, enc='cp936', lim=250):
    print('=' * 100); print('FILE:', path, os.path.getsize(path) if os.path.exists(path) else 'MISSING')
    if not os.path.exists(path): return
    with io.open(path, 'r', encoding=enc, errors='replace') as f:
        for i in range(n):
            ln = f.readline()
            if not ln: break
            s = ln.rstrip('\r\n'); print('  L%-3d len=%-4d |%s|' % (i + 1, len(s), s[:lim]))
B = 'src/Multi1D++Portable20241128/matter++/'
show(B + 'mat_Al-1.0/Al.feos', 6)
show(B + 'mat_Al-1.0/AL_eos.feos', 6)
show(B + 'mat_B/B.feos', 6)
show(B + 'mat_Others/SiO2.feos', 6)
show(B + 'Ta2O5/Ta2O5.feos', 6)
