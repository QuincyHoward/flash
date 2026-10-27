# -*- coding: utf-8 -*-
"""
cov_inventory.py -- 全量逐文件覆盖矩阵 for matter++/
产出: coverage_matrix.tsv, coverage_records.json, coverage_counts.txt

路径: gen_eos_op/src/Multi1D++Portable20241128/matter++/
输出: gen_eos_op/src/multi_src/05_cross_validation/
"""
import os, io, re, json, math
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))          # .../src/multi_src/05_cross_validation
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))      # .../src
ROOT = os.path.abspath(os.path.join(SRC, '..'))             # gen_eos_op
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
OUTDIR = HERE
TSV  = os.path.join(OUTDIR, 'coverage_matrix.tsv')
JSONF = os.path.join(OUTDIR, 'coverage_records.json')
CNTF = os.path.join(OUTDIR, 'coverage_counts.txt')

NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')
OPID = re.compile(r'^\s*(?:\d{8}|[0-9]*\.?[0-9]+[eE]\+0[34])\s')

NONDATA = {'.gif','.js','.html','.htm','.bak','.opj','.mat','.xmind','.db','.manifest',
           '.dem','.gid','.hlp','.png','.jpg','.jpeg','.zip','.gz','.xlsx','.xls',
           '.docx','.doc','.pdf','.ico','.svg'}
ACCT = {'MODINFO','FILELIST','LOCK','CHECKSUM'}

def head_text(p, n=4096):
    try:
        with open(p, 'rb') as fh:
            b = fh.read(n)
    except Exception:
        return ''
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def whole_text(p):
    try:
        with open(p, 'rb') as fh:
            b = fh.read()
    except Exception:
        return ''
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def split_lines(t):
    return [l.rstrip('\n') for l in t.replace('\r\n','\n').replace('\r','\n').split('\n')]

def floats_fixed(s, width=15):
    out = []
    for i in range(0, len(s), width):
        c = s[i:i+width].strip()
        if not c:
            continue
        try:
            out.append(float(c.replace('D','E').replace('d','e')))
        except ValueError:
            mv = re.search(r'(?<![eEdD])[-+]?\d*\.?\d+[eEdD][-+]?\d+$', c)
            if mv:
                exp = c[mv.start():]
                toks = NUMRE.findall(c[:mv.start()])
                for t in (toks[:-1] if len(toks) > 1 else toks):
                    out.append(float(t.replace('D','E').replace('d','e')))
                if toks:
                    try:
                        out.append(float(toks[-1].lstrip('+') + exp.replace('D','E').replace('d','e')))
                    except ValueError:
                        out.append(float(toks[-1]))
            else:
                for t in NUMRE.findall(c):
                    out.append(float(t.replace('D','E').replace('d','e')))
    return out

def floats_any(s):
    return [float(t.replace('D','E').replace('d','e')) for t in NUMRE.findall(s)]

def tally_nums(s):
    """count numbers the way floats_fixed would consume them"""
    n = 0
    for i in range(0, len(s), 15):
        c = s[i:i+15].strip()
        if not c:
            continue
        try:
            float(c.replace('D','E').replace('d','e')); n += 1; continue
        except ValueError:
            pass
        mv = re.search(r'(?<![eEdD])[-+]?\d*\.?\d+[eEdD][-+]?\d+$', c)
        if mv:
            toks = NUMRE.findall(c[:mv.start()])
            n += len(toks)
        else:
            n += len(NUMRE.findall(c))
    return n

