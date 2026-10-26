"""test_arch_guards.py — 分层护栏的**负向样本**测试（解耦计划 B0）

为什么要这个文件：本项目已两次做出「报喜不报忧的护栏」——
  · `deploy/test_offline_install.py` 的 `check()` 只 print 不 assert，
    全文件 `assert` 计数为 0 ⇒「183 项自检」在 pytest 下是空转；
  · 分层检查若用 `^from flash` 行首锚定，部署层 6 处函数内 import 会
    全数漏检**并显示"通过"**。

因此每条规则都必须证明「能失败」。缺一条负向样本，该规则就不算护栏。
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

sys_path_root = Path(__file__).resolve().parent
for _ in range(12):
    if (sys_path_root / "pyproject.toml").exists():
        break
    sys_path_root = sys_path_root.parent

from flash.input_gen.gen_checker.check_scene_sources import (  # noqa: E402
    RULES,
    check_rules,
    repo_root_of,
)


# ── 夹具：一次性假仓库 ────────────────────────────────────────────

def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "start_flash.py").write_text("# stub\n", encoding="utf-8")
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content), encoding="utf-8")
    return tmp_path


def _codes(repo: Path) -> set[str]:
    new, _old = check_rules(repo)
    return {v.token for v in new}


# ── 逐条负向样本：每个都应该被拦下 ────────────────────────────────

def test_scene02_direct_executor_call(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_dispatch.py": """
            from flash.scenarios.runner import run_wsl
            def main(cfg):
                run_wsl(spec, cfg)
        """,
    })
    assert "R-SCENE-02" in _codes(repo)


def test_scene03_launcher_literal(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_launch.py": """
            cmd = ["wsl", "bash", "-lc", "echo hi"]
        """,
    })
    assert "R-SCENE-03" in _codes(repo)


def test_scene04_inline_sbatch(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_sub.py": """
            import subprocess
            subprocess.run(["sbatch", "x.sl"])
        """,
    })
    assert "R-SCENE-04" in _codes(repo)


def test_scene05_device_table(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_part.py": """
            HPC_PARTITION = {"flash_ssh": "v5_192"}
        """,
    })
    assert "R-SCENE-05" in _codes(repo)


def test_scene06_absolute_home(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_home.py": """
            PY = r"C:\\\\Users\\\\x\\\\python.exe"
        """,
    })
    assert "R-SCENE-06" in _codes(repo)


def test_scene07_mode_literal_comparison(tmp_path):
    """最贵的一条：`!= "hpc"` 在 hpc→hpc-remote 归一后恒真，v5 已真实踩过。"""
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_mode.py": """
            def main(run_mode):
                if run_mode != "hpc":
                    return False
        """,
    })
    assert "R-SCENE-07" in _codes(repo)


def test_layer01_deploy_imports_scenarios_indented(tmp_path):
    """★ 关键：**缩进**的 import 必须被抓到（行首锚定会漏）。"""
    repo = _make_repo(tmp_path, {
        "deploy/hpc_deploy/bad_deploy.py": """
            def run():
                from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession
                return RemoteSession
        """,
    })
    assert "R-LAYER-01" in _codes(repo)


def test_layer02a_flash_run_module_level_import(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/flash_run/bad_fr.py": """
            from flash.scenarios.insitu_runner import run_insitu
        """,
    })
    assert "R-LAYER-02a" in _codes(repo)


def test_layer02a_allows_function_level_import(tmp_path):
    """函数内延迟导入是允许的（B2 后才收紧）——否则规则当天就红。"""
    repo = _make_repo(tmp_path, {
        "flash/flash_run/ok_fr.py": """
            def run():
                from flash.scenarios.insitu_runner import run_insitu
                return run_insitu
        """,
    })
    assert "R-LAYER-02a" not in _codes(repo)


def test_layer03_flash_run_must_not_mention_scene_names(tmp_path):
    """★ 执行层不得出现子场景名（2026-10-26 新增）。

    背景：`SNB_POLICY` / `SCENE_DEVICE_DEFAULTS` 曾写在 `flash_run` 里，
    提交器 `submit_sandwich.py` 也曾长出场景映射表 ⇒ 执行层被场景污染。
    """
    repo = _make_repo(tmp_path, {
        "flash/flash_run/bad_scene_ref.py": """
            SNBOneCH_POLICY = {"allowed": ("hpc-remote",)}
        """,
    })
    assert "R-LAYER-03" in _codes(repo)


def test_layer03_allows_generic_flash_run_code(tmp_path):
    """正向样本：通用执行层代码必须 0 违规。"""
    repo = _make_repo(tmp_path, {
        "flash/flash_run/ok_generic.py": """
            from flash.flash_run.remote.job_layout import JobLayout

            def render():
                return JobLayout().shell_vars()
        """,
    })
    assert "R-LAYER-03" not in _codes(repo)


# ── 正向样本：合规代码必须 0 违规（否则规则写宽了也测不出来） ──────

def test_good_scene_has_zero_violations(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/good_scene.py": """
            from flash.flash_run.execution import SceneSpec, ExecutionPolicy

            SCENE = SceneSpec(name="good", sim_name="Good", objdir="obj", basenm="g_")

            def main(argv=None):
                from flash.scenarios.cli import run_scene_cli
                return run_scene_cli(SCENE, argv)
        """,
    })
    assert _codes(repo) == set()


# ── 基线机制：冻结后不再判失败，但**必须仍被记录** ────────────────

def test_baseline_suppresses_known_debt(tmp_path):
    repo = _make_repo(tmp_path, {
        "flash/scenarios/bad_mode.py": "x = (1 != \"hpc\")\n",
    })
    base = repo / "flash" / "input_gen" / "gen_checker" / "baseline_guards.txt"
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_text("R-SCENE-07\tflash/scenarios/bad_mode.py\n", encoding="utf-8")

    new, old = check_rules(repo)
    assert not new, "基线内条目不应判失败"
    assert any(v.token == "R-SCENE-07" for v in old), "但必须仍被记录为债"


# ── 真实仓库回归门槛 ─────────────────────────────────────────────

def test_real_repo_has_no_new_violations():
    """★ 仓库当前必须 0 新增违规（基线只降不升）。

    若此测试失败：说明新增了内联运行细节 —— 修代码，**不要**用
    `--freeze` 登记（那会让护栏失效）。
    """
    new, _old = check_rules(repo_root_of())
    if new:
        detail = "\n".join(f"  {v}" for v in new[:10])
        pytest.fail(f"新增 {len(new)} 处分层违规：\n{detail}")


def test_rules_table_shape():
    """规则表自检：码值唯一、每条都有提示与作用域。"""
    codes = [r.code for r in RULES]
    assert len(codes) == len(set(codes))
    for r in RULES:
        assert r.scope in ("scenes", "deploy", "flash_run")
        assert r.hint.strip()
