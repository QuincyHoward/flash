# -*- coding: utf-8 -*-
"""表号归位：把新增速查卡的非数字号 T59b..g / T64a / T64b
   改为顺序号 T65..T71（附录续编，接在 T64 之后），并同步前置-2.4 的编号说明。"""
import io

P = r'src/multi_docs/MultiEOSOP格式说明.md'
d = io.open(P, encoding='utf-8').read()
n0 = len(d)

MAP = [
    ('T59b', 'T65'),   # B.16 .mexport
    ('T59c', 'T66'),   # B.17 .cst
    ('T59d', 'T67'),   # B.18 critical/isobaric
    ('T59e', 'T68'),   # B.19 ShowEOS 4gnuplot
    ('T59f', 'T69'),   # B.20 .sesame 变体
    ('T59g', 'T70'),   # B.21 名实不符
    ('T64a', 'T71'),   # F.2 已核验网络来源
    ('T64b', 'T72'),   # F.2 仍待核验
]
log = []
for old, new in MAP:
    c = d.count(old)
    assert c >= 1, '%s missing' % old
    d = d.replace(old, new)
    log.append('%s -> %s (%d)' % (old, new, c))

# 前置-2.4 编号说明：更新占用区间
OLD_NOTE = (u'- \u8868\u7f16\u53f7\uff1a\u6b63\u6587\uff08\u7b2c0\u201314\u7ae0\uff09\u4f7f\u7528 `T0`\u2013`T36`\uff1b'
            u'**\u9644\u5f55 A\u2013F \u7684 28 \u5f20\u5b9e\u4f53\u8868\u7eed\u7f16 `T37`\u2013`T64`**')
assert d.count(OLD_NOTE) == 1, 'note not found'
NEW_NOTE = (u'- \u8868\u7f16\u53f7\uff1a\u6b63\u6587\uff08\u7b2c0\u201315\u7ae0\uff09\u4f7f\u7528 `T0`\u2013`T36`\uff08\u5b9e\u5360 29 \u4e2a\u53f7\u4f4d\uff09\uff1b'
            u'**\u9644\u5f55 A\u2013F \u7684\u5b9e\u4f53\u8868\u7eed\u7f16 `T37`\u2013`T72`\uff08\u5b9e\u5360 36 \u4e2a\u53f7\u4f4d\uff09**')
d = d.replace(OLD_NOTE, NEW_NOTE, 1)
log.append('front-note updated')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (%+d)' % (n0, len(d), len(d) - n0))
