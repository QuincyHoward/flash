# -*- coding: utf-8 -*-
"""最终清扫: 把根目录所有 `_*` 文件 (除 3 个运行中任务的 txt) 移入归档。"""
import io, os, shutil
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")
os.makedirs(DEST, exist_ok=True)
KEEP_IN_PLACE = {"_wsl_fix3.txt", "_nce_rerun.txt", "_nce_short_run.txt"}

moved = []
for f in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        continue
    if f.startswith("_") or f == "]":
        if f in KEEP_IN_PLACE:
            shutil.copy2(p, os.path.join(DEST, f))
            moved.append((f, "copy"))
        else:
            try:
                shutil.move(p, os.path.join(DEST, f))
                moved.append((f, "move"))
            except Exception as ex:
                print(f"  [FAIL] {f}: {ex}")

print(f"处理 {len(moved)}:")
for f, a in moved:
    print(f"  [{a}] {f}")

files = sorted(f for f in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, f)))
print(f"\n根目录剩余文件 ({len(files)}):")
for f in files:
    print(f"  {os.path.getsize(os.path.join(ROOT,f)):>10,}  {f}")
print(f"\n归档目录条目数: {len(os.listdir(DEST))}")
