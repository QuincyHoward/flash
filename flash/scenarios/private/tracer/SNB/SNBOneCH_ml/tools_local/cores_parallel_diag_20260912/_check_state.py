import os, json, glob, hashlib
from pathlib import Path

SC = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
CP = SC / "flash_output" / "hpc_flash_ssh" / "cores_parallel"

print("=== cores_parallel tree ===")
if CP.exists():
    for n in sorted(CP.iterdir()):
        if n.is_dir():
            print(f"[{n.name}]")
            for f in sorted(n.iterdir()):
                print(f"   {f.stat().st_size:>12,}  {f.name}")
else:
    print("MISSING:", CP)

print("\n=== root pollution check (SC root) ===")
for f in sorted(SC.glob("*")):
    if f.is_file():
        print(f"   {f.stat().st_size:>12,}  {f.name}")

print("\n=== state json ===")
sj = SC / "cores_parallel_jobs.json"
if sj.exists():
    print(sj.read_text(encoding="utf-8"))

print("\n=== health json ===")
hj = SC / "flash_output" / "cores_parallel_health.json"
if hj.exists():
    print(hj.read_text(encoding="utf-8")[:3000])
else:
    print("no health json at", hj)
