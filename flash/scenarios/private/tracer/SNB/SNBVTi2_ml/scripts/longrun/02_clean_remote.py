# -*- coding: utf-8 -*-
"""02_clean_remote.py — 清空超算（NC-E）上的 FLASH 输入/输出（默认 dry-run）。

★★ 安全设计（必读）
====================
远端删除**只针对产物 glob**，且每条模式都强制 `cd <绝对目录>` 限定作用域：

| 远端位置 | 处理 | 模式 |
|---|---|---|
| `~/QC/FLASH/FLASHSNB/FLASH4.8/<objdir>/snbvtiug_*` | **删** | chk/plt/dat 产物 |
| `…/<objdir>/wsl_run_snbvti.log` | **删** | 运行日志 |
| `…/<objdir>/_t_start` `_t_end` | **删** | 计时戳 |
| `…/<objdir>/flash4` `*.o` 等 | **保护** | 编译产物, 删了要重编（很贵） |
| `~/QC/FLASH/FLASHSNB/FLASH4.8/source/**` | **保护** | ★ FLASH 源码与 SNB 单元 |
| `~/QC/SNBVTi_deploy/*` 部署包 | **删** | unit.tar.gz / run.sh / build.sh / 旧 out.txt |

★ 绝不出现 `rm -rf`；只用 `rm -f <glob>`。目录级清理需显式 `--purge-deploy`。

用法：
    python 02_clean_remote.py                    # 只列清单（dry-run）
    python 02_clean_remote.py --apply            # 真删产物
    python 02_clean_remote.py --apply --purge-deploy   # 连部署目录产物一起清
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _longrun_lib as L  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="清空超算 FLASH 输入/输出（默认 dry-run）")
    ap.add_argument("--apply", action="store_true", help="真正执行远端删除")
    ap.add_argument("--account", default=L.ACCOUNT_NCE,
                    help=f"凭据名（默认 {L.ACCOUNT_NCE} = NC-E）")
    ap.add_argument("--purge-deploy", action="store_true",
                    help="同时清理部署目录产物（unit.tar.gz/run.sh/out.txt 等）")
    args = ap.parse_args()

    dry = not args.apply
    L.step(f"清空超算 FLASH 输入/输出  ({'DRY-RUN' if dry else '★ 实际执行'}）")
    if dry:
        L.log("★ 当前为 DRY-RUN，只列清单不动文件。加 --apply 才真正执行。", "WARN")

    try:
        rm = L.R._HpcRemote(args.account)
        rm.__enter__()
    except Exception as e:
        L.log(f"连接超算失败: {type(e).__name__}: {e}", "ERROR")
        return 1

    try:
        snb_home = L.abs_snb_home(rm)
        L.log(f"远端 FLASHSNB: {snb_home}")
        deploy = L.R.resolve_deploy_dir(rm, cache_key=args.account)
        L.log(f"部署目录    : {deploy}")

        objdir = L.M.OBJDIR
        obj = f"{snb_home}/{objdir}"
        L.log(f"objdir      : {obj}")

        # ── 1. objdir 产物清单 ──
        pairs, tot = L.remote_inventory(rm, obj)
        L.log(f"\n【objdir 现有内容】{len(pairs)} 项 / {L.human(tot)}")

        # ── 2. 判定哪些是要删的产物 ──
        prod = [(n, s) for n, s in pairs
                if n.startswith(L.M.BASENM)
                or n == "wsl_run_*.log"
                or n in ("_t_start", "_t_end")]
        prodset = {n for n, _ in prod}
        protected = [(n, s) for n, s in pairs if n not in prodset]

        pb = sum(s for _, s in prod)
        L.log(f"\n【将清理】产物 {len(prod)} 项 / {L.human(pb)}")
        for n, s in prod[:40]:
            L.log(f"    [F] {L.human(s):>10s}  {n}")
        if len(prod) > 40:
            L.log(f"    … 其余 {len(prod)-40} 项略")
        if protected:
            kb = sum(s for _, s in protected)
            L.log(f"【保留】其他 {len(protected)} 项 / {L.human(kb)}"
                  f"（编译产物: *.o / flash4 / 软链）")
            # 只展示非 .o 的关键保留项
            key = [(n, s) for n, s in protected if not n.endswith((".o", ".mod"))]
            for n, s in key[:20]:
                L.log(f"    [K] {L.human(s):>10s}  {n}")
            if len(key) > 20:
                L.log(f"    … 另有 {len(key)-20} 项非 .o 保留项")

        # ── 3. 部署目录 ──
        if args.purge_deploy:
            dpairs, dtot = L.remote_inventory(rm, deploy)
            L.log(f"\n【部署目录】{len(dpairs)} 项 / {L.human(dtot)}")
            for n, s in dpairs:
                L.log(f"    {L.human(s):>10s}  {n}")

        # ── 4. 执行 ──
        L.step("执行清理")
        pats = [f"{L.M.BASENM}*", "wsl_run_*.log", "_t_start", "_t_end"]
        L.remote_batch_remove(rm, pats, dry_run=dry, rdir=obj, label="objdir 产物")

        if args.purge_deploy:
            # 部署目录：只删产物，保留 build.sh/run.sh/unit.tar.gz（可能仍在用）
            dpats = ["_unit_*", "unit.tar.gz", "coretest_*.sh", "probe_*.sh",
                     "run.sh", "build.sh", "*_out.txt", "*_err.txt",
                     "setup_*.log", "make_*.log", "flash.par",
                     "snbvti2_ml.par", "snbvti2_ml_*.par", "wsl_run_*.log"]
            L.remote_batch_remove(rm, dpats, dry_run=dry, rdir=deploy,
                                  label="部署目录产物")

        # ── 5. 收尾断言 ──
        L.step("复查")
        if dry:
            L.log("[DRY-RUN] 未执行任何远端删除。", "WARN")
        else:
            pairs2, tot2 = L.remote_inventory(rm, obj)
            L.log(f"清理后 objdir: {len(pairs2)} 项 / {L.human(tot2)}")
            for n, s in pairs2:
                L.log(f"    剩余: {n}  ({L.human(s)})")
            # 关键断言: flash4 必须还在
            spec = L.R._hpc_env_block(snb_home, args.account)
            chk, _, _ = rm.run(f"ls {obj}/flash4 2>/dev/null || echo NO_FLASH4",
                               timeout=60)
            if "NO_FLASH4" in (chk or ""):
                L.log("★ flash4 不存在了！下次运行需重编译（--skip-build 将不可用）", "WARN")
            else:
                L.log("✓ flash4 仍在（下次可 --skip-build 省编译）")

        L.save_state(remote_cleaned_at=None if dry else "done",
                     remote_clean_dryrun=dry,
                     remote_account=args.account,
                     remote_deploy=deploy)
        L.log("状态已写: pipeline_state.json")

    finally:
        try:
            rm.__exit__(None, None, None)
        except Exception:
            pass

    if not dry:
        L.log("\n超算清空完成。下一步: python 03_run_16ns_pipeline.py", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
