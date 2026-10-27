# -*- coding: utf-8 -*-
"""Self-check: confirm all deliverables exist and report their sizes."""
import os, io, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
EXPECT = [
    'eos_readers.py', 'cross_validation.md', 'xval_s1_inventory.py',
    'xval_s1_inventory.txt', 'xval_s1b_files.py', 'xval_s1b_files.txt',
    'xval_s1c_names.py', 'xval_s1c_names.txt', 'xval_s2b_proof.py',
    'xval_s2b_proof.txt', 'xval_s6.py', 'xval_s6.txt', 'xval_s11.py',
    'xval_s11.txt', 'xval_s13.py', 'xval_s13.txt', 'xval_s14.py',
    'xval_s14.txt', 'run_capture.py',
]
lines = []
for f in EXPECT:
    p = os.path.join(HERE, f)
    if os.path.exists(p):
        sz = os.path.getsize(p)
        with open(p, 'rb') as fh:
            h = hashlib.md5(fh.read()).hexdigest()[:10]
        lines.append("OK    %-28s %9d bytes  md5=%s" % (f, sz, h))
    else:
        lines.append("MISS  %-28s" % f)
out = os.path.join(HERE, 'DELIVERABLES.txt')
with io.open(out, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print('\n'.join(lines))
print("WROTE", out)
