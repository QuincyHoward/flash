"""ZPinch 生成器 golden 对账测试。

基准: flash/input_gen/test/golden/zpinch/（8 文件，来自官方 magnetoHD/ZPinch
逐字快照 + 极短验证定版 par）。
对账三方: 生成器输出 ↔ golden 基准 ↔ (可选) 官方 FLASH 源文件。

★ 2026-11-15 三环境可移植化: golden 中 5 个无扩展名/``*.F90`` 文件被
  ``.gitignore`` 排除（FLASH 分发源码不入库），只存在于开发机。WSL / 超算
  重建仓库后缺失 ⇒ 相关用例回退到**本地官方 FLASH 源**（实测 LF 归一后与
  golden 逐字节一致）；Windows 则经 wsl 命令读取同一官方源。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

GOLD_DIR = Path(__file__).resolve().parent / "golden" / "zpinch"

#: 官方 FLASH 源相对家目录的位置（Windows 经 wsl 读；WSL / 超算直接读本地树）
OFFICIAL_REL = Path(
    "QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/magnetoHD/ZPinch")

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


def _official_bytes(name: str) -> bytes | None:
    """读取官方 FLASH 源（CRLF→LF 归一）；不可读返回 None。

    Windows: ``wsl bash -c cat ~/QC/...``；WSL / 超算: 本地 FLASH 树直接读。
    旧的 ``Path("/proc/version").exists()`` 判据把任何 Linux 都当成 WSL，
    导致超算调用不存在的 wsl 命令报 FileNotFoundError —— 已废弃。
    """
    if shutil.which("wsl"):
        r = subprocess.run(
            ["wsl", "bash", "-c", f"cat ~/{OFFICIAL_REL.as_posix()}/{name}"],
            capture_output=True, timeout=60)
        return r.stdout.replace(b"\r\n", b"\n") if r.returncode == 0 else None
    p = Path.home() / OFFICIAL_REL / name
    return p.read_bytes().replace(b"\r\n", b"\n") if p.is_file() else None


def _golden_bytes(name: str) -> bytes:
    """golden 基准；私有基准未随仓库分发时回退官方 FLASH 源（逐字等价）。"""
    p = GOLD_DIR / name
    if p.is_file():
        return p.read_bytes()
    official = _official_bytes(name)
    if official is None:
        pytest.skip(f"{name}: golden 未随仓库分发且官方 FLASH 源不可用")
    return official


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
        gold = _golden_bytes(name)
        if name == "Makefile":
            from flash.input_gen.gen_makefile import MakefileGenerator
            content = MakefileGenerator().generate()
        elif name == "current.dat":
            # ★ R5 可移植化：按场景名经 discovery 解析（scene_ref），
            #   不绑定层级包路径 —— 场景任意收纳/移动不受影响。
            from flash.scenarios.common.scene_ref import scene_module
            content = scene_module("zpinch_beliner", stem="gen_inputs").CURRENT_DAT
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
    """与官方 FLASH 源文件对账（CRLF→LF 归一后逐字节；源/基准不可读则跳过）。"""

    @pytest.mark.parametrize("name", OFFICIAL_SRC_FILES)
    def test_official_source_matches_golden(self, name):
        official = _official_bytes(name)
        if official is None:
            pytest.skip(f"官方 FLASH 源不可读: {name}")
        gold = GOLD_DIR / name
        if not gold.is_file():
            pytest.skip(
                f"{name}: golden 私有基准未随仓库分发（生成器对账由 "
                f"test_output_matches_golden_bytes 回退官方源覆盖）")
        assert gold.read_text(encoding="utf-8") == official.decode("utf-8", errors="replace"), \
            f"{name} golden 与官方源文件不一致"
