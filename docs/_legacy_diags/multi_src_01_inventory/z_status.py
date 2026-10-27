# -*- coding: utf-8 -*-
"""检查两个代理的交付物是否落盘 + tmp 最新文件（按 mtime）。"""
import os, time

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')

EXPECT = [
    r'src\multi_src\04_probe\04_feos\feos_src_adjudication.md',
    r'src\multi_src\05_cross_validation\coverage_matrix.tsv',
    r'src\multi_src\05_cross_validation\coverage_summary.md',
    r'src\multi_src\05_cross_validation\cross_validation_round2.md',
]
print('=== 期望交付物 ===')
for e in EXPECT:
    p = os.path.join(ROOT, e)
    if os.path.exists(p):
        print('  OK   %-58s %9d B  %s' % (os.path.basename(p), os.path.getsize(p),
              time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p)))))
    else:
        print('  MISS %s' % e)

print()
print('=== .workbuddy/tmp 最近 30 分钟修改的文件 ===')
now = time.time()
recent = []
for name in os.listdir(TMP):
    p = os.path.join(TMP, name)
    if os.path.isdir(p):
        continue
    try:
        m = os.path.getmtime(p)
    except OSError:
        continue
    if now - m < 3600:
        recent.append((m, name, os.path.getsize(p)))
for m, n, s in sorted(recent, reverse=True)[:40]:
    print('  %s  %-46s %9d B' % (time.strftime('%H:%M:%S', time.localtime(m)), n, s))

print()
print('=== tmp 中的代理新产物（feos_src*/cov_*/xv2_*/DEBUG_*/RECHECK_*）===')
for name in sorted(os.listdir(TMP)):
    if any(name.startswith(k) for k in
           ('feos_src', 'cov_', 'xv2_', 'DEBUG_', 'RECHECK_', 'coverage_', 'xv_round2')):
        p = os.path.join(TMP, name)
        if os.path.isfile(p):
            print('  %-52s %9d B  %s' % (name, os.path.getsize(p),
                  time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p)))))
