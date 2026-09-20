# -*- coding: utf-8 -*-
import os
R = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op'
base = R + '/src/Multi1D++Portable20241128'
pats = ['qeos_2115', 'qeos_3115', 'z67', 'coldopac', 'ionpot', 'lw.f', 'density.dat', 'idata.dat', 'bulkmod', 'size_density']
out = []
for dp, dn, fns in os.walk(base):
    rel = os.path.relpath(dp, R).replace('\\', '/')
    for fn in fns:
        low = fn.lower()
        if any(p in low for p in pats):
            out.append('%-70s %10d' % (rel + '/' + fn, os.path.getsize(os.path.join(dp, fn))))
print('\n'.join(sorted(out)))
