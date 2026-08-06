import h5py
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
file = sorted(OUTPUT_DIR.glob("lasslab_hdf5_plt_cnt_0000*"))[0]

with h5py.File(str(file), "r") as f:
    print("Key datasets:")
    dens = f["dens"]
    print(f"  dens shape: {dens.shape}")
    
    coords = f["coordinates"]
    print(f"  coordinates shape: {coords.shape}")
    print(f"  coordinates[:10]: {coords[:10].flatten()}")
    print(f"  coordinates[-10:]: {coords[-10:].flatten()}")
    
    bbox = f["bounding box"]
    print(f"  bounding box shape: {bbox.shape}")
    print(f"  bbox[:3]: {bbox[:3]}")
    
    # Let's read the actual dens data and flatten it
    d = dens[:]
    print(f"  dens flat shape: {d.flatten().shape}")
    print(f"  dens min: {d.min()}, max: {d.max()}")
    
    # For 1D: each block has NXB cells. We need coordinates for each cell.
    # Let me try to reconstruct from bbox
    print("\nReconstructing coordinates from bbox:")
    nblocks = bbox.shape[0]
    nx = dens.shape[3]
    all_x = []
    all_d = []
    for b in range(min(nblocks, 5)):  # show first 5 blocks
        xmin = bbox[b, 0, 0]
        xmax = bbox[b, 0, 1]
        x_cells = np.linspace(xmin, xmax, nx + 1)
        x_center = (x_cells[:-1] + x_cells[1:]) / 2
        block_dens = d[b, 0, 0, :]
        all_x.append(x_center)
        all_d.append(block_dens)
        print(f"  Block {b}: x=[{xmin:.6e}, {xmax:.6e}], dens={block_dens}")

    all_x = np.concatenate(all_x)
    all_d = np.concatenate(all_d)
    
    # Sort by x
    idx = np.argsort(all_x)
    all_x = all_x[idx]
    all_d = all_d[idx]
    
    print(f"\nSorted full x range: [{all_x[0]:.6e}, {all_x[-1]:.6e}]")
    print(f"Sorted full dens range: [{all_d.min():.4e}, {all_d.max():.4f}]")
    
    # Check the three zones
    vac = all_d[all_x < 0.014]
    targ = all_d[(all_x >= 0.014) & (all_x < 0.016)]
    poly = all_d[all_x >= 0.016]
    print(f"\nVacuum zone: mean = {vac.mean():.4e}, n={len(vac)}")
    print(f"Targ zone: mean = {targ.mean():.4f}, n={len(targ)}")
    print(f"Poly zone: mean = {poly.mean():.4f}, n={len(poly)}")
    
    # Check species
    poly_species = f["poly"][:]
    poly_flat = poly_species.flatten()[idx]
    poly_zone_frac = poly_flat[all_x >= 0.016].mean()
    print(f"poly mass fraction in poly zone: {poly_zone_frac:.4f}")