# ------------------------------------------------------------------ classification
def classify(rel, name, size, txt):
    """return (family, evidence, status, remark)"""
    ext = os.path.splitext(name)[1]
    el = ext.lower()
    nl = name.lower()
    rl = rel.lower().replace('\\','/')
    lines = [l for l in split_lines(txt) if l.strip()]
    l0 = lines[0] if lines else ''
    ev = l0.strip()[:84]
    up = name.upper()

    # --- 记账 / 非数据
    if size == 0:
        return ('空文件', '(0 字节)', '不可', '空文件，无内容')
    if up in ACCT:
        return ('记账(MODINFO/FILELIST/LOCK/CHECKSUM)', ev or '(空)', '可解析', '记账/元数据')
    if el in NONDATA:
        return ('非数据', ev or '(二进制/非文本)', '不可', '非数据文件')

    # --- 明确后缀族
    if el == '.feos':
        return ('F3 FEOS原生.feos', ev, '可解析', '150字符×10字段')
    if el in ('.301', '.304', '.305'):
        return ('F4 MPQeos .301/.304/.305', ev, '可解析', 'SESAME mexport 风格')
    if el in ('.cn4', '.cnr'):
        return ('F6 IONMIX .cn4/.cnr', ev, '部分', 'IONMIX 多块格式')
    if el == '.cst':
        return ('FEOS辅助(.cst等)', ev, '可解析', 'Rostock 四列 T=0 等温线')
    if el == '.mexport':
        return ('FEOS辅助(.cst等)', ev, '可解析', '80字符×5字段+5掩码')
    if el == '.hyades' or 'hyades' in nl:
        return ('F2 Hyades', ev, '部分', 'Hyades EOS')
    if el == '.hug' or nl.endswith('.hug') or '_eos.hug' in nl or '.hug' in nl:
        return ('.hug', ev, '部分', 'Hugoniot 曲线')
    if 'coldopacity' in nl:
        return ('.coldopacity', ev, '部分', '冷不透明度')
    if 'multigroupopacity' in nl or 'grayopacity' in nl:
        return ('F1 MULTI反演EOS/多群不透明度', ev, '可解析', 'MULTI 多群/灰度不透明度')
    if el in ('.planck', '.ross', '.rosseland', '.eps', '.zeff'):
        return ('F1 MULTI反演EOS/多群不透明度', ev, '可解析', '带点号专用不透明度文件')

    # --- SESAME
    if nl.endswith('.sesame_planck') or nl.endswith('.sesame_rosseland') or nl.endswith('.sesame_ross'):
        return ('SESAME .sesame*', ev, '部分', '不透明度(哨兵+PLANCK/ROSSELAND)，非EOS 301')
    if nl.endswith('.sesame') or nl.endswith('.sesame_') or nl.endswith('.sesame'):
        return ('SESAME .sesame*', ev, '可解析', 'EOS 301，n=4+2nr+ne+2nr·ne')
    if el == '.par' or nl.endswith('.par'):
        return ('FEOS辅助(.cst等)', ev, '可解析', 'FEOS 输入卡 (.PAR)')

    # --- ATOMIC/LEDCOP 变体与 FEOS 曲线导出
    if el in ('.avsqfree', '.nofree'):
        return ('F5 ATOMIC/LEDCOP/TOPS', ev, '部分', 'LEDCOP 不透明度变体 (AvSqFree/NoFree 表)')
    if nl.startswith('#') or name.startswith('#'):
        return ('F5 ATOMIC/LEDCOP/TOPS', ev, '部分', '注释/标签文件')
    if el in ('.ist', '.isc', '.ise', '.mnt', '.ist4gnuplot', '.isc4gnuplot',
              '.ise4gnuplot', '.mnt4gnuplot'):
        return ('FEOS辅助(.cst等)', ev, '可解析', 'FEOS Rho-T / Rho-P 曲线导出')
    if el in ('.info', '.inhalt'):
        return ('幂律.readme', ev, '可解析', '说明/信息文件')
    if el in ('.ini', '.case'):
        return ('配置(.ini/.case)', ev, '可解析', 'FEOS 配置/算例')
    if el == '.out':
        return ('记账(MODINFO/FILELIST/LOCK/CHECKSUM)', ev, '可解析', '运行输出')
    if el == '.inv':
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '反演输入')
    if el == '.snop':
        return ('F7 SNOP', ev, '可解析', 'SNOP 文件（带扩展名）')

    # --- SNOP / Thermos
    if 'snop' in nl:
        return ('F7 SNOP', ev, '可解析', 'SNOP 不透明度')
    if 'thermos' in nl or 'thermo' in nl:
        return ('F8 Thermos', ev, '部分', 'Thermos 格式')

    # --- 说明 / 索引
    if 'readme' in nl or nl.startswith('read'):
        return ('幂律.readme', ev, '可解析', '说明文档')
    if el in ('.base', '.user', '.list') or nl in ('material.base', 'material.user'):
        return ('索引(material.base/.user/.list)', ev, '可解析', '材料索引')
    if el == '.log':
        return ('记账(MODINFO/FILELIST/LOCK/CHECKSUM)', ev, '可解析', '运行日志')

    # --- 无扩展名 / 命名族
    if '_ieos' in nl:
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '反演 EOS，数密度轴')
    if nl.endswith('_eos_e') or nl.endswith('_eos_i'):
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '电子/离子分离 EOS')
    if nl.endswith('_eosd') or nl.endswith('_eos') or nl.endswith('_eos_') or nl.endswith('_eos.dat'):
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '反演 EOS')
    if re.search(r'_op03[epprz]$', nl) or nl.endswith('_opp') or nl.endswith('_opr'):
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '不透明度(MULTI 反演)')
    if '_mop' in nl:
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', '多群不透明度(MULTI)')
    if el == '.in' or el == '.input' or el == '.inv':
        return ('F1 MULTI反演EOS/多群不透明度', ev, '部分', 'MULTI/SNOP 输入卡')

    if el in ('.dat', '.txt', '.xml', '.csv', '.tsv'):
        # may still be an opacity table with a .dat extension (e.g. C_Z.dat)
        if OPID.match(l0) or any(c in l0 for c in ('PLANCK','ROSSELAND','EPS','ZEFF')):
            return ('无扩展名多群不透明度表(PLANCK/ROSSELAND/EPS/ZEFF)', ev, '可解析',
                    '表号+Z/NR/NT 表头 (扩展名伪装)')
        if 'FEOS' in l0 or 'SESAME' in l0.upper():
            return ('FEOS辅助(.cst等)', ev, '部分', 'FEOS 输出文本')
        return ('曲线/常数(.dat/.xml/.txt)', ev, '部分', '曲线/常数/文本数据')

    # --- 无扩展名：用内容嗅探
    if ext == '':
        if any(c in l0 for c in ('PLANCK','ROSSELAND','EPS','ZEFF')) or OPID.match(l0):
            return ('无扩展名多群不透明度表(PLANCK/ROSSELAND/EPS/ZEFF)', ev, '可解析',
                    '表号+NR/NT 表头')
        if 'ATOMIC' in rl or 'LEDCOP' in rl or 'TOPS' in rl:
            return ('F5 ATOMIC/LEDCOP/TOPS', ev, '部分', 'ATOMIC/LEDCOP/TOPS 目录')
        return ('未识别', ev or '(空)', '不可', '无扩展名且未匹配已知模式')

    # --- 目录提示
    if 'ATOMIC' in rl or 'LEDCOP' in rl or 'TOPS' in rl:
        return ('F5 ATOMIC/LEDCOP/TOPS', ev, '部分', 'ATOMIC/LEDCOP/TOPS 目录')
    if 'ionmix' in rl:
        return ('F6 IONMIX .cn4/.cnr', ev, '部分', 'IONMIX 目录')

    return ('未识别', ev or '(空)', '不可', '后缀 %r 未匹配' % ext)


