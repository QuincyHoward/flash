# -*- coding: utf-8 -*-
"""batch.calibrate — 批量优化前标定驱动（E1 核数扫描 / E2 打包扫描 / 余量档）
════════════════════════════════════════════════════════════════════════════

一个场景做批量仿真前的标定测试（多节点并行：每个配置独立作业独占节点）：

  E1      单实例核数扫描 1/2/4/8/16/24/32/48（各 1 个 seq 作业，串行独占）
  E2      打包密度扫描 (12,4)(6,8)(3,16)(2,24)(24,2)（各 1 个 conc 作业，48 rank 满节点）
  margin  最佳打包 -1 实例（余量对照）

产物：adapter.batch_root()/calibration.json + leaderboard.json 追加
（batch_id = cal_e1_nt8 / cal_e2_i12nt4 / cal_margin_...）。

CLI（skill 可直接调用）:
    python -m flash.flash_run.remote.batch.calibrate \
        --adapter "module:ADAPTER" [--skip-e1] [--dry-run] [--time-limit E2=04:00:00]

早停钩子：on_probe 回调（缺省只打印进度，不自动取消）。★ 自动早停
（投影终值 < threshold×榜单最优即 scancel，2026-11-08 用户规则）已在
runner.run_batch 缺省启用（--no-early-cancel 关闭）；标定流程如需同款
行为，可在 on_probe 传入 runner.make_auto_probe 的判定逻辑。部分数据
由内联归档保全，取消后照常 collect 留痕。
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from .control import (cancel_batch, collect_batch, load_json, parse_slurm_time,
                      poll_batch, probe_batch, save_json,
                      stats_to_leaderboard_entry, merge_leaderboard, submit_batch)
from .plans import PlanSpec, load_calibration
from .runner import (_exe, _paths, _query_cores, _render_and_upload,
                     _shared_roots, _default_partition, build_instances,
                     plan_batch)

#: E1 核数档（各为独立单节点 seq 作业）
E1_CONFIGS = (1, 2, 4, 8, 16, 24, 32, 48)
#: E2 打包 (instances, ntasks)
E2_PACKINGS = ((12, 4), (6, 8), (3, 16), (2, 24), (24, 2))
#: 余量档：最佳打包实例数减 1
MARGIN_DELTAS = (-1,)
#: 各阶段缺省墙钟（1.6ns 同任务口径实测：1 rank ~1h、24×2 需 >3h）
E1_TIME_LIMIT = "02:30:00"
E2_TIME_LIMIT = "04:00:00"


def _mk_plan(kind: str, instances: int, ntasks: int, mode: str,
             wall_clock: str) -> PlanSpec:
    return PlanSpec(name=f"cal_{kind}", instances=instances,
                    ntasks_per=ntasks, mode=mode, wall_clock=wall_clock,
                    note="标定专用方案（不计入方案库 PLANS）")


def _launch(adapter, bid: str, spec: PlanSpec, overrides: dict, *,
            mode: str, n_overrides: int, ntasks_list, partition: str,
            time_limit: str, dry_run: bool) -> dict:
    """单配置：plan_batch → 渲染上传 → 提交（不等待）。"""
    planned = plan_batch(adapter, [overrides] * n_overrides, spec,
                         same_task=(n_overrides > 1), ntasks_list=ntasks_list,
                         partition=partition, time_limit=time_limit,
                         batch_id=bid, dry_run=dry_run)
    if dry_run:
        state = _render_and_upload(adapter, bid, spec, planned["instances"],
                                   mode, time_limit,
                                   planned["manifest"]["partition"],
                                   dry_run=True)
        return {"bid": bid, "dry_run": True}
    state = _render_and_upload(adapter, bid, spec, planned["instances"],
                               mode, time_limit,
                               planned["manifest"]["partition"])
    exe, _m = _exe()
    state = submit_state(adapter, bid, state)
    return state


def submit_state(adapter, bid: str, state: dict) -> dict:
    from .runner import submit_state as _submit  # 复用 runner 实现
    return _submit(adapter, bid, state)


def calibrate(adapter, *, partition: str = "", overrides: dict | None = None,
              skip_e1: bool = False, packings=None, skip_margin: bool = False,
              e1_time_limit: str = E1_TIME_LIMIT,
              e2_time_limit: str = E2_TIME_LIMIT,
              poll_interval: int = 180, dry_run: bool = False,
              on_probe=None) -> dict:
    """标定主流程：提交全部配置（多节点并行）→ 轮询 → 收集 → calibration.json。"""
    ov = overrides or {"power_factor": 1.0}
    partition = partition or _default_partition()
    cores = _query_cores(partition)
    print(f"[calibrate] scene={adapter.scene} cores/node={cores} "
          f"partition={partition}" + ("  [dry-run]" if dry_run else ""))

    jobs: list[dict] = []   # {bid, spec, state, kind, key}

    # ── 1) 生成配置集 ──
    cfgs = []
    if not skip_e1:
        cfgs += [("e1", f"cal_e1_nt{n}", _mk_plan(f"e1_nt{n}", 1, n, "seq", e1_time_limit),
                  1, [n], n, e1_time_limit) for n in E1_CONFIGS]
    pk = packings or E2_PACKINGS
    cfgs += [("e2", f"cal_e2_i{m}nt{nt}", _mk_plan(f"e2_i{m}nt{nt}", m, nt, "conc", e2_time_limit),
              m, [nt] * m, m * nt, e2_time_limit) for (m, nt) in pk]
    if not skip_margin and pk:
        m0, nt0 = pk[0]                      # 主打包（E2 实测最优 12×4）
        mm = max(m0 + min(MARGIN_DELTAS), 1)  # 余量档：实例数 -1（如 11×4）
        cfgs += [("margin", f"cal_margin_i{mm}nt{nt0}",
                  _mk_plan(f"margin_i{mm}nt{nt0}", mm, nt0, "conc", e2_time_limit),
                  mm, [nt0] * mm, mm * nt0, e2_time_limit)]

    # ── 2) 并行提交全部（不等待） ──
    for kind, bid, spec, n_ov, nts, _total, tl in cfgs:
        print(f"── {bid} ({spec.instances}×{spec.ntasks_per} {spec.mode}) ──")
        st = _launch(adapter, bid, spec, ov, mode=spec.mode,
                     n_overrides=n_ov, ntasks_list=nts, partition=partition,
                     time_limit=tl, dry_run=dry_run)
        jobs.append({"bid": bid, "spec": spec, "state": st, "kind": kind})

    if dry_run:
        print("[calibrate] dry-run 完成（渲染核对，未提交）")
        return {"dry_run": True, "n_configs": len(cfgs)}

    # ── 3) 轮询收集（先完成先收集；probe 早停钩子可选） ──
    exe, _m = _exe()
    pending = {j["bid"]: j for j in jobs}
    deadline = time.time() + max(parse_slurm_time(e2_time_limit),
                                 parse_slurm_time(e1_time_limit)) + 1800
    stats_by_key: dict[str, dict] = {}
    while pending and time.time() < deadline:
        for bid, j in list(pending.items()):
            st = poll_batch(exe, j["state"]["job_id"])
            if any(st.startswith(t) for t in
                   ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF",
                    "NODE_FAIL")):
                print(f"[calibrate] {bid} 终态 {st}")
                from flash.flash_run.remote.session import RemoteSession
                from flash.flash_run.env.devices import credential_name
                with RemoteSession(credential_name(), verbose=False) as s:
                    stats = collect_batch(exe, s, j["state"],
                                          Path(adapter.batch_root()) / bid / "download")
                entry = stats_to_leaderboard_entry(
                    stats, plan=j["spec"].name, cores_per_node=cores)
                merge_leaderboard(Path(adapter.batch_root()) / "leaderboard.json",
                                  entry)
                key = (f"{j['kind']}:" +
                       (f"nt{j['spec'].ntasks_per}" if j["kind"] == "e1"
                        else f"{j['spec'].instances}x{j['spec'].ntasks_per}"))
                stats_by_key[key] = stats
                del pending[bid]
            elif on_probe:
                sp = j["state"]["shared"]
                probe = probe_batch(exe, f"{sp['log']}/{j['state']['job_name']}"
                                         f"*_{j['state']['job_id']}.out")
                on_probe(bid, j, probe)
        if pending:
            time.sleep(poll_interval)

    # 超时兜底：取消残留作业（部分数据已内联归档）
    for bid, j in pending.items():
        print(f"[calibrate] {bid} 未在预算内结束，取消（部分数据已归档）")
        cancel_batch(exe, j["state"]["job_id"])

    # ── 4) 汇总 calibration.json ──
    e1 = {k.split(":")[1].replace("nt", ""): v["summary"]["aggregate_steps_per_s"]
          for k, v in stats_by_key.items() if k.startswith("e1:")}
    e2 = {k.split(":")[1].replace("x", "×"): v["summary"]["aggregate_steps_per_s"]
          for k, v in stats_by_key.items() if k.startswith("e2:")}
    peak_inst, best_pack = None, None
    if e1:
        peak_inst = max(e1, key=lambda k: e1[k] or 0)
    if e2:
        best_pack = max(e2, key=lambda k: e2[k] or 0)
    hint = None
    for k, v in stats_by_key.items():
        if best_pack and k.endswith(best_pack.replace("×", "x")) and v.get("job_elapsed_hint"):
            hint = v["job_elapsed_hint"]
    suggested = (f"{int((hint or 9000) * 1.5) // 3600}:"
                 f"{(int((hint or 9000) * 1.5) % 3600) // 60:02d}:00") if hint else None
    cal = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scene": adapter.scene, "partition": partition,
        "cores_per_node": cores, "overrides": ov,
        "e1_steps_per_s": e1, "e2_aggregate": e2,
        "best_packing": best_pack, "per_instance_peak": e1.get(peak_inst) if peak_inst else None,
        "suggested_wall_clock": suggested,
        "n_configs": len(cfgs), "n_collected": len(stats_by_key),
    }
    out = Path(adapter.batch_root()) / "calibration.json"
    save_json(out, cal)
    print(f"[calibrate] calibration.json -> {out}")
    print(f"[calibrate] 最佳打包={best_pack}  单实例峰值={cal['per_instance_peak']} 步/s")
    return cal


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="flash.flash_run.remote.batch.calibrate",
        description="批量优化前标定（E1/E2/margin，多节点并行；适配器经 --adapter 指定）")
    ap.add_argument("--adapter", required=True, help="适配器 'module:ADAPTER'")
    ap.add_argument("--overrides-json", default='{"power_factor": 1.0}',
                    help="标定任务 overrides（缺省 PF=1.0）")
    ap.add_argument("--partition", default="")
    ap.add_argument("--skip-e1", action="store_true")
    ap.add_argument("--skip-margin", action="store_true")
    ap.add_argument("--packings", default="",
                    help="逗号分隔 m x nt 列表，如 '12x4,6x8'（缺省 E2_PACKINGS）")
    ap.add_argument("--e1-time-limit", default=E1_TIME_LIMIT)
    ap.add_argument("--e2-time-limit", default=E2_TIME_LIMIT)
    ap.add_argument("--poll-interval", type=int, default=180)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    from .runner import load_adapter
    adapter = load_adapter(args.adapter)
    ov = json.loads(args.overrides_json)
    packings = ([tuple(int(x) for x in p.split("x"))
                 for p in args.packings.split(",")] if args.packings else None)
    calibrate(adapter, partition=args.partition, overrides=ov,
              skip_e1=args.skip_e1, packings=packings,
              skip_margin=args.skip_margin,
              e1_time_limit=args.e1_time_limit,
              e2_time_limit=args.e2_time_limit,
              poll_interval=args.poll_interval, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    import json as _json
    raise SystemExit(main())
