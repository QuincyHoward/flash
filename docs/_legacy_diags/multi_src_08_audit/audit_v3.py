# -*- coding: utf-8 -*-
"""综合核查 v3（终版）：修正 v2 的两处误判
   - 表定义识别三种形态（粗体行 / 节标题 / 正文内联）
   - 外部文档 §N.M 与内部 §N.M 分离（上下文窗口加宽 + 更多marker）
"""
import os, re, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
L = txt.split('\n')
out = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    out.append(s)
    print(s)


P('=' * 76)
P('MultiEOSOP格式说明.md 综合核查 v3（终版）')
P('=' * 76)
P('字节数 :', os.path.getsize(DOC))
P('字符数 :', len(txt))
P('总行数 :', len(L))
cn = len(re.findall(r'[\u4e00-\u9fff]', txt))
P('汉字数 :', cn, '(门禁 80,000)', 'PASS' if cn >= 80000 else 'FAIL')
P()

# ── 1 围栏 ───────────────────────────────────────────────────
P('-' * 76); P('[1] 代码围栏配对'); P('-' * 76)
fen = [i for i, l in enumerate(L) if l.strip().startswith('```')]
P('围栏总数:', len(fen), 'PASS' if len(fen) % 2 == 0 else 'FAIL')
langs = collections.Counter()
for k in range(0, len(fen) - 1, 2):
    langs[L[fen[k]].strip()[3:].strip() or '(none)'] += 1
P('代码块数:', sum(langs.values()), dict(langs))
P()

# ── 2 表号 ───────────────────────────────────────────────────
P('-' * 76); P('[2] 表号 T1–T99'); P('-' * 76)
allref = [m.group(1) + (m.group(2) or '')
          for m in re.finditer(r'表\s*T(\d+)((?:-[ab])|(?:[ab]))?', txt)]
cnt = collections.Counter(allref)
bold, head, inline = collections.Counter(), collections.Counter(), set()
for l in L:
    s = l.strip()
    m = re.match(r'^\*\*表\s*T(\d+)((?:-[ab])|(?:[ab]))?', s)
    if m:
        bold[m.group(1) + (m.group(2) or '')] += 1
    if re.match(r'^#{2,4}\s', s):
        for m in re.finditer(r'表\s*T(\d+)((?:-[ab])|(?:[ab]))?', s):
            head[m.group(1) + (m.group(2) or '')] += 1
for n in cnt:
    if n not in bold and n not in head:
        inline.add(n)
def tkey(x):
    i = 0
    while i < len(x) and x[i].isdigit():
        i += 1
    return (int(x[:i]) if i else 0, x)


P('不同表号:', len(cnt), '范围:', (tkey(min(allref, key=tkey))[0], tkey(max(allref, key=tkey))[0]))
dupd = {k: v for k, v in bold.items() if v > 1}
P('重复"粗体定义"表号:', dupd if dupd else '无  PASS')
duph = {k: v for k, v in head.items() if v > 1}
P('重复"标题定义"表号:', duph if duph else '无  PASS')
P('粗体行定义 :', len(bold), sorted(bold, key=tkey))
P('标题式定义 :', len(head), sorted(head, key=tkey))
P('内联式定义 :', len(inline), sorted(inline, key=tkey))
gap_in_used = [i for i in range(1, 75) if str(i) not in cnt]
P('单数字根编号缺口 (%d): %s' % (len(gap_in_used), gap_in_used))
def_union = set(bold) | set(head) | inline
P('被引用但三种定义皆无:', sorted(set(cnt) - def_union) or '无  PASS')
out.append('   粗体行定义 = %s' % sorted(bold))
out.append('   标题式定义 = %s' % sorted(head))
out.append('   内联式定义 = %s' % sorted(inline))
P()

# ── 3 章节顺序 ───────────────────────────────────────────────
P('-' * 76); P('[3] 章节编号顺序'); P('-' * 76)
ch = [int(m.group(1)) for l in L for m in [re.match(r'^## 第(\d+)章', l)] if m]
P('第N章:', ch, 'PASS' if ch == sorted(ch) else 'FAIL')
apps = [m.group(1) for l in L for m in [re.match(r'^## 附录 ([A-F])', l)] if m]
P('附录  :', apps, 'PASS' if apps == sorted(apps) else 'FAIL')
bad = []
for pat, lab in [(r'^### (\d+)\.(\d+)\b', '三'), (r'^#### (\d+)\.(\d+)\.(\d+)\b', '四')]:
    grp = collections.defaultdict(list)
    for i, l in enumerate(L):
        m = re.match(pat, l)
        if m:
            g = m.groups()
            grp[(int(g[0]), int(g[1]))].append((i + 1, int(g[-1])))
    for k, lst in sorted(grp.items()):
        vs = [v for _, v in lst]
        if vs != sorted(vs):
            bad.append((lab, k, vs))
