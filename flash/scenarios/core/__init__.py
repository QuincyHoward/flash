# -*- coding: utf-8 -*-
"""flash.scenarios.core — 场景层核心模块（2026-10-27 目录整洁化）

scenarios 根只保留包组织（__init__/__main__）与分区目录
（public/flash_demo/private/scripts/core）；所有核心模块在此：

    base          SimulationScenario 数据类
    registry      声明式场景注册表（get_scenario/register）
    discovery     scene.json 零注册发现器
    catalog       可执行场景目录（CLI 数据源）
    cli           python -m flash.scenarios.core.cli（统一入口）
    launcher      场景目录 run.py 薄启动器实现
    simulator     FlashSimulatorEngine
    policies      场景族执行策略（R-LAYER-03：场景层唯一归属）
    hpc_job       场景超算提交声明
    device_defaults 场景核数默认值
    submit_cli    超算提交流程
    insitu_runner runner    兼容壳（转发 flash_run.modes.runner）
    interpolator  hints     轻量提示

旧路径 `flash.scenarios.<mod>` 经 scenarios/__init__.__getattr__ 兼容转发。
"""
