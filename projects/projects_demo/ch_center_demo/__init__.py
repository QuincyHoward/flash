"""ch_center_demo — ch_center 场景双密度对比演示

对 ch_center (CH 靶中心演化) 场景, 用两种不同的 CH 靶密度
在本地 WSL 中运行 FLASH 仿真, 并对比分析结果。

对比方案:
  - 低密度: sim_rhoTarg = 0.5 g/cm³
  - 高密度: sim_rhoTarg = 2.0 g/cm³

输出:
  runs_ch_center_compare/
  ├── low_dens/    (run_id=000001)
  └── high_dens/   (run_id=000002)
"""

from __future__ import annotations
