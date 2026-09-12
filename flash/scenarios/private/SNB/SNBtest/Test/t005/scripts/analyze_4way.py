"""修复后四腿逐帧定量分析 (t005, 作者原版驱动 + dtmax=2e-12)。"""
import sys
from pathlib import Path
import h5py
import numpy as np

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else
            r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
            r'\scenarios\private\SNB\SNBtest\Test\t005\scene\flash_output')


def scalar(f, want='time'):
    arr = f['real scalars'][()]
    for n, v in zip(arr['name'], arr['value']):
        if n.decode().strip() == want:
            return float(v)
    return float('nan')


def get(f, key):
    o = f[key]
    if isinstance(o, h5py.Dataset):
        return np.asarray(o).ravel()
    return np.concatenate([np.asarray(o[k]).ravel() for k in o.keys()])


def coords(f):
    c = f['coordinates']
    if isinstance(c, h5py.Dataset):
        return np.asarray(c)
    return np.vstack([np.asarray(c[k]) for k in c.keys()])


def x_nodes(f, nxb=128):
    """重建节点坐标 (µm): 块中心 + linspace, 每块左闭右开。"""
    c = coords(f)
    xs = []
    for blk in c:
        lo = blk[0] - (blk[0] - blk[0])  # placeholder
    # 用 bounding box 更稳妥
    bb = np.asarray(f['bounding box'][()]).ravel()
    lo, hi = float(bb[0]), float(bb[1])
    return np.linspace(lo, hi, nxb + 1)[:-1] * 1e4


print(f'{"leg/tag":14s} {"t[ps]":>8s} {"rho_max":>10s} {"M_tot":>12s} '
      f'{"Te_max[eV]":>11s} {"Trad_max":>10s}')
for leg in ('snb', 'flsh'):
    for tag in ('radon', 'radoff'):
        d = BASE / f'sim_{leg}' / tag
        chks = sorted(d.glob(f'{leg}_{tag}_hdf5_chk_*'))
        if not chks:
            print(f'{leg}/{tag}: MISSING')
            continue
        rows = []
        for c in chks:
            with h5py.File(c, 'r') as f:
                t = scalar(f)
                rho = get(f, 'dens')
                te = get(f, 'tele') if 'tele' in f else None
                tr = get(f, 'trad') if 'trad' in f else None
            rows.append((t, rho.max(), rho.sum(), 
                         te.max() if te is not None else np.nan,
                         tr.max() if tr is not None else np.nan))
        for i in (0, len(rows) // 4, len(rows) // 2, len(rows) - 1):
            t, rmax, rsum, tem, trm = rows[i]
            print(f'{leg + "/" + tag:14s} {t * 1e9:8.1f} {rmax:10.4f} '
                  f'{rsum:12.1f} {tem:11.2f} {trm:10.4e}')
        print()
