"""列出 chk 中 real scalars 的字段名与可用量。"""
import sys
from pathlib import Path
import h5py
import numpy as np

p = Path(sys.argv[1])
with h5py.File(p, 'r') as f:
    print('keys:', list(f.keys()))
    rs = f['real scalars']
    print('real scalars type:', type(rs))
    if hasattr(rs, 'dtype') and rs.dtype.names:
        print('fields:', rs.dtype.names)
        arr = rs[()]
        for n in rs.dtype.names:
            print(f'   {n:28s} = {np.array(arr[n]).ravel()[0]}')
    for k in list(f.keys()):
        o = f[k]
        if isinstance(o, h5py.Group):
            print(f'Group {k}: subkeys={list(o.keys())[:20]}')
