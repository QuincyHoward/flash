# -*- coding: utf-8 -*-
"""flash.scenarios.scripts — 场景共享脚本区（2026-11-05 功能化重组）

布局::

    scripts/
    ├── relocate/     场景收纳整理工具链（audit/make_portable/decouple/relocate/verify/clone）
    ├── checks/       初始帧快检（check_suite_initial / check_sic_initial）
    ├── validation/   公开场景极短验证入口（run_demo / short_validation）
    └── legacy/       一次性失效工具归档（docstring 指向旧 tracer 布局，复用需适配路径）

场景共享纯函数库 ``time_control.py`` 已迁 ``flash/scenarios/common/``。
本目录被 discovery 排除（_EXCLUDE_SUBTREES），不会被视为场景。
"""
