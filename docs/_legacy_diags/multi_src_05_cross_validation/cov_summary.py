# -*- coding: utf-8 -*-
"""
cov_summary.py -- 由 coverage_records.json 生成 coverage_summary.md
含: 按族/按后缀计数表 + 未完成语意识别的文件清单 + 诚实缺口说明
"""
import os, io, json
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
JSONF = os.path.join(HERE, 'coverage_records.json')
MD = os.path.join(HERE, 'coverage_summary.md')

with io.open(JSONF, encoding='utf-8') as fh:
    R = json.load(fh)

by_fam = Counter(r['family'] for r in R)
by_suf = Counter(r['suffix'] for r in R)
by_st  = Counter(r['parse_status'] for r in R)
by_fam_st = defaultdict(Counter)
for r in R:
    by_fam_st[r['family']][r['parse_status']] += 1
tot_bytes = sum(r['bytes'] for r in R if r['bytes'] > 0)

UNID = [r for r in R if r['family'] == '未识别']
EMPTY = [r for r in R if r['family'] == '空文件']
NONDATA = [r for r in R if r['family'] == '非数据']
PART = [r for r in R if r['parse_status'] == '部分']
NOTPARSE = [r for r in R if r['parse_status'] == '不可']

L = []
def P(s=''): L.append(str(s))

P("# 全量覆盖矩阵与语意识别汇总")
P("")
P("> 数据根：`src/Multi1D++Portable20241128/matter++/`")
P("> 生成脚本：`cov_inventory.py` → `cov_summary.py`")
P("> 逐文件明细见同目录 `coverage_matrix.tsv`（TSV，含表头，共 %d 行数据）" % len(R))
P("")
P("## 0. 规模")
P("")
P("| 指标 | 数值 |")
P("|---|---|")
P("| 文件总数 | **%d** |" % len(R))
P("| 总字节 | **%d**（%.1f MB） |" % (tot_bytes, tot_bytes / 1048576))
P("| 含文件的目录数 | %d |" % len(set(os.path.dirname(r['relative_path']) for r in R)))
P("| 识别出的格式族 | **%d** |" % len(by_fam))
P("| 无扩展名文件 | **%d** |" % by_suf.get('(无扩展名)', 0))
P("| 可解析 | %d |" % by_st.get('可解析', 0))
P("| 部分可解析 | %d |" % by_st.get('部分', 0))
P("| 不可解析 | %d |" % by_st.get('不可', 0))
P("")

P("## 1. 按格式族计数（%d 族）" % len(by_fam))
P("")
P("| 格式族 | 文件数 | 可解析 | 部分 | 不可 |")
P("|---|---:|---:|---:|---:|")
for f, n in by_fam.most_common():
    c = by_fam_st[f]
    P("| %s | %d | %d | %d | %d |" % (f, n, c.get('可解析',0), c.get('部分',0), c.get('不可',0)))
P("")
P("**族归属说明**：`FEOS辅助(.cst等)` 合并了 `.cst/.mexport/.PAR/.data.txt/.Rho-*.ist/.mnt/.hug 之外的 FEOS 导出`；"
  "`无扩展名多群不透明度表` 是文件名无后缀但表头带表号的多群 κ 表；"
  "`F1 MULTI反演EOS` 含 `.PLANCK/.ROSS/.EPS/.ZEFF` 带点号形式与 `_ieos/_eos/_mop/_op03*` 形式。")
P("")

P("## 2. 按后缀计数（top 45）")
P("")
P("| 后缀 | 文件数 |")
P("|---|---:|")
for s, n in by_suf.most_common(45):
    P("| `%s` | %d |" % (s, n))
P("")
P("其余后缀（各 <5 个）：%s" % ', '.join(
    '`%s`(%d)' % (s, n) for s, n in by_suf.most_common()[45:] if s != '(无扩展名)'))
P("")

P("## 3. 族 × 解析状态")
P("")
for f, c in sorted(by_fam_st.items(), key=lambda kv: -sum(kv[1].values())):
    P("- **%s** — %s" % (f, ', '.join('%s %d' % (k, v) for k, v in c.most_common())))
P("")

