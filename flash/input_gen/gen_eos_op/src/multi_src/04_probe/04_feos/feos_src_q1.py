# -*- coding: utf-8 -*-
# feos_src_q1.py -- Q1: dump .feos headers and decompose into 15-char fields
import glob, os, sys

BASE = 'src/Multi1D++Portable20241128/matter++/'


def read_lines(p):
    with open(p, 'rb') as f:
        raw = f.read()
    # CRLF-aware
    parts = raw.split(b'\r\n')
    if len(parts) == 1:
        parts = raw.split(b'\n')
    return [x for x in parts if x]


def show_feos_header(p, nhead=2):
    try:
        lines = read_lines(p)
    except Exception as e:
        print('  ERR', p, e)
        return None
    print('=' * 8, p, '(%d B)' % os.path.getsize(p))
    rows = []
    for i in range(min(nhead, len(lines))):
        L = lines[i]
        fields = []
        for j in range(0, len(L) - 14, 15):
            fields.append(L[j:j + 15].decode('ascii', 'replace'))
        print('  line%d len=%d nfields=%d' % (i, len(L), len(fields)))
        for k, v in enumerate(fields):
            print('     [%2d] %r' % (k, v))
        rows.append(fields)
    return rows


def main():
    files = sorted(glob.glob(BASE + '**/*.feos', recursive=True))
    print('# total .feos files:', len(files))
    # focus: Al variants and any with soft-sphere zeros
    targets = [f for f in files if os.path.basename(f).startswith(('Al', 'AL'))]
    print('\n# ---- Al* targets:', len(targets))
    for f in targets:
        show_feos_header(f)

    print('\n# ---- all headers, line0 field[0..2] summary')
    for f in files:
        try:
            lines = read_lines(f)
        except Exception:
            continue
        L0 = lines[0]
        f0 = [L0[j:j + 15].decode('ascii', 'replace').strip()
              for j in range(0, len(L0) - 14, 15)]
        L1 = lines[1]
        f1 = [L1[j:j + 15].decode('ascii', 'replace').strip()
              for j in range(0, len(L1) - 14, 15)]
        print('%-58s | L0:%s' % (os.path.relpath(f, BASE), ','.join(f0[:4])))
        print('%-58s | L1:%s' % ('', ','.join(f1)))


main()
