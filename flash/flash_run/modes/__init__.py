"""
flash.flash_run.modes — 三种运行模式的执行体（2026-10-22 自 scenarios 迁入）
═══════════════════════════════════════════════════════════

模块划分:
  * runner.py      : 统一场景运行器（wsl / hpc-remote / hpc-insitu 三模式执行体、
                     规格 dataclass、资源默认值、断点续跑）
  * （运行细节唯一归属本包；scenarios/runner.py 仅是兼容 re-export 壳）

兼容性:
  * 老脚本 `from flash.scenarios.runner import ...` 全部经 scenarios/runner.py
    壳转发到本包，零修改可跑（含下划线名 _to_wsl_path 等）。
"""
