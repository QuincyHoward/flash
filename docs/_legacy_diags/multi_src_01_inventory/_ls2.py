# -*- coding: utf-8 -*-
import os, fnmatch
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
lo = []
for p in ['ionmix','ionmix/ionmix','ionmix/ionmix/docs','ionmix/ionmix/eosop_pro',
          'src/Multi1D++Portable20241128/ionmix','src/Multi1D++Portable20241128/XOP',
          'src/Multi1D++Portable20241128/tools','src/Multi1D++Portable20241128/extern',
          'src/Multi1D++Portable20241128/python','src/Multi1D++Portable20241128/Matlab']:
    fp = os.path.join(BASE, p)
    lo.append("%-58s %s" % (p, "DIR" if os.path.isdir(fp) else ("FILE" if os.path.exists(fp) else "MISSING")))
lo.append("")
lo.append("=== ionmix tree top ===")
ip = os.path.join(BASE,'ionmix')
if os.path.isdir(ip):
    for root, ds, fs in os.walk(ip):
        depth = root[len(ip):].count(os.sep)
        if depth <= 3:
            lo.append("  "+os.path.relpath(root, BASE).replace('\\','/')+'/  ['+', '.join(fs[:12])+']')
        if depth >= 3: ds[:] = []
lo.append("")
lo.append("=== global: any XOP / macfarlane / Rho-PTF anywhere in BASE ===")
for pat in ['XOP','macfarlane*','*Rho-PTF*','*Rho-P.ist*','*Rho-T.ist*','*Rho-E.ist*','eosop_pro']:
    hits=[]
    for root, ds, fs in os.walk(BASE):
        if '.git' in root: continue
        for fn in ds+fs:
            if fnmatch.fnmatch(fn, pat.strip('*') if not pat.startswith('*') else pat):
                hits.append(os.path.relpath(os.path.join(root,fn), BASE).replace('\\','/'))
        if len(hits)>8: break
    lo.append("  %-18s -> %s" % (pat, hits[:8] if hits else "NONE"))
open(BASE+"/.workbuddy/tmp/dirlist2.txt",'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo[:80]))
