"""flash-sim 场景包 — 物理专题 + 场景两层组织

scenarios/
├── __init__.py               ← 本文件, 导入所有场景触发注册
├── base.py                   ← SimulationScenario 数据类
├── registry.py               ← 场景注册表
├── README.md                 ← 创建新场景的指南
├── plasma_preparation/       ← 等离子体制备 (待扩充)
├── collision_compression/    ← 对撞压缩
│   └── thin_layer_sandwich/  ← Si + Al 三层靶
└── center_evolution/         ← 中心演化系列
    └── ch_center/            ← CH 靶中心演化
"""

# 导入所有子包触发 register() 调用
from . import plasma_preparation  # noqa: F401
from . import collision_compression  # noqa: F401
from . import center_evolution  # noqa: F401
