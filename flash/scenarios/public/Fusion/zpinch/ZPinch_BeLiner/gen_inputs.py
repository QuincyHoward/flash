#!/usr/bin/env python3
"""gen_inputs.py — ZPinch_BeLiner 场景输入装配层 (v2, 接入 flash/input_gen 模块)。

职责: 调用 flash/input_gen 各隔离生成器, 在 flash_input/ 下生成全部 8 个输入文件:

  Config                        <- gen_config/zpinch_config.py   (ZPinch 隔离文件)
  Makefile                      <- gen_makefile (通用生成器, 零改动复用)
  Simulation_data.F90           <- gen_sim_data/zpinch_data.py   (ZPinch 隔离文件)
  Simulation_init.F90           <- gen_sim_init/zpinch_init.py   (ZPinch 隔离文件)
  Simulation_initBlock.F90      <- gen_sim_initblock/zpinch_initblock.py (隔离)
  Simulation_adjustEvolution.F90 <- gen_sim_adjustevo (专用子包, 只负责此文件)
  zpinch_be.par                 <- gen_par/zpinch_par.py (隔离 par 模块, 非激光)
  current.dat                   <- 场景内置波形 (按约定 *.dat 不入 input_gen)

EOS 表 (Be-006-imx.cn4 / DD-006-imx.cn4) 不在此生成, 随 setup DATAFILES
机制从 FLASH 源码树获取。

隔离保证: 本装配层与激光系参数 (ParGeneratorExtended / ed_* 激光默认值)
零耦合; gen_par/zpinch_par.py 不 import gen_par 激光实现文件。

用法:
  python gen_inputs.py            # 生成到 flash_input/
  python gen_inputs.py <outdir>   # 生成到指定目录
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ── repo-root 自举 (定位包含 flash/ 包的仓库根, 使 flash.input_gen 可导入) ──
_REPO = SCRIPT_DIR
for _ in range(8):
    _REPO = _REPO.parent
    if (_REPO / "flash" / "input_gen").is_dir():
        break
else:
    raise RuntimeError("未找到 flash/input_gen 所在仓库根")
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from flash.input_gen.gen_config.zpinch_config import ZPinchConfigGenerator
from flash.input_gen.gen_makefile import MakefileGenerator
from flash.input_gen.gen_par.zpinch_par import build_zpinch_par
from flash.input_gen.gen_sim_adjustevo import SimAdjustEvoGenerator
from flash.input_gen.gen_sim_data.zpinch_data import ZPinchSimDataGenerator
from flash.input_gen.gen_sim_init.zpinch_init import ZPinchSimInitGenerator
from flash.input_gen.gen_sim_initblock.zpinch_initblock import ZPinchBlockGenerator

OUT_DIR = SCRIPT_DIR / "flash_input"

# ── 极短验证覆盖 ──
# 基线 (ZPINCH_BASELINE) 已含极短验证定版值 (tmax=1e-12 / dtinit=1e-14 /
# 每步出 plt / basenm=zpbe_ 等), 此处空表 = 逐用基线; 需变体时按
# {键: 字面量字符串 | (字面量, 行尾注释)} 填写。
VERIFY_OVERRIDES = {}

# ── 官方 stock 电流波形 (magnetoHD/ZPinch/current.dat, ns vs MA, 零修改) ──
CURRENT_DAT = """0.    0.
20.   2.
60.   20.
100.  27.
120.  23.
200.  23.
"""


def main(outdir=None) -> int:
    """装配并写出全部场景输入文件。"""
    out = Path(outdir) if outdir else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "Config": ZPinchConfigGenerator().generate(),
        "Makefile": MakefileGenerator().generate(sim_path="magnetoHD/ZPinch"),
        "Simulation_data.F90": ZPinchSimDataGenerator().generate(),
        "Simulation_init.F90": ZPinchSimInitGenerator().generate(),
        "Simulation_initBlock.F90": ZPinchBlockGenerator().generate(),
        "Simulation_adjustEvolution.F90": SimAdjustEvoGenerator().generate(),
        "zpinch_be.par": build_zpinch_par(VERIFY_OVERRIDES),
        "current.dat": CURRENT_DAT,
    }
    for name, text in files.items():
        dst = out / name
        dst.write_text(text, encoding="utf-8", newline="\n")
        print(f"[gen_inputs] gen -> {dst.name} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
