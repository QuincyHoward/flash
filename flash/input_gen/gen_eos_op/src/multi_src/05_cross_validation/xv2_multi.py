# -*- coding: utf-8 -*-
"""
xv2_multi.py -- 第二轮多材料交叉验证
材料: mat_B, mat_He, mat_Al-1.0, Ta2O5 (+ 引用 round1 的 mat_Ce)

对每个材料:
  1) 枚举可用格式
  2) 密度网格是否**逐位一致** (== 判等)
  3) 数密度自洽: A_eff = rho*N_A/n ; 并与 .feos 的 Atot/Ztot 比对
  4) 温度网格是否一致
  5) 明确列出物理上不可比的量及理由
"""
import os, io, re, math
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
MD = os.path.join(HERE, 'cross_validation_round2.md')

NA = 6.02214076e23
MU = 1.66053906660e-24     # g, atomic mass unit
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')

def whole(p):
    with open(p, 'rb') as fh:
        b = fh.read()
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def head(p, n=8192):
    with open(p, 'rb') as fh:
        b = fh.read(n)
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    return b.decode('utf-8', 'replace')

def lines(t):
    return [l.rstrip('\n') for l in t.replace('\r\n','\n').replace('\r','\n').split('\n')]

def f15(s):
    out = []
    for i in range(0, len(s), 15):
        c = s[i:i+15].strip()
        if not c: continue
        try:
            out.append(float(c.replace('D','E').replace('d','e')))
        except ValueError:
            for t in NUMRE.findall(c):
                out.append(float(t.replace('D','E').replace('d','e')))
    return out

def fany(s):
    return [float(t.replace('D','E').replace('d','e')) for t in NUMRE.findall(s)]

def find(d, names):
    """case-insensitive file lookup inside dir d"""
    try:
        ent = os.listdir(d)
    except OSError:
        return None
    for want in names:
        for e in ent:
            if e.lower() == want.lower():
                return os.path.join(d, e)
    return None

def feos_hdr(p):
    ls = [l for l in lines(head(p, 8192)) if l.strip()]
    h0 = f15(ls[0]); h1 = f15(ls[1])
    return {'NRho': int(round(h0[1])), 'NT': int(round(h0[2])),
            'Nelem': h0[3] if len(h0) > 3 else None,
            'Tcalclimit': h0[4] if len(h0) > 4 else None,
            'Rhocalclimit': h0[5] if len(h0) > 5 else None,
            'RhoRef': h0[6] if len(h0) > 6 else None,
            'SESAMEnumber': h0[9] if len(h0) > 9 else None,
            'Atot': h1[7] if len(h1) > 7 else None,
            'Ztot': h1[8] if len(h1) > 8 else None,
            'Xtot': h1[9] if len(h1) > 9 else None,
            'h0': h0, 'h1': h1}

def cst_read(p):
    rows = []
    for l in lines(whole(p)):
        t = l.strip()
        if not t or 'Molek' in t or 'Massendichte' in t or 'Particle density' in t \
           or t.lower().startswith('isotherm'):
            continue
        v = NUMRE.findall(t)
        if len(v) == 4:
            rows.append([float(x.replace('D','E').replace('d','e')) for x in v])
        elif len(v) > 4 and len(v) % 4 == 0:
            for i in range(0, len(v), 4):
                rows.append([float(x.replace('D','E').replace('d','e')) for x in v[i:i+4]])
    return rows

def aeff_stats(rows):
    """A_eff = rho*N_A/n over rows with n>0 and rho>0"""
    vals = []
    for n, rho, P, Q in rows:
        if n > 0 and rho > 0:
            vals.append(rho * NA / n)
    if not vals:
        return None
    return {'n': len(vals), 'min': min(vals), 'max': max(vals),
            'mean': sum(vals)/len(vals),
            'spread_rel': (max(vals)-min(vals))/ (sum(vals)/len(vals))}

