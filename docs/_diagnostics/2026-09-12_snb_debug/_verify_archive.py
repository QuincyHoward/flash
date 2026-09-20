# -*- coding: utf-8 -*-
import io, os
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")
files = sorted(f for f in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, f)))
dirs = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
print(f"=== 根目录文件 ({len(files)}) ===")
for f in files:
    print(f"  {os.path.getsize(os.path.join(ROOT,f)):>10,}  {f}")
print(f"\n=== 根目录子目录 ({len(dirs)}) ===")
for d in dirs:
    try:
        n = len(os.listdir(os.path.join(ROOT, d)))
    except Exception:
        n = -1
    print(f"  {n:>7} 项  {d}/")
print(f"\n=== 归档目录 ===")
if os.path.isdir(DEST):
    a = sorted(os.listdir(DEST))
    print(f"  存在: {DEST}")
    print(f"  条目数: {len(a)}")
    print(f"  前 8: {a[:8]}")
else:
    print(f"  ★ 不存在: {DEST}")
