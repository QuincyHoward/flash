# -*- coding: utf-8 -*-
"""p8_fixorder: 修正三处编号乱序（幂等）。
  A. §15.12 : 15.12.5 与 15.12.4 互换 -> 15.12.4 在前
  B. §15.13 : 把 15.13 正文 + 15.13.1 排到 15.14 之前（当前 15.14 夹在中间）
  C. 附录 B : B.21 排到 B.22 之前
"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')

H_15125 = '#### 15.12.5 【勘误】第三轮对前两版的更正（本轮新增）'
H_15124 = '#### 15.12.4 【勘误】第一版曾推测但**不成立**的两项'
H_1513X = '#### 15.13.x 第三轮新增规约（R16–R19）'
H_15131 = '#### 15.13.1 第三轮新增规约（R16–R19）'
H_1514  = '### 15.14 第三轮新增：本轮解出与登记的条目'
H_1513B = '### 15.13 本章的解析器规约（可直接落地的清单）'
H_B22   = '### B.22 无扩展名多群不透明度表'
H_B21   = '### B.21 不同后缀名、同一内容：名实不符清单'
H_APPC  = '## 附录 C 实测样本索引'


def load():
    return open(DOC, encoding='utf-8').read()


def save(t):
    open(DOC, 'w', encoding='utf-8', newline='\n').write(t)


def move(text, start, end, before, before_from=None):
    """把 [start, end) 整块移到 before 之前。"""
    a = text.index(start)
    b = text.index(end, a)
    blk = text[a:b]
    rest = text[:a] + text[b:]
    i = rest.index(before, before_from or 0)
    return rest[:i] + blk + rest[i:]


log = []

# ── A. §15.12 互换 ───────────────────────────────────────────
t = load()
if H_15125 in t and H_15124 in t and t.index(H_15125) < t.index(H_15124):
    end = H_1513X if H_1513X in t else H_1514
    t = move(t, H_15124, end, H_15125)
    save(t)
    log.append('A: 15.12.4 moved before 15.12.5')
else:
    log.append('A: already ok / anchors missing')

# ── B. §15.13 正文 + 15.13.1 排到 15.14 前 ───────────────────
t = load()
if H_1513X in t:
    t = t.replace(H_1513X, H_15131, 1)
    save(t)
    log.append('B1: 15.13.x -> 15.13.1')
else:
    log.append('B1: 15.13.1 already renamed')

t = load()
if H_1513B in t and H_15131 in t and t.index(H_1513B) > t.index(H_15131):
    a = t.index(H_1513B)
    b = t.index('### 本章实测锚点', a)
    blk = t[a:b]
    rest = t[:a] + t[b:]
    i = rest.index(H_15131)
    t = rest[:i] + blk + rest[i:]
    save(t)
    log.append('B2: 15.13 body moved before 15.13.1')
else:
    log.append('B2: already ok / anchors missing')

# ── C. 附录 B: B.21 排到 B.22 前 ─────────────────────────────
t = load()
if H_B21 in t and H_B22 in t and t.index(H_B21) > t.index(H_B22):
    a = t.index(H_B21)
    b = t.index(H_APPC, a)
    blk = t[a:b]
    rest = t[:a] + t[b:]
    i = rest.index(H_B22)
    t = rest[:i] + blk + rest[i:]
    save(t)
    log.append('C: B.21 moved before B.22')
else:
    log.append('C: already ok / anchors missing')

print('\n'.join(log))
print('size =', len(load()))

# ── 验证 ─────────────────────────────────────────────────────
import re
L = load().split('\n')
print()
print('=== §15.12+ 顺序 ===')
started = False
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.12\b', l):
        started = True
    if started and re.match(r'^#{1,4}\s', l):
        tag = l[:70]
        print('%6d  %s' % (i + 1, tag))
    if l.startswith('# 附录'):
        break
print()
print('=== 附录 B.20+ 顺序 ===')
for i, l in enumerate(L):
    if re.match(r'^### B\.(1[89]|2[0-9])\b', l):
        print('%6d  %s' % (i + 1, l[:70]))