P("## 4. 未完成语意识别的文件清单")
P("")
P("### 4.1 完全未识别（族 = 未识别，%d 个）—— 需人工判定" % len(UNID))
P("")
P("| 相对路径 | 字节 | 后缀 | 首行片段 |")
P("|---|---:|---|---|")
for r in sorted(UNID, key=lambda x: x['relative_path']):
    P("| `%s` | %d | `%s` | `%s` |" % (r['relative_path'], r['bytes'], r['suffix'],
                                        (r['evidence'] or '(空)')[:60]))
P("")
P("### 4.2 空文件（%d 个）" % len(EMPTY))
P("")
for r in EMPTY:
    P("- `%s`" % r['relative_path'])
P("")
P("### 4.3 已识别族但解析未完成（状态 = 部分，%d 个）" % len(PART))
P("")
cnt = Counter(r['family'] for r in PART)
P("按族分布：")
P("")
P("| 格式族 | 部分可解析数 | 主要原因 |")
P("|---|---:|---|")
REASON = {
 'FEOS辅助(.cst等)': '`.mexport` 多记录块、`.data.txt` 列语义、`.PAR` 非数据卡',
 'F1 MULTI反演EOS/多群不透明度': '`_ieos/_eos/_eosd` 多块结构未闭合；`_mop*` 记录数未定',
 '曲线/常数(.dat/.xml/.txt)': '自由格式曲线/常数，无统一记录结构',
 'F4 MPQeos .301/.304/.305': '体区三列归属(T/P/E 顺序)未由物理量独立验证',
 '.coldopacity': '冷不透明度，记录结构未逆向',
 'F5 ATOMIC/LEDCOP/TOPS': 'LEDCOP AvSqFree/NoFree 块结构未逆向',
 'F6 IONMIX .cn4/.cnr': 'IONMIX 18/7 块结构未逐块闭合',
 '.hug': 'Hugoniot 曲线，格式未定',
 'F2 Hyades': 'Hyades 记录序未由闭合确认',
 'SESAME .sesame*': '`.sesame_PLANCK/ROSSELAND` 是不透明度记录，非 EOS-301 公式',
 'F3 FEOS原生.feos': '3 个文件的表头字段数不足 9',
}
for f, n in cnt.most_common():
    P("| %s | %d | %s |" % (f, n, REASON.get(f, '—')))
P("")
P("### 4.4 非数据文件（%d 个，不计入语意识别缺口）" % len(NONDATA))
P("")
nd = Counter(r['suffix'] for r in NONDATA)
P("按后缀：%s" % ', '.join('`%s`×%d' % (s, n) for s, n in nd.most_common()))
P("")

P("## 5. 诚实缺口说明（%d 条）" % 8)
P("")
P("1. **`.coldopacity`（67 个）结构未逆向**：全部标为「部分」，仅确认其为冷（T=0）不透明度，"
  "未确定是几维网格、单位与记录顺序。这是最大的一块未闭合数据。")
P("2. **F4 `.301/.304/.305`（82 个）体区列序未由物理量独立验证**：已确定体区为 `3 + 3·ne + 3·nr` 的三列结构，"
  "但三列是 `(T,P,E)` 还是别的顺序，未用独立物理量（如冷压单调性）反证。")
P("3. **`.mexport`（23 个）虽识别但记录块边界未逐块闭合**：仅确认 80 字符行宽与 `line[75:80]` 掩码。")
P("4. **F5 ATOMIC/LEDCOP（19 个）**：`.AvSqFree`/`.NoFree` 两种变体的块结构未逆向。")
P("5. **F6 IONMIX（17 个）**：`.cn4` 18 块 / `.cnr` 7 块，仅识别未逐块闭合。")
P("6. **`.dat`（401 个）中相当一部分是自由格式曲线/常数**，无统一记录结构，"
  "只能标记为「曲线/常数」，不宣称已识别具体语义。")
P("7. **31 个完全未识别文件**（见 4.1）多为无扩展名或罕见后缀，需人工或上游文档裁定。")
P("8. **本矩阵的「可解析」仅表示表头/尺寸通过闭合校验**，不等于已完成全部字段的语义标注。")

with io.open(MD, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')

# 额外: 导出 31 个未识别便于检查
with io.open(os.path.join(HERE, 'unknown_files.txt'), 'w', encoding='utf-8') as fh:
    for r in sorted(UNID, key=lambda x: x['relative_path']):
        fh.write("%-62s %10d  %-16s | %s\n" % (r['relative_path'], r['bytes'],
                                               r['suffix'], (r['evidence'] or '')[:70]))
print("WROTE %s %d" % (MD, os.path.getsize(MD)))
