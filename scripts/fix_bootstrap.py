#!/usr/bin/env python3
"""
fix_bootstrap.py — 修复 bootstrap 代码: 将 `str(_ROOT)` 改为 `str(_ROOT.parent)`

flash 包本身就是项目根目录 (有 __init__.py + pyproject.toml),
导入 flash 需要将其父目录加入 sys.path, 而非自身。
"""

import sys
import re
from pathlib import Path

FLASH_ROOT = Path(__file__).resolve().parent.parent

OLD_MARKER = "_bootstrap.py"
NEW_MARKER = "__init__.py"
OLD_INSERT = 'if str(_ROOT) not in sys.path:\n    sys.path.insert(0, str(_ROOT))'
NEW_INSERT = '_PARENT = _ROOT.parent\nif str(_PARENT) not in sys.path:\n    sys.path.insert(0, str(_PARENT))'

OLD_ERR = 'raise RuntimeError("Cannot locate flash project root (_bootstrap.py not found)")'
NEW_ERR = 'raise RuntimeError("Cannot locate flash package root")'


def process_file(filepath: Path) -> bool:
    content = filepath.read_text(encoding="utf-8")
    
    # Only process files that have the old bootstrap
    if OLD_MARKER not in content:
        return False
    if "Bootstrap" not in content:
        return False
    if "_ROOT = Path(__file__).resolve().parent" not in content:
        return False
    
    # Check if already fixed
    if "_PARENT = _ROOT.parent" in content:
        return False
    
    # Replace marker check
    content = content.replace(
        f'if (_ROOT / "{OLD_MARKER}").exists() and (_ROOT / "pyproject.toml").exists():',
        f'if (_ROOT / "{NEW_MARKER}").exists() and (_ROOT / "pyproject.toml").exists():'
    )
    
    # Replace error message
    content = content.replace(OLD_ERR, NEW_ERR)
    
    # Replace insert logic
    # Two variants: with and without scenarios addition
    content = _replace_insert(content)
    
    # Also fix scenarios addition if present
    content = content.replace(
        '_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"',
        '_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"'
    )
    
    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ {filepath.relative_to(FLASH_ROOT)}")
    return True


def _replace_insert(content: str) -> str:
    """Replace the sys.path.insert logic."""
    # Pattern: the block after the for-else loop
    # Old: if str(_ROOT) not in sys.path:\n    sys.path.insert(0, str(_ROOT))
    # New: _PARENT = _ROOT.parent\nif str(_PARENT) not in sys.path:\n    sys.path.insert(0, str(_PARENT))
    
    old_pattern = 'if str(_ROOT) not in sys.path:\n    sys.path.insert(0, str(_ROOT))'
    new_pattern = '_PARENT = _ROOT.parent\nif str(_PARENT) not in sys.path:\n    sys.path.insert(0, str(_PARENT))'
    
    return content.replace(old_pattern, new_pattern)


def main():
    dry_run = "--dry-run" in sys.argv
    mode = "DRY-RUN" if dry_run else "FIX"
    print(f"\n{'='*60}")
    print(f"  flash bootstrap 修复 ({mode})")
    print(f"  搜索: {FLASH_ROOT}")
    print(f"{'='*60}\n")
    
    count = 0
    errors = []
    
    for pyfile in sorted(FLASH_ROOT.rglob("*.py")):
        if '__pycache__' in str(pyfile) or '.bak' in str(pyfile):
            continue
        if pyfile.name in ('_bootstrap.py', 'fix_bootstrap.py', 'migrate_imports.py'):
            continue
        
        try:
            if process_file(pyfile):
                count += 1
        except Exception as e:
            errors.append((pyfile, str(e)))
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"  ✅ 已修复: {count}")
    if errors:
        print(f"  ❌ 错误: {len(errors)}")
        for f, e in errors:
            print(f"     - {f}: {e}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
