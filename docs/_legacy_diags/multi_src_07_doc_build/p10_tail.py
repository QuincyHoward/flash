# -*- coding: utf-8 -*-
"""p10: 收尾三处
   (a) L6419 外部引用补文档名（"与 §3.5.2" -> "与 **FEOS 说明** §3.5.2"）
   (b) 表 T31 勘误行改写，避免与 T31 定义行同形（审计假阳性）
   (c) §15.12.6 补 (五) 子编号表 T35-a/T35-b、T62/T62b 为合法
"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
orig = txt
log = []


def rep(old, new, tag, count=1):
    global txt
    n = txt.count(old)
    if n != count:
        raise SystemExit('[FAIL] %s: found %d expected %d\n  head=%r' % (tag, n, count, old[:140]))
    txt = txt.replace(old, new, count)
    log.append(tag)


# (a)
rep('计算密度下限 **1e-50 g/cm³**；与 §3.5.2 的',
    '计算密度下限 **1e-50 g/cm³**；与 **FEOS 说明** §3.5.2 的', 'a: L6419 补文档名')

# (b)
rep('**表 T31 该行曾出现的两处笔误',
    '**勘误 · 表 T31 该行曾出现的两处笔误', 'b: T31 勘误行改写')

# (c)
old_tail = """**审计规则应相应修正**：判定"表是否被定义"时须同时匹配**三种形态**，否则会像本轮
第一遍那样产生 11 条假阳性（T1–T5、T7、T8、T12、T13、T35、T36）。

---"""
new_tail = """**审计规则应相应修正**：判定"表是否被定义"时须同时匹配**三种形态**，否则会像本轮
第一遍那样产生 11 条假阳性（T1–T5、T7、T8、T12、T13、T35、T36）。

**(五) 合法的"字母子编号"（保留，非撞号）。** 以下两组共用一个数字根，但用 `-a/-b` 或
`b` 后缀区分，属**同一主题的两张分表**，与撞号性质不同：

| 数字根 | 子编号 | 内容 |
|---|---|---|
| T35 | **T35-a** / **T35-b** | muParser 内置函数（26 个）/ 内置二元运算符（15 个） |
| T62 | **T62** / **T62b** | 全局已知缺口汇总 / 第三轮新增缺口（格式侧） |

**审计规则须先剥离 `-a/-b/b` 后缀再判重**，否则会把这两组误报为撞号。
本文档约定：**新增分表时优先用字母后缀，不得直接复用已占用的数字根**。

**(六) 本轮审计的净结果。** 全文 66 个不同表号（T1–T74 区间内），其中：

```
粗体行定义 58 个      标题式定义 3 个（T1、T8、T36）
内联式定义  5 个（T2–T5、T7）      字母子编号 2 组（T35-a/b、T62/T62b）
真撞号 2 处（T30、T31）——本轮已改号为 T73、T74
合法编号占用 3 处（T11、T12、T13）——原文已标注，保留
未使用编号 7 个（T6、T18–T22、T64）——登记备查，不回收
```

至此**全文表号唯一性成立**：任意 `表 Tn` 引用在"数字根 + 字母后缀"层面均可唯一定位
`[S-L4] 机械审计`。

---"""
rep(old_tail, new_tail, 'c: 15.12.6 补 (五)(六)')

open(DOC, 'w', encoding='utf-8', newline='\n').write(txt)
print('PATCH10 done: %+d chars (%d -> %d)' % (len(txt) - len(orig), len(orig), len(txt)))
for l in log:
    print('   ', l)
