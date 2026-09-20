# -*- coding: utf-8 -*-
"""盘点两处 tmp 目录：C:\\Users\\Administrator\\.workbuddy\\tmp 与工作区 .workbuddy/tmp"""
import os

CANDS = [
    r'C:\Users\Administrator\.workbuddy\tmp',
    r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp',
]

for d in CANDS:
    print('=' * 78)
    print('DIR:', d)
    print('exists:', os.path.isdir(d))
    if not os.path.isdir(d):
        print()
        continue
    entries = sorted(os.listdir(d))
    files = [e for e in entries if os.path.isfile(os.path.join(d, e))]
    dirs = [e for e in entries if os.path.isdir(os.path.join(d, e))]
    print('files: %d   subdirs: %d' % (len(files), len(dirs)))
    if dirs:
        print('  subdirs:', dirs[:40])
    print('-' * 78)
    tot = 0
    for f in files:
        p = os.path.join(d, f)
        sz = os.path.getsize(p)
        tot += sz
        print('  %-52s %12d' % (f, sz))
    print('  TOTAL BYTES:', tot)
    print()
