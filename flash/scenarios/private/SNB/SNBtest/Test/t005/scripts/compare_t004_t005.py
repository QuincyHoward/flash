"""对比 t004 (成功基线) 与 t005 (修复后) 的 SNB 腿逐帧量。"""
import sys
from pathlib import Path
import h5py
import numpy as np

RUNS = {
    't004/snb/radon': Path(r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
                           r'\scenarios\private\SNB\SNBtest\Test\t004\sim_snb'
                           r'\flash_output\radon'),
    't005/snb/radon': Path(r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash'
                           r'\scenarios\private\SNB\SNBtest\Test\t005\scene'
                           r'\flash_output\sim_snb\radon'),
}


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


for lbl, d in RUNS.items():
    chks = sorted(d.glob('*chk_*'))
    print(f'=== {lbl}  ({len(chks)} chk)  dir={d.name}')
    if not chks:
        print('   MISSING'); continue
    print(f'   {"t[ps]":>8s} {"rho_max":>10s} {"rho_min":>10s} '
          f'{"Te_max[eV]":>13s} {"Tion_max":>11s} {"Ye_max":>8s}')
    for i in (0, len(chks) // 4, len(chks) // 2, len(chks) - 1):
        with h5py.File(chks[i], 'r') as f:
            t = scalar(f)
            rho = get(f, 'dens')
            te = get(f, 'tele') if 'tele' in f else np.array([np.nan])
            ti = get(f, 'tion') if 'tion' in f else np.array([np.nan])
            ye = get(f, 'ye') if 'ye' in f else np.array([np.nan])
        print(f'   {t * 1e9:8.1f} {rho.max():10.4f} {rho.min():10.3e} '
              f'{np.nanmax(te):13.2f} {np.nanmax(ti):11.2f} {np.nanmax(ye):8.4f}')
    print()