if bad:
    for lab, k, vs in bad:
        P('  非单调 [%s级] %s -> %s' % (lab, k, vs))
else:
    P('  二/三/四级节全部单调  PASS')
b = [int(m.group(1)) for l in L for m in [re.match(r'^### B\.(\d+)\b', l)] if m]
P('  附录 B 子节:', b, 'PASS' if b == sorted(b) else 'FAIL')
pre = [int(m.group(1)) for l in L for m in [re.match(r'^## 前置-(\d)', l)] if m]
P('  前置序列:', pre, 'PASS' if pre == sorted(pre) else 'FAIL')
P()

# ── 4 交叉引用 ───────────────────────────────────────────────
P('-' * 76); P('[4] 交叉引用有效性'); P('-' * 76)
defined = set()
for l in L:
    for pat in [r'^#{2,4}\s+(\d+\.\d+(?:\.\d+)?)\b',
                r'^#{2,4}\s+(前置-\d+\.\d+)\b',
                r'^#{2,4}\s+([A-F]\.\d+(?:\.\d+)?)\b']:
        m = re.match(pat, l)
        if m:
            defined.add(m.group(1))
EXT = ['FEOS', '手册', 'IONMIX', 'FLASH', '指南', 'Package Documentation',
       "User's Guide", '文档 §', 'doc/', 'UG §', 'Hrutkai', 'MULTI2002',
       'CPC', '论文', 'SNOP.MANUAL', '说明', 'Guide', 'manual']
refs = []
for i, l in enumerate(L):
    for m in re.finditer(r'§\s*((?:\d+\.\d+(?:\.\d+)?)|(?:前置-\d+\.\d+)|(?:[A-F]\.\d+(?:\.\d+)?))', l):
        ctx = l[max(0, m.start() - 70):m.start()]
        refs.append((i + 1, m.group(1), any(e in ctx for e in EXT), ctx.strip()[-45:]))
intr = [r for r in refs if not r[2]]
extr = [r for r in refs if r[2]]
P('引用总数:', len(refs), ' 内部:', len(intr), ' 外文档:', len(extr))
dang = [r for r in intr if r[1] not in defined]
if dang:
    P('  !! 内部悬空引用 (%d):' % len(dang))
    for ln, k, _, ctx in dang:
        P('     L%-6d §%-10s ← %s' % (ln, k, ctx))
else:
    P('  内部引用全部有效  PASS')
P()

# ── 5 表格列数 ───────────────────────────────────────────────
P('-' * 76); P('[5] 表格列数一致性'); P('-' * 76)
def cells(l):
    s = l.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    o, b, i, code = [], '', 0, False
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            b += s[i:i+2]; i += 2; continue
        if c == '`':
            code = not code; b += c; i += 1; continue
        if c == '|' and not code:
            o.append(b); b = ''; i += 1; continue
        b += c; i += 1
    o.append(b)
    return [x.strip() for x in o]

bad_t, ntab, i = [], 0, 0
while i < len(L):
    if L[i].strip().startswith('|') and i + 1 < len(L) and re.match(r'^\s*\|[\s:|-]+\|\s*$', L[i+1]):
        ntab += 1
        n = len(cells(L[i]))
        j, rows = i + 2, []
        while j < len(L) and L[j].strip().startswith('|'):
            if len(cells(L[j])) != n:
                rows.append((j + 1, len(cells(L[j]))))
            j += 1
        if len(cells(L[i+1])) != n:
            rows.append((i + 2, len(cells(L[i+1]))))
        if rows:
            bad_t.append((i + 1, n, rows[:6], len(rows)))
        i = j
    else:
        i += 1
P('表格总数:', ntab, ' 列数不一致:', len(bad_t), 'PASS' if not bad_t else 'FAIL')
for ln, n, rows, tot in bad_t:
    P('    L%d 表头%d列 异常%d行 %s' % (ln, n, tot, rows))
P()

# ── 6 残留 ───────────────────────────────────────────────────
P('-' * 76); P('[6] 残留标记'); P('-' * 76)
for pat, lab in [(r'TODO|FIXME|待补充|待写|\bXXX\b', 'TODO/待补'),
                 (r'\{\{|\}\}', '模板占位'),
                 (r'\]\(\s*\)', '空链接'),
                 (r'<<<|>>>|<<<<<<<|>>>>>>>', '冲突标记')]:
    hits = [i + 1 for i, l in enumerate(L) if re.search(pat, l)]
    P('%-12s %d %s' % (lab, len(hits), hits[:6]))
P()
P('=' * 76); P('核查结束'); P('=' * 76)

open(os.path.join(ROOT, '.workbuddy', 'tmp', 'audit_v3.txt'), 'w',
     encoding='utf-8', newline='\n').write('\n'.join(out))
print('\n[written] .workbuddy/tmp/audit_v3.txt')
