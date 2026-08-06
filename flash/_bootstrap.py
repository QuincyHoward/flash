"""
_bootstrap.py — flash 包导入路径引导标记文件

此文件作为路径标记, 用于脚本通过向上搜索找到项目根目录。

关键发现 (2026-08-06 目录重组后): flash 包位于项目根的 flash/ 子目录
(标准包布局)。项目根含 pyproject.toml, 导入 flash 需将项目根加入 sys.path。

标准引导代码模板:

```python
import sys
from pathlib import Path

# Bootstrap: find flash package root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
```
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    _ROOT = Path(__file__).resolve().parent
    print(f"flash package root: {_ROOT}")
    print(f"flash/__init__.py exists: {(_ROOT / '__init__.py').exists()}")
