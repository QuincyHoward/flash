#!/usr/bin/env python3
r"""
USB 备份脚本 - 将项目复制到 U 盘或本地目录 (支持多种模式)
=================================================================

模式:
  gitee   仿 Gitee 仓库备份: 使用 .gitignore/.gitattributes 规则,
          备份内容 = 推送到 Gitee 仓库的内容 (不运行测试, 不含 .git)
          - 文件列表来自 `git ls-files` (索引 + 未跟踪且未被忽略)
          - 文本文件按 .gitattributes 规范化为 LF 行尾
  full    几乎全量备份: 仅使用脚本内 EXCLUDE_DIRS / EXCLUDE_FILES 排除

使用方法:
  python usb_backup.py [目标路径]                # 默认 gitee 模式
  python usb_backup.py --mode gitee E:\          # 仿 Gitee 备份到 U 盘
  python usb_backup.py --mode full  E:\          # 几乎全量备份到 U 盘
  python usb_backup.py --dest D:\backups         # 指定目标目录 (不存在时自动创建)
  python usb_backup.py --name flash_release      # 自定义备份目录名
  python usb_backup.py -n                        # dry-run 试运行 (不复制)

支持备份到任意目录 (U 盘/本地/深层路径均可, 目标不存在会自动创建)。
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ============================================================================
#  full 模式: 排除目录/文件 (脚本内规则)
# ============================================================================
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "build",
    "dist",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    "temp_delete",
    # ".workbuddy",
    # ".codebuddy",
}

EXCLUDE_FILES = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.exe",
    "*.log",
    "*.tmp",
    ".pre-commit-config.yaml",
}


def should_exclude(path: Path) -> bool:
    """检查路径是否应该被排除 (full 模式)"""
    # 检查目录
    for part in path.parts:
        if part in EXCLUDE_DIRS or any(
            part.endswith(ext[1:]) for ext in EXCLUDE_DIRS if ext.startswith("*")
        ):
            return True

    # 检查文件
    if path.is_file():
        for pattern in EXCLUDE_FILES:
            if pattern.startswith("*"):
                if path.name.endswith(pattern[1:]):
                    return True
            elif path.name == pattern:
                return True

    return False


# ============================================================================
#  gitee 模式: 解析 .gitattributes → (binary_exts, text_names)
# ============================================================================
def parse_gitattributes():
    """解析 .gitattributes, 返回 (binary_exts:set, text_names:set)

    binary_exts: 标记为 binary 的扩展名 (如 png, pdf, h5)
    text_names:  标记为 text 的无扩展名文件名 (如 Makefile, README)
    """
    binary_exts = set()
    text_names = set()
    ga = PROJECT_ROOT / ".gitattributes"
    if not ga.exists():
        return binary_exts, text_names

    for line in ga.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pat, attrs = parts[0], parts[1:]
        if "binary" in attrs:
            if pat.startswith("*."):
                binary_exts.add(pat[2:].lower())
        elif any(a.startswith("text") for a in attrs):
            if not pat.startswith("*."):
                text_names.add(pat.lower())
    return binary_exts, text_names


def list_gitee_files() -> list:
    """获取仿 Gitee 备份的文件列表 (相对项目根目录)

    等价于 `git add -A` 后 `git status --porcelain` 所覆盖的文件:
      - 索引中的已跟踪文件
      - 未跟踪且未被 .gitignore 忽略的文件
    """
    cmd = ["git", "-c", "core.quotepath=false",
           "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"❌ git ls-files 失败: {r.stderr.strip()}")
        sys.exit(1)
    return [p for p in r.stdout.split("\0") if p]


def copy_file_with_lf(src: Path, dst: Path, binary_exts: set) -> str:
    """复制文件; 文本文件按 .gitattributes 规范化为 LF 行尾.

    返回: "copy"(原样复制) | "lf"(LF 规范化) | "bin"(二进制)
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    ext = src.suffix[1:].lower() if src.suffix else ""
    if ext in binary_exts:
        shutil.copy2(src, dst)
        return "bin"
    # 文本尝试: 内容含 NUL 视为二进制
    data = src.read_bytes()
    if b"\x00" in data:
        shutil.copy2(src, dst)
        return "bin"
    norm = data.replace(b"\r\n", b"\n")
    if norm != data:
        dst.write_bytes(norm)
        return "lf"
    shutil.copy2(src, dst)
    return "copy"


# ============================================================================
#  gitee 模式: 仿 Gitee 仓库备份
# ============================================================================
def backup_gitee(backup_dir: Path, dry_run: bool = False) -> dict:
    """仿 Gitee 仓库备份: 文件列表 = git 索引 + 未忽略未跟踪文件"""
    files = list_gitee_files()
    print(f"   仿 Gitee 文件列表: {len(files)} 个文件 (来自 git ls-files)")

    binary_exts, _ = parse_gitattributes()
    copied = lf_converted = skipped = 0
    total_bytes = 0

    for i, rel in enumerate(files, 1):
        src = PROJECT_ROOT / rel
        if not src.is_file():
            skipped += 1          # 工作区已删除 (待 commit 的删除)
            continue
        dst = backup_dir / rel
        if dry_run:
            copied += 1
            continue
        mode = copy_file_with_lf(src, dst, binary_exts)
        if mode == "lf":
            lf_converted += 1
        copied += 1
        total_bytes += src.stat().st_size
        if i % 1000 == 0:
            print(f"   ... 进度 {i}/{len(files)}")

    return {"copied": copied, "lf": lf_converted, "skipped": skipped,
            "bytes": total_bytes}


