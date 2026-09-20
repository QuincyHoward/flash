# -*- coding: utf-8 -*-
"""Locate the specific B-1..B-14 path errors in the doc and find correct forms."""
import os, re, sys

ROOT = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op'
PRIMARY = ROOT + '/src/Multi1D++Portable20241128'

targets = [
 'mat_Al-1.0/Al.feos.301',
 'mat_Al-1.0/Vacuum_Opacity.dat',
 'XOP/data/inpro/idata.dat',
 'mat_S/Ta2O5.Rho-PTF.ise',
 'eos_41.dat.hug',
 'eos_41.dat',
 'eos_11.dat',
 'eos_21.dat',
 'eos_44.dat',
 'src/Ionmix/',
 'eosop_pro/parsers',
 'Density/',
 'eosop_pro/docs/',
 'qeos_2115.DAT',
 'qeos_3115.DAT',
 'idata.dat',
 'Ta2O5.Rho-PTF.ise',
 'Ta2O5.Rho-PTF.ist',
 'eos_32.hug',
 'eos_41.hug',
 'Vacuum_Opacity.dat',
 'Al.feos.301',
 'Bulkmat/1e10',
]
for t in targets:
    print('=== 搜索: %s ===' % t)
    found = []
    for base in [PRIMARY, ROOT]:
        for dp, dns, fns in os.walk(base):
            rel = os.path.relpath(dp, ROOT).replace('\\','/')
            for fn in fns:
                r = (rel+'/'+fn) if rel != '.' else fn
                if t.lower() in r.lower():
                    found.append(r)
    for f in sorted(set(found))[:40]:
        print('   ', f)
    if not found:
        print('    <NONE>')
