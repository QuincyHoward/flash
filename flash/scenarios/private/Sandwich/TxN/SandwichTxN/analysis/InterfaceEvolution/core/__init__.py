# -*- coding: utf-8 -*-
"""InterfaceEvolution core — SandwichTxN 关键界面提取核心库.

模块:
  chk_io       chk 帧读取 (叶块过滤, bounding box 逐格 x 重建) + 派生量
               (nele/nion/zbar/Γ_i/Θ_e, 单位换算均按 FLASH物理量说明.md §0.3/§2)
  criteria     界面判据: x_c (§3.1) / x_a (§3.2 镜像) / Si 区域 (dens·targ 半高)
               / shok 候选区切分 (§3.3)
  velocity     §3.4 统一速度差分链 (medfilt + savgol, 全库标准)
  shock_track  §3.3 冲击波轨迹: 候选区贪心最近邻跟踪 + 物理筛选
               (① v_s 与 v_a 同号 ② |v_s|>|v_a| ③ 位于 x_a 运动方向前方
                ④ 初始位置距 x_a ≤ X0_TOL), 只保留向心发展段
  fields       时空场统一网格采样 + Si 区域平均量
"""
