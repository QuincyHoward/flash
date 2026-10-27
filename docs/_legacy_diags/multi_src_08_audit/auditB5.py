# -*- coding: utf-8 -*-
import re, os, collections, fnmatch

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
SRC = BASE + "/src/Multi1D++Portable20241128"
OUT = BASE + "/.workbuddy/tmp/auditB_final.txt"

text = open(DOC, encoding='utf-8').read()
LINES = text.split('\n')

tree, dirs = set(), set()
for root, ds, fs in os.walk(SRC):
    rel = os.path.relpath(root, SRC).replace('\\','/')
    if rel != '.': dirs.add(rel)
    for fn in fs: tree.add((rel+'/'+fn) if rel!='.' else fn)
for c in ['docext','doc','pdfext','ionmix','src','.workbuddy']:
    d = os.path.join(BASE, c)
    if os.path.isdir(d):
        for root, ds, fs in os.walk(d):
            rel = os.path.relpath(root, BASE).replace('\\','/')
            if rel != '.': dirs.add(rel)
            for fn in fs: tree.add(rel+'/'+fn)

# ---- specific checks ----
CHECKS = [
 ("matter++/hyades/README",                  "matter++/hyades/README"),
 ("matter++/mat_B/FEOS/B.feos.301",          "matter++/mat_B/FEOS/B.feos.301"),
 ("matter++/mat_Al-1.0/Al.feos.301",         "matter++/mat_Al-1.0/Al.feos.301"),
 ("matter++/mat_Al-1.0/Vacuum_Opacity.dat",  "matter++/mat_Al-1.0/Vacuum_Opacity.dat"),
 ("sesame/eos_41.dat.hug",                   "hyades/sesame/eos_41.dat.hug"),
 ("XOP/data/inpro/idata.dat",                "XOP/data/inpro/idata.dat"),
 ("matter++/mat_S/Ta2O5.Rho-PTF.ise",        "matter++/mat_S/Ta2O5.Rho-PTF.ise"),
 ("matter++/mat_Ge/New File.txt",            "matter++/mat_Ge/New File.txt"),
 ("matter++/mat_Ge/New",                     "matter++/mat_Ge/New File.txt"),
]
lo = ["="*25, "AUDIT B FINAL: targeted existence checks", "="*25]
for label, q in CHECKS:
    hits = [f for f in tree if f == q or f.endswith('/'+q)]
    hitsd = [d for d in dirs if d==q or d.endswith('/'+q)]
    lo.append("  %-42s -> %s" % (label, ("EXISTS: "+str(hits[:3])) if (hits or hitsd) else "*** NOT FOUND ***"))
    if hitsd and not hits: lo.append("      (as directory: %s)" % hitsd[:3])

# location of Vacuum_Opacity.dat
lo.append("")
lo.append("-- where does Vacuum_Opacity.dat really live? --")
for f in sorted(tree):
    if 'Vacuum_Opacity' in f: lo.append("   " + f)
    if f.lower().endswith('vacuum') or '/mat_Vacuum' in f: lo.append("   (vac) " + f)

# glob checks
lo.append("")
lo.append("-- GLOB patterns used in doc --")
for pat in ['matter++/mat_*/*.readme','matter++/*.dat','matter++/*.xml','matter++/*.txt',
            'doc/FEOS/*.pdf','doc/FEOS/*','eosop_pro/parsers/*.py','Crystal/*',
            'XrayMassCoef/*','RadiativeCoolingRates/*.dat','HeatCapacity/*',
            'src/Ionmix/macfarlane1989.{md,pdf}']:
    hits = fnmatch.filter(tree, pat)
    if not hits:
        # try suffix glob
        hits = [f for f in tree if fnmatch.fnmatch(f.split('/',1)[-1], pat.split('/',1)[-1])]
    lo.append("  %-45s -> %d hits %s" % (pat, len(hits), hits[:3]))

# directory checks for the bare-dir list
lo.append("")
lo.append("-- bare directory refs (L688 etc.) --")
for d in ['hyades','ATOMIC','Ionmix','Thermos','SNOP','FEOS','Opacity','qeos','sesame',
          'Crystal','XrayMassCoef','RadiativeCoolingRates','HeatCapacity','ColdOpacity',
          'mat_Ti','Density','eosop_pro','doc/FEOS','doc','docext','pdfext']:
    hitsd = [x for x in dirs if x==d or x.endswith('/'+d)]
    lo.append("  %-32s -> %s" % (d, ("OK: "+str(hitsd[:2])) if hitsd else "*** MISSING ***"))

open(OUT,'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo))
