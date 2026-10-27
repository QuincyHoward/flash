# -*- coding: utf-8 -*-
"""Download IONMIX reports from FTI Wisconsin (UWFDM-750) and check reachability
of the Prism/MacFarlane GitHub orgs."""
import os, sys, urllib.request, traceback
sys.stdout.reconfigure(encoding="utf-8")

BASE = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp\vendor"
os.makedirs(BASE, exist_ok=True)

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "*/*"}

TARGETS = [
    ("UWFDM-750_IONMIX_MacFarlane_1987.pdf",
     "https://fti.neep.wisc.edu/fti.neep.wisc.edu/pdf/fdm750.pdf"),
    ("UWFDM-750_alt_IONMIX.pdf",
     "https://fti.neep.wisc.edu/pdf/fdm750.pdf"),
    ("UWFDM-750_alt2_IONMIX.pdf",
     "http://fti.neep.wisc.edu/fti.neep.wisc.edu/pdf/fdm750.pdf"),
]

for fname, url in TARGETS:
    out = os.path.join(BASE, fname)
    print("=== try:", url)
    try:
        req = urllib.request.Request(url, headers=HDRS)
        with urllib.request.urlopen(req, timeout=150) as r:
            print("   status:", r.status, "ctype:", r.headers.get("Content-Type"),
                  "clen:", r.headers.get("Content-Length"))
            data = r.read()
        print("   bytes:", len(data), "magic:", data[:8])
        if data[:4] != b"%PDF":
            print("   NOT A PDF, skip")
            continue
        with open(out, "wb") as f:
            f.write(data)
        print("   saved ->", out)
    except Exception as e:
        print("   FAIL:", type(e).__name__, e)

# Probe candidate GitHub orgs / repos
print("\n=== GitHub reachability probe ===")
PROBES = [
    "https://api.github.com/orgs/prism-codes/repos?per_page=100",
    "https://api.github.com/orgs/uwplasma/repos?per_page=100",
    "https://api.github.com/search/repositories?q=ionmix&per_page=50",
    "https://api.github.com/search/code?q=ionmix+extension:cn4",
    "https://api.github.com/search/repositories?q=opacplot2&per_page=20",
]
for u in PROBES:
    print("---", u)
    try:
        req = urllib.request.Request(u, headers={**HDRS, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
        print("    status OK, bytes:", len(body))
        print("    head:", body[:1200].replace("\n", " "))
    except Exception as e:
        print("    FAIL:", type(e).__name__, e)
