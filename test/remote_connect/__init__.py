"""超算链接诊断工具包。

快速定位 SSH 连接、凭据、路由、文件传输、SLURM 等问题。

用法:
    python -m flash.test.remote_connect         # 运行全部诊断
    python -m flash.test.remote_connect --quick  # 快速检查
"""

from flash.test.remote_connect.diagnostics import run_diagnostics, main

__all__ = ["run_diagnostics", "main"]
