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


# ═══════════════════════════════════════════════════════════════════
# 规则引擎（2026-10-24 解耦计划 B0）
# ═══════════════════════════════════════════════════════════════════
# 设计要点（计划 §5.2 的四条纪律）：
#   1. **不用行首锚定** —— 部署层 6 处 import 全在函数体内（带缩进），
#      `^from flash` 会全数漏检并显示"通过"。一律 `^\s*(from|import)\s+`。
#   2. **不手写文件条数** —— 基线由 `--freeze` 生成，只降不升。
#   3. 每条规则必须有**负向样本**（见 test/test_arch_guards.py）。
#   4. 未证明会失败的护栏不算护栏。

@dataclass(frozen=True)
class Rule:
    """一条静态检查规则。"""
    code: str
    scope: str                 # "scenes" | "deploy" | "flash_run"
    pattern: str
    hint: str
    allow: str | None = None   # 命中该正则的行视为合法
    top_level_only: bool = False


RULES: tuple[Rule, ...] = (
    Rule("R-SCENE-02", "scenes",
         r"\b(run_wsl|HpcRunner|run_insitu|collect_local)\s*\(",
         "场景层不得直接调执行体；应调 flash.flash_run.execution.run_scene"
         "（由场景声明 SceneSpec，执行细节归执行层）"),
    Rule("R-SCENE-03", "scenes",
         r'\[\s*["\']wsl["\']\s*,\s*["\'](bash|-lc)["\']',
         "启动器构造应下沉 flash_run.remote.executors.WslExecutor"),
    Rule("R-SCENE-04", "scenes",
         r"(?:subprocess|Popen)[^\n]*\b(sbatch|sinfo|srun|mpiexec)\b",
         "作业提交/查询应走 flash_run.remote.slurm_control"),
    Rule("R-SCENE-05", "scenes",
         r"\bHPC_PARTITION\b\s*=|[\"']v5_192[\"']|[\"']v6_384[\"']|/public1/soft",
         "装置参数（账户/分区/模块）应下沉 flash_run/env/devices.py 或凭据配置"),
    Rule("R-SCENE-06", "scenes",
         r"[A-Za-z]:\\\\Users\\\\|[\"']C:\\\\|/home/[a-z][a-z0-9_]{2,}/",
         "绝对家目录路径不可移植；应用 Path.home() 或由执行层注入"),
    Rule("R-SCENE-07", "scenes",
         r"(?:==|!=)\s*[\"'](?:wsl|hpc|hpc-remote|hpc-insitu|local)[\"']",
         "禁止模式**字面量**比较（改名即静默失效：`!= \"hpc\"` 在 "
         "hpc→hpc-remote 归一后恒真，曾使两个 demo 入口永远 return False）；"
         "须用 mode_is_local()/mode_is_remote()/mode_allows()",
         allow=r"^\s*#"),
    Rule("R-LAYER-01", "deploy",
         r"^\s*(?:from|import)\s+flash\.scenarios",
         "部署层不得依赖**场景层**（依赖方向：deploy → flash_run → _core）；"
         "SSH 请用 flash.flash_run.remote.session.RemoteSession"),
    Rule("R-LAYER-02a", "flash_run",
         r"^from\s+flash\.scenarios|^import\s+flash\.scenarios",
         "执行层不得**模块级**依赖场景层（会造成 import 循环 + 拉入整个场景包）；"
         "确需场景能力请函数内延迟导入，并在 B2 后消除",
         top_level_only=True),
)

#: 规则基线（`--freeze` 生成，只降不升）。格式：`CODE<TAB>相对路径`
BASELINE_NAME = "baseline_guards.txt"


def repo_root_of(start: Path | None = None) -> Path:
    """仓库根（含 pyproject.toml + start_flash.py）。"""
    p = (start or Path(__file__)).resolve()
    for cand in [p, *p.parents]:
        if (cand / "pyproject.toml").is_file() and (cand / "start_flash.py").is_file():
            return cand
    return p.parents[3]


def _load_baseline(path: Path) -> set[tuple[str, str]]:
    if not path.is_file():
        return set()
    out: set[tuple[str, str]] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) == 2:
            out.add((parts[0].strip(), parts[1].strip().replace("\\", "/")))
    return out