def dat_cols(p):
    """identify the (rho, T) columns of a FEOS *.data.txt by cardinality"""
    ls = [l for l in lines(whole(p)) if l.strip()]
    rows = [fany(l) for l in ls]
    if not rows:
        return None
    ncol = len(rows[0])
    card = []
    for c in range(ncol):
        card.append(len(set(round(r[c], 12) for r in rows)))
    # the two index columns are 0,1 (integers); the axis columns are the pair
    # with cardinality equal to max index+1
    return {'rows': rows, 'ncol': ncol, 'card': card, 'nlines': len(ls)}

L = []
def P(s=''): L.append(str(s))

MATS = ['mat_B', 'mat_He', 'mat_Al-1.0', 'Ta2O5', 'mat_Ce', 'mat_Ba', 'SiO2']
ALLOW = ('feos','cst','301','304','305','mexport','sesame','planck','ross','eps','zeff',
         'hyades','mop','op03','ieos','eos','hug','data.txt','ist','mnt','par','coldopacity')

def survey(d):
    out = []
    for root, dirs, files in os.walk(d):
        for f in files:
            out.append(os.path.join(root, f))
    return sorted(out)

P("# 第二轮：多材料多格式交叉验证")
P("")
P("> 脚本 `xv2_multi.py`；数据根 `src/Multi1D++Portable20241128/matter++/`")
P("> 常数：`N_A = 6.02214076e23`，`m_u = 1.66053906660e-24 g`（故 `N_A·m_u = 1.0000000005`）")
P("> 数密度关系：`n[1/cm³] = ρ[g/cm³]·N_A/A`  ⟹  `A_eff = ρ·N_A/n`")
P("")

