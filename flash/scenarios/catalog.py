"""可执行场景目录 —— 名字 → `SceneSpec` 的唯一映射
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B2）：这是 `python -m flash.scenarios.cli` 的目录源。

为什么不用 `registry.py`：那个注册表登记的是**声明式物理场景**
（`SimulationScenario` 数据类，供引擎 `FlashSimulatorEngine` 用），
而这里是**可执行场景**（有输入生成 + 运行 + 分析全流程）。
两者受众不同，混在一起会让"新增一个能跑的算例"必须改引擎注册表。

★ 存量脚本的处置（诚实说明）：
  24 个场景脚本各自有成熟 `main()`，本轮**不重写**它们（B7 才收编
  SNB 执行体）。这里用 `runner_kind` 做适配，策略校验与目标解析
  仍统一走 `execution.resolve_target` —— 所以 `SNB_POLICY` 的
  "禁本地"是**真的生效**，不会因为走的是旧脚本而绕过。
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flash.flash_run.execution import (
    DEFAULT_POLICY,
    SNB_POLICY,
    ExecOptions,
    ExecutionPolicy,
    SceneSpec,
)

__all__ = ["CatalogEntry", "CATALOG", "list_scenes", "get_scene", "repo_root"]


def repo_root() -> Path:
    """仓库根（含 pyproject.toml + start_flash.py）。"""
    here = Path(__file__).resolve()
    for cand in [here, *here.parents]:
        if (cand / "pyproject.toml").is_file() and (cand / "start_flash.py").is_file():
            return cand
    raise RuntimeError("无法定位仓库根（需含 pyproject.toml 与 start_flash.py）")


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    rel_module: str = ""              # runner_kind="main" 时的模块路径
    script: str = ""                  # runner_kind="script" 时的脚本相对路径
    runner_kind: str = "main"         # main | script
    policy: ExecutionPolicy = DEFAULT_POLICY
    aliases: Tuple[str, ...] = ()
    description: str = ""
    default_args: Tuple[str, ...] = ()
    sim_name: str = ""
    basenm: str = ""

    # ── 两个适配器：把 ExecOptions 翻译成"存量脚本能听懂的东西" ──

    def _runner_main(self, opts: ExecOptions) -> Dict[str, Any]:
        target = str(opts.extra.get("_target") or opts.mode or "")
        if target and target != "auto":
            # 存量脚本的 resolve_run_mode() 只认环境变量（它们没有 argparse）
            os.environ["FLASH_RUN_MODE"] = target
        mod = importlib.import_module(self.rel_module)
        if not hasattr(mod, "main"):
            return {"ok": False, "reason": f"{self.rel_module} 无 main()"}
        ok = mod.main()
        return {"ok": bool(ok), "reason": "" if ok else "场景 main() 返回 False"}

    def _runner_script(self, opts: ExecOptions) -> Dict[str, Any]:
        script = repo_root() / self.script
        if not script.is_file():
            return {"ok": False, "reason": f"脚本不存在: {script}"}
        target = str(opts.extra.get("_target") or opts.mode or "")
        cmd: List[str] = [sys.executable, str(script), *self.default_args]
        if target and target != "auto":
            cmd += ["--mode", target]
        if opts.account:
            cmd += ["--account", opts.account]
        if opts.nproc:
            cmd += ["--nproc", str(opts.nproc)]
        if opts.tmax:
            cmd += ["--tmax", str(opts.tmax)]
        cmd += list(opts.extra.get("args", ()))
        print(f"[run] {' '.join(cmd)}")
        rc = subprocess.run(cmd, cwd=str(script.parent)).returncode
        return {"ok": rc == 0, "reason": "" if rc == 0 else f"rc={rc}"}

    def build_runner(self):
        return self._runner_main if self.runner_kind == "main" else self._runner_script


#: ── 目录（新增可执行算例 = 这里加一条，不要改引擎注册表） ──
CATALOG: Tuple[CatalogEntry, ...] = (
    CatalogEntry(
        name="ch_center",
        rel_module="flash.scenarios.public.center_evolution.ch_center."
                   "laserslab1d_local_custom",
        runner_kind="main",
        aliases=("laserslab1d", "laserslab", "center_evolution"),
        description="1D LaserSlab（CH 中心层，官方一键场景；wsl/hpc-remote/hpc-insitu 三模式）",
        sim_name="laserslab1d",
        basenm="lasslab_",
    ),
    CatalogEntry(
        name="SNBOneCH_m",
        script="flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py",
        runner_kind="script",
        policy=SNB_POLICY,
        aliases=("snb_m",),
        description="SNB 非局域热传导（CH，单温；**仅超算**，131 进程=网格定义）",
        default_args=("all",),
    ),
    CatalogEntry(
        name="SNBOneCH_ml",
        script="flash/scenarios/private/tracer/SNB/SNBOneCH_ml/SNBOneCH_ml.py",
        runner_kind="script",
        policy=SNB_POLICY,
        aliases=("snb_ml",),
        description="SNB 非局域热传导（CH，多群；**仅超算**）",
        default_args=("all",),
    ),
)


def list_scenes() -> List[Tuple[str, str, Tuple[str, ...]]]:
    """[(name, description, allowed_targets)]。"""
    return [(e.name, e.description, e.policy.allowed) for e in CATALOG]


def _lookup(name: str) -> CatalogEntry:
    key = (name or "").strip()
    for entry in CATALOG:
        if key == entry.name or key in entry.aliases:
            return entry
    known = ", ".join(e.name for e in CATALOG)
    raise KeyError(f"未知可执行场景: {name!r}；可用: {known}")


def get_scene(name: str) -> SceneSpec:
    """取 `SceneSpec`（含策略与 runner）。"""
    entry = _lookup(name)
    return SceneSpec(
        name=entry.name,
        sim_name=entry.sim_name,
        basenm=entry.basenm,
        config={},
        runner=entry.build_runner(),
        policy=entry.policy,
        description=entry.description,
    )
