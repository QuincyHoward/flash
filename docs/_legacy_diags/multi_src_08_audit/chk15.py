import re, os
p = r'src/multi_docs/MultiEOSOP格式说明.md'
txt = open(p, encoding='utf-8').read()
print('size', len(txt))
L = txt.split('\n')
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.\d+', l):
        print(i + 1, l[:80])
