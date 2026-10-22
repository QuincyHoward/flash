"""
scenarios.runner — 兼容壳（2026-10-22 模块化改造）
═══════════════════════════════════════════════════════════

★ 运行逻辑已于 2026-10-22 整体迁至 ``flash.flash_run.modes.runner``；
  本文件仅为兼容壳：30+ 现有场景脚本的
  ``from flash.scenarios.runner import ...``（含下划线名 ``_to_wsl_path``）
  经此处转发，**零修改可跑**。

新代码请直接使用::

    from flash.flash_run.modes.runner import run_scenario, WslSpec, HpcSpec
"""
# 显式逐一转发（import * 不带下划线名，且保证未来改名时此处立即报错暴露）
from flash.flash_run.modes.runner import (  # noqa: F401
    LOG_TAG,
    RUN_MODES,
    RUN_MODE_ALIASES,
    HpcRunner,
    HpcSpec,
    Remote,
    WslSpec,
    allocate_run_id,
    bash_launcher,
    default_nprocs,
    detect_native_linux,
    discover_flash_home,
    get_sim_user_dir,
    load_hpc_routes,
    log,
    normalize_run_mode,
    package_root,
    resolve_run_mode,
    resolve_venv_python,
    run_id_name,
    run_scenario,
    run_wsl,
    runs_root,
    user_flash_home,
    _check_env,
    _run_wsl_with_progress,
    _tail_lines,
    _to_wsl_path,
)
