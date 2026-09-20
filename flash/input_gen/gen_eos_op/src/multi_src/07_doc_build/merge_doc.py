#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Merge the per-chapter Markdown parts into the single deliverable
`src/multi_docs/MultiEOSOP格式说明.md`, in the canonical chapter order.

Usage:
    python merge_doc.py [--out <path>] [--parts <dir>]

Prints a per-part table (chars / CJK han / lines) and the grand total,
plus a gate check against the 80,000-han minimum.
"""
import argparse
import io
import os
import sys

# Canonical order of the parts written by the writing agents.
ORDER = [
    '00_front.md',
    '10_ch0.md',
    '11_ch1.md',
    '12_ch2.md',
    '13_ch3.md',
    '14_ch4.md',
    '15_ch5.md',
    '16_ch6.md',
    '17_ch7.md',
    '18_ch8.md',
    '19_ch9.md',
    '20_ch10.md',
    '21_ch11.md',
    '22_ch12.md',
    '23_ch13.md',
    '24_ch14.md',
    '30_appendix.md',
]

CJK_RANGES = (('\u4e00', '\u9fff'), ('\u3400', '\u4dbf'), ('\uf900', '\ufaff'))


def han(txt):
    n = 0
    for c in txt:
        for lo, hi in CJK_RANGES:
            if lo <= c <= hi:
                n += 1
                break
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='src/multi_docs/MultiEOSOP格式说明.md')
    ap.add_argument('--parts', default='.workbuddy/tmp/multi_doc_parts')
    ap.add_argument('--list', action='store_true',
                    help='only list parts that currently exist, in order')
    args = ap.parse_args()

    present, missing = [], []
    for name in ORDER:
        p = os.path.join(args.parts, name)
        (present if os.path.exists(p) else missing).append((name, p))

    if args.list:
        for name, p in present:
            print('PRESENT %s' % name)
        for name, p in missing:
            print('MISSING %s' % name)
        return 0

    if missing:
        print('!! %d part(s) missing, refusing to merge:' % len(missing))
        for name, p in missing:
            print('   %s' % name)
        return 2

    tc = th = tl = 0
    print('%-18s %9s %9s %8s' % ('part', 'chars', 'CJK', 'lines'))
    print('-' * 48)
    buf = []
    for name, p in present:
        with io.open(p, 'r', encoding='utf-8', errors='replace') as fh:
            txt = fh.read()
        c, h, ln = len(txt), han(txt), txt.count('\n') + 1
        tc += c
        th += h
        tl += ln
        print('%-18s %9d %9d %8d' % (name, c, h, ln))
        buf.append(txt.rstrip('\n'))
    print('-' * 48)
    print('%-18s %9d %9d %8d' % ('TOTAL', tc, th, tl))

    merged = '\n\n---\n\n'.join(buf) + '\n'
    d = os.path.dirname(args.out)
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(merged)

    mh = han(merged)
    print()
    print('wrote %s' % args.out)
    print('  chars=%d  CJK=%d  lines=%d' % (len(merged), mh, merged.count('\n') + 1))
    gate = 80000
    if mh >= gate:
        print('  GATE PASS: %d >= %d  (margin +%d)' % (mh, gate, mh - gate))
        return 0
    print('  GATE FAIL: %d < %d  (short by %d)' % (mh, gate, gate - mh))
    return 1


if __name__ == '__main__':
    sys.exit(main())
