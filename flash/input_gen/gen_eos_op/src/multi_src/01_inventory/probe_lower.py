# -*- coding: utf-8 -*-
import io, os

def show(path, nline, enc='cp936', tags=True):
    print('=' * 100)
    print('FILE:', path, os.path.getsize(path) if os.path.exists(path) else 'MISSING')
    with io.open(path, 'r', encoding=enc, errors='replace') as f:
        for i in range(nline):
            ln = f.readline()
            if not ln: break
            s = ln.rstrip('\r\n')
            print('  L%-3d len=%-4d |%s|' % (i + 1, len(s), s))

B = 'src/Multi1D++Portable20241128/matter++/Ionmix/'
show(B + 'h-imx-1grp.cn4', 22)
show(B + 'al-imx-002.cn4', 22)
show(B + 'polystyrene-imx-008.cn4', 22)
show(B + 'al-imx-001.cnr', 22)
show(B + 'h-100grp-lte.cnr', 22)
show(B + 'n-100grp-lte.cnr', 20)
show(B + 'xe-005grp-lte.cnr', 20)
show('src/Multi1D++Portable20241128/matter++/ATOMIC/#LEDCOP', 6)
show('src/Multi1D++Portable20241128/matter++/ATOMIC/Al.NoFree', 20)
show('src/Multi1D++Portable20241128/matter++/ATOMIC/Al.GrayOpacity_PLANCK', 20)
show('src/Multi1D++Portable20241128/matter++/ATOMIC/Al.MultiGroupOpacity_PLANCK', 24)
show('src/Multi1D++Portable20241128/matter++/ATOMIC/Al.AvSqFree', 8)
