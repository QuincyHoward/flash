# -*- coding: utf-8 -*-
"""收尾核查修正：
 - L514 / L1020 / L6198 三处仍称 .feos 为 4x15
 - L9222 表头列数（4 -> 6/8 混排）与 L9950「记录序」行的竖线转义
"""
import io

P = r'src/multi_docs/MultiEOSOP格式说明.md'
d = io.open(P, encoding='utf-8').read()
n0 = len(d)
log = []

def rep(old, new, name):
    global d
    c = d.count(old)
    assert c == 1, '%s: count=%d' % (name, c)
    d = d.replace(old, new, 1)
    log.append('%s ok (%+d)' % (name, len(new) - len(old)))

# L514 数据血缘图的 FEOS 行
rep(u'\u2502 FEOS / SHOWEOS \u2502\u2500\u2500\u2500 Al.feos\uff084\u00d715 \u539f\u751f\uff09\u2500\u2500\u2500\u2500\u2500\u2192  F3',
    u'\u2502 FEOS / SHOWEOS \u2502\u2500\u2500\u2500 Al.feos\uff0810\u00d715 \u539f\u751f\uff09\u2500\u2500\u2500\u2500\u2192  F3',
    'L514')

# L1020 分派顺序表陷阱列
rep(u'| 3 | \u5339\u914d\u987a\u5e8f\u5fc5\u987b\u4e3a `hyades` \u2192 `.301/.304/.305` \u2192 `.feos` \u2192 \u9ed8\u8ba4 | \u6309\u4efb\u610f\u987a\u5e8f | `Al.feos.301` \u540c\u65f6\u542b `.feos` \u4e0e `.301`\uff1b\u82e5 `.feos` \u5148\u5339\u914d\uff0c4\u00d715 \u5207\u5206\u6574\u4efd\u6587\u4ef6\u5931\u8d25 |',
    u'| 3 | \u5339\u914d\u987a\u5e8f\u5fc5\u987b\u4e3a `hyades` \u2192 `.301/.304/.305` \u2192 `.feos` \u2192 \u9ed8\u8ba4 | \u6309\u4efb\u610f\u987a\u5e8f | `Al.feos.301` \u540c\u65f6\u542b `.feos` \u4e0e `.301`\uff1b\u82e5 `.feos` \u5148\u5339\u914d\uff0c\u6309 **10\u00d715** \u5207\u5206\u6574\u4efd\u6587\u4ef6\u5931\u8d25 |',
    'L1020')

# L6198 10.1 推荐路径
rep(u'\u5373**\u63a8\u8350\u8def\u5f84\u662f `.feos` \u539f\u751f 4\u00d715**\uff08\u4fe1\u606f\u6700\u5b8c\u6574\uff09\uff0c',
    u'\u5373**\u63a8\u8350\u8def\u5f84\u662f `.feos` \u539f\u751f 10\u00d715**\uff08\u4fe1\u606f\u6700\u5b8c\u6574\uff09\uff0c',
    'L6198')

# L9222 表头：该表实际有 6 列（后缀/数量/判定/判定依据 是 4，
# 但数据行含额外竖线把 判定 拆开）——先看数据行真实列数，改为 4 列且把内嵌竖线转义
# （此处保守：只修「记录序」行的内嵌竖线，它是真正的格式破坏）
rep(u'| **\u8bb0\u5f55\u5e8f** | **`\u8868\u5934(4) | r[nr] | de[ne] | e0[nr] | P[ne\u00b7nr] | T[ne\u00b7nr]`** |',
    u'| **\u8bb0\u5f55\u5e8f** | **\u8868\u5934(4) \u2192 r[nr] \u2192 de[ne] \u2192 e0[nr] \u2192 P[ne\u00b7nr] \u2192 T[ne\u00b7nr]** |',
    'L9950-pipe')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (%+d)' % (n0, len(d), len(d) - n0))
