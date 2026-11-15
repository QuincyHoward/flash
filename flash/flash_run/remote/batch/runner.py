# -*- coding: utf-8 -*-
"""batch.runner — 批量一键链 plan→upload→submit→poll→collect（场景无关）
════════════════════════════════════════════════════════════════════════════

场景差异全部经 SceneBatchAdapter 注入；方案选择两级回退
（显式 --plan → 内置默认 = 单节点单任务 p1x32_lowlat）。

CLI（skill 可直接调用，适配器经 module:ATTR 指定）:
    python -m flash.flash_run.remote.batch.runner <scene-adapter> \
        run --overrides-json '[{"power_factor":1.0}]' [--plan p6x8] [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path
from typing import Optional, Sequence

from .control import (cancel_batch, collect_batch, load_json, parse_slurm_time,
                      poll_batch, probe_batch, save_json, stats_to_leaderboard_entry,
                      submit_batch, upload_batch_inputs, merge_leaderboard)
from .plans import PlanSpec, resolve_plan, suggest_wall_clock, load_calibration
from .scripts import BatchGroupSpec, BatchInstance, render_batch_job_body, \
    render_batch_sbatch

_TERMINAL = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF",
             "NODE_FAIL")


# ────────────────────────────────────────────────────────────────────
# 适配器加载 / 共享路径
# ────────────────────────────────────────────────────────────────────

def load_adapter(spec: str):
    """'module:ATTR' → 适配器对象（子场景薄壳也可直接传对象跳过此步）。"""
    mod_name, _, attr = spec.partition(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, attr) if attr else mod


def _shared_roots(adapter):
    from flash.scenarios.core.hpc.submit_cli import remote_root
    decl = adapter.hpc_decl()
    shared = remote_root()
    flash_home = decl.flash_home_default
    if "$HOME" in shared or "$HOME" in flash_home:
        from flash.scenarios.core.hpc.submit_cli import _remote_capture
        home = _remote_capture("printf '%s' \"$HOME\"", timeout=60)
        if not home.startswith("/"):
            raise RuntimeError(f"无法解析远端 $HOME: {home!r}")
        shared = shared.replace("$HOME", home)
        flash_home = flash_home.replace("$HOME", home)
    return decl, shared, flash_home


def _paths(bid: str, shared: str, scene: str) -> dict:
    return {
        "input":  f"{shared}/pf_batch/{bid}/input",
        "out":    f"{shared}/flash_output/{scene}/pf_batch/{bid}",
        "log":    f"{shared}/flash_logs/{scene}/pf_batch/{bid}",
        "script": f"{shared}/flash_logs/{scene}/pf_batch/{bid}/batch_{bid}.sh",
    }


def _exe():
    from flash.flash_run.remote.executors import SSHExecutor, LocalExecutor
    import shutil
    if shutil.which("sbatch"):
        return LocalExecutor(), "local"
    from flash.flash_run.env.devices import credential_name
    return SSHExecutor(credential=credential_name()), "ssh"


def _default_partition() -> str:
    from flash.flash_run.env.devices import partition
    return partition()


def _query_cores(partition: str, default: int = 48) -> int:
    try:
        exe, _ = _exe()
        from flash.flash_run.remote.slurm_control import cores_per_node
        return int(cores_per_node(exe, partition, default=default))
    except Exception as e:
        print(f"  [cores] 查询失败 ({e}), 回退 default={default}")
        return default


# ────────────────────────────────────────────────────────────────────
# 实例模型构建
# ────────────────────────────────────────────────────────────────────

def _instance_tag(i: int, overrides: dict, par_base: str, same_task: bool) -> str:
    pf = overrides.get("power_factor")
    if pf is not None:
        return f"r{i}_pf{pf}" if same_task else f"pf{pf}"
    return f"r{i}_" + Path(par_base).stem


def build_instances(overrides_list: Sequence[dict], plan: PlanSpec,
                    adapter, same_task: bool = False,
                    ntasks_list: Optional[Sequence[int]] = None) -> list[dict]:
    """overrides 列表 → 实例 dicts [{tag, par_name, ntasks, overrides}]。

    same_task=True 时所有实例共用 overrides[0]（公平对比/标定），
    实例数 = len(ntasks_list) 或 len(overrides_list)。
    """
    if same_task:
        base = overrides_list[0]
        n = len(ntasks_list) if ntasks_list else len(overrides_list)
        nts = list(ntasks_list) if ntasks_list else [plan.ntasks_per] * n
        pairs = [(base, n_i) for n_i in nts]
    else:
        if ntasks_list and len(ntasks_list) != len(overrides_list):
            raise ValueError("--ntasks-list 与 overrides 数量不一致（或加 same_task）")
        nts = (list(ntasks_list) if ntasks_list
               else [plan.ntasks_per] * len(overrides_list))
        pairs = list(zip(overrides_list, nts))
    instances = []
    for i, (ov, n_i) in enumerate(pairs):
        par_base = adapter.par_basename(ov)
        instances.append({"tag": _instance_tag(i, ov, par_base, same_task),
                          "par_name": par_base, "ntasks": int(n_i),
                          "overrides": ov})
    return instances


# ────────────────────────────────────────────────────────────────────
# plan（本地渲染） / upload / submit / poll / collect
# ────────────────────────────────────────────────────────────────────

def plan_batch(adapter, overrides_list: Sequence[dict], plan: PlanSpec, *,
               same_task: bool = False, ntasks_list=None, partition: str = "",
               time_limit: str = "", batch_id: str = "", dry_run: bool = False) -> dict:
    """渲染 par + 静态输入 + manifest → {bid, instances, ...}。"""
    bid = batch_id or time.strftime("b_%Y%m%d_%H%M%S")
    partition = partition or _default_partition()
    cores = _query_cores(partition)
    instances = build_instances(overrides_list, plan, adapter, same_task,
                                ntasks_list)
    root = Path(adapter.batch_root()) / bid
    inp = root / "inputs"
    inp.mkdir(parents=True, exist_ok=True)

    # 1) par 渲染（unique overrides 去重）
    seen: dict[str, str] = {}
    for inst in instances:
        name = inst["par_name"]
        if name in seen:
            continue
        (inp / name).write_text(adapter.render_par(inst["overrides"]),
                                encoding="utf-8", newline="\n")
        seen[name] = inst["tag"]
        print(f"  [plan] {name} (首实例 {inst['tag']})")

    # 2) 静态输入
    for fname, blob in adapter.static_inputs().items():
        (inp / fname).write_bytes(blob)

    manifest = {
        "batch_id": bid, "plan": plan.name,
        "instances": [{k: v for k, v in i.items() if k != "overrides"}
                      for i in instances],
        "overrides_list": [i["overrides"] for i in instances],
        "mode": plan.mode,
        "pin": getattr(plan, "pin", "cumulative"),
        "same_task": bool(same_task),
        "cores_per_node": cores, "partition": partition,
        "n_instances": len(instances),
        "total_ranks": sum(i["ntasks"] for i in instances),
        "alloc_ranks": (max(i["ntasks"] for i in instances)
                        if getattr(plan, "pin", "cumulative") == "shared"
                        else sum(i["ntasks"] for i in instances)),
        "time_limit": time_limit or plan.wall_clock,
        "par_files": sorted(seen),
    }
    manifest["occupancy"] = round(100.0 * manifest["alloc_ranks"]
                                  / max(cores, 1), 1)
    save_json(root / "manifest.json", manifest)
    print(f"[plan] batch={bid} plan={plan.name} mode={plan.mode} "
          f"pin={manifest['pin']} 实例={len(instances)} "
          f"申请rank={manifest['alloc_ranks']} cores/node={cores} "
          f"占用率={manifest['occupancy']}%")
    return {"bid": bid, "instances": instances, "manifest": manifest,
            "root": root, "cores": cores}


def _render_and_upload(adapter, bid: str, plan: PlanSpec, instances, mode: str,
                       time_limit: str, partition: str, dry_run: bool = False) -> dict:
    """渲染 sbatch 文本 + 上传输入与脚本 → state dict。"""
    decl, shared, flash_home = _shared_roots(adapter)
    sp = _paths(bid, shared, adapter.scene)
    root = Path(adapter.batch_root()) / bid
    inp = root / "inputs"
    from flash.scenarios.core.hpc.submit_cli import build_env_block
    env_block = build_env_block(decl.env_profile, flash_home)
    group = BatchGroupSpec(
        instances=[BatchInstance(tag=i["tag"], par_name=i["par_name"],
                                 ntasks=i["ntasks"]) for i in instances],
        mode=mode, pin=getattr(plan, "pin", "cumulative"),
        touch_files=adapter.touch_files(), env_block=env_block,
    )
    body = render_batch_job_body(
        bid, group, input_dir=sp["input"], output_dir=sp["out"],
        scratch_root=f"/dev/shm/flash_batch_{bid}",
        unit=decl.unit_for(bid),
        flash_home=flash_home, setup_args=" ".join(decl.setup_args()),
    )
    text = render_batch_sbatch(bid, body, group, partition=partition,
                               time_limit=time_limit,
                               out_dir=sp["log"], workdir=sp["log"].rsplit("/flash_logs", 1)[0])
    script_local = root / "batch.sh"
    script_local.write_text(text, encoding="utf-8", newline="\n")
    print(f"[render] sbatch -> {script_local}")

    if dry_run:
        return {"dry_run": True, "script_local": str(script_local)}

    from flash.flash_run.remote.session import RemoteSession
    from flash.flash_run.env.devices import credential_name
    with RemoteSession(credential_name(), verbose=False) as s:
        s.run(f"mkdir -p {sp['input']} {sp['out']} {sp['log']}", timeout=60)
        n = upload_batch_inputs(s, inp, sp["input"])
        print(f"[upload] {n} 个文件 -> {sp['input']}")
        if not s.upload(str(script_local), sp["script"]):
            raise RuntimeError("作业脚本上传失败")
        s.run(f"sed -i 's/\\r$//' {sp['script']} && chmod +x {sp['script']}",
              timeout=30)
        print(f"[upload] 作业脚本 -> {sp['script']}")

    state = {"batch_id": bid, "job_name": f"batch_{bid}",
             "shared": sp, "instances": instances, "mode": mode,
             "cores_per_node": manifest_cores(adapter, bid),
             "log_name": group.log_name,
             "markers": {"elapsed": group.elapsed_marker,
                         "steps": group.steps_marker}}
    save_json(root / "state.json", state)
    return state


def manifest_cores(adapter, bid: str) -> int:
    mf = load_json(Path(adapter.batch_root()) / bid / "manifest.json", {}) or {}
    return int(mf.get("cores_per_node", 48))


def submit_state(adapter, bid: str, state: dict) -> dict:
    exe, _mode = _exe()
    job_id = submit_batch(exe, state["shared"]["script"], state["job_name"])
    state["job_id"] = job_id
    save_json(Path(adapter.batch_root()) / bid / "state.json", state)
    print(f"[submit] batch={bid}  job_id={job_id}")
    return state


def wait_state(adapter, bid: str, state: dict, *, poll_interval: int = 180,
               probe_every: int = 3, on_probe=None) -> str:
    """轮询到终态；每 probe_every 次 poll 触发 on_probe(state, probe)（早停钩子）。"""
    exe, _mode = _exe()
    job_id = state["job_id"]
    bound = parse_slurm_time(state.get("time_limit", "04:00:00")) + 900
    t0 = time.time()
    n_poll = 0
    while True:
        st = poll_batch(exe, job_id)
        print(f"[poll] batch={bid} job={job_id} state={st}")
        if any(st.startswith(t) for t in _TERMINAL):
            return st
        if time.time() - t0 > bound:
            print(f"[poll] 超出墙钟预算，放弃等待")
            return "TIMEOUT"
        n_poll += 1
        if on_probe and n_poll % probe_every == 0:
            sp = state["shared"]
            probe = probe_batch(exe, f"{sp['log']}/{state['job_name']}*_{job_id}.out")
            on_probe(state, probe)
        time.sleep(poll_interval)


def finish_batch(adapter, bid: str, state: dict, plan: PlanSpec) -> dict:
    """collect → stats.json → leaderboard 追加。"""
    exe, _mode = _exe()
    from flash.flash_run.remote.session import RemoteSession
    from flash.flash_run.env.devices import credential_name
    with RemoteSession(credential_name(), verbose=False) as s:
        stats = collect_batch(exe, s, state,
                              Path(adapter.batch_root()) / bid / "download")
    entry = stats_to_leaderboard_entry(stats, plan=plan.name,
                                       cores_per_node=state.get("cores_per_node", 48))
    merge_leaderboard(Path(adapter.batch_root()) / "leaderboard.json", entry)
    return stats


# ────────────────────────────────────────────────────────────────────
# 自动早停（用户规则：提速测试中显著低于当前最优的方案可终止、记录、另测）
# ────────────────────────────────────────────────────────────────────

def make_auto_probe(adapter, bid: str, *, threshold: float = 0.9,
                    min_completed: int = 3) -> "callable":
    """构建 on_probe 回调：投影终值聚合 < threshold×榜单最优 → scancel。

    判据（2026-11-08 用户规则：提速测试中显著低于当前最优的方案终止、
    记录、另测；部分数据已内联归档，终态 CANCELLED 后照常 collect 留痕）：
        proj = partial_aggregate + 剩余实例数 × 已观测最低单实例步速
        proj < threshold × 榜单当前最优聚合 → 取消
    防误杀护栏：
        - 剩余实例 < 3 不判（临近完成让其自然收尾，避免低估尾部）
        - 完成实例 < min_completed 不判（样本不足）
        - 榜单无实测（首个测量配置）不判
    """
    exe, _mode = _exe()
    lb_path = Path(adapter.batch_root()) / "leaderboard.json"

    def _best_aggregate() -> Optional[float]:
        lb = load_json(lb_path, None) or {}
        vals = [float(e["aggregate_steps_per_s"]) for e in lb.get("entries", [])
                if e.get("aggregate_steps_per_s")]
        return max(vals) if vals else None

    def on_probe(state, probe) -> None:
        n_done = probe.get("n_done", 0)
        partial = probe.get("partial_aggregate") or 0.0
        if n_done < min_completed or partial <= 0:
            return
        best = _best_aggregate()
        if best is None:
            return
        n_total = len(state.get("instances", [])) or n_done
        remaining = max(n_total - n_done, 0)
        if remaining < 3:
            return
        elapsed, steps = probe.get("elapsed", {}), probe.get("steps", {})
        sps = [steps[t] / el for t, el in elapsed.items()
               if t in steps and el > 0 and steps[t] > 0]
        proj = partial + remaining * (min(sps) if sps else 0.0)
        if proj < threshold * best:
            job_id = state.get("job_id")
            print(f"[probe] {bid}: {n_done}/{n_total} 完成, 部分聚合 {partial:.1f}, "
                  f"投影终值 {proj:.1f} < {threshold:.0%}×最优 {best:.1f} → 自动取消")
            state["early_cancelled"] = {
                "at_done": n_done, "partial_aggregate": partial,
                "proj_aggregate": round(proj, 1), "best_at_cancel": best,
                "threshold": threshold}
            save_json(Path(adapter.batch_root()) / bid / "state.json", state)
            cancel_batch(exe, str(job_id))

    return on_probe


# ────────────────────────────────────────────────────────────────────
# 一键链
# ────────────────────────────────────────────────────────────────────

def run_batch(adapter, overrides_list: Sequence[dict], plan: str | PlanSpec = "", *,
              same_task: bool = False, ntasks_list=None, batch_id: str = "",
              wall_clock: str = "", partition: str = "", poll_interval: int = 180,
              early_cancel: bool = True, cancel_threshold: float = 0.9,
              min_probe_completed: int = 3,
              dry_run: bool = False, on_probe=None) -> dict:
    """plan→upload→submit→poll→collect 一键链。

    plan: 名字串或 PlanSpec；缺省 "" → 单节点单任务默认方案
    （p1x12：整节点给单仿真，核数取标定峰值）。
    打包方案经 --plan 显式选择；--ntasks-list 为标定式实验（合成 custom 方案）。
    early_cancel: 提速测试自动早停——探针投影终值聚合 <
      cancel_threshold × 榜单当前最优 → scancel、记录、部分数据照常收集
      （2026-11-08 用户规则）；on_probe 显式传入时优先于自动探针。
    """
    p = plan if isinstance(plan, PlanSpec) else (
        # ntasks_list 显式给定时为标定式实验 → 合成 custom 方案（不冒用自动方案名）
        PlanSpec(f"custom_{sum(ntasks_list)}r", len(ntasks_list), ntasks_list[0],
                 mode="conc")
        if ntasks_list else resolve_plan(plan))
    cal = load_calibration(Path(adapter.batch_root()) / "calibration.json")
    tl = wall_clock or suggest_wall_clock(cal, p)
    print(f"[run] plan={p.name} ({p.instances}×{p.ntasks_per}, {p.mode}) "
          f"墙钟={tl}" + ("  [dry-run]" if dry_run else ""))

    planned = plan_batch(adapter, overrides_list, p, same_task=same_task,
                         ntasks_list=ntasks_list, partition=partition,
                         time_limit=tl, batch_id=batch_id, dry_run=dry_run)
    bid = planned["bid"]
    state = _render_and_upload(adapter, bid, p, planned["instances"], p.mode,
                               tl, planned["manifest"]["partition"],
                               dry_run=dry_run)
    if dry_run:
        return {"dry_run": True, "bid": bid, "plan": p.name}
    state = submit_state(adapter, bid, state)
    if on_probe is None and early_cancel:
        on_probe = make_auto_probe(adapter, bid, threshold=cancel_threshold,
                                   min_completed=min_probe_completed)
    final = wait_state(adapter, bid, state, poll_interval=poll_interval,
                       on_probe=on_probe)
    print(f"[run] 终态 {final}，收集产物…")
    stats = finish_batch(adapter, bid, state, p)
    return {"bid": bid, "plan": p.name, "state": final, "stats": stats}


# ────────────────────────────────────────────────────────────────────
# CLI（适配器经 module:ATTR 指定）
# ────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="flash.flash_run.remote.batch.runner",
        description="场景批量提速一键链（适配器经 --adapter module:ATTR 指定）")
    ap.add_argument("--adapter", required=True, help="适配器 'module:ADAPTER'")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="一键 run_batch")
    p.add_argument("--overrides-json", required=True,
                   help='实例 overrides 列表 JSON，如 [{"power_factor":1.0}]')
    p.add_argument("--plan", default="",
                   help="方案名（缺省 = 单节点单任务 p1x32_lowlat；"
                        "打包方案如 p12x4_full 需显式指定）")
    p.add_argument("--same-task", action="store_true")
    p.add_argument("--ntasks-list", default="")
    p.add_argument("--batch-id", default="")
    p.add_argument("--wall-clock", default="")
    p.add_argument("--partition", default="")
    p.add_argument("--poll-interval", type=int, default=180)
    p.add_argument("--no-early-cancel", action="store_true",
                   help="关闭自动早停（缺省：投影终值 < 90%%×榜单最优即取消）")
    p.add_argument("--cancel-threshold", type=float, default=0.9,
                   help="自动早停阈值（投影/最优比，缺省 0.9）")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=_cli_run)

    p = sub.add_parser("plans", help="列出方案库与当前排序")
    p.set_defaults(fn=_cli_plans)

    args = ap.parse_args(argv)
    return args.fn(args)


def _cli_run(args) -> int:
    adapter = load_adapter(args.adapter)
    overrides = json.loads(args.overrides_json)
    nts = ([int(x) for x in args.ntasks_list.split(",") if x.strip()]
           if args.ntasks_list else None)
    run_batch(adapter, overrides, args.plan, same_task=args.same_task,
              ntasks_list=nts, batch_id=args.batch_id,
              wall_clock=args.wall_clock, partition=args.partition,
              poll_interval=args.poll_interval,
              early_cancel=not args.no_early_cancel,
              cancel_threshold=args.cancel_threshold,
              dry_run=args.dry_run)
    return 0


def _cli_plans(args) -> int:
    from .plans import rank_plans
    for plan, value in rank_plans():
        print(f"  {value:>7.1f} 步/s  {plan.name:<14} "
              f"{plan.instances}×{plan.ntasks_per} {plan.mode}  {plan.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
