# -*- coding: utf-8 -*-
"""flash.scenarios.common — 场景间共享代码包（非场景，位置固定，永不移动）
════════════════════════════════════════════════════════════════════════

★ 场景收纳整理改造（2026-11-04）引入。

★ 定位：任何需要被**多个场景复用**的 Python 代码（如 RemoteSession、
  插值器、共享物理工具函数）一律住这里 —— 场景统一
  ``from flash.scenarios.common.xxx import ...``（固定包路径，与场景
  自身位置无关），场景之间**零互相 import**，子场景保持独立可迁移。

★ 约束：
  - 本包内**禁止** import 任何具体场景模块（flash.scenarios.<分区>.…），
    否则共享层反向绑定场景、移动场景会破坏共享层；
  - 允许依赖 flash.scenarios.core.*（框架层）与 flash.* 通用设施；
  - 本目录不含 scene.json，discovery 天然不识别为场景。
"""
