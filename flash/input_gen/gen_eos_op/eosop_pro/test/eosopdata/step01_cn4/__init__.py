"""``eosopdata/cn4`` 子包 —— ``.cn4`` 材料的提取 / 绘图 / 路径测试。

三层覆盖面（对应 ``eosop_pro.cn4`` 的三个模块）:

* **提取**  ``cn4_io.py``      —— 18 块解析、头部、丰度、原子量、往返
* **彩图**  ``cn4_plots.py``   —— 二维热图 / 群不透明度大图 / 一维曲线
* **路径**  ``cn4_paths.py``   —— 等温线 / 等压线 / 等熵线 / 冲击雨贡纽 / P-V
"""

import os as _os
import sys as _sys

_TEST = _os.path.dirname(_os.path.dirname(_os.path.dirname(
    _os.path.abspath(__file__))))
if _TEST not in _sys.path:
    _sys.path.insert(0, _TEST)
if _os.path.dirname(_TEST) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_TEST))
del _os, _sys, _TEST
