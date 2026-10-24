"""部署目标解析 —— `start_flash.py --target` 的唯一判定源
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B3）：此前部署侧有**两套入口**且互不知道对方：
    `start_flash.py`（win/wsl 安装，全文 0 处 sbatch/ssh 感知）
    `deploy/hpc_deploy/run_all.py`（超算 11 步链）
  用户必须记住两套命令，且 `run_all.py` 第 42 行写死了本机
  `C:\\Users\\Administrator\\...python.exe`（换机即失效）。

本模块把「在哪部署」收敛成一个名字，`start_flash.py --target` 消费它：

    auto  按平台判定（Windows→win，POSIX→wsl）
    win   Windows 本地安装
    wsl   在 WSL 内安装（Windows 侧会重新在 WSL 里启动自己）
    hpc   超算链（委托 deploy/hpc_deploy/run_all.py）

★ 平台判定的**执行侧**逻辑不在这里重写：`flash/flash_run/execution.py`
  是纯 stdlib（模块级零 flash import），可直接按文件路径加载 ——
  这样"安装前就要判平台"和"装好后的运行判定"用**同一份**判定代码。
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

DEPLOY_TARGETS = ("auto", "win", "wsl", "hpc")

#: 执行侧目标 → 部署目标
_EXEC_TO_DEPLOY = {
    "local": "wsl",          # POSIX 本机：走 Linux 原生安装流程（旧名 local_env_wsl）
    "wsl": "wsl",
    "hpc-remote": "hpc",
    "hpc-insitu": "hpc",     # 已在登录节点 ⇒ 部署链就在本机跑
}


def _load_execution():
    """按文件路径加载 execution.py（此时 flash 包可能尚未安装）。"""
    path = REPO_ROOT / "flash" / "flash_run" / "execution.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_flash_execution_for_deploy", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_flash_execution_for_deploy", mod)
    spec.loader.exec_module(mod)
    return mod


def resolve_deploy_target(mode: str | None = None,
                          env: dict | None = None) -> tuple[str, list[str]]:
    """→ (deploy_target, trace)。未知值抛 ValueError。"""
    env = os.environ if env is None else env
    trace: list[str] = []
    raw = (mode or "auto").strip().lower()

    if raw in DEPLOY_TARGETS and raw != "auto":
        trace.append(f"[deploy] 显式指定 --target {raw}")
        return raw, trace

    aliases = {"windows": "win", "linux": "wsl", "posix": "wsl",
               "slurm": "hpc", "remote": "hpc", "supercomputer": "hpc"}
    if raw in aliases:
        trace.append(f"[deploy] 别名 {raw} → {aliases[raw]}")
        return aliases[raw], trace

    if raw not in ("auto", ""):
        raise ValueError(f"未知 --target {mode!r}；可选: {', '.join(DEPLOY_TARGETS)}")

    # auto：优先复用执行侧判定（一份代码，两处使用）
    ex = _load_execution()
    if ex is not None:
        try:
            exec_target, exec_trace = ex.resolve_target("auto", ex.DEFAULT_POLICY, env=env)
            deploy = _EXEC_TO_DEPLOY.get(exec_target)
            if deploy:
                trace.extend(exec_trace)
                trace.append(f"[deploy] 执行侧目标 {exec_target} → 部署目标 {deploy}")
                return deploy, trace
        except Exception as exc:                     # noqa: BLE001 - 判定失败退回本机规则
            trace.append(f"[deploy] 执行侧判定不可用（{type(exc).__name__}: {exc}），退回本机规则")

    deploy = "win" if os.name == "nt" else "wsl"
    trace.append(f"[deploy] 按 os.name={os.name} 判定 → {deploy}")
    return deploy, trace
