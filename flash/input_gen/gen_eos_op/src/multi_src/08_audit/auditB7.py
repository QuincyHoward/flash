# -*- coding: utf-8 -*-
import os, fnmatch
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
SRC = BASE + "/src/Multi1D++Portable20241128"
lo = []
def ex(rel, root=SRC):
    return os.path.exists(os.path.join(root, rel))
def anywhere(rel):
    a = ex(rel, SRC); b = ex(rel, BASE)
    return (a, b)

CASES = [
 # (as-written in doc, real path, root-to-use)
 ("matter++/mat_Al-1.0/Al.feos.301",      "matter++/mat_Al-1.0/FEOS/Al.feos.301"),
 ("matter++/mat_Al-1.0/Vacuum_Opacity.dat","matter++/mat_Vacuum/Vacuum_Opacity.dat"),
 ("matter++/XOP/data/inpro/idata.dat",    "matter++/idata.dat"),
 ("matter++/mat_S/Ta2O5.Rho-PTF.ise",     "matter++/Ta2O5/Ta2O5.Rho-PTF.ist"),
 ("hyades/sesame/eos_41.dat.hug",         "matter++/hyades/sesame/eos_41.hug"),
 ("src/Ionmix/macfarlane1989.{md,pdf}",   "ionmix/ionmix/src/Ionmix/macfarlane1989.md"),
 ("src/Ionmix/README.txt",                "ionmix/ionmix/src/Ionmix/README.txt"),
 ("src/Ionmix/cnrdeos",                   "ionmix/ionmix/src/Ionmix/cnrdeos"),
 ("src/Ionmix/ionmxout",                  "ionmix/ionmix/src/Ionmix/ionmxout"),
 ("src/Ionmix/ionmxbug",                  "ionmix/ionmix/src/Ionmix/ionmxbug"),
 ("eosop_pro/parsers/*.py",               "ionmix/ionmix/eosop_pro/core/"),
 ("eosop_pro/docs/20_格式规格与物理量单位手册.md", None),
 ("matter++/mat_Ge/New File.txt",         "matter++/mat_Ge/New File.txt"),
 ("ionmix/ionmix/docs/IONMIX用户指南.md",   "ionmix/ionmix/docs/IONMIX用户指南.md"),
 ("docext/Hyades 数据格式说明.txt",         ".workbuddy/tmp/docext/Hyades 数据格式说明.txt"),
 ("doc/Hyades 数据格式说明.doc",            "doc/Hyades 数据格式说明.doc"),
 ("doc/MULTI使用的SESAME数据文件格式.docx",   "doc/MULTI使用的SESAME数据文件格式.docx"),
 ("doc/SNOP.MANUAL",                      "doc/SNOP.MANUAL"),
 ("doc/Atomic(LEDCOP)说明.doc",            "doc/Atomic(LEDCOP)说明.doc"),
 ("doc/muParser.txt",                     "doc/muParser.txt"),
 ("doc/FEOS/FEOS-Package-Documentation2012.pdf","doc/FEOS/FEOS-Package-Documentation2012.pdf"),
 (".workbuddy/tmp/web_verify.md",          ".workbuddy/tmp/web_verify.md" if os.path.exists(BASE+"/.workbuddy/tmp/web_verify.md") else "workbuddy/tmp/web_verify.md"),
]
for written, real in CASES:
    a = ex(written, SRC); b = ex(written, BASE)
    verdict = "OK(src)" if a else ("OK(base)" if b else "*** NOT FOUND ***")
    rl = ""
    if real and not (a or b):
        rr = ex(real, SRC) or ex(real, BASE) or os.path.isdir(os.path.join(SRC,real)) or os.path.isdir(os.path.join(BASE,real))
        rl = "   -> real: %s  [%s]" % (real, "EXISTS" if rr else "ALSO MISSING")
    lo.append("  %-46s %-16s%s" % (written, verdict, rl))

lo.append("\n### doc/ and docext/ and pdfext/ listings ###")
for d in ['doc', '.workbuddy/tmp/docext', '.workbuddy/tmp/pdfext']:
    fp = os.path.join(BASE, d)
    lo.append("  %s: %s" % (d, (sorted(os.listdir(fp)) if os.path.isdir(fp) else "MISSING")))
print('\n'.join(lo))
open(BASE+"/.workbuddy/tmp/verdictB2.txt",'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
