# -*- coding: utf-8 -*-
"""probe_10_docs: search Multi1D++ doc/ for naming-convention evidence; list doc tree."""
import os, re, json

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
R = os.path.join(REPO, "src", "Multi1D++Portable20241128")
DOC = os.path.join(R, "doc")
OUT = os.path.join(REPO, ".workbuddy", "tmp", "out_10.txt")

buf = []
buf.append("=== doc/ tree (dirs and files) ===")
for dp, dn, fn in os.walk(DOC):
    rel = os.path.relpath(dp, DOC).replace("\\", "/")
    buf.append("[DIR] %s  (%d files)" % (rel, len(fn)))
    for f in sorted(fn):
        p = os.path.join(dp, f)
        try: sz = os.path.getsize(p)
        except OSError: sz = -1
        buf.append("      %-60s %10d" % (f, sz))

PAT = re.compile(r"(_opp\b|_opr\b|_mopp|_mopr|_ieos|op100|mop20|IEOS|灰不透明|多群不透明|命名|文件格式|文件类型|后缀)", re.I)
buf.append("\n=== keyword hits in doc/ text files ===")
texts = []
for dp, dn, fn in os.walk(DOC):
    for f in fn:
        if f.lower().endswith((".txt", ".md", ".log", ".manual", ".dat", ".ini", ".pdf".replace("pdf","txt"))):
            texts.append(os.path.join(dp, f))
# also any file that looks like docs
for dp, dn, fn in os.walk(DOC):
    for f in fn:
        low = f.lower()
        if any(k in low for k in ("manual", "readme", "doc", "format", "manual")):
            texts.append(os.path.join(dp, f))
texts = sorted(set(texts))

for p in texts:
    try:
        t = open(p, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        continue
    for i, ln in enumerate(t.splitlines(), 1):
        if PAT.search(ln):
            buf.append("%s:%d: %s" % (os.path.relpath(p, R).replace("\\", "/"), i, ln.strip()[:200]))

open(OUT, "w", encoding="utf-8").write("\n".join(buf))
print("written", OUT, len(buf), "lines")