# ============================================================================
#  full 模式: 几乎全量备份
# ============================================================================
def backup_full(backup_dir: Path, dry_run: bool = False) -> dict:
    """几乎全量备份: 仅脚本内 EXCLUDE_DIRS/EXCLUDE_FILES 排除"""
    copied = skipped = 0
    total_bytes = 0

    for src_path in PROJECT_ROOT.rglob("*"):
        if should_exclude(src_path):
            skipped += 1
            continue

        rel_path = src_path.relative_to(PROJECT_ROOT)
        dst_path = backup_dir / rel_path

        if src_path.is_file():
            if dry_run:
                copied += 1
                continue
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            copied += 1
            total_bytes += src_path.stat().st_size
        elif src_path.is_dir():
            if not dry_run:
                dst_path.mkdir(exist_ok=True)

    return {"copied": copied, "lf": 0, "skipped": skipped, "bytes": total_bytes}


# ============================================================================
#  主流程
# ============================================================================
def backup_project(dest_path: Path | None = None, mode: str = "gitee",
                   name: str | None = None, dry_run: bool = False) -> bool:
    """备份项目到目标路径

    Args:
        dest_path: 目标目录 (可选). 为 None 时备份到 flash 的同级目录.
                   不存在时自动创建 (支持任意目录/深层路径).
        mode:      "gitee"(仿 Gitee) 或 "full"(几乎全量)
        name:      备份目录名前缀 (默认 flash_backup_<mode>)
        dry_run:   仅列出将要复制的文件, 不实际复制
    """
    if dest_path is None:
        dest_path = PROJECT_ROOT.parent
    dest_path = Path(dest_path)

    if not dest_path.exists():
        if dry_run:
            print(f"⚠️  目标路径不存在 (dry-run 不创建): {dest_path}")
        else:
            dest_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 目标路径不存在, 已自动创建: {dest_path}")

    prefix = name or f"flash_backup_{mode}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = dest_path / f"{prefix}_{timestamp}"
    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)

    mode_cn = "仿 Gitee 仓库 (gitee)" if mode == "gitee" else "几乎全量 (full)"
    print(f"🚀 [{'试运行' if dry_run else '备份'}] 模式: {mode_cn}")
    print(f"   项目根目录: {PROJECT_ROOT}")
    print(f"   目标目录  : {backup_dir}")
    if mode == "full":
        print(f"   排除目录  : {', '.join(sorted(EXCLUDE_DIRS))}")
        print(f"   排除文件  : {', '.join(sorted(EXCLUDE_FILES))}")
    print()

    if mode == "gitee":
        stat = backup_gitee(backup_dir, dry_run)
    else:
        stat = backup_full(backup_dir, dry_run)

    print()
    if dry_run:
        print(f"✅ 试运行完成! 将复制 {stat['copied']} 个文件, 跳过 {stat['skipped']} 个")
        print(f"   备份目录 (未创建): {backup_dir}")
    else:
        size_mb = stat["bytes"] / 2**20
        print(f"✅ 备份完成!")
        print(f"   复制文件  : {stat['copied']}")
        print(f"   跳过文件  : {stat['skipped']}")
        if mode == "gitee" and stat["lf"]:
            print(f"   LF 规范化 : {stat['lf']}")
        print(f"   总大小    : {size_mb:.1f} MB")
        print(f"   备份位置  : {backup_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="USB 备份脚本 — 支持 gitee(仿Gitee仓库) / full(几乎全量) 双模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python usb_backup.py                       # gitee 模式 → 同级目录
  python usb_backup.py --mode gitee E:\\     # 仿 Gitee 备份到 U 盘
  python usb_backup.py --mode full  E:\\     # 几乎全量备份到 U 盘
  python usb_backup.py --dest D:\\backups    # 指定目标目录
  python usb_backup.py --name flash_rel      # 自定义备份目录名
  python usb_backup.py -n                    # dry-run 试运行
""",
    )
    parser.add_argument("dest", nargs="?", default=None,
                        help="目标目录 (默认: flash 的同级目录)")
    parser.add_argument("--mode", choices=["gitee", "full"], default="gitee",
                        help="备份模式: gitee=仿Gitee仓库(默认), full=几乎全量")
    parser.add_argument("--dest", dest="dest_opt", default=None,
                        help="目标目录 (与位置参数二选一)")
    parser.add_argument("--name", default=None, help="备份目录名前缀")
    parser.add_argument("-n", "--dry-run", action="store_true", help="试运行 (不复制)")

    args = parser.parse_args()

    dest = args.dest_opt or args.dest
    success = backup_project(
        dest_path=dest, mode=args.mode, name=args.name, dry_run=args.dry_run,
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
