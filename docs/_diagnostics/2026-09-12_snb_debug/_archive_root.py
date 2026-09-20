# -*- coding: utf-8 -*-
"""把 flash 工作区根目录的临时诊断脚本/日志收纳到 docs/_diagnostics/ 下。

规则:
  - 只移动 `_` 前缀文件 (临时诊断, 历史惯例)
  - 保留合法项目文件 (.md/.toml/start_flash.py/LICENSE/NOTICE/Makefile/...)
  - quick_test_1d.h5 (1.9MB 测试产物) 也收走
  - 不删除任何东西, 只移动 → 可逆
默认 dry-run, 加 --apply 才真正移动。
"""
import io
import os
import shutil
import sys

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")

# 根目录必须保留的项目文件 (大小写敏感)
KEEP = {
    ".gitattributes", ".gitignore", ".pre-commit-config.yaml",
    "INSTALL_TEST_REPORT.txt", "LICENSE", "NOTICE", "Makefile",
    "README.md", "pyproject.toml", "start_flash.py",
    "pytest_framework.log", "pytest_input_gen.log",
    "pytest_output_processors.log",
}

# 明确要收走的非 `_` 前缀文件
#   quick_test_1d.h5 : 1.9MB 早期测试产物
#   "]"              : 误创建的垃圾文件 (疑似重定向笔误)
ALSO_MOVE = {"quick_test_1d.h5", "]"}

APPLY = "--apply" in sys.argv


def main():
    entries = os.listdir(ROOT)
    files, dirs = [], []
    for e in entries:
        p = os.path.join(ROOT, e)
        if os.path.isdir(p):
            dirs.append(e)
        else:
            files.append(e)

    move = []
    keep_report = []
    for f in sorted(files):
        if f in KEEP:
            keep_report.append(f)
            continue
        if f.startswith("_") or f in ALSO_MOVE:
            move.append(f)
        else:
            keep_report.append(f)

    print("=" * 70)
    print(f"根目录: {ROOT}")
    print(f"  文件 {len(files)} 个 | 目录 {len(dirs)} 个")
    print("=" * 70)
    print(f"\n--- 将收纳 ({len(move)}) ---")
    tot = 0
    for f in move:
        sz = os.path.getsize(os.path.join(ROOT, f))
        tot += sz
        print(f"  {sz:>10,}  {f}")
    print(f"  合计 {tot/1024/1024:.2f} MB")

    print(f"\n--- 保留在根目录 ({len(keep_report)}) ---")
    for f in keep_report:
        print(f"  {os.path.getsize(os.path.join(ROOT, f)):>10,}  {f}")

    print(f"\n--- 子目录 ({len(dirs)}) ---")
    for d in sorted(dirs):
        try:
            n = len(os.listdir(os.path.join(ROOT, d)))
        except Exception:
            n = -1
        print(f"  {n:>7} 项  {d}/")

    if not APPLY:
        print("\n[DRY-RUN] 未做任何改动。加 --apply 执行。")
        return

    os.makedirs(DEST, exist_ok=True)
    ok, fail = 0, 0
    for f in move:
        src = os.path.join(ROOT, f)
        dst = os.path.join(DEST, f)
        try:
            shutil.move(src, dst)
            ok += 1
        except Exception as ex:
            fail += 1
            print(f"  [FAIL] {f}: {ex}")
    print(f"\n[APPLY] 移动成功 {ok} / 失败 {fail} → {DEST}")

    with io.open(os.path.join(DEST, "_INDEX.txt"), "w", encoding="utf-8") as fh:
        fh.write("flash 工作区根目录临时诊断文件归档\n")
        fh.write("归档时间: 2026-09-12\n")
        fh.write(f"来源: {ROOT}\n")
        fh.write(f"数量: {ok}\n")
        fh.write("性质: 均为 SNBOneCH_ml 场景调参期的临时探测脚本/日志/中间产物\n")
        fh.write("注意: 只做移动, 未删除; 需要时可原路移回。\n")
    print(f"[APPLY] 已写入 _INDEX.txt")


main()
