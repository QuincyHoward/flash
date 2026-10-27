# -*- coding: utf-8 -*-
import os, sys, re, traceback
BASE = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp\vendor\FEOS_extract\inner\FEOS"
pdf = os.path.join(BASE, "Documents", "FEOS-Package-Documentation.pdf")
print("PDF:", pdf, os.path.getsize(pdf))

txt = None
for mod, fn in [("pypdf", "pypdf"), ("PyPDF2", "PyPDF2"), ("pdfminer", "pdfminer.high_level")]:
    try:
        __import__(mod.split(".")[0])
    except Exception as e:
        print("not available:", mod, e)
        continue
    try:
        if mod == "pdfminer":
            from pdfminer.high_level import extract_text
            txt = extract_text(pdf)
        else:
            m = __import__(mod)
            r = m.PdfReader(pdf)
            print("pages:", len(r.pages))
            txt = "\n".join((p.extract_text() or "") for p in r.pages)
        print("OK with", mod, "chars:", len(txt))
        break
    except Exception as e:
        print("FAIL", mod, type(e).__name__, e)
        traceback.print_exc()

if txt is None:
    print("NO PDF LIBRARY AVAILABLE")
    sys.exit(2)

outp = os.path.join(os.path.dirname(pdf), "FEOS-Package-Documentation.txt")
with open(outp, "w", encoding="utf-8", newline="\n") as f:
    f.write(txt)
print("wrote", outp, len(txt))
print("=" * 60)
print(txt[:6000])
