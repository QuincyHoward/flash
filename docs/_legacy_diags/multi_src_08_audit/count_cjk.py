import sys, os

p = sys.argv[1]
with open(p, 'rb') as f:
    raw = f.read()
try:
    s = raw.decode('utf-8')
except Exception as e:
    s = raw.decode('gbk', errors='replace')
cjk = sum(1 for ch in s if '\u4e00' <= ch <= '\u9fff')
lines = s.count('\n') + (0 if s.endswith('\n') else 1)
nchars = len(s)
print("chars=%d / CJK=%d / lines=%d" % (nchars, cjk, lines))
