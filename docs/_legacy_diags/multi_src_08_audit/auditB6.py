# -*- coding: utf-8 -*-
import os, fnmatch
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
SRC = BASE + "/src/Multi1D++Portable20241128"
lo = ["### VERDICT TABLE ###"]
def has(rel, roots=(SRC, BASE)):
    for r in roots:
        if os.path.exists(os.path.join(r, rel)): return True
    return False
def glob_any(pat, root=SRC):
    for rt, ds, fs in os.walk(root):
        for fn in fs:
            p = os.path.relpath(os.path.join(rt,fn), SRC).replace('\\','/')
            if fnmatch.fnmatch(p, pat): return True
    return False

ITEMS = [
 ("matter++/hyades/README", "REFERENCED-AS-MISSING (by design: doc says MISSING)", None),
 ("matter++/mat_B/FEOS/B.feos.301", "REFERENCED-AS-MISSING (by design)", None),
 ("matter++/mat_Al-1.0/Al.feos.301", "WRONG: real is mat_Al-1.0/FEOS/Al.feos.301", has("matter++/mat_Al-1.0/FEOS/Al.feos.301")),
 ("matter++/mat_Al-1.0/Vacuum_Opacity.dat", "WRONG location: real is matter++/mat_Vacuum/Vacuum_Opacity.dat", has("matter++/mat_Vacuum/Vacuum_Opacity.dat")),
 ("matter++/XOP/data/inpro/idata.dat", "WRONG: real is matter++/idata.dat", has("matter++/idata.dat")),
 ("XOP/data/inpro/idata.dat", "WRONG prefix: real is matter++/idata.dat", has("matter++/idata.dat")),
 ("matter++/mat_S/Ta2O5.Rho-PTF.ise", "WRONG: Ta2O5 files live in matter++/Ta2O5/, not mat_S/; extension is .ist not .ise", has("matter++/Ta2O5/Ta2O5.Rho-PTF.ist")),
 ("hyades/sesame/eos_41.dat.hug", "eos_41.dat.hug does NOT exist (eos_41.hug / eos_32.hug exist)", has("matter++/hyades/sesame/eos_41.hug")),
 ("src/Ionmix/macfarlane1989.{md,pdf}", "does NOT exist anywhere", glob_any("*macfarlane*")),
 ("src/Ionmix/README.txt", "exists only as ionmix/ionmix/src/Ionmix/ ... check", None),
 ("src/Ionmix/cnrdeos", "exists as ionmix/ionmix/src/Ionmix/cnrdeos", has("ionmix/ionmix/src/Ionmix/cnrdeos")),
 ("src/Ionmix/ionmxout", "NO such name; real is ionmix/ionmix/src/Ionmix/implot0*", glob_any("*ionmxout*")),
 ("src/Ionmix/ionmxbug", "exists as ionmix/ionmix/src/Ionmix/ionmxbug", has("ionmix/ionmix/src/Ionmix/ionmxbug")),
 ("eosop_pro/parsers/*.py", "path does not exist; real is ionmix/ionmix/eosop_pro/core/*.py", has("ionmix/ionmix/eosop_pro/core")),
 ("eosop_pro/docs/20_格式规格与物理量单位手册.md", "NOT FOUND", None),
 ("matter++/mat_Ge/New File.txt", "EXISTS", has("matter++/mat_Ge/New File.txt")),
]
for rel, note, ok in ITEMS:
    lo.append("  %-52s exists=%-5s  %s" % (rel, ok, note))

lo.append("")
lo.append("### eos_41* / eos_32* actual ###")
for rt, ds, fs in os.walk(os.path.join(SRC,'matter++/hyades')):
    for fn in fs:
        if fn.startswith(('eos_41','eos_32','eos_11','eos_21','eos_44','eos_2051')) and '.hug' in fn:
            lo.append("   "+os.path.relpath(os.path.join(rt,fn), SRC).replace('\\','/'))
lo.append("")
lo.append("### src/Ionmix real listing ###")
d = os.path.join(BASE,'ionmix/ionmix/src/Ionmix')
if os.path.isdir(d): lo.append("   " + " | ".join(sorted(os.listdir(d))))
d = os.path.join(BASE,'ionmix/ionmix/docs')
if os.path.isdir(d): lo.append("   docs/ = " + " | ".join(sorted(os.listdir(d))))
d = os.path.join(BASE,'eosop_pro')
if os.path.isdir(d): lo.append("   eosop_pro/ = " + " | ".join(sorted(os.listdir(d))))
print('\n'.join(lo))
open(BASE+"/.workbuddy/tmp/verdictB.txt",'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
