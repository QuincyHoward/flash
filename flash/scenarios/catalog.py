"""可执行场景目录 —— 名字 → `SceneSpec` 的唯一映射
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B2）：这是 `python -m flash.scenarios.cli` 的目录源。

为什么不用 `registry.py`：那个注册表登记的是**声明式物理场景**
（`SimulationScenario` 数据类，供引擎 `FlashSimulatorEngine` 用），
而这里是**可执行场景**（有输入生成 + 运行 + 分析全流程）。
两者受众不同，混在一起会让"新增一个能跑的算例"必须改引擎注册表。

★ 2026-10-24（公开场景统一 auto）：`public/` 下的三个公开场景
  （ch_center / grad_dens_sandwich / thin_layer_sandwich_si）全部进目录，
  **缺省模式 = auto**（平台自适应），用户不需要知道本机是 Windows / WSL
  还是超算登录节点 —— 判定只走 `execution.resolve_target` 一份实现。
  两条执行体：
    · ch_center          → `runner_kind="main"`   （场景自有 main，三模式齐）
    · 两个 sandwich 场景 → `runner_kind="engine"`（声明式场景 + 引擎）
  引擎只承接本机执行（local/wsl），故其策略显式限定 allowed=(local, wsl)；
  auto 判定到 hpc-* 时**明确报错**而不是静默降级。

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
    mode_is_remote,
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
    runner_kind: str = "main"         # main | script | engine
    policy: ExecutionPolicy = DEFAULT_POLICY
    aliases: Tuple[str, ...] = ()
    description: str = ""
    default_args: Tuple[str, ...] = ()
    sim_name: str = ""
    basenm: str = ""

    # ── 三个适配器：把 ExecOptions 翻译成"存量脚本能听懂的东西" ──

    def _runner_main(self, opts: ExecOptions) -> Dict[str, Any]:
        target = str(opts.extra.get("_target") or opts.mode or "")
        if target and target != "auto":
            # 存量脚本的 resolve_run_mode() 只认环境变量（它们没有 argparse）
            os.environ["FLASH_RUN_MODE"] = target
        mod = importlib.import_module(self.rel_module)
        if not hasattr(mod, "main"):
            return {"ok": False, "reason": f"{self.rel_module} 无 main()"}

        # 能接收参数的 main 优先显式传参（比环境变量更可测、且不污染子进程）；
        # 只传该 main 签名里真正存在的参数，老脚本零改动仍可跑。
        import inspect
        try:
            params = inspect.signature(mod.main).parameters
        except (TypeError, ValueError):
            params = {}
        kwargs: Dict[str, Any] = {}
        if "mode" in params:
            kwargs["mode"] = target or None
        if "tmax" in params and opts.tmax:
            kwargs["tmax"] = opts.tmax
        ok = mod.main(**kwargs)
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

    def _runner_engine(self, opts: ExecOptions) -> Dict[str, Any]:
        """声明式场景（`registry` 注册的 SimulationScenario）→ 引擎执行。

        ★ 引擎**只承接本机执行**（local/wsl）；超算目标必须由场景脚本
          （runner_kind="main"/"script"）承担。策略层已把 allowed 限定为
          local/wsl，这里再显式拦截一次，防止有人给 catalog 条目误配策略后
          静默走到引擎的"只承接本机"提示。
        """
        target = str(opts.extra.get("_target") or opts.mode or "")
        if mode_is_remote(target):
            return {"ok": False,
                    "reason": (f"引擎只承接本机执行（local/wsl），当前目标 {target}；"
                               f"该场景的超算执行请用其自带的 sbatch 脚本")}
        from flash.scenarios.registry import get_scenario
        from flash.scenarios.simulator import FlashSimulatorEngine

        scenario = get_scenario(self.name)
        engine = FlashSimulatorEngine(scenario)
        params: Dict[str, Any] = {}
        if opts.tmax:
            params["tmax"] = float(opts.tmax)
        # 运行目录固定落在 `flash/scenarios/public/runs_<name>/`（与既有
        # 约定一致）：引擎默认按"调用者所在目录"推导，CLI 调用时会落到
        # `flash/scenarios/runs_*`，与场景自带的历史产物目录割裂。
        runs_dir = repo_root() / "flash" / "scenarios" / "public" / scenario.run_dir_name
        res = engine.run(params_override=params or None,
                         mode=target or "auto",
                         runs_dir=str(runs_dir),
                         dry_run=opts.dry_run)
        return {"ok": bool(getattr(res, "success", False)),
                "reason": str(getattr(res, "error_message", "") or ""),
                "run_dir": str(getattr(res, "run_dir", "") or ""),
                "n_chk": int(getattr(res, "n_chk", 0) or 0)}

    def build_runner(self):
        return {
            "main": self._runner_main,
            "script": self._runner_script,
            "engine": self._runner_engine,
        }.get(self.runner_kind, self._runner_main)


#: ── 目录（新增可执行算例 = 这里加一条，不要改引擎注册表） ──

#: 公开场景策略：允许本机两种执行目标（Windows→WSL / Linux→本地）。
#: ⚠ 与 DEFAULT_POLICY 的区别在 **preferred**：引擎型场景在超算登录节点上
#:   auto 会判到 hpc-insitu（判据 4：slurm 健康），而引擎不承接超算 ⇒
#:   显式把 allowed 收窄到 (local, wsl)，让 auto 在超算上**明确报错**
#:   而不是跑到引擎才给一句模糊提示。
PUBLIC_SCENE_POLICY = ExecutionPolicy(
    allowed=("local", "wsl"),
    preferred="auto",
    forbid_reason=("公开场景的引擎执行体只承接本机（local/wsl）；"
                   "在超算上请用该场景自带的 sbatch 脚本"),
)


CATALOG: Tuple[CatalogEntry, ...] = (
    CatalogEntry(
        name="ch_center",
        rel_module="flash.scenarios.public.center_evolution.ch_center."
                   "laserslab1d_local_custom",
        runner_kind="main",
        policy=DEFAULT_POLICY,
        aliases=("laserslab1d", "laserslab", "center_evolution"),
        description="1D LaserSlab（CH 中心层，官方一键场景；auto/wsl/hpc-remote/hpc-insitu）",
        sim_name="laserslab1d",
        basenm="lasslab_",
    ),
    CatalogEntry(
        name="grad_dens_sandwich",
        runner_kind="engine",
        policy=PUBLIC_SCENE_POLICY,
        aliases=("grad_dens",),
        description="HE-CH-Si-CH-HE 渐变密度 CH 靶（超高斯脉冲；auto = 平台自适应）",
        sim_name="grad_dens_sandwich",
        basenm="lasslab_",
    ),
    CatalogEntry(
        name="thin_layer_sandwich_si",
        runner_kind="engine",
        policy=PUBLIC_SCENE_POLICY,
        aliases=("thin_layer_sandwich", "thin_layer"),
        description="Si/CH/He 三层靶激光烧蚀（新 EOS 表；auto = 平台自适应）",
        sim_name="grid_rede_si",
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
