"""projects_demo — 用户项目演示包

本包演示如何在 flash-sim 框架之上构建自己的仿真项目:
  - projects_demo.ch_center_demo: ch_center 场景双密度对比演示

项目结构约定:
  projects/
  └── projects_demo/          ← 本演示包
      ├── __init__.py
      ├── README.md           ← 演示项目说明
      └── ch_center_demo/     ← ch_center 双密度对比
          ├── __init__.py
          ├── run_compare.py      ← 双密度 WSL 仿真运行器
          └── plot_compare.py     ← 对比绘图
"""

from __future__ import annotations
