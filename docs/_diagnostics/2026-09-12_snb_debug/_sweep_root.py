# -*- coding: utf-8 -*-
"""收尾: 把残留在根目录的 _* 文件、']' 垃圾文件、%SystemDrive% 垃圾目录处理掉。"""
import io, os, shutil
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")
os.makedirs(DEST, exist_ok=True)

moved, junk = [], []
for f in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        continue
    if f.startswith("_") or f == "]":
        if f in ("_wsl_fix3.txt", "_nce_rerun.txt", "_nce_short_run.txt"):
            # 这三个可能仍被运行中的任务写入 → 复制而非移动, 保留原位供轮询
            try:
                shutil.copy2(p, os.path.join(DEST, f))
                moved.append((f, "copy"))
            except Exception as ex:
                print(f"  [FAIL-copy] {f}: {ex}")
        else:
            try:
                shutil.move(p, os.path.join(DEST, f))
                moved.append((f, "move"))
            except Exception as ex:
                print(f"  [FAIL-move] {f}: {ex}")

# %SystemDrive% 垃圾目录 (环境变量未展开导致)
sd = os.path.join(ROOT, "%SystemDrive%")
if os.path.isdir(sd):
    for root_, ds, fs in os.walk(sd):
        for x in fs:
            print(f"  [junk-dir] {os.path.relpath(os.path.join(root_,x), ROOT)}  "
                  f"{os.path.getsize(os.path.join(root_,x))} B")
    print(f"  ★ %SystemDrive%/ 内容如上 (仅列出, 未删除)")

print(f"\n处理 {len(moved)} 项:")
for f, act in moved:
    print(f"  [{act}] {f}")

files = sorted(f for f in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, f)))
print(f"\n根目录剩余文件 ({len(files)}):")
for f in files:
    print(f"  {os.path.getsize(os.path.join(ROOT,f)):>10,}  {f}")
