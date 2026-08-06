"""
gen_shell_script — 可执行脚本生成

为 3 个平台生成 FLASH 运行脚本:
  - Windows (.bat) → 通过 WSL
  - WSL (.sh) → 直接在 WSL/Linux 终端
  - SLURM (.slurm) → 超算作业提交
"""

from .generator import ShellScriptGenerator

__all__ = ["ShellScriptGenerator"]
