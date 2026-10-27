# -*- coding: utf-8 -*-
"""Fix section-name references that actually point at body text lines.

The audit (see 15.12.3) flagged places where a *body sentence* inside the docx
manual was cited with section-heading syntax  §"...".  Render them as
   `path` 手册正文：“...”
so a heading can be told apart from a quoted line.

NOTE: the offending citations use ASCII straight quotes (U+0022), not the
typographic curly quotes the rest of the document prefers.
"""
import io
import os

P = os.path.join('src', 'multi_docs', 'MultiEOSOP\u683c\u5f0f\u8bf4\u660e.md')
t = io.open(P, encoding='utf-8').read()
before = len(t.encode('utf-8'))
report = []

Q = '"'          # ASCII straight quote, as found in the offending lines
LQ, RQ = '\u201c', '\u201d'   # typographic, for the replacement


def sub(old, new, label):
    n = t.count(old)
    report.append((n, label))
    return t.replace(old, new)


MAN = 'doc/MULTI\u4f7f\u7528\u7684SESAME\u6570\u636e\u6587\u4ef6\u683c\u5f0f.docx'
S1 = '[S-L1] ' + MAN
BODY = '` \u624b\u518c\u6b63\u6587\uff1a'   # ` 手册正文：

# --- L2372 : quoted line "参数单位制分别为(cgs)" --------------------------
t = sub('`' + S1 + ' \u00a7' + Q + '\u53c2\u6570\u5355\u4f4d\u5236\u5206\u522b\u4e3a(cgs)' + Q + '`\uff1a',
        '`' + S1 + '`' + BODY + LQ + '\u53c2\u6570\u5355\u4f4d\u5236\u5206\u522b\u4e3a(cgs)' + RQ + '\uff1a',
        'L2372 body-cite units')

# --- L2527 : quoted line "密度和温度为指数坐标" ---------------------------
t = sub('`' + S1 + ' \u00a7' + Q + '\u5bc6\u5ea6\u548c\u6e29\u5ea6\u4e3a\u6307\u6570\u5750\u6807' + Q + '`',
        '`' + S1 + '`' + BODY + LQ + '\u5bc6\u5ea6\u548c\u6e29\u5ea6\u4e3a\u6307\u6570\u5750\u6807' + RQ,
        'L2527 body-cite rho range')

# --- L2705 : quoted line "对定标公式" -------------------------------------
t = sub('`' + MAN + ' \u00a7' + Q + '\u5bf9\u5b9a\u6807\u516c\u5f0f' + Q + '`\uff09\uff1a',
        '`' + MAN + '`' + BODY + LQ + '\u5bf9\u5b9a\u6807\u516c\u5f0f' + RQ + '\uff09\uff1a',
        'L2705 body-cite scaling formula')

# --- L2881 : already half-edited by an earlier shell attempt ---------------
t = sub('`' + MAN + ' \u00a7' + Q + '\u7b2c\u4e00\u884c\u7b2c\u4e8c\u5217' + Q + '` \u624b\u518c\u6b63\u6587\uff1a'
        + LQ + '\u7b2c\u4e00\u884c\u7b2c\u4e8c\u5217' + RQ + ' \u7ed9\u51fa\u8868\u683c\uff1a',
        '`' + MAN + '`' + BODY + LQ + '\u7b2c\u4e00\u884c\u7b2c\u4e8c\u5217' + RQ + ' \u7ed9\u51fa\u8868\u683c\uff1a',
        'L2881 body-cite first-row-2nd-col (dedup)')

io.open(P, 'w', encoding='utf-8', newline='').write(t)
after = len(t.encode('utf-8'))
print('\n'.join('%-4d %s' % (n, lb) for n, lb in report))
print('bytes %d -> %d' % (before, after))