# ------------------------------------------------------------------ deep parse status
def deep_status(fam, rel, name, size, path):
    """Upgrade status with an exact closure check where a cheap one exists."""
    el = os.path.splitext(name)[1].lower()
    try:
        if fam == 'SESAME .sesame*' and 'planck' not in name.lower() and 'ross' not in name.lower():
            f = []
            for l in split_lines(whole_text(path)):
                if l.strip():
                    f.extend(floats_fixed(l, 15))
            if len(f) >= 4:
                nr = int(round(f[2])); ne = int(round(f[3]))
                if nr > 0 and ne > 0 and len(f) == 4 + 2*nr + ne + 2*nr*ne:
                    return '可解析', '闭合成 (nr=%d, ne=%d)' % (nr, ne)
                return '部分', '尺寸闭合成失败: N=%d nr=%d ne=%d' % (len(f), nr, ne)
        if fam == 'F4 MPQeos .301/.304/.305':
            f = []
            for l in split_lines(whole_text(path)):
                if l.strip():
                    f.extend(floats_fixed(l, 15))
            return '部分', '总数值 %d（体区/3列归属待裁定）' % len(f)
        if fam == 'FEOS辅助(.cst等)' and el == '.cst':
            raw = whole_text(path)
            rows = 0; bad = 0
            for l in split_lines(raw):
                t = l.strip()
                if not t or 'Molek' in t or 'Massendichte' in t or t.lower().startswith('isotherm'):
                    continue
                v = NUMRE.findall(t)
                if len(v) == 4:
                    rows += 1
                elif v:
                    bad += 1
            if rows and not bad:
                return '可解析', '%d 行均为 4 列' % rows
            return '部分', '4列行=%d 异常行=%d' % (rows, bad)
        if fam == 'F3 FEOS原生.feos':
            ls = [l for l in split_lines(head_text(path, 4096)) if l.strip()]
            if len(ls) >= 2 and len(floats_fixed(ls[0], 15)) >= 9 and len(floats_fixed(ls[1], 15)) >= 9:
                return '可解析', '两行表头各≥9字段'
            return '部分', '表头字段不足'
        if fam == 'F1 MULTI反演EOS/多群不透明度' and el in ('.planck', '.ross', '.rosseland', '.eps', '.zeff'):
            ls = [l for l in split_lines(head_text(path, 512)) if l.strip()]
            if ls and (OPID.match(ls[0]) or any(c in ls[0] for c in ('PLANCK','ROSSELAND','EPS','ZEFF'))):
                return '可解析', '表头匹配'
            return '部分', '表头未匹配'
        if fam.startswith('无扩展名多群不透明度表'):
            ls = [l for l in split_lines(head_text(path, 512)) if l.strip()]
            if ls and (OPID.match(ls[0]) or any(c in ls[0] for c in ('PLANCK','ROSSELAND','EPS','ZEFF'))):
                return '可解析', '表头匹配'
            return '部分', '表头未匹配'
    except Exception as e:
        return '部分', '检查异常 %s' % type(e).__name__
    return None, None


