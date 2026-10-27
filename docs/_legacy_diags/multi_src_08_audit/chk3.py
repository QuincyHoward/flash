# -*- coding: utf-8 -*-
import os
R = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/Multi1D++Portable20241128'
for sub in ['matter++/hyades/sesame', 'matter++/hyades/qeos', 'matter++/hyades/Opacity', 'matter++/Thermos/mat_Al']:
    d = os.path.join(R, sub.replace('/', '\\'))
    print('###', sub, 'EXISTS' if os.path.isdir(d) else 'MISSING')
    if os.path.isdir(d):
        fs = sorted(os.listdir(d))
        print('   %d files' % len(fs))
        want = {
            'matter++/hyades/sesame': ['eos_11.dat','eos_21.dat','eos_41.dat','eos_44.dat','eos_2051.dat','eos_32.hug','eos_41.hug','eos_41.dat.feos','eos_41.dat.par'],
            'matter++/hyades/qeos': ['QEOS_2115.DAT','QEOS_3115.DAT','qeos_115.dat','qeos_381.dat','qeos_391.dat','qeos_392.dat','qeos_392.dat.feos','qeos_392.dat.par','qeos_402.dat','qeos_411.dat','qeos_422.dat','qeos_481.dat','qeos_52.dat'],
            'matter++/hyades/Opacity': ['opc_1022.dat','opc_1051.dat','opc_1151.dat','opc_1201.dat','opc_1281.dat','opc_1371.dat','opc_1401.dat','opc_1461.dat','opc_1491.dat'],
            'matter++/Thermos/mat_Al': ['Al.ini','Al_Planck.dat','Al_Rosseland.dat','Al_Z.dat','Al_Zeff.dat'],
        }.get(sub, [])
        for w in want:
            print('   %-24s %s' % (w, 'OK' if w in fs else '** MISSING **'))
