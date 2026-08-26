"""测试 gen_checker/ 子包 — 完整功能测试。

此文件支持双重模式，使用 _compat.py 进行智能导入。

注意：
1. 目录名是 gen_checker（一个下划线）
2. 模块文件名是 checker.py（不是 generator.py）
3. 类名是 DependencyChecker（不是 CheckerGenerator）
4. gen_checker/ 在 input_gen/ 目录下（不是 flash/ 目录下）
"""

import pytest
from pathlib import Path


class TestDependencyCheckerBasic:
    """基本测试。"""

    def test_import(self):
        """测试导入 DependencyChecker。"""
        # 注意：目录名是 gen_checker，模块文件名是 checker.py，类名是 DependencyChecker
        from flash.input_gen.gen_checker.checker import DependencyChecker
        assert DependencyChecker is not None

    def test_checker_module_exists(self):
        """测试 gen_checker/checker.py 文件存在。"""
        # 计算 input_gen/ 目录路径
        input_gen_dir = Path(__file__).resolve().parent.parent
        checker_dir = input_gen_dir / "gen_checker"
        checker_file = checker_dir / "checker.py"

        assert checker_dir.exists(), f"gen_checker/ directory not found: {checker_dir}"
        assert checker_file.exists(), f"checker.py not found: {checker_file}"

    def test_checker_init_exists(self):
        """测试 gen_checker/__init__.py 文件存在。"""
        input_gen_dir = Path(__file__).resolve().parent.parent
        checker_dir = input_gen_dir / "gen_checker"
        init_file = checker_dir / "__init__.py"

        assert init_file.exists(), f"__init__.py not found: {init_file}"

    def test_dependency_checker_init(self):
        """测试 DependencyChecker 初始化（需要 sim_dir 参数）。"""
        from flash.input_gen.gen_checker.checker import DependencyChecker
        checker = DependencyChecker(sim_dir=".")
        assert checker is not None


class TestDependencyCheckerEdgeCases:
    """边界测试。"""

    def test_empty_check(self):
        """测试空检查（初始化的默认状态）。"""
        from flash.input_gen.gen_checker.checker import DependencyChecker
        checker = DependencyChecker(sim_dir=".")
        assert checker is not None


class TestRelationChecker:
    """内在关联检查器（check_relations.py）测试。"""

    # ch_center 场景的生成目录（已验证内部一致）
    _SCENARIO_DIR = (
        Path(__file__).resolve().parents[2]
        / "scenarios" / "center_evolution" / "ch_center" / "flash_input"
    )

    def test_import_relation_checker(self):
        """测试从 gen_checker 包导入 RelationChecker。"""
        from flash.input_gen.gen_checker import RelationChecker
        assert RelationChecker is not None

    def test_relations_module_exists(self):
        """测试 relations/ 子包与主脚本存在。"""
        input_gen_dir = Path(__file__).resolve().parent.parent
        checker_dir = input_gen_dir / "gen_checker"
        assert (checker_dir / "check_relations.py").exists(), "check_relations.py 缺失"
        assert (checker_dir / "relations" / "_core.py").exists(), "relations/_core.py 缺失"

    def test_all_rules_registered(self):
        """测试所有内置规则已注册（应≥14条）。"""
        from flash.input_gen.gen_checker import REGISTRY
        assert len(REGISTRY) >= 14, f"期望至少14条规则，实际 {len(REGISTRY)}"

    def test_run_on_scenario_dir(self):
        """对 ch_center flash_input 运行全部规则，应无失败项。"""
        if not self._SCENARIO_DIR.exists():
            pytest.skip(f"场景目录不存在: {self._SCENARIO_DIR}")
        from flash.input_gen.gen_checker import RelationChecker
        rc = RelationChecker(self._SCENARIO_DIR)
        results = rc.run_all()
        failed = rc.failed()
        assert not failed, f"存在失败项: {[(r.rule_id, r.message) for r in failed]}"
        assert len(results) >= 14

    def test_error_detection_missing_datafiles(self, tmp_path):
        """人为从 Config 删除 DATAFILES，应触发 par_cn4_in_config_datafiles FAIL。"""
        if not self._SCENARIO_DIR.exists():
            pytest.skip("场景目录不存在")
        # 复制必要文件到临时目录
        for f in ("Config", "laserslab_chcenter.par", "Z02_1.00-20260708_0851.cn4",
                  "Z06_0.50-Z01_0.50-20260708_0850.cn4"):
            src = self._SCENARIO_DIR / f
            if src.exists():
                (tmp_path / f).write_text(src.read_text(encoding="utf-8",
                                                        errors="replace"),
                                          encoding="utf-8")
        # 删除 DATAFILES 行
        cfg_path = tmp_path / "Config"
        lines = [ln for ln in cfg_path.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().upper().startswith("DATAFILES")]
        cfg_path.write_text("\n".join(lines), encoding="utf-8")

        from flash.input_gen.gen_checker import RelationChecker
        rc = RelationChecker(tmp_path)
        rc.run_all(rule_ids=["par_cn4_in_config_datafiles"])
        failed = rc.failed()
        assert any(r.rule_id == "par_cn4_in_config_datafiles" for r in failed)
