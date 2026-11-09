"""ZPinch 生成器 golden 对账测试。

基准: flash/input_gen/test/golden/zpinch/（8 文件，来自官方 magnetoHD/ZPinch
逐字快照 + 极短验证定版 par）。
对账三方: 生成器输出 ↔ golden 基准 ↔ (可选) WSL 官方源文件。
"""

from pathlib import Path

import pytest

GOLD_DIR = Path(__file__).resolve().parent / "golden" / "zpinch"

BYTE_IDENTICAL_FILES = [
    "Config",
    "Makefile",
    "Simulation_data.F90",
    "Simulation_init.F90",
    "Simulation_initBlock.F90",
    "Simulation_adjustEvolution.F90",
    "current.dat",
]

OFFICIAL_SRC_FILES = [
    "Config",
    "Makefile",
    "Simulation_data.F90",
    "Simulation_init.F90",
    "Simulation_initBlock.F90",
    "Simulation_adjustEvolution.F90",
]


def _generators():
    from flash.input_gen.gen_config.zpinch_config import ZPinchConfigGenerator
    from flash.input_gen.gen_sim_adjustevo import SimAdjustEvoGenerator
    from flash.input_gen.gen_sim_data.zpinch_data import ZPinchSimDataGenerator
    from flash.input_gen.gen_sim_init.zpinch_init import ZPinchSimInitGenerator
    from flash.input_gen.gen_sim_initblock.zpinch_initblock import (
        ZPinchBlockGenerator,
    )
    return {
        "Config": ZPinchConfigGenerator,
        "Simulation_data.F90": ZPinchSimDataGenerator,
        "Simulation_init.F90": ZPinchSimInitGenerator,
        "Simulation_initBlock.F90": ZPinchBlockGenerator,
        "Simulation_adjustEvolution.F90": SimAdjustEvoGenerator,
    }


def _parse_par(text: str) -> dict:
    """解析 par 键值（剥 # 注释、按 = 切、strip；值保留字面量）。"""
    out = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        kv = s.split("#", 1)[0]
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        out[k.strip()] = v.strip()
    return out


class TestGoldenByteIdentical:
    @pytest.mark.parametrize("name", BYTE_IDENTICAL_FILES)
    def test_output_matches_golden_bytes(self, name):
        gold = (GOLD_DIR / name).read_bytes()
        if name == "Makefile":
            from flash.input_gen.gen_makefile import MakefileGenerator
            content = MakefileGenerator().generate()
        elif name == "current.dat":
            from flash.scenarios.public.Fusion.zpinch.ZPinch_BeLiner.gen_inputs import (
                CURRENT_DAT,
            )
            content = CURRENT_DAT
        else:
            content = _generators()[name]().generate()
        assert content.encode("utf-8") == gold, f"{name} 与 golden 逐字节不一致"

    def test_par_key_value_equivalence(self):
        """par 允许列宽格式差异，但键集合与值字面量必须等价。"""
        gold = _parse_par((GOLD_DIR / "zpinch_be.par").read_text(encoding="utf-8"))
        from flash.input_gen.gen_par.zpinch_par import build_zpinch_par
        new = _parse_par(build_zpinch_par())
        assert set(gold) == set(new), (
            f"键集合不等价: missing={sorted(set(gold) - set(new))[:5]}, "
            f"extra={sorted(set(new) - set(gold))[:5]}")
        diff = [k for k in gold if gold[k] != new[k]]
        assert not diff, f"值不等价: {diff[:10]}"


class TestOfficialSourceCrossCheck:
    """与 WSL 官方源文件对账（CRLF→LF 归一后逐字节；WSL 不可用则跳过）。"""

    @pytest.mark.parametrize("name", OFFICIAL_SRC_FILES)
    def test_official_source_matches_golden(self, name):
        import shutil
        import subprocess
        if shutil.which("wsl") is None and not Path("/proc/version").exists():
            pytest.skip("WSL 不可用")
        wsl_path = ("~/QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/"
                    "magnetoHD/ZPinch/" + name)
        r = subprocess.run(
            ["wsl", "bash", "-c", f"cat {wsl_path}"],
            capture_output=True, timeout=60)
        if r.returncode != 0:
            pytest.skip(f"官方源文件不可读: {name}")
        official = r.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        gold = (GOLD_DIR / name).read_text(encoding="utf-8")
        assert gold == official, f"{name} golden 与官方源文件不一致"
