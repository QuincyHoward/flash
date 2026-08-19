"""flash-sim 场景包 — 物理专题 + 场景两层组织

scenarios/
├── __init__.py               ← 本文件, 导入所有场景触发注册
├── base.py                   ← SimulationScenario 数据类
├── registry.py               ← 场景注册表
├── README.md                 ← 创建新场景的指南
├── runner.py                 ← 统一运行器 (RUN_MODE 一键切换 wsl/hpc)
├── center_evolution/         ← 中心演化系列
│   └── ch_center/            ← CH 靶中心演化
├── flash_demo/               ← 演示场景 (demo_local/demo_hpc/hello_flash)
└── private/                  ← 私有场景 (tracer 系列, 不随发布包分发)
"""

from __future__ import annotations

import warnings

# 容错导入场景包: 依赖私有分区的场景在克隆/发布环境缺失时优雅跳过,
# 保证公共包可独立导入。tracer 等私有场景以 python -m 直跑, 不在此注册。
for _pkg in ("center_evolution", "flash_demo", "private"):
    try:
        __import__(f"flash.scenarios.{_pkg}")
    except ImportError as _e:  # pragma: no cover - 依赖私有分区时才触发
        warnings.warn(f"场景包 {_pkg} 加载失败: {_e}", stacklevel=2)
