"""穷尽比对 t004 与 t005 的 SNB 侧 flash_input 全部文件 (含非 F90)。"""
import hashlib
from pathlib import Path

T004 = Path(r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
            r'\scenarios\private\SNB\SNBtest\Test\t004\sim_snb\flash_input')
T005 = Path(r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
            r'\scenarios\private\SNB\SNBtest\Test\t005\scene\sim_snb\flash_input')


def h(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12], p.stat().st_size


def norm(names):
    """把 t004<->t005 的文件名归一 (t004snb_* vs snb_*)。"""
    out = {}
    for n in names:
        k = n
        for pre in ('t004snb_', 'snb_'):
            if k.startswith(pre):
                k = k[len(pre):]
                break
        out[k] = n
    return out


a = norm([p.name for p in T004.iterdir() if p.is_file()])
b = norm([p.name for p in T005.iterdir() if p.is_file()])
print(f't004 files={len(a)}  t005 files={len(b)}')
print('\n=== 仅 t004 有 ===')
for k in sorted(set(a) - set(b)):
    print(f'   {k:50s} {h(T004 / a[k])}')
print('\n=== 仅 t005 有 ===')
for k in sorted(set(b) - set(a)):
    print(f'   {k:50s} {h(T005 / b[k])}')
print('\n=== 同名文件内容比对 ===')
same = diff = 0
for k in sorted(set(a) & set(b)):
    ha, sa = h(T004 / a[k])
    hb, sb = h(T005 / b[k])
    if ha == hb:
        same += 1
        print(f'   [SAME] {k:48s} {sa}')
    else:
        diff += 1
        print(f'   [DIFF] {k:48s} t004={sa:9d}/{ha}  t005={sb:9d}/{hb}')
print(f'\n汇总: same={same}  diff={diff}')
