"""``eosopdata`` 子包 —— 材料数据模块功能测试。

覆盖三步（文件夹已按 step 编号命名）:

* ``step01_cn4/``    —— ``.cn4`` 文件的**提取 / 彩图（nion-T、ne-T、rho-T
  双坐标）/ 等温线 / 等熵线 / 等压线 / 冲击雨贡纽** 等材料相关模块
* ``step02_families/`` —— 其它格式族（F1–F6）的同类能力（彩图 + 可行的
  路径图）+ **逐类型批量出图**（每种文件类型一个独立文件夹一个脚本
  ``test_plot_<type>.py``，产物落 ``<type>/_out/``，``_report.txt`` 给出
  网格点 / 物理意义 / 单位 / checked 状态，便于逐类型人工核查）+
  check 字典守护（只有 cn4 全 checked）
* ``step03_transcn4/`` —— **其它格式 -> cn4** 的转换（缺失数据用 NaN 占位且对齐）

设计原则
--------
1. **不猜物理量单位**：单位一律从 ``eosop_pro`` 的权威模块取，测试只断言
   "与权威来源一致"，不写死数值。
2. **不写死脆弱路径**：样品文件通过 :mod:`_samples` 惰性发现，
   全树扫描一次后缓存；缺失时 `skip` 而非 FAIL（数据非代码产物）。
3. **产物跟测试走**：所有出图/写文件落在**本测试文件夹**的 ``_out/``
   内（如 ``step01_cn4/_out/``），便于人工核查；该目录已 gitignore，
   不污染仓库（2026-09-15 前曾统一写 ``test/_tmp/plots`` / ``tempfile``）。
"""

import os as _os
import sys as _sys

# ── 让子目录内的测试文件仍能 ``import _runner`` ──────────────────
# ``_runner.py`` 位于上两级 ``test/``。直接
# ``python test/eosopdata/cn4/test_x.py`` 时 ``sys.path[0]`` 是子目录本身，
# 找不到 ``_runner``，故在此把 ``test/`` 与其所有子包补进 ``sys.path``。
_TEST = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _TEST not in _sys.path:
    _sys.path.insert(0, _TEST)
for _p in (_TEST, _os.path.dirname(_TEST)):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
del _os, _sys, _TEST, _p
