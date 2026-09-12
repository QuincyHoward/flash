"""四腿密度演化快速核查 (t005, 判断 SNB 是否崩塌)。

chk 直读布局 (本 +ug 场景):
  - 'real scalars' 是复合 Dataset (dtype.names = ('name','value')), 取 time
  - 变量以 'dens' 为 Dataset, shape (nb,1,1,nxb) 或 (nb,nxb)
"""
import sys
from pathlib import Path
import h5py
import numpy as np

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else
            r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
            r'\scenarios\private\SNB\SNBtest\Test\t005\scene\flash_output')


def scalar(f, want='time'):
    rs = f['real scalars']
    arr = rs[()]
    for n, v in zip(arr['name'], arr['value']):
        if n.decode().strip() == want:
            return float(v)
    return float('nan')


def get(f, key):
    """读变量: 兼容 Dataset(直读, +ug 每进程一块) 与 Group(每块一子键) 两种布局。"""
    o = f[key]
    if isinstance(o, h5py.Dataset):
        return np.asarray(o).ravel()
    return np.concatenate([np.array(o[k]).ravel() for k in o.keys()])


def dens(f):
    return get(f, 'dens')


for leg in ('snb', 'flsh'):
    for tag in ('radon', 'radoff'):
        d = BASE / f'sim_{leg}' / tag
        chks = sorted(d.glob(f'{leg}_{tag}_hdf5_chk_*')) if d.exists() else []
        if not chks:
            print(f'{leg:4s}/{tag:6s} MISSING  {d}')
            continue
        print(f'--- {leg}/{tag}  ({len(chks)} chk)')
        idx = sorted({0, len(chks) // 4, len(chks) // 2, len(chks) - 1})
        for i in idx:
            with h5py.File(chks[i], 'r') as f:
                t = scalar(f)
                r = dens(f)
            print(f'      t={t * 1e9:7.1f} ps   rho_max={r.max():9.4f}'
                  f'   rho_min={r.min():10.3e}')
