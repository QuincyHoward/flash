# -*- coding: utf-8 -*-
import os, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
R = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
M = os.path.join(R, "matter++")

KNOWN = set(""".dat .feos .301 .304 .305 .mexport .cst .planck .ross .zeff .eps .nofree .avsqfree
.coldopacity .cn4 .cnr .sesame .snop .hug .ist .isc .ise .mnt .dem .opj .mat .xmind .base
.manifest .list .cat .db .template .case .ini .gplt .gid .mnu .hlp .animate .inv .inhalt .info
.user .zeff_old .sesame_planck .sesame_rosseland .tab1 .tab2 .input .dat_multi .10 .in .par
.log .txt .out .cst .gif .md .docx .m .data""".split())
KNOWN_SUFFIX_FRAG = ("grayopacity_", "multigroupopacity_")

# ---------- C. three-level tree of matter++ ----------
print("@@TREE@@")
rows = []
for dirpath, dirnames, filenames in os.walk(M):
    rel = os.path.relpath(dirpath, M).replace("\\", "/")
    if rel == ".": rel = ""
    depth = 0 if rel == "" else rel.count("/") + 1
    if depth > 3:
        continue
    nf = 0; nb = 0
    for f in filenames:
        try:
            nf += 1; nb += os.path.getsize(os.path.join(dirpath, f))
        except: pass
    # count recursive files for empty-check
    tot_all = 0
    for dp2, dn2, fn2 in os.walk(dirpath):
        tot_all += len(fn2)
    rows.append((depth, rel if rel else "<matter++>", len(filenames), len(dirnames), nf, nb, tot_all))
for depth, rel, nd, ndirs, nf, nb, tall in rows:
    print("%s%s| files(here)=%d bytes(here)=%d subdirs=%d recursive_files=%d" % (
        "  " * depth, rel, nf, nb, ndirs, tall))

# ---------- suffix census over matter++ ----------
print("@@SUFFIX@@")
suf = collections.Counter()
suf_ex = {}
for dp, dn, fn in os.walk(M):
    for f in fn:
        e = os.path.splitext(f)[1].lower()
        if e:
            suf[e] += 1
            suf_ex.setdefault(e, os.path.relpath(os.path.join(dp, f), M).replace("\\", "/"))
        else:
            suf["<none>"] += 1
            suf_ex.setdefault("<none>", os.path.relpath(os.path.join(dp, f), M).replace("\\", "/"))
for k, v in sorted(suf.items(), key=lambda x: -x[1]):
    known = k in KNOWN or any(f in k for f in KNOWN_SUFFIX_FRAG)
    print("%-26s n=%-5d known=%-5s ex=%s" % (k, v, "Y" if known else "N", suf_ex[k]))
