# -*- coding: utf-8 -*-
"""综合核查：汉字门禁 / 代码围栏配对 / 表号重号与缺口 / 内部引用有效性 /
表格列数（转义感知）/ 章节顺序单调性。"""
import os, re, sys, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
L = txt.split('\n')

out = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    out.append(s)
    print(s)

P('=' * 70)
P('MultiEOSOP格式说明.md 综合核查')
P('=' * 70)
P('字节数        :', os.path.getsize(DOC))
P('字符数        :', len(txt))
P('总行数        :', len(L))
cn = len(re.findall(r'[\u4e00-\u9fff]', txt))
P('汉字数        :', cn, ' (门禁 80,000)', '  PASS' if cn >= 80000 else '  FAIL')
P()

# ── 1. 代码围栏配对 ─────────────────────────────────────────
P('-' * 70)
P('[1] 代码围栏配对')
P('-' * 70)
fences = [i for i, l in enumerate(L) if l.strip().startswith('```')]
P('围栏标记总数 :', len(fences), '(偶数=配对)', 'PASS' if len(fences) % 2 == 0 else 'FAIL')
# 逐块显示语言标签统计
langs = collections.Counter()
for k in range(0, len(fences) - 1, 2):
    tag = L[fences[k]].strip()[3:].strip() or '(none)'
    langs[tag] += 1
P('代码块数     :', sum(langs.values()))
P('语言分布     :', dict(langs))
# 找未闭合
if len(fences) % 2:
    P('  !! 奇数个围栏，检查奇数索引处:')
    for k in range(0, len(fences), 1):
        P('    L%d: %s' % (fences[k] + 1, L[fences[k]].strip()[:70]))
P()

# ── 2. 表号检查 ─────────────────────────────────────────────
P('-' * 70)
P('[2] 表号 T1–T99 重号与缺口')
P('-' * 70)
tabs = [int(m) for m in re.findall(r'表\s*T(\d+)\b', txt)]
cnt = collections.Counter(tabs)
dups = {k: v for k, v in cnt.items() if v > 1}
P('出现的不同表号数:', len(cnt), ' 取值范围:', (min(tabs), max(tabs)) if tabs else None)
if dups:
    P('  重号:')
    for k in sorted(dups):
        P('    T%d 出现 %d 次' % (k, dups[k]))
else:
    P('  无重号  PASS')
# 缺口
if tabs:
    missing = [i for i in range(min(tabs), max(tabs) + 1) if i not in cnt]
    P('  编号缺口 (%d 个): %s' % (len(missing), missing if len(missing) < 40 else missing[:40]))
P()

# ── 3. 章节顺序单调性 ───────────────────────────────────────
P('-' * 70)
P('[3] 章节编号单调性')
P('-' * 70)
# 第N章
ch = [(i + 1, int(m.group(1))) for i, l in enumerate(L)
      for m in [re.match(r'^## 第(\d+)章', l)] if m]
nums = [n for _, n in ch]
P('第N章 序列:', nums)
P('  单调递增:', 'PASS' if nums == sorted(nums) else 'FAIL ' + str(nums))
# 0–15 连续
if nums:
    exp = list(range(0, max(nums) + 1))
    miss = [n for n in exp if n not in nums]
    P('  缺章:', miss if miss else '无  PASS')
# 附录
apps = [m.group(1) for l in L for m in [re.match(r'^## 附录 ([A-F])', l)] if m]
P('附录序列 :', apps, 'PASS' if apps == sorted(apps) else 'FAIL')
# 三级节 §N.M 单调性
sects = {}
for i, l in enumerate(L):
    m = re.match(r'^### (\d+)\.(\d+)\b', l)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        sects.setdefault(a, []).append((i + 1, b))
bad = []
for a, lst in sorted(sects.items()):
    bs = [b for _, b in lst]
    if bs != sorted(bs):
        bad.append((a, bs))
if bad:
    P('  三级节非单调的章:')
    for a, bs in bad:
        P('    第%d章: %s' % (a, bs))
else:
    P('  三级节全部单调  PASS')
# 前置
pre = [m.group(1) for l in L for m in [re.match(r'^## 前置-(\d)', l)] if m]
P('前置序列 :', pre)
P()

# ── 4. 内部引用有效性 ───────────────────────────────────────
P('-' * 70)
P('[4] 内部交叉引用有效性（§X.Y / §X.Y.Z）')
P('-' * 70)
# 收集已定义的节号
defined = set()
for l in L:
    m = re.match(r'^#{3,4}\s+(\d+\.\d+(?:\.\d+)?)\b', l)
    if m:
        defined.add(m.group(1))
    m2 = re.match(r'^#{3,4}\s+(\d+\.\d+\.\d+)\b', l)
    if m2:
        defined.add(m2.group(1))
# 也收集 前置-N.M / 附录 X.N
for l in L:
    m = re.match(r'^#{3,4}\s+((?:前置-\d+\.\d+)|(?:[A-F]\.\d+))\b', l)
    if m:
        defined.add(m.group(1))

refs = collections.Counter(re.findall(r'§\s*(\d+\.\d+(?:\.\d+)?)', txt))
refs_pre = collections.Counter(re.findall(r'§\s*(前置-\d+\.\d+)', txt))
refs_app = collections.Counter(re.findall(r'§\s*([A-F]\.\d+(?:\.\d+)?)', txt))
P('正文 §N.M 引用种数:', len(refs), ' 实例数:', sum(refs.values()))
P('前置 § 引用:', dict(refs_pre))
P('附录 § 引用:', dict(refs_app))