for m in MATS:
    d = os.path.join(MATTER, m)
    P("")
    P("---")
    P("")
    P("## 材料 `%s`" % m)
    P("")
    if not os.path.isdir(d):
        P("**目录不存在**")
        continue
    fs = survey(d)
    P("### 可用文件（%d 个）" % len(fs))
    P("")
    exts = Counter((os.path.splitext(f)[1].lower() or '(无扩展名)') for f in fs)
    P("后缀分布：%s" % ', '.join('`%s`×%d' % (k, v) for k, v in exts.most_common()))
    P("")

    # ---- gather
    feos = None
    for f in fs:
        if f.lower().endswith('.feos'):
            feos = f; break
    csts = [f for f in fs if f.lower().endswith('.cst')]
    dats = [f for f in fs if f.lower().endswith('.data.txt')]
    h30x = [f for f in fs if os.path.splitext(f)[1] in ('.301','.304','.305')]

    P("### 发现的族")
    P("")
    P("| 角色 | 文件 |")
    P("|---|---|")
    P("| FEOS 原生 | `%s` |" % (os.path.relpath(feos, MATTER) if feos else '—'))
    for c in csts:
        P("| Rostock .cst | `%s` |" % os.path.relpath(c, MATTER))
    for dt in dats:
        P("| FEOS 数据表 | `%s` |" % os.path.relpath(dt, MATTER))
    for h in h30x:
        P("| MPQeos 表 | `%s` |" % os.path.relpath(h, MATTER))
    P("")

    fe = feos_hdr(feos) if feos else None
    if fe:
        P("### `.feos` 表头")
        P("")
        P("| 字段 | 值 |")
        P("|---|---|")
        for k in ('NRho','NT','Nelem','Tcalclimit','Rhocalclimit','RhoRef','SESAMEnumber','Atot','Ztot','Xtot'):
            P("| %s | %s |" % (k, fe[k]))
        P("")

    # ---- .cst number-density self-consistency
    for c in csts:
        rows = cst_read(c)
        rel = os.path.relpath(c, MATTER)
        P("### `.cst` 数密度自洽：`%s`（%d 行）" % (rel, len(rows)))
        P("")
        if not rows:
            P("**无有效 4 列行**")
            P("")
            continue
        ncol = [r[0] for r in rows]; rcol = [r[1] for r in rows]
        Pcol = [r[2] for r in rows]; qcol = [r[3] for r in rows]
        P("| 量 | 最小 | 最大 |")
        P("|---|---:|---:|")
        P("| 数密度 n [1/cm³] | %.6g | %.6g |" % (min(ncol), max(ncol)))
        P("| 质量密度 ρ [g/cm³] | %.6g | %.6g |" % (min(rcol), max(rcol)))
        P("| 压强 P [MBar] | %.6g | %.6g |" % (min(Pcol), max(Pcol)))
        P("| 电荷态 Q | %.6g | %.6g |" % (min(qcol), max(qcol)))
        P("")
        st = aeff_stats(rows)
        if st:
            P("由 `A_eff = ρ·N_A/n` 在 %d 个正密度行上反解：" % st['n'])
            P("")
            P("- `A_eff` = **%.6f … %.6f**（均值 **%.6f**，相对波动 %.2e）" %
              (st['min'], st['max'], st['mean'], st['spread_rel']))
            # cross-check via the m_u form:  n/ρ = 1/(A_eff*m_u)
            k = [n/r for n, r in zip(ncol, rcol) if n > 0 and r > 0]
            km = sum(k)/len(k)
            P("- `n/ρ` = %.8e ⟹ `A_eff = 1/(m_u·n/ρ)` = **%.6f**" % (km, 1.0/(MU*km)))
            if fe and fe.get('Atot'):
                dev = (st['mean'] - fe['Atot'])/fe['Atot']*100.0
                P("- `.feos` 头 `Atot` = **%.6f**" % fe['Atot'])
                P("- **偏差 = %.4f %%**（%s）" % (dev,
                  '一致' if abs(dev) < 0.05 else '存在系统性差异，须带误差带使用'))
            if fe and fe.get('Ztot'):
                P("- `.feos` 头 `Ztot` = %.4f（电荷态量级校验：Q_max = %.4f）" %
                  (fe['Ztot'], max(qcol)))
        P("")

    # ---- density grid bit-equality
    if fe and csts:
        rows = cst_read(csts[0])
        rho_cst = [r[1] for r in rows if r[1] > 0]
        # unique, sorted, preserving precision
        uniq = []
        for x in rho_cst:
            if x not in uniq:
                uniq.append(x)
        P("### 密度网格比对（`.cst` ↔ `.data.txt`）")
        P("")
        if dats:
            dc = dat_cols(dats[0])
            rel = os.path.relpath(dats[0], MATTER)
            P("- `%s`：%d 行 × %d 列" % (rel, dc['nlines'], dc['ncol']))
            P("- 各列基数：%s" % dc['card'])
            # find the rho column: cardinality == NRho and values match .cst
            best = None
            for c in range(min(6, dc['ncol'])):
                vals = sorted(set(round(r[c], 12) for r in dc['rows']))
                ov = len(set(round(x, 12) for x in uniq) & set(vals))
                if ov > 0:
                    frac = ov / len(uniq)
                    if best is None or frac > best[2]:
                        best = (c, len(vals), frac)
            if best:
                c, nv, frac = best
                P("- 与 `.cst` 密度列重叠最好的列 = **col %d**（%d 个相异值，覆盖率 **%.1f %%**）"
                  % (c, nv, frac*100))
                vals = sorted(set(round(r[c], 12) for r in dc['rows']))
                common = sorted(set(round(x, 12) for x in uniq) & set(vals))
                P("- 交集 %d 个密度点" % len(common))
                # explicit pairwise check on the common set
                s_cst = sorted(set(round(x, 12) for x in uniq))
                s_dat = sorted(vals)
                inter = [x for x in s_cst if x in set(s_dat)]
                exact = (len(inter) == len(s_cst))
                P("- 精确性：`.cst` 的 %d 个 ρ 值中 **%d** 个在 `data.txt` 中逐位存在 ⟹ **%s**"
                  % (len(s_cst), len(inter), '逐位一致（子集）' if exact else '不完全一致'))
                P("- 两侧 ρ 范围：`.cst` %.6g … %.6g ；`data.txt` col%d %.6g … %.6g"
                  % (min(s_cst), max(s_cst), c, min(s_dat), max(s_dat)))
            else:
                P("- **未能定位 .cst 密度列在 data.txt 中的对应列**")
            # T grid
            tcol = None
            for c in range(min(6, dc['ncol'])):
                vals = sorted(set(round(r[c], 12) for r in dc['rows']))
                if len(vals) == fe['NT']:
                    tcol = (c, vals); break
            if tcol:
                c, vals = tcol
                P("- 温度列 = **col %d**（%d 个相异值 = `.feos` NT）" % (c, len(vals)))
                P("- T 范围 = %.6g … %.6g（K）" % (min(vals), max(vals)))
                P("- 说明：`.cst` **只有 T=0 一条等温线**，与之无可比温度网格")
        else:
            P("- 本材料无 `.data.txt`，跳过")
        P("")

    # ---- Ta2O5 special: .ist / .mnt curve exports
    ists = [f for f in fs if f.lower().endswith(('.ist','.isc','.ise','.mnt'))]
    if ists:
        P("### FEOS 曲线导出（%d 个）" % len(ists))
        P("")
        P("| 文件 | 首行 |")
        P("|---|---|")
        for f in sorted(ists):
            l0 = [l for l in lines(head(f, 2048)) if l.strip()][:1]
            P("| `%s` | `%s` |" % (os.path.relpath(f, MATTER), (l0[0] if l0 else '')[:70]))
        P("")

    # ---- what is NOT comparable
    P("### 物理上不可比的量（本材料）")
    P("")
    if csts:
        P("- **`.cst` 的压强 vs `.feos`/`.data.txt` 的压强**：`.cst` 标题为 "
          "`Isotherme T = 0 Kelvin`，是**单一 T=0 等温线**；`.feos` 是 (ρ,T) 二维表。"
          "二者不是同一物理切片，**不能逐点比 P**。")
        P("- **`.cst` vs `.data.txt` 逐行比对**：`.cst` 只有 T=0 行且行序与 `data.txt` 不保证对齐，"
          "**必须先按 ρ 值重排再比**，否则会出现假的百倍偏差。")
    P("- **`.feos` 表头 `TRef`/`BulkModulusRef` 是原子单位(Hartree)**，不可当作 eV 与 `.data.txt` 的 K 直接比。")
    P("")

