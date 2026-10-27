# -*- coding: utf-8 -*-
"""整体核查：
 (1) 代码围栏配对
 (2) 表号连续性 / 重号
 (3) 内部章节引用是否存在（如 "10.6"、"15.2.4"）
 (4) 表格列数一致性（每张表的分隔行与数据行列数）
 (5) 已关闭的 [S-UNK] 是否仍有残留断言
 (6) 4x15 断言 .feos 的残留
"""
import io, re, collections

P = r'src/multi_docs/MultiEOSOP格式说明.md'
d = io.open(P, encoding='utf-8').read()
L = d.split('\n')
out = []

# (1) 代码围栏
fences = [i for i, l in enumerate(L, 1) if l.startswith('```')]
out.append('=== (1) code fences: %d -> %s' % (len(fences), 'PAIRED' if len(fences) % 2 == 0 else 'ODD(ERROR)'))
if len(fences) % 2:
    out.append('   last few: %s' % fences[-5:])

# (2) 表号
tabs = re.findall(r'\u8868 (T\d+)\u3000', d)
cnt = collections.Counter(tabs)
dups = {k: v for k, v in cnt.items() if v > 1}
out.append('=== (2) 表号声明 %d 个, 重号: %s' % (len(tabs), dups if dups else 'none'))
nums = sorted({int(t[1:]) for t in tabs})
out.append('   range T%d..T%d, missing: %s' % (nums[0], nums[-1],
           sorted(set(range(nums[0], nums[-1]+1)) - set(nums))))

# (3) 内部引用完整性：抓所有 "见 X.Y" / "（见 X.Y.Z）" 形如 数字.数字
refs = set()
for m in re.finditer(r'(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s*\u8282', d):
    refs.add(m.group(1))
# 已有小节标题号
heads = set()
for l in L:
    m = re.match(r'^#{2,4}\s+(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)[\s\u3000]', l)
    if m:
        heads.add(m.group(1))
    m2 = re.match(r'^#{2,4}\s+(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)b[\s\u3000]', l)
    if m2:
        heads.add(m2.group(1) + 'b')
bad = sorted(r for r in refs if r not in heads and not re.match(r'^\d+\.\d+$', r) or (r not in heads and r.count('.') == 2))
bad = sorted(r for r in refs if r not in heads)
out.append('=== (3) 引用 %d 个, 未见对应标题 %d 个' % (len(refs), len(bad)))
out.append('   %s' % bad[:40])

# (4) 表格列数
bad_tabs = []
i = 0
while i < len(L):
    l = L[i]
    if l.startswith('|') and i + 1 < len(L) and re.match(r'^\|[\s:|-]+\|$', L[i+1].strip()):
        ncol = l.count('|') - 1
        j = i + 2
        while j < len(L) and L[j].startswith('|'):
            if L[j].count('|') - 1 != ncol:
                bad_tabs.append((i + 1, ncol, L[j].count('|') - 1, L[j][:60]))
            j += 1
        i = j
    else:
        i += 1
out.append('=== (4) 列数不一致的行: %d' % len(bad_tabs))
for t in bad_tabs[:30]:
    out.append('   L%d 头%d 数据%d | %s' % t)

# (5) 残留 ".feos 4x15" 断言
resid = [i for i, l in enumerate(L, 1)
         if (u'.feos' in l) and (u'4\u00d715' in l) and (u'10\u00d715' not in l) and (u'Readme' not in l)]
out.append('=== (5) 残留称 .feos 为 4x15 的行: %d' % len(resid))
for i in resid[:25]:
    out.append('   L%d %s' % (i, L[i-1][:150]))

# (6) 摘要式
out.append('=== (6) 关键串出现次数')
for k in [u'10\u00d715', u'4\u00d716', u'S-UNK', u'S-SRC', u'S-WEB', u'10.6']:
    out.append('   %s : %d' % (k, d.count(k)))

io.open(r'.workbuddy/tmp/audit.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('written')
