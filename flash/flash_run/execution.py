"""统一执行契约 —— 场景层与执行层之间**唯一**的接口
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B2）：本模块回答两个问题，且只回答这两个：

    ① **在哪跑**  → `resolve_target(mode, policy)`：平台自适应判定表
    ② **怎么跑**  → `run_scene(scene, opts)`：校验策略后交给执行层

分层铁律（可机器校验，见 check_scene_sources 的 R-LAYER-*）：
    scenarios/  →  flash_run/  →  _core/        （禁止反向）

设计取舍（为什么 `run_scene` 看起来"只是转发"）：
    本项目最大的问题是**抽象已存在、落地不全**——`run_scenario()` 全仓 0 次
    调用、`slurm_control.CommandExecutor` 未被 `HpcRunner` 使用。再造一层
    执行实体会变成第 5 条路径。因此 `run_scene` 只做三件事：
    策略校验 → 目标解析 → 转发现有实现（`run_wsl` / `HpcRunner` /
    `run_insitu` / `LocalExecutor`）。真正被执行的是同一份代码。

    `SceneSpec.runner` 是给**存量脚本**的适配口（它们各有成熟的 main），
    声明式 `build_inputs` 路径给新场景；两者共用同一套策略与判定，
    不会因为入口不同而绕过 `allowed_modes`（SNB 禁本地就是靠这个）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "EXEC_TARGETS",
    "ExecutionTargetError",
    "ExecutionPolicy",
    "NprocRule",
    "SceneSpec",
    "ExecOptions",
    "RunResult",
    "DEFAULT_POLICY",
    "SNB_POLICY",
    "normalize_target",
    "mode_is_remote",
    "mode_is_local",
    "resolve_target",
    "explain_target",
    "run_scene",
]


# ═══════════════════════════════════════════════════════════════════
# 目标词汇表
# ═══════════════════════════════════════════════════════════════════

#: canonical 目标（**新增**，不改动 `modes.runner.RUN_MODES` 三元组，
#: 因此 `test_scenarios_modes.py:39` 的断言零改动）。
EXEC_TARGETS: Tuple[str, ...] = ("local", "wsl", "hpc-remote", "hpc-insitu")

_ALIASES: Dict[str, str] = {
    "": "auto",
    "auto": "auto",
    "local": "local",
    "native": "local",
    "wsl": "wsl",
    "hpc": "hpc-remote",
    "hpc-remote": "hpc-remote",
    "remote": "hpc-remote",
    "ssh": "hpc-remote",
    "slurm": "hpc-remote",
    "supercomputer": "hpc-remote",
    "hpc-insitu": "hpc-insitu",
    "insitu": "hpc-insitu",
    "in-situ": "hpc-insitu",
}


class ExecutionTargetError(RuntimeError):
    """目标解析失败 / 被场景策略拒绝（明确报错，绝不静默降级）。"""


def normalize_target(value: str | None) -> str:
    """别名归一 → canonical target 或 `"auto"`。未知值原样返回（交给调用方报错）。"""
    key = (value or "").strip().lower()
    return _ALIASES.get(key, key)


def mode_is_remote(target: str | None) -> bool:
    """是否为"提交到超算"的两种模式（含别名）。

    ★ 场景层禁止再写 `run_mode != "hpc"` 字面量比较 —— 2026-10-22 把
    `hpc` 归一为 `hpc-remote` 后，这种写法**恒真**，使两个 demo 入口
    永远 `return False`（真实回归 G1）。本函数是唯一正确写法。
    """
    return normalize_target(target) in ("hpc-remote", "hpc-insitu")


def mode_is_local(target: str | None) -> bool:
    """是否在本机执行（`local` 或 Windows 的 `wsl`）。"""
    return normalize_target(target) in ("local", "wsl")


# ═══════════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class NprocRule:
    """核数约束。`exact` 表示**执行层禁止改写**（SNB 网格定义即核数）。"""
    mode: str = "auto"                  # auto | exact | at_most
    value: Optional[int] = None
    note: str = ""

    def validate(self, nproc: int | None) -> Optional[str]:
        """返回错误信息；None = 通过。"""
        if self.mode == "auto" or nproc is None or self.value is None:
            return None
        if self.mode == "exact" and nproc != self.value:
            return (f"本场景核数必须恰为 {self.value}（给的是 {nproc}）。{self.note}")
        if self.mode == "at_most" and nproc > self.value:
            return f"本场景核数上限 {self.value}（给的是 {nproc}）。{self.note}"
        return None


@dataclass(frozen=True)
class ExecutionPolicy:
    """场景级执行约束。执行层强制执行，**不可协商**。"""
    allowed: Tuple[str, ...] = EXEC_TARGETS
    preferred: str = "auto"
    requires_slurm: bool = False
    forbid_reason: str = ""
    nproc: NprocRule = field(default_factory=NprocRule)
    build_timeout: int = 7200
    run_timeout: int = 7200
    analysis_timeout: int = 3600


DEFAULT_POLICY = ExecutionPolicy()

#: SNB 族：非局域热传导算例，nproc 是网格定义的一部分（`iProcs*nxb=25000`
#: ⇒ `dx=0.02 µm`，改核数即改网格）。且 131/125 进程在 24 核本机必然超订卡死。
SNB_POLICY = ExecutionPolicy(
    allowed=("hpc-remote", "hpc-insitu"),
    requires_slurm=True,
    forbid_reason=("nproc 是本场景网格定义的一部分（iProcs×nxb=const ⇒ dx=0.02 µm），"
                   "且 125/131 进程远超本机核数"),
    nproc=NprocRule(mode="exact", value=None,
                    note="请用场景自带的 --nproc（默认即超算配置）"),
)


@dataclass
class SceneSpec:
    """场景声明。场景文件唯一向执行层交付的东西。

    两条路径（同一套策略校验）：
      * `runner` 已给 → 存量脚本适配（转调场景自己的 main）；
      * `runner` 为空 → 声明式（`build_inputs` → 交给 modes 策略执行）。
    """
    name: str
    sim_name: str = ""
    objdir: str = ""
    basenm: str = ""
    input_dir: Optional[Path] = None
    tree: str = "flash"                 # flash | snb
    device: str = ""
    config: Mapping[str, Any] = field(default_factory=dict)
    build_inputs: Optional[Callable[[Dict[str, Any]], Any]] = None
    analyze_local: Optional[Callable[[Path, Path], int]] = None
    runner: Optional[Callable[["ExecOptions"], Any]] = None
    policy: ExecutionPolicy = DEFAULT_POLICY
    log_names: Tuple[str, ...] = ()
    description: str = ""


@dataclass
class ExecOptions:
    """本次调用的选项（CLI 参数的下沉）。"""
    mode: str = "auto"
    account: str = ""
    partition: str = ""
    distro: str = ""
    nproc: Optional[int] = None
    tmax: Optional[str] = None
    action: str = "all"
    wait: int = 0
    poll: float = 0.0
    with_plt: bool = False
    frames: int = 0
    skip_build: bool = False
    collect_move: bool = True
    dry_run: bool = False
    explain_only: bool = False
    timeout: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    ok: bool
    target: str = ""
    run_dir: Optional[Path] = None
    job_id: str = ""
    collected: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    trace: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# 平台探测（纯 stdlib，不 import flash —— 安装前也要能用）
# ═══════════════════════════════════════════════════════════════════

def _has_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _probe_slurm_healthy(timeout: int = 10) -> Tuple[bool, str]:
    """三条命令齐备 **且** 控制器可达才算 insitu 节点。

    ★ 只查 `which sbatch` 是不够的：WSL 里 `apt install slurm-client`
    也会装上客户端，但连不上控制器。必须 `sinfo -s` 成功返回分区行。
    """
    missing = [c for c in ("sbatch", "sacct", "sinfo") if not _has_cmd(c)]
    if missing:
        return False, f"缺少命令 {','.join(missing)}"
    try:
        r = subprocess.run(["sinfo", "-s"], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"sinfo 无法执行: {exc}"
    if r.returncode != 0:
        return False, f"sinfo rc={r.returncode}（控制器不可达？SLURM_CONF 未设？）"
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if len(lines) < 2:            # 1 行表头 + ≥1 分区
        return False, "sinfo 无分区行（控制器不可达）"
    return True, f"sinfo 返回 {len(lines) - 1} 个分区"


def _probe_wsl() -> Tuple[bool, str]:
    if not _has_cmd("wsl"):
        return False, "wsl.exe 不在 PATH"
    try:
        r = subprocess.run(["wsl", "-l", "-q"], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"wsl -l -q 失败: {exc}"
    # wsl -l -q 输出 UTF-16LE（Windows 实现细节）→ 用字节解码兜底
    raw = r.stdout or b""
    if isinstance(raw, bytes):
        text = raw.decode("utf-16-le", errors="replace")
    else:
        text = str(raw)
    distros = [d.strip() for d in text.replace("\x00", "").splitlines() if d.strip()]
    if r.returncode != 0 or not distros:
        return False, "未安装任何 WSL 发行版（wsl --install）"
    return True, f"发行版 {distros[0]}"


def resolve_target(mode: str | None = None,
                   policy: ExecutionPolicy = DEFAULT_POLICY,
                   env: Optional[Mapping[str, str]] = None) -> Tuple[str, List[str]]:
    """平台自适应判定表 → (target, trace)。

    判定顺序（与计划 §2.3 一致）：
      1. `mode` 显式            → 该值
      2. `FLASH_RUN_MODE` 环境  → 该值
      3. `policy.preferred`     → 该值（非 auto）
      4. 本机 slurm 健康        → hpc-insitu
      5. `os.name != "nt"`      → local
      6. Windows 且有 wsl       → wsl
      7. 全否                   → ExecutionTargetError

    最后与 `policy.allowed` 求交，**交集为空即报错**（绝不静默降级）。
    """
    env = os.environ if env is None else env
    trace: List[str] = []

    explicit = normalize_target(mode)
    if explicit and explicit != "auto":
        trace.append(f"[target] 判据 1 命中 (--mode={mode}) → {explicit}")
        target = explicit
    else:
        env_mode = normalize_target(env.get("FLASH_RUN_MODE", ""))
        if env_mode and env_mode != "auto":
            trace.append(f"[target] 判据 2 命中 (FLASH_RUN_MODE={env_mode}) → {env_mode}")
            target = env_mode
        elif normalize_target(policy.preferred) != "auto":
            target = normalize_target(policy.preferred)
            trace.append(f"[target] 判据 3 命中 (场景 preferred) → {target}")
        else:
            target = _auto_probe(trace)

    if target not in EXEC_TARGETS:
        raise ExecutionTargetError(
            f"未知运行模式 {mode!r}；可选: {', '.join(EXEC_TARGETS)}（或 auto）")

    if target not in policy.allowed:
        detail = "\n".join(trace)
        raise ExecutionTargetError(
            f"[X] 场景只允许 {', '.join(policy.allowed)}，当前判定为 {target}\n"
            f"    原因: {policy.forbid_reason or '（场景策略限制）'}\n"
            f"    判定轨迹:\n{detail}\n"
            f"    修复: 显式指定 --mode {policy.allowed[0]}，或设置 FLASH_RUN_MODE")

    trace.append(f"[target] 已校验策略 allowed={list(policy.allowed)} → {target}")
    return target, trace


def _auto_probe(trace: List[str]) -> str:
    if os.name == "nt":
        trace.append("[target] 判据 4 未命中 (os.name=nt ⇒ Windows 永不判 insitu)")
    else:
        ok, why = _probe_slurm_healthy()
        if ok:
            trace.append(f"[target] 判据 4 命中 ({why}) → hpc-insitu")
            return "hpc-insitu"
        trace.append(f"[target] 判据 4 未命中 ({why})")

    if os.name != "nt":
        trace.append(f"[target] 判据 5 命中 (os.name={os.name} ≠ nt) → local")
        return "local"

    ok_wsl, why_wsl = _probe_wsl()
    if ok_wsl:
        trace.append(f"[target] 判据 6 命中 ({why_wsl}) → wsl")
        return "wsl"
    trace.append(f"[target] 判据 6 未命中 ({why_wsl})")

    raise ExecutionTargetError(
        "[X] 无法判定运行环境：\n"
        "    · Windows 上未检测到可用的 WSL\n"
        "    · 本机也没有 slurm（sbatch/sacct/sinfo）\n"
        "    修复任选其一：\n"
        "      ① 安装 WSL:  wsl --install\n"
        "      ② 显式指定:  --mode hpc-remote（需 SSH 凭据）\n"
        "      ③ 在 Linux 主机/容器内运行（→ local）\n"
        "    诊断: 加 --explain-target 打印完整判定轨迹")


def explain_target(mode: str | None = None,
                   policy: ExecutionPolicy = DEFAULT_POLICY) -> str:
    """`--explain-target`：只打印判定全过程，不执行任何东西。"""
    lines = [f"场景策略: allowed={list(policy.allowed)} preferred={policy.preferred}"]
    if policy.forbid_reason:
        lines.append(f"禁止原因: {policy.forbid_reason}")
    if policy.nproc.mode != "auto":
        lines.append(f"核数约束: {policy.nproc.mode}={policy.nproc.value} {policy.nproc.note}")
    try:
        target, trace = resolve_target(mode, policy)
        lines.extend(trace)
        lines.append(f"结论: {target}")
    except ExecutionTargetError as exc:
        lines.append(str(exc))
        lines.append("结论: 拒绝执行")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 唯一执行入口
# ═══════════════════════════════════════════════════════════════════

def run_scene(scene: SceneSpec, opts: Optional[ExecOptions] = None) -> RunResult:
    """校验策略 → 解析目标 → 转发现有执行实现。

    失败一律 `ok=False`（含被策略拒绝）；**绝不吞错返回假成功**
    （历史回归 G3：引擎在 FLASH 失败时合成数据并报 success=True）。
    """
    opts = opts or ExecOptions()

    # ① 核数约束先于任何执行
    err = scene.policy.nproc.validate(opts.nproc)
    if err:
        return RunResult(ok=False, reason=f"[X] 核数约束不满足: {err}")

    # ② 目标解析（含 allowed 校验）
    try:
        target, trace = resolve_target(opts.mode, scene.policy)
    except ExecutionTargetError as exc:
        for line in str(exc).splitlines():
            print(line)
        return RunResult(ok=False, target="", reason=str(exc).splitlines()[0], trace=[])

    for line in trace:
        print(line)
    if opts.explain_only:
        return RunResult(ok=True, target=target, reason="explain-only", trace=trace)

    print(f"[run] 场景={scene.name} target={target}")

    # ③ 执行：存量脚本走 runner，否则走声明式
    if scene.runner is not None:
        # 把已解析目标交给 runner —— 存量脚本据此设置 FLASH_RUN_MODE，
        # 避免"二次解析"得出不同结论（例如 auto 两次探测结果不一致）。
        opts.extra["_target"] = target
        try:
            result = scene.runner(opts)
        except Exception as exc:                      # noqa: BLE001
            return RunResult(ok=False, target=target, trace=trace,
                             reason=f"{type(exc).__name__}: {exc}")
        if isinstance(result, RunResult):
            result.target = target
            result.trace = trace
            return result
        if isinstance(result, dict):
            return RunResult(ok=bool(result.get("ok", True)), target=target,
                             reason=str(result.get("reason", "")), trace=trace,
                             stats=result)
        return RunResult(ok=bool(result), target=target, trace=trace)

    return _run_declarative(scene, opts, target, trace)


def _run_declarative(scene: SceneSpec, opts: ExecOptions, target: str,
                     trace: List[str]) -> RunResult:
    """声明式路径（新场景）：build_inputs → modes 策略 → 统一回收。

    ★ 目前只接 `local` / `wsl`（两者都是"单机跑 run_flash.sh"），
      hpc-* 的声明式执行在 B7 与 SNB 执行体一起收编；在此之前
      超算场景请提供 `runner`（存量脚本适配），避免出现半套实现。
    """
    if target.startswith("hpc"):
        return RunResult(ok=False, target=target, trace=trace,
                         reason=("声明式场景暂不支持 hpc-*（B7 收编中）；"
                                 "请为该场景提供 SceneSpec.runner"))

    if scene.build_inputs is None:
        return RunResult(ok=False, target=target, trace=trace,
                         reason="声明式场景缺少 build_inputs")

    try:
        scene.build_inputs(dict(scene.config))
    except Exception as exc:                          # noqa: BLE001
        return RunResult(ok=False, target=target, trace=trace,
                         reason=f"输入生成失败: {type(exc).__name__}: {exc}")

    if opts.dry_run:
        return RunResult(ok=True, target=target, trace=trace, reason="dry-run")

    from .modes.runner import (
        WslSpec,
        allocate_run_id,
        package_root,
        run_wsl,
    )
    from .remote.executors import LocalExecutor, WslExecutor
    from .remote.artifacts import fetch_artifacts
    from .remote.fetch_policy import select_fetch_files  # noqa: F401  (文档锚点)

    input_dir = scene.input_dir or (package_root() / scene.objdir)
    runs_dir = package_root().parent / "flash_sim_runs" / scene.name
    rid = allocate_run_id(runs_dir, input_dir)
    run_dir = runs_dir / f"run_{rid:06d}"
    out_dir = run_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    exe = LocalExecutor() if target == "local" else WslExecutor(distro=opts.distro)
    script = f"{scene.input_dir}/run_flash.sh"
    out, err, rc = exe.run(
        f"cd '{Path(scene.input_dir).as_posix()}' && FLASH_COLLECT_DIR='{out_dir.as_posix()}' "
        f"bash run_flash.sh", timeout=scene.policy.run_timeout)

    collected, stats = fetch_artifacts(
        exe, str(Path(scene.objdir)), out_dir,
        basenm=scene.basenm, with_plt=opts.with_plt,
        frames=opts.frames, log_names=scene.log_names, move=opts.collect_move)

    ok = rc == 0 and bool(collected)
    return RunResult(
        ok=ok, target=target, run_dir=run_dir, collected=collected,
        stats={"rc": rc, **stats, "script": script},
        reason="" if ok else ("rc=%d" % rc if rc != 0 else "零产物（收集为空）"),
        trace=trace,
    )
