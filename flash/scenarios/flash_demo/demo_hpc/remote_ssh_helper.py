"""demo_hpc 的 SSH 助手 —— **已迁移，仅为兼容壳**

★ 2026-10-24（解耦计划 B1）：唯一实现已迁至
``flash.flash_run.remote.session``。

保留本文件的原因（禁止删除）：
  1. 部署链 6 个脚本、`SNBOneCH_ml`、`demo_hpc` 演示、`slurm_control`
     文档约定都按 ``remote_ssh_helper.RemoteSession`` 这个名字引用；
  2. ``check_scene_sources.KNOWN_DEBT`` 曾按文件名挂账（本项已还清）。

本文件**只允许 re-export**，不得再放任何实现（`R-LAYER-02a` 会拦）。
"""

from flash.flash_run.remote.session import (      # noqa: F401  (re-export)
    RemoteSession,
    quick_download,
    quick_run,
    quick_upload,
    scp_download,
    scp_upload,
    ssh_cmd,
)

__all__ = [
    "RemoteSession",
    "quick_run",
    "quick_upload",
    "quick_download",
    "ssh_cmd",
    "scp_upload",
    "scp_download",
]
