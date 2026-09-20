# -*- coding: utf-8 -*-
"""Stage 1b: inspect concrete files for the shortlisted materials: sizes, first/last bytes, line widths."""
import os, io, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xval_s1b_files.txt')

TARGETS = ['mat_Ce', 'Ta2O5', 'mat_Au-1.0', 'mat_C-1.0', 'mat_Ba', 'mat_Ti', 'mat_He', 'mat_B']

lines = []
def P(s=''):
    lines.append(str(s))

def peek(path, nbytes=400):
    with open(path, 'rb') as fh:
        head = fh.read(nbytes)
        fh.seek(0, 2)
        sz = fh.tell()
        tail = b''
        if sz > nbytes:
            fh.seek(max(0, sz - nbytes))
            tail = fh.read()
    return sz, head, tail

def linewidths(path, maxlines=6):
    ws = []
    with open(path, 'rb') as fh:
        for i, ln in enumerate(fh):
            if i >= maxlines: break
            raw = ln.rstrip(b'\r\n')
            ws.append(len(raw))
    return ws

for m in TARGETS:
    d = os.path.join(MATTER, m)
    P("=" * 100)
    P("MATERIAL DIR: %s   (exists=%s)" % (m, os.path.isdir(d)))
    P("=" * 100)
    if not os.path.isdir(d):
        continue
    entries = []
    for root, dirs, files in os.walk(d):
        for f in sorted(files):
            entries.append(os.path.join(root, f))
    for path in entries:
        rel = os.path.relpath(path, d)
        try:
            sz, head, tail = peek(path, 300)
        except Exception as e:
            P("  %-40s ERROR %s" % (rel, e)); continue
        try:
            ws = linewidths(path, 4)
        except Exception:
            ws = []
        # detect text vs binary
        binary = b'\x00' in head
        P("")
        P("  FILE: %s   size=%d bytes  linewidths(first4)=%s  binary=%s" % (rel, sz, ws, binary))
        try:
            txt = head.decode('utf-8', 'replace').replace('\r', '<CR>')
            P("    HEAD: " + txt[:260].replace('\n', '\n          '))
        except Exception as e:
            P("    HEAD undecodable: %s" % e)
        try:
            txt2 = tail.decode('utf-8', 'replace').replace('\r', '<CR>')
            P("    TAIL: " + txt2[-200:].replace('\n', '\n          '))
        except Exception:
            pass

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
