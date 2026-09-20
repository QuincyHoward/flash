# -*- coding: utf-8 -*-
"""精确定位每群结构：打印群边界处原文 + 30字符行间距分布。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')


def analyze(path, tag):
    raw = open(path, 'rb').read().replace(b'\r\n', b'\n')
    Ln = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    L30 = [i for i, l in enumerate(Ln) if len(l) == 30]
    print('=' * 78)
    print(tag, ' 非空行=%d  群数(30字符行)=%d' % (len(Ln), len(L30)))
    d = [L30[i + 1] - L30[i] for i in range(len(L30) - 1)]
    from collections import Counter
    print('  群间距分布:', dict(Counter(d)))
    hdr = Ln[0]
    print('  头部: %r' % hdr[:80])
    print('  头字段: %s' % [hdr[j:j+15].strip() for j in range(0, 60, 15)])
    # 第 1 群边界
    print('  --- 第 1 群 (索引 0..%d) 尾部 ---' % d[0])
    for i in range(max(0, d[0] - 6), min(d[0] + 3, len(Ln))):
        print('   %4d [%3d] %r' % (i, len(Ln[i]), Ln[i][:80]))
    # 第 2 群边界
    if len(L30) > 2:
        print('  --- 第 2 群边界 (索引 %d..%d) ---' % (L30[1] - 3, L30[1] + 2))
        for i in range(L30[1] - 3, min(L30[1] + 3, len(Ln))):
            print('   %4d [%3d] %r' % (i, len(Ln[i]), Ln[i][:80]))
    print('  --- 文件末尾 6 行 ---')
    for i in range(max(0, len(Ln) - 6), len(Ln)):
        print('   %4d [%3d] %r' % (i, len(Ln[i]), Ln[i][:80]))
    print()


analyze(os.path.join(M, 'mat_Ce', 'Ce.PLANCK'), 'mat_Ce/Ce.PLANCK')
analyze(os.path.join(M, 'mat_Au-1.0', 'AU_op03p'), 'mat_Au-1.0/AU_op03p')
analyze(os.path.join(M, 'mat_Be-1.0', 'opbe'), 'mat_Be-1.0/opbe')
analyze(os.path.join(M, 'mat_Gd', 'Gd100PLANCK'), 'mat_Gd/Gd100PLANCK')
