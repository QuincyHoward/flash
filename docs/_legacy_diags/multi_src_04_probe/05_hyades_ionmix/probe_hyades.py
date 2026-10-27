# -*- coding: utf-8 -*-
import io, os

def show(path, nline=12, label=''):
    print('=' * 100)
    print('FILE:', path)
    if not os.path.exists(path):
        print('  MISSING')
        return
    print('  BYTES:', os.path.getsize(path))
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        for i in range(nline):
            ln = f.readline()
            if not ln:
                break
            ln = ln.rstrip('\r\n')
            print('  L%-3d |%s|  (len=%d)' % (i + 1, ln, len(ln)))

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
show(base + 'sesame/eos_2051.dat', 6)
show(base + 'sesame/eos_41.dat', 5)
show(base + 'sesame/eos_41.hug', 10)
show(base + 'sesame/eos_32.hug', 8)
show(base + 'Opacity/opc_1151.dat', 5)
show(base + 'Opacity/opc_1051.dat', 6)
show(base + 'Opacity/opc_1491.dat', 6)
show(base + 'qeos/qeos_115.dat', 5)
show(base + 'ionpot.dat', 8)
show(base + 'coldopac.dat', 8)
show(base + 'tmp.dat', 8)
show(base + 'tmp2.dat', 6)
show(base + 'EOS.list', 12)
show(base + 'Opacity.list', 10)
show(base + '### Data from hyades%Data directory.txt', 12)
