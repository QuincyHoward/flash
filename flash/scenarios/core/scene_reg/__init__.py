# -*- coding: utf-8 -*-
"""scene_reg — 场景发现/注册/目录族（2026-11-05 功能化重组）。

发现（discovery）→ 注册（registry，声明式场景对象）→ 目录（catalog，
可执行场景入口）；policies 为场景族策略常量；device_defaults 为核数
默认值表。四者均懒加载 manifest，保持 CLI ``list`` 零场景 import 语义。
"""
