# -*- coding: utf-8 -*-
import os, re, fnmatch
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
SRC = BASE + "/src/Multi1D++Portable20241128"
lo = []
for d in ['matter++/mat_Al-1.0', 'matter++/mat_Al-1.0/FEOS', 'matter++/mat_B', 'matter++/mat_B/FEOS',
          'matter++/hyades', 'matter++/hyades/sesame', 'matter++/mat_S', 'matter++/XOP',
          'matter++/mat_Vacuum', 'ionmix/ionmix/docs', 'ionmix/ionmix']:
    fp = os.path.join(SRC, d)
    if os.path.isdir(fp):
        fs = sorted(os.listdir(fp))
        lo.append("### %s (%d):" % (d, len(fs)))
        lo.append("   " + " | ".join(fs[:60]))
    else:
        lo.append("### %s : *** NOT A DIRECTORY ***" % d)
    lo.append("")
# hunt for name patterns
lo.append("=== global hunts ===")
for pat in ['*Al.feos.301*','*Vacuum_Opacity*','*eos_41*','*idata.dat*','*Rho-PTF*','*macfarlane*',
            '*B.feos.301*','*/hyades/README*','*eosop_pro*','*20_*格式规格*']:
    hits = []
    for root, ds, fs in os.walk(SRC):
        for fn in fs:
            if fnmatch.fnmatch(fn, pat.strip('*')):
                hits.append(os.path.relpath(os.path.join(root,fn), SRC).replace('\\','/'))
    lo.append("  %-24s -> %s" % (pat, hits[:6] if hits else "NONE"))
open(BASE+"/.workbuddy/tmp/dirlist.txt",'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo))
