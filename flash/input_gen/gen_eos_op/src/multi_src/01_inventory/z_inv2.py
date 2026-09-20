# -*- coding: utf-8 -*-
"""紧凑盘点：只列出顶层文件（名+字节），写文件供 Read。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')
OUT = os.path.join(TMP, 'z_inv_list.txt')

lines = []
dirs, files = [], []
for name in sorted(os.listdir(TMP)):
    p = os.path.join(TMP, name)
    if os.path.isdir(p):
        n = sum(len(f) for _, _, f in os.walk(p))
        sz = sum(os.path.getsize(os.path.join(dp, f))
                 for dp, _, fn in os.walk(p) for f in fn)
        dirs.append((name, n, sz))
    else:
        files.append((name, os.path.getsize(p)))

lines.append('### TOP-LEVEL DIRECTORIES (%d)' % len(dirs))
for n, c, s in dirs:
    lines.append('D %-40s %5df %10dB' % (n, c, s))
lines.append('')
lines.append('### TOP-LEVEL FILES (%d)' % len(files))
tot = 0
for n, s in files:
    tot += s
    lines.append('F %-44s %10dB' % (n, s))
lines.append('')
lines.append('files total bytes = %d' % tot)
lines.append('')
lines.append('### SUBDIR TREES')
for n, c, s in dirs:
    lines.append('# ' + n)
    base = os.path.join(TMP, n)
    for dp, dn, fn in os.walk(base):
        rel = os.path.relpath(dp, TMP)
        lines.append('   @ %s/  (%d files)' % (rel, len(fn)))
        for f in sorted(fn)[:60]:
            lines.append('       %-50s %9d' % (f, os.path.getsize(os.path.join(dp, f))))
        if len(fn) > 60:
            lines.append('       ... (+%d more)' % (len(fn) - 60))
    lines.append('')

open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('written', OUT, len(lines), 'lines')