def check(counter, label):
    miss = [(k, v) for k, v in sorted(counter.items()) if k not in defined]
    if miss:
        P('  [%s] 指向未定义的节 (%d):' % (label, len(miss)))
        for k, v in miss:
            P('     §%s  x%d' % (k, v))
    else:
        P('  [%s] 全部有效  PASS' % label)
    return miss

m1 = check(refs, '正文')
m2 = check(refs_pre, '前置')
m3 = check(refs_app, '附录')
P()

# ── 5. 表格列数一致性（转义感知） ───────────────────────────
P('-' * 70)
P('[5] Markdown 表格列数一致性')
P('-' * 70)

def split_row(l):
    """转义感知的 | 分割；忽略 \| 与代码 span 内的 |。"""
    s = l.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    cells, buf, i = [], '', 0
    in_code = False
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            buf += s[i:i + 2]; i += 2; continue
        if c == '`':
            in_code = not in_code; buf += c; i += 1; continue
        if c == '|' and not in_code:
            cells.append(buf); buf = ''; i += 1; continue
        buf += c; i += 1
    cells.append(buf)
    return [c.strip() for c in cells]

bad_tables = []
i = 0
n_tables = 0
while i < len(L):
    if L[i].strip().startswith('|') and i + 1 < len(L) and re.match(r'^\s*\|[\s:|-]+\|\s*$', L[i + 1]):
        n_tables += 1
        start = i
        hdr = split_row(L[i])
        n = len(hdr)
        rows = []
        j = i + 2
        while j < len(L) and L[j].strip().startswith('|'):
            r = split_row(L[j])
            if len(r) != n:
                rows.append((j + 1, len(r)))
            j += 1
        if len(split_row(L[i + 1])) != n:
            rows.append((i + 2, len(split_row(L[i + 1]))))
        if rows:
            bad_tables.append((start + 1, n, rows[:8], len(rows)))
        i = j
    else:
        i += 1

P('表格总数     :', n_tables)
if bad_tables:
    P('  列数不一致的表 (%d 个):' % len(bad_tables))
    for ln, n, rows, tot in bad_tables:
        P('    表起始 L%d  表头 %d 列  异常行 %d 个' % (ln, n, tot))
        for rl, rc in rows:
            P('       L%d -> %d 列' % (rl, rc))
else:
    P('  全部表格列数一致  PASS')
P()

# ── 6. 单行超长 ─────────────────────────────────────────────
P('-' * 70)
P('[6] 单行长度统计')
P('-' * 70)
mx = max((len(l), i + 1) for i, l in enumerate(L))
P('最长行       : L%d  %d 字符' % (mx[1], mx[0]))
over = [(i + 1, len(l)) for i, l in enumerate(L) if len(l) > 2000]
P('超 2000 字符的行:', len(over), over[:10])
P()

# ── 7. 残留占位/异常标记 ────────────────────────────────────
P('-' * 70)
P('[7] 残留标记扫描')
P('-' * 70)
for pat, label in [
    (r'TODO|FIXME|XXX|待补|待写|略\b', 'TODO/待补'),
    (r'\{\{|\}\}', '未替换模板占位'),
    (r'\]\(\s*\)', '空链接'),
    (r'。\s*。', '重复句号'),
]:
    hits = [(i + 1, l.strip()[:80]) for i, l in enumerate(L) if re.search(pat, l)]
    P('%-16s %d 处' % (label, len(hits)))
    for ln, s in hits[:6]:
        P('    L%d: %s' % (ln, s))
P()

# ── 8. 关键结论存在性 ───────────────────────────────────────
P('-' * 70)
P('[8] 本轮关键结论存在性（应全部存在）')
P('-' * 70)
must = [
    ('14.5 无扩展名多群不透明度表节', '14.5 无扩展名多群不透明度表'),
    ('14.5.14 定稿解析器', 'read_multigroup_opacity'),
    ('B.22 速查卡', 'B.22 无扩展名多群不透明度表'),
    ('B.23 记账文件', 'B.23 记账文件'),
    ('B.24 .cst 双变体', 'B.24 FEOS `.cst`'),
    ('15.14 第三轮新增', '15.14 第三轮新增'),
    ('15.12.5 第三轮勘误', '15.12.5 【勘误】第三轮'),
    ('15.12.5b 代理否决', '15.12.5b 对代理结论的'),
    ('15.9.1 群级重复结构', '15.9.1 补充'),
    ('15.2.4 哨兵常量', '15.2.4 补充'),
    ('R16 规约', '**R16**'),
    ('R19 规约', '**R19**'),
    ('15.8.0 后缀覆盖审计', '15.8.0 第三轮：后缀覆盖审计'),
    ('outputMULTIOpacity.m 引用', 'outputMULTIOpacity.m'),
    ('SysV-16/BSD-16', 'SysV-16'),
    ('-1.#INF00e+000', '-1.#INF00e+000'),
    ('A_eff=141.1332', '141.1332'),
]
for label, needle in must:
    ok = needle in txt
    P('  [%s] %-32s' % ('OK ' if ok else 'MISS', label))
P()
P('=' * 70)
P('核查结束')
P('=' * 70)

with open(os.path.join(ROOT, '.workbuddy', 'tmp', 'audit_round3.txt'), 'w',
          encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(out))
print('\n[written] .workbuddy/tmp/audit_round3.txt')