# ------------------------------------------------------------------ main walk
records = []
for dirpath, dirnames, filenames in os.walk(MATTER):
    dirnames.sort()
    for f in sorted(filenames):
        p = os.path.join(dirpath, f)
        try:
            size = os.path.getsize(p)
        except OSError:
            size = -1
        rel = os.path.relpath(p, MATTER).replace('\\', '/')
        txt = head_text(p, 4096)
        fam, ev, status, remark = classify(rel, f, size, txt)
        el = os.path.splitext(f)[1].lower()
        try:
            st2, rk2 = deep_status(fam, rel, f, size, p)
            if st2:
                status, remark = st2, rk2
        except Exception as e:
            status = '部分'; remark = '深检异常 %s' % type(e).__name__
        records.append({
            'relative_path': rel, 'bytes': size,
            'suffix': el if el else '(无扩展名)',
            'family': fam,
            'evidence': ' '.join(ev.split())[:84],
            'parse_status': status,
            'remark': ' '.join(remark.split())[:110],
        })

# ------------------------------------------------------------------ write TSV
cols = ['relative_path','bytes','suffix','family','evidence','parse_status','remark']
with io.open(TSV, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\t'.join(cols) + '\n')
    for r in records:
        fh.write('\t'.join(
            str(r[c]).replace('\t',' ').replace('\n',' ').replace('\r',' ') for c in cols
        ) + '\n')

with io.open(JSONF, 'w', encoding='utf-8') as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ counts
by_fam = Counter(r['family'] for r in records)
by_suf = Counter(r['suffix'] for r in records)
by_st  = Counter(r['parse_status'] for r in records)
by_fam_st = defaultdict(Counter)
for r in records:
    by_fam_st[r['family']][r['parse_status']] += 1

tot_bytes = sum(r['bytes'] for r in records if r['bytes'] > 0)
L = []
def P(s=''): L.append(str(s))
P("全量覆盖矩阵统计")
P("=" * 90)
P("文件总数 = %d ; 总字节 = %d (%.1f MB)" % (len(records), tot_bytes, tot_bytes/1048576))
P("")
P("### 按格式族计数 (%d 族)" % len(by_fam))
P("%-58s %6s" % ("格式族", "文件数"))
for f, n in by_fam.most_common():
    P("%-58s %6d" % (f, n))
P("")
P("### 按解析状态")
for s, n in by_st.most_common():
    P("  %-10s %6d" % (s, n))
P("")
P("### 族 × 状态")
for f, c in sorted(by_fam_st.items(), key=lambda kv: -sum(kv[1].values())):
    P("  %-56s %s" % (f, dict(c)))
P("")
P("### 按后缀计数 (top 60)")
for s, n in by_suf.most_common(60):
    P("  %-30s %6d" % (s, n))
P("")
P("### 解析状态 != 可解析 的文件清单")
ne = [r for r in records if r['parse_status'] != '可解析']
P("共 %d 个" % len(ne))
P("%-56s %-14s %-58s %s" % ("相对路径", "状态", "族", "备注"))
for r in ne:
    P("%-56s %-14s %-58s %s" % (r['relative_path'][:56], r['parse_status'],
                                r['family'][:58], r['remark'][:70]))

with io.open(CNTF, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE %s %d ; %s %d ; %s %d" % (TSV, os.path.getsize(TSV), JSONF,
                                       os.path.getsize(JSONF), CNTF, os.path.getsize(CNTF)))