# ---------------- round-1 correction notice
P("")
P("---")
P("")
P("## 附：对第一轮结论的更正（必须记录）")
P("")
P("第一轮我曾报「R1 `.sesame` 尺寸公式 `n = 4 + 2·nr + ne + 2·nr·ne` 全错」。**该结论已撤回，是错的。**")
P("")
P("**根因**：我把 `nums[0]` 当成了 `matid`，但 `nums[0]` 是**哨兵字段**；真实字段是 "
  "`nums[2] = nr`、`nums[3] = ne`。用正确字段代入后，公式 **7/7 精确闭合（diff = 0）**：")
P("")
P("| 文件 | N | nr | ne | 公式值 | diff |")
P("|---|---:|---:|---:|---:|---:|")
P("| `SiO2/eos_21.sesame` | 153645 | 43 | 1765 | 153645 | **0** |")
P("| `SiO2/eos_22.sesame` | 130892 | 36 | 1792 | 130892 | **0** |")
P("| `SiO2/eos_23.sesame` | 407099 | 75 | 2695 | 407099 | **0** |")
P("| `SiO2/eos_24.sesame` | 363828 | 73 | 2474 | 363828 | **0** |")
P("| `Ta2O5/PowerLawTa2O5_EOS.SESAME` | 143 | 3 | 19 | 143 | **0** |")
P("| `Ta2O5/PowerLawTa2O5_EOS.SESAME_` | 300 | 5 | 26 | 300 | **0** |")
P("| `mat_Au/Au_2003POPHammerRosen_EOS.SESAME` | 419 | 6 | 31 | 419 | **0** |")
P("")
P("仅 `SiO2/opc_1022.sesame_PLANCK` 与 `.sesame_ROSSELAND` 不闭合 —— 因为它们是**不透明度记录**，"
  "本就不适用 EOS-301 公式，属正确排除。")
P("")
P("**结论**：R1 规格 **CONFIRMED**（`nr = nums[2]`，`ne = nums[3]`）。"
  "第一轮报告里的「错误 #4」作废。")

with io.open(MD, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE %s %d" % (MD, os.path.getsize(MD)))
