import re, os

p = 'src/multi_docs/MultiEOSOP格式说明.md'
t = open(p, encoding='utf-8').read()
lines = t.split('\n')

# Locate insertion points
for pat in [r'^### 14\.\d+', r'^## 第14章', r'^## 第15章', r'^### 15\.\d+',
            r'^## 附录 A', r'^### B\.2\d', r'^### B\.1\d', r'^## 附录 B']:
    print('--- %s ---' % pat)
    for i, l in enumerate(lines):
        if re.match(pat, l):
            print('  L%-6d %s' % (i + 1, l[:100]))
