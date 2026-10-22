#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_scene_sources.py — 场景源码「去运行化」检查器（2026-10-22 模块化改造新增）
═══════════════════════════════════════════════════════════

背景（模块化改造计划 §5 / 需求 3）:
  场景目录只做场景搭建 + 参数覆盖；运行方式、SSH/sbatch 细节、装置绝对路径
  一律收敛到 flash.flash_run（modes / env.resource_config / hpc.py）。
  本检查器扫描场景源码，发现**内联运行细节**即报违规。

检查规则（R-SCENE-01）:
  场景 .py 中禁止出现以下运行细节 token（注释/文档字符串也计，提示性违规；
  import flash.flash_run.* 与 flash_run 的合法调用不计）:
    - sbatch / scancel / squeue / sacct     （作业调度命令）
    - paramiko / SSHClient                  （SSH 细节）
    - /publicfs01、AI/Aitemp                （装置绝对路径）
    - .venv-hpc-nce                         （登录节点 venv 细节）

CLI:
    python -m flash.input_gen.gen_checker.check_scene_sources [目录]
    # 目录缺省 = flash/scenarios

Python API:
    from flash.input_gen.gen_checker.check_scene_sources import check_scene_sources
    violations = check_scene_sources()      # List[SceneViolation]
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

#: 违规 token → 说明
FORBIDDEN_TOKENS: dict[str, str] = {
    "sbatch": "作业提交应走 flash_run（runner HpcRunner / hpc.py submit）",
    "scancel": "作业取消应走 flash_run（hpc.py cancel）",
    "squeue": "队列查询应走 flash_run（hpc.py status）",
    "sacct": "作业状态应走 flash_run（hpc.py wait/status）",
    "paramiko": "SSH 细节应走 flash_run.remote",
    "SSHClient": "SSH 细节应走 flash_run.remote",
    "/publicfs01": "装置绝对路径应下沉 flash_run/env/resource_config 装置配置",
    "AI/Aitemp": "装置临时目录应下沉 flash_run/env/resource_config 装置配置",
    ".venv-hpc-nce": "登录节点 venv 名应下沉 flash_run/env 配置",
}

#: 合法豁免：flash_run 自身的运行实现不在场景目录，无需豁免条目；
#: 场景内对 flash_run 的**调用**（from flash.flash_run import ...）不含上述 token。
_TOKEN_RE = re.compile(
    "|".join(re.escape(k) for k in sorted(FORBIDDEN_TOKENS, key=len, reverse=True))
)

#: 已知债（文件级，2026-10-22 基线）：这些文件含历史内联运行细节，待专项迁移，
#: **不新增文件**即可通过。 Debt 只降不升——文件从清单移除后不得再加回。
KNOWN_DEBT: dict[str, str] = {
    "scenarios/insitu_runner.py": "运行基础设施，待迁 flash_run/modes（hpc-insitu 执行体就地 sbatch）",
    "remote_ssh_helper.py": "运行基础设施（demo_hpc 共用 SSH 壳），待迁 flash_run/remote",
    "SNBOneCH_m.py": "SNB 自带 HPC 驱动（约 300 行），待 SNB 方法包专项收编 run_scene",
    "SNBOneCH_ml.py": "同上",
    "SNBVTi2um.py": "同上",
    "run_snb_hpc.py": "SNB t001 直跑驱动，同上",
    "laserslab1d_hpc_demo_batch.py": "demo_hpc 批处理内联驱动，待改参数化调 flash_run",
    "laserslab1d_hpc_demo.py": "同上",
    "laserslab1d_supercomputer_demo.py": "同上",
    "laserslab1d_local_custom.py": "官方一键场景：多数为 flash_run 合法调用残留注释，待清理",
    "hello_flash/deploy_flash.py": "部署脚本位于场景目录（历史位置），待迁根目录 deploy/",
    "submit_msfix_all.py": "SNB 批量提交一次性工具，待改调 flash_run/hpc.py",
    "run_cores_parallel.py": "SNB 多核数并行提交工具，待改调 flash_run/hpc.py",
    "_fetch_nce_results.py": "SNB 结果下载一次性工具（自建 SFTP），待收编 flash_run.remote",
    "_fetch_par.py": "同上",
    "fetch_hpc_output.py": "SNBVTi 并行下载工具，待收编 flash_run.remote",
    "hpc_fetch.py": "VTi 结果下载工具，同上",
    "hpc_watch.py": "VTi 作业监视工具，待改调 flash_run/hpc.py",
    "watch_l500.py": "VTi_oldstyle 作业监视，同上",
    "build_vti_oldstyle.py": "VTi_oldstyle 生成器含历史提交细节，待清理",
    "probe2_hpc_env.py": "SNBtest t001 一次性环境探针（诊断工具）",
    "probe3_sbatch_smoke.py": "同上",
    "probe4_bscc_smoke.py": "同上",
    "tools_local/": "SNBOneCH_ml 本地诊断工具集（一次性，历史债整体挂账）",
    "scripts/longrun/": "SNB 长跑流水线（03_run_16ns_pipeline/_longrun_lib/_fetch/_track），专项收编 run_scene 时处理",
    "scripts/monitor/": "SNB 作业监视工具，待改调 flash_run/hpc.py",
}


