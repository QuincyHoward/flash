import os, json
from pathlib import Path
import numpy as np
import h5py

SC = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")

print("="*100)
print("PAR CHECK: xmin/xmax/geometry")
print("="*100)
# locate the par actually used
cands = list(SC.rglob("*.par"))
for p in cands:
    print("  par:", p.relative_to(SC), p.stat().st_size)
