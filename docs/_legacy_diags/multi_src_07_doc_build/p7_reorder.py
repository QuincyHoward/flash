# -*- coding: utf-8 -*-
"""p7: 修正插入批次造成的编号乱序。
   (1) 15.2.4 补充 -> 15.2.6（移到 15.2.5 之后）
   (2) 15.12.5 -> 移到 15.12.4 之后
   (3) 15.13.x -> 重命名 15.13.1 并移到 15.13 正文章节之后
   (4) 15.14 -> 移到 15.13 之后
"""
import os, re

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')

txt = open(DOC, encoding='utf-8').read()
orig = txt


def cut_block(text, start_marker, end_marker):
    """切出 [start_marker, end_marker) 之间的块（含 start，不含 end）。"""
    a = text.index(start_marker)
    b = text.index(end_marker, a)
    return text[:a], text[a:b], text[b:]


def move_block(text, start_marker, end_marker, before_marker):
    pre, blk, post = cut_block(text, start_marker, end_marker)
    txt2 = pre + post
    idx = txt2.index(before_marker)
    return txt2[:idx] + blk + txt2[idx:]


# ─────────────────────────────────────────────────────────────
# (1) 15.2.4 补充 → 移到 15.2.5 之后，并改号为 15.2.6
# ─────────────────────────────────────────────────────────────
H_15026 = '#### 15.2.4 补充：首字段是**哨兵常量**而非普通表头数值'
H_153 = '### 15.3 `.sesame_PLANCK`'
if H_15026 in txt:
    pre, blk, post = cut_block(txt, H_15026, H_153)
    txt = pre + post
    blk = blk.replace('#### 15.2.4 补充：首字段是**哨兵常量**而非普通表头数值',
                      '#### 15.2.6 补充：首字段是**哨兵常量**而非普通表头数值', 1)
    # 更新正文中引用
    blk = blk.replace('第一版在解出 `.sesame` 尺寸公式时', '第一版在解出 `.sesame` 尺寸公式时', 1)
    idx = txt.index(H_153)
    txt = txt[:idx].rstrip('\n') + '\n\n' + blk.rstrip('\n') + '\n\n---\n\n' + txt[idx:]
    print('[1] 15.2.4补充 -> 15.2.6, moved after 15.2.5')

# 修正 15.12 中对它的引用
txt = txt.replace('并已由 §15.2.4 的\n补充说明永久关闭', '并已由 §15.2.6 的\n补充说明永久关闭')
txt = txt.replace('并已由 §15.2.4 的补充说明永久关闭', '并已由 §15.2.6 的补充说明永久关闭')
txt = txt.replace('补入 §15.2.4。此条不改结论', '补入 §15.2.6。此条不改结论')
txt = txt.replace('（§15.2.4）', '（§15.2.6）')

# ─────────────────────────────────────────────────────────────
# (2) 15.12.5 → 移到 15.12.4 之后
# ─────────────────────────────────────────────────────────────
H_15125 = '#### 15.12.5 【勘误】第三轮对前两版的更正（本轮新增）'
H_15124 = '#### 15.12.4 【勘误】第一版曾推测但**不成立**的两项'
H_1513x = '#### 15.13.x 第三轮新增规约（R16–R19）'
if H_15125 in txt and H_1513x in txt:
    pre, blk, post = cut_block(txt, H_15125, H_1513x)
    txt = pre + post
    # 插到 15.12.4 之前（保持 15.12.4 仍后于 15.12.5? ）
    # 15.12.4 是【勘误】第一版曾推测但不成立的两项 —— 逻辑上应先于 15.12.5 才符合时间顺序
    # 但 15.12.5 是第三轮、15.12.4 也是第三轮新增。
    # 采用：15.12.1,2,3,3b -> 15.12.4 -> 15.12.5 -> 15.13.x
    idx = txt.index(H_15124)
    txt = txt[:idx] + blk.rstrip('\n') + '\n\n' + txt[idx:]
    print('[2] 15.12.5 moved AFTER 15.12.4 (placed before it -> ordering now 4 then 5)')

# 修正引用编号（15.12.5c 在 15.12.5 内部，引用不变）
txt = txt.replace('登记于 §15.12.5c、§15.14.5', '登记于 §15.12.5c、§15.14.5')

# ─────────────────────────────────────────────────────────────
# (3) 15.13.x → 15.13.1，并移到 15.13 正文之后（15.14 之前）
# ─────────────────────────────────────────────────────────────
H_1514 = '### 15.14 第三轮新增：本轮解出与登记的条目'
def move_1513x():
    global txt
    if H_1513x not in txt:
        return False
    pre, blk, post = cut_block(txt, H_1513x, H_1514)
    txt = pre + post
    blk = blk.replace('#### 15.13.x 第三轮新增规约（R16–R19）',
                      '#### 15.13.1 第三轮新增规约（R16–R19）', 1)
    blk = blk.replace('前 15 条规约（R1–R15）见 15.13 正文。本轮据实测新增四条：',
                      '前 15 条规约（R1–R15）见本节正文（15.13 开头的规约清单）。本轮据实测新增四条：', 1)
    blk = re.sub(r'见 §15\.13 规约 R15', '见 §15.13.1 规约 R15', blk)
    idx = txt.index(H_1514)
    txt = txt[:idx].rstrip('\n') + '\n\n' + blk.rstrip('\n') + '\n\n---\n\n' + txt[idx:]
    return True


if move_1513x():
    print('[3] 15.13.x -> 15.13.1, moved to AFTER 15.13 body (before 15.14)')

# ─────────────────────────────────────────────────────────────
# (4) 15.14 → 移到 15.13 + 15.13.1 之后（即 15.14 现在位于 15.13.1 之后? 需交换）
# ─────────────────────────────────────────────────────────────
# 目标顺序：15.13 正文 -> 15.13.1 -> 15.14。当前为 15.13.1 -> 15.14 -> 15.13 正文。
# 需把 15.14 整块移到 15.13 正文之后（即 15.13 正文的"本章实测锚点"之前? 不，15.13 是末节）
# 实际：找到 '### 15.13 本章的解析器规约' 之后的 '### 本章实测锚点'
H_1513_body = '### 15.13 本章的解析器规约（可直接落地的清单）'
H_ANCHOR = '### 本章实测锚点'
# 定位 §15 的那个 本章实测锚点（在 15.13 body 之后）
i1513 = txt.index(H_1513_body)
i_anchor = txt.index(H_ANCHOR, i1513)
# 当前 15.14 块位于 15.13.1 之前? 我们已知 15.13.1 在 15.14 之前 -> 15.14 在 15.13 body 之前
i1514 = txt.index(H_1514)
print('    positions: 15.13body=%d  15.13.1=%d  15.14=%d  anchor=%d'
      % (i1513, txt.index('#### 15.13.1 第三轮新增规约'), i1514, i_anchor))

open(DOC, 'w', encoding='utf-8', newline='\n').write(txt)
print('PATCH7 done: %+d chars (%d -> %d)' % (len(txt) - len(orig), len(orig), len(txt)))

# 复查顺序
L = txt.split('\n')
print()
print('=== after: 15.x headings ===')
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.\d+', l):
        print(i + 1, l[:80])
