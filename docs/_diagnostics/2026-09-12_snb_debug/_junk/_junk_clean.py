# -*- coding: utf-8 -*-
"""清掉 3 个误建垃圾文件, 并做最终校验。"""
import io, os, shutil
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")
JUNK = ["0.03\u00b5m", "56", "]"]

for j in JUNK:
    p = os.path.join(ROOT, j)
    if os.path.exists(p) and os.path.isfile(p):
        sz = os.path.getsize(p)
        d = os.path.join(DEST, "_junk", j)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.move(p, d)
        print(f"  [junk->archive] {j}  ({sz} B)")

files = sorted(f for f in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, f)))
dirs = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
print(f"\n=== 根目录文件 ({len(files)}) ===")
for f in files:
    print(f"  {os.path.getsize(os.path.join(ROOT,f)):>10,}  {f}")
print(f"\n=== 根目录子目录 ({len(dirs)}) ===")
for d in dirs:
    try:
        n = len(os.listdir(os.path.join(ROOT, d)))
    except Exception:
        n = -1
    print(f"  {n:>7} 项  {d}/")
print(f"\n归档目录条目数: {len(os.listdir(DEST))}")
