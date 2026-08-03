"""
_bootstrap.py — flash 包导入路径引导标记文件

此文件作为路径标记, 用于脚本通过向上搜索找到 flash 包根目录。

关键发现: flash 包就是项目根目录 (含 __init__.py + pyproject.toml)。
导入 flash 需要将其父目录加入 sys.path。

标准引导代码模板:

```python
import sys
from pathlib import Path

# Bootstrap: find flash package root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
```
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path
    _ROOT = Path(__file__).resolve().parent
    print(f"flash package root: {_ROOT}")
    print(f"flash/__init__.py exists: {(_ROOT / '__init__.py').exists()}")
