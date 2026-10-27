# -*- coding: utf-8 -*-
"""Download FEOS.tar.gz from Mendeley Data and extract it."""
import os, sys, json, urllib.request, tarfile, traceback

BASE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
os.makedirs(BASE, exist_ok=True)
print("BASE =", BASE)

URLS = [
    "https://data.mendeley.com/public-api/zip/6vjsv6v48p/download/1",
    "https://data.mendeley.com/public-files/datasets/6vjsv6v48p/files/6vjsv6v48p/download/1",
    "https://data.mendeley.com/datasets/6vjsv6v48p/1",
]

HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "*/*",
}

out = os.path.join(BASE, "FEOS.tar.gz")
got = False
for u in URLS:
    print("=== try:", u)
    try:
        req = urllib.request.Request(u, headers=HDRS)
        with urllib.request.urlopen(req, timeout=120) as r:
            print("   status:", r.status, "ctype:", r.headers.get("Content-Type"),
                  "clen:", r.headers.get("Content-Length"))
            data = r.read()
        print("   bytes:", len(data), "head:", data[:16])
        if len(data) < 200:
            print("   too small, skip:", data[:200])
            continue
        with open(out, "wb") as f:
            f.write(data)
        got = True
        print("   saved ->", out)
        break
    except Exception as e:
        print("   FAIL:", type(e).__name__, e)
        traceback.print_exc()

if not got:
    print("ALL URLS FAILED")
    sys.exit(1)

# detect gzip/tar
with open(out, "rb") as f:
    magic = f.read(4)
print("magic:", magic)

extract_dir = os.path.join(BASE, "FEOS_extract")
os.makedirs(extract_dir, exist_ok=True)

# try tarfile first
try:
    with tarfile.open(out, "r:*") as tf:
        names = tf.getnames()
        print("tar members:", len(names))
        for n in names[:50]:
            print("   ", n)
        tf.extractall(extract_dir)
    print("tar extract OK ->", extract_dir)
except Exception as e:
    print("tarfile FAIL:", type(e).__name__, e)
    # maybe it's a zip wrapper
    try:
        import zipfile
        with zipfile.ZipFile(out) as zf:
            print("zip members:", zf.namelist()[:50])
            zf.extractall(extract_dir)
        print("zip extract OK")
        # recurse: find inner tar
        for root, dirs, files in os.walk(extract_dir):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    with tarfile.open(p, "r:*") as tf:
                        print("inner tar:", p, len(tf.getnames()))
                        tf.extractall(os.path.join(extract_dir, "inner"))
                except Exception:
                    pass
    except Exception as e2:
        print("zip FAIL:", type(e2).__name__, e2)

# full tree listing
print("\n=== TREE ===")
for root, dirs, files in os.walk(extract_dir):
    rel = os.path.relpath(root, extract_dir)
    for fn in sorted(files):
        p = os.path.join(root, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            sz = -1
        print(f"{sz:>10}  {os.path.join(rel, fn)}")