@dataclass
class SceneViolation:
    path: Path
    line_no: int
    token: str
    line: str
    hint: str

    def __str__(self) -> str:
        return (f"{self.path.relative_to(self.path.parents[3]) if len(self.path.parents) > 3 else self.path}"
                f":{self.line_no}: [{self.token}] {self.line.strip()[:100]}\n"
                f"    → {self.hint}")


def check_scene_sources(scenarios_root: str | Path | None = None,
                        include_private: bool = True
                        ) -> tuple[list[SceneViolation], list[SceneViolation]]:
    """扫描场景目录下全部 .py。

    Returns:
        (violations, debt) —— violations=需修复（含未知文件，令 RC=1）；
        debt=KNOWN_DEBT 清单内的已知历史债（只报告不失败）。
    """
    root = Path(scenarios_root) if scenarios_root else Path(__file__).resolve().parents[2] / "scenarios"
    if not root.is_dir():
        raise FileNotFoundError(f"场景目录不存在: {root}")
    out: list[SceneViolation] = []
    debt: list[SceneViolation] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts or "flash_run" in py.parts:
            continue
        if "temp_delete" in py.parts:      # 待删除区不检查
            continue
        if not include_private and "private" in py.parts:
            continue
        debt_reason = next((r for suffix, r in KNOWN_DEBT.items()
                            if str(py).replace("\\", "/").endswith(suffix)
                            or f"/{suffix}" in str(py).replace("\\", "/")),
                           None)
        try:
            text = py.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = py.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            m = _TOKEN_RE.search(line)
            if not m:
                continue
            # 豁免: 对 flash_run 的合法委托（import/调用）不算内联细节
            if "flash.flash_run" in line or "flash_run." in line:
                continue
            # 豁免: work_base= 属场景允许的参数覆盖（默认值已下沉 resource_config）
            if "work_base=" in line:
                continue
            item = SceneViolation(py, i, m.group(0), line,
                                  FORBIDDEN_TOKENS[m.group(0)])
            (debt if debt_reason else out).append(item)
    return out, debt


def main(argv: list[str] | None = None) -> int:
    root = argv[0] if argv else None
    v, debt = check_scene_sources(root)
    if debt:
        print(f"[debt] 已知历史债 {len(debt)} 处（KNOWN_DEBT 清单内，待专项迁移，不计失败）")
    if not v:
        print("[OK] R-SCENE-01 通过：场景源码无新增内联运行细节")
        return 0
    print(f"[FAIL] R-SCENE-01 新增违规 {len(v)} 处:")
    for item in v:
        print(" ", item)
    print("→ 修复: 运行细节迁移 flash.flash_run（modes/hpc.py/resource_config），场景仅留参数")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
