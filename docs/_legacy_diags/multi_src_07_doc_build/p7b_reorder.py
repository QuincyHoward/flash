# -*- coding: utf-8 -*-
"""p7b: 修正编号乱序（幂等、分步、每步独立落盘）。

目标顺序（§15 内）：
  15.2.1 15.2.2 15.2.3 15.2.4 15.2.5 15.2.6(原"15.2.4 补充")
  15.12.1 15.12.2 15.12.3 15.12.3b 15.12.4 15.12.5
  15.13 (正文) 15.13.1(原"15.13.x")  15.14(含 15.14.1-15.14.9)
"""
import os, re, sys

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')


def load():
    return open(DOC, encoding='utf-8').read()


def save(t):
    open(DOC, 'w', encoding='utf-8', newline='\n').write(t)


def move(text, start, end, before):
    """把 [start, end) 块移到 before 之前。返回新文本。
       end 可为 None 表示到文末。"""
    a = text.index(start)
    b = text.index(end, a) if end else len(text)
    blk = text[a:b]
    rest = text[:a] + text[b:]
    i = rest.index(before)
    return rest[:i] + blk + rest[i:]


def renumber(text):
    """对全文做编号/引用重命名。"""
    return text


# ══════════════════════════════════════════════════════════════
# STEP 1: 15.2.4 补充 -> 15.2.6，移到 15.2.5 之后（即 15.3 之前）
# ══════════════════════════════════════════════════════════════
H_A = '#### 15.2.4 补充：首字段是**哨兵常量**而非普通表头数值'
H_153 = '### 15.3 `.sesame_PLANCK`'
t = load()
if H_A in t and t.index(H_A) < t.index(H_153):
    t = move(t, H_A, H_153, H_153)
    t = t.replace(H_A, '#### 15.2.6 补充：首字段是**哨兵常量**而非普通表头数值', 1)
    save(t)
    print('[1] 15.2.4补充 -> 15.2.6  (moved after 15.2.5)')
else:
    print('[1] already done or anchor missing')

# ══════════════════════════════════════════════════════════════
# STEP 2: 引用修正 15.2.4 -> 15.2.6
# ══════════════════════════════════════════════════════════════
t = load()
before = t
t = t.replace('补入 §15.2.4。', '补入 §15.2.6。')
t = t.replace('（§15.2.4）', '（§15.2.6）')
t = t.replace('并已由 §15.2.4 的', '并已由 §15.2.6 的')
t = t.replace('见 15.2.4）', '见 15.2.6）')
t = t.replace('15.2.3–15.2.5', '15.2.3–15.2.6')
if t != before:
    save(t)
    print('[2] refs 15.2.4 -> 15.2.6 updated')
else:
    print('[2] no ref change needed')

# ══════════════════════════════════════════════════════════════
# STEP 3: 15.12.5 移到 15.12.4 之前（使 15.12.4 -> 15.12.5 单调）
#        块区间 = [15.12.5, 15.13.x)
# ══════════════════════════════════════════════════════════════
H_15125 = '#### 15.12.5 【勘误】第三轮对前两版的更正（本轮新增）'
H_15124 = '#### 15.12.4 【勘误】第一版曾推测但**不成立**的两项'
H_1513X = '#### 15.13.x 第三轮新增规约（R16–R19）'
t = load()
if H_15125 in t and H_15124 in t:
    if t.index(H_15125) < t.index(H_15124):
        t = move(t, H_15125, H_1513X, H_15124)
        save(t)
        print('[3] 15.12.5 moved AFTER 15.12.4')
    else:
        print('[3] already ordered')
else:
    print('[3] anchor missing', H_15125 in t, H_15124 in t)

# ══════════════════════════════════════════════════════════════
# STEP 4: 15.13.x -> 15.13.1，并移到 15.14 之前（即 15.13 正文之后）
#        块区间 = [15.13.x, 15.14)
# ══════════════════════════════════════════════════════════════
H_1514 = '### 15.14 第三轮新增：本轮解出与登记的条目'
t = load()
if H_1513X in t and H_1514 in t:
    if t.index(H_1513X) < t.index(H_1514):
        t = move(t, H_1513X, H_1514, H_1514)
        t = t.replace(H_1513X, '#### 15.13.1 第三轮新增规约（R16–R19）', 1)
        t = t.replace('前 15 条规约（R1–R15）见 15.13 正文。本轮据实测新增四条：',
                      '前 15 条规约（R1–R15）见本节正文开头的规约清单。本轮据实测新增四条：', 1)
        t = t.replace('见 §15.13 规约 R15', '见 §15.13.1 规约 R15')
        save(t)
        print('[4] 15.13.x -> 15.13.1  (moved after 15.13 body)')
    else:
        print('[4] already ordered')
else:
    print('[4] anchor missing', H_1513X in t, H_1514 in t)

print('done. size =', len(load()))
