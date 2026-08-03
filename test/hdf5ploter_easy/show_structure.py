import h5py
f=h5py.File('lasslab_hdf5_plt_cnt_0066','r')
from collections import defaultdict

groups=defaultdict(list)
for k in f:
    d=f[k]
    if isinstance(d, h5py.Dataset):
        sig=(tuple(d.shape), str(d.dtype))
        groups[sig].append(k)

lines=['=== FLASH HDF5 PLT structure ===\n']
for sig, names in sorted(groups.items(), key=lambda x:-len(x[1])):
    shape, dtype = sig
    if len(names)>2:
        lines.append(f'  [{shape}, {dtype}] x{len(names)}: {", ".join(names)}\n')
    else:
        for n in names:
            lines.append(f'  [{n}] shape={shape} dtype={dtype}\n')

lines.append('\n=== Group hierarchy check ===\n')
try:
    f['flash']
    lines.append('  [flash] group exists! Try f["flash"]["dens"]\n')
except KeyError:
    lines.append('  No group nesting, all data flat at root level\n')

lines.append('\n=== Direct access test ===\n')
try:
    d=f['dens']
    lines.append(f'  f["dens"] -> shape={d.shape}, access OK\n')
except:
    lines.append('  f["dens"] unavailable\n')

try:
    x=f['coordinates']
    lines.append(f'  f["coordinates"] -> shape={x.shape}, dtype={x.dtype}\n')
    lines.append('  One (x,y,z) center per block, not per-cell coords\n')
except:
    lines.append('  f["coordinates"] unavailable\n')

lines.append('\nConclusion: cannot use f["flash"]["dens"] path\n')
lines.append('Position must be reconstructed from bounding box (see plot_dens.py)\n')

# UTF-8 file (avoids cp936 garbling on Windows)
open('hdf5_structure.txt','w',encoding='utf-8').writelines(lines)
print('Structure saved to hdf5_structure.txt (UTF-8)')
