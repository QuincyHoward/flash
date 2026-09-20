# -*- coding: utf-8 -*-
"""Search authoritative extracted docs for noext format keywords."""
import os, re
tmp = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/.workbuddy/tmp"
files = ["src_doc_core.md", "src_doc_aux.md", "src_doc_tables.md", "src_doc_tree.md",
         "src_sesame_ledcop.md", "src_ionmix_snop.md", "explore_multi_formats.md",
         "formats_from_source.md", "formats_resolved.md", "doc_misc.txt", "textdocs.txt"]
kws = ["noextension", "no extension", "ieos", "IEOS", "SIMPLE_PLANCK", "IDEAL_GAS", "MODINFO",
       "FILELIST", "ZEFF", "op03", "MOPP", "MOPR", "mopp", "mopr", "PLANCK M", "ROSSELAND M",
       "EPS M", "%15", "15.7", "Ideal_Gas", "_eos", "eosd", "MULTI", "inverse EOS",
       "inverse opacity", "0.1234567", "sentinel", "PROPERTY", "mat_Au"]
out = []
for f in files:
    fp = os.path.join(tmp, f)
    if not os.path.isfile(fp):
        out.append(f"### {f}  MISSING")
        continue
    try:
        txt = open(fp, encoding="utf-8", errors="replace").read()
    except Exception as e:
        out.append(f"### {f}  ERR {e}")
        continue
    out.append(f"\n{'='*80}\n### {f}  ({len(txt)} chars)\n{'='*80}")
    lines = txt.splitlines()
    for kw in kws:
        hits = [(i+1, l) for i, l in enumerate(lines) if kw in l]
        if hits:
            out.append(f"\n--- kw={kw!r}  hits={len(hits)}")
            for i, l in hits[:14]:
                out.append(f"  L{i}: {l.strip()[:240]}")
open(os.path.join(tmp, "probe_noext", "docsearch.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out)[:200])
print("WROTE docsearch.txt")