def _iter_scope(repo: Path, scope: str):
    """产出 (文件, 相对路径)。"""
    if scope == "scenes":
        base, skip = repo / "flash" / "scenarios", ("temp_delete", "__pycache__", "flash_run")
    elif scope == "deploy":
        base, skip = repo / "deploy", ("__pycache__",)
    elif scope == "flash_run":
        base = repo / "flash" / "flash_run"
        # ★ remote/test/scripts 是一次性诊断探针（从不被包 import），
        #   不属执行层代码，排除以免基线段被噪声填满。
        skip = ("__pycache__", "test")
    else:
        return
    for py in sorted(base.rglob("*.py")):
        if any(s in py.parts for s in skip):
            continue
        yield py, py.relative_to(repo).as_posix()


def check_rules(repo: Path | None = None,
                rules: tuple[Rule, ...] = RULES) -> tuple[list[SceneViolation],
                                                           list[SceneViolation]]:
    """按规则表扫描，返回 (new_violations, baselined)。

    baselined = 基线内既有违规（只报告，不判失败）。
    """
    repo = repo or repo_root_of()
    baseline = _load_baseline(repo / "flash" / "input_gen" / "gen_checker" / BASELINE_NAME)
    new: list[SceneViolation] = []
    old: list[SceneViolation] = []
    for rule in rules:
        rx = re.compile(rule.pattern)
        allow_rx = re.compile(rule.allow) if rule.allow else None
        for py, rel in _iter_scope(repo, rule.scope):
            try:
                text = py.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = py.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if not rx.search(line):
                    continue
                if allow_rx and allow_rx.search(line):
                    continue
                if rule.top_level_only and line[:1].isspace():
                    continue          # 函数内延迟导入允许（B2 后再收紧）
                item = SceneViolation(py, i, rule.code, line, rule.hint)
                (old if (rule.code, rel) in baseline else new).append(item)
    return new, old


def freeze_baseline(repo: Path | None = None) -> Path:
    """把当前全部命中写入基线（B0 建立基线用；之后只允许收缩）。"""
    repo = repo or repo_root_of()
    new, old = check_rules(repo)
    rels = sorted({(v.token, v.path.relative_to(repo).as_posix()) for v in (*new, *old)})
    out = repo / "flash" / "input_gen" / "gen_checker" / BASELINE_NAME
    header = (
        "# 规则基线（自动生成，勿手改）——`python -m flash.input_gen.gen_checker."
        "check_scene_sources --freeze`\n"
        "# 语义：本清单内 = 已知历史债（只报告）；清单外 = 新增违规（RC=1）。\n"
        "# ★ 只降不升：修复后重跑 --freeze 会自动收缩；不要手工追加条目。\n"
        f"# 生成时间基线条目数: {len(rels)}\n"
    )
    out.write_text(header + "".join(f"{c}\t{p}\n" for c, p in rels), encoding="utf-8")
    return out



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
    """CLI：规则 + 旧 token 扫描。

    ``--freeze``      重新生成基线（修复后收缩；不要手工追加）
    ``--report-only`` 只报告不判失败（基线建立期用）
    ``--rules-only``  跳过旧 token 扫描（R-SCENE-01）
    """
    argv = list(argv or [])
    freeze = "--freeze" in argv
    report_only = "--report-only" in argv
    rules_only = "--rules-only" in argv
    positional = [a for a in argv if not a.startswith("-")]
    root = positional[0] if positional else None

    if freeze:
        path = freeze_baseline()
        print(f"[OK] 基线已写入 {path}")
        return 0

    new, old = check_rules()

    # ── 旧 token 扫描（R-SCENE-01，保持向后兼容） ──
    v1: list[SceneViolation] = []
    debt1: list[SceneViolation] = []
    if not rules_only:
        v1, debt1 = check_scene_sources(root)

    total_debt = len(old) + len(debt1)
    if total_debt:
        print(f"[debt] 基线内已知历史债 {total_debt} 处"
              f"（R-SCENE-01 {len(debt1)} + 规则基线 {len(old)}；只降不升，不计失败）")

    # ── 按规则分组输出 ──
    all_new = [*v1, *new]
    if not all_new:
        codes = ", ".join(r.code for r in RULES)
        print(f"[OK] 场景层/部署层护栏通过（{codes}）")
        return 0

    by_code: dict[str, list[SceneViolation]] = {}
    for item in all_new:
        by_code.setdefault(item.token, []).append(item)
    print(f"[FAIL] 新增违规 {len(all_new)} 处（{len(by_code)} 条规则）:")
    for code in sorted(by_code):
        items = by_code[code]
        print(f"\n  ── {code}（{len(items)} 处）")
        for item in items[:12]:
            print("   ", item)
        if len(items) > 12:
            print(f"    ... 其余 {len(items) - 12} 处省略")
    print("\n→ 修复：运行细节下沉 flash.flash_run；确属历史债请评估后用 --freeze 登记（须说明理由）")
    return 0 if report_only else 1



if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
