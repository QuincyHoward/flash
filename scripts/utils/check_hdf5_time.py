import h5py, glob, os

wsl_dir = r'scenarios\flash_demo\hello_flash\outputfiles\hdf5files\laserslab1d'
ssh1_dir = r'scenarios\flash_demo\hello_flash\outputfiles\hdf5filesfrom_ssh1\laserslab1d'

for label, d in [('WSL', wsl_dir), ('SSH1', ssh1_dir)]:
    files = sorted(glob.glob(os.path.join(d, '*hdf5_plt_cnt_*')))
    print(f'{label}: {len(files)} plot files')
    if files:
        with h5py.File(files[-1], 'r') as f:
            if 'real scalars' in f:
                for row in f['real scalars']:
                    name = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
                    if 'time' in name.lower():
                        print(f'  Last plot time: {row[1]}')
                        break
            if 'integer scalars' in f:
                for row in f['integer scalars']:
                    name = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
                    if 'nstep' in name.lower():
                        print(f'  Last nstep: {row[1]}')
                        break
