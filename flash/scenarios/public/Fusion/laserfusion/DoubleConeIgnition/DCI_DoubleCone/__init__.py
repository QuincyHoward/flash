"""dci_double_cone — 双锥对撞点火 (DCI) 几何验证场景 (2D rz)。

对向 Au 开口双锥 (半角 35°, 锥顶 ±0.6mm, 壁厚 30um, 锥口 1.5mm)
+ 中心 CH 燃料球 (外半径 1.2mm, 内 He 气) + 锥内 CH 燃料填充 + He 真空。
DCI 参考: 张杰 2020 (Phil. Trans. R. Soc. A 378, 20200015); 神光 II 升级
8 束加热 (物理学报 72, 20230442)。
入口: run_dci_verify.py (tmax=1e-13 s 极短验证; 辐射 MGD 10 群已开)。
FLASH 源文件 (Config/F90/par/cn4) 直接存放于 flash_input/ 子目录。
"""

from pathlib import Path

from flash.scenarios.core.engine.base import SimulationScenario

_HERE = Path(__file__).resolve().parent

scenario = SimulationScenario(
    name="dci_double_cone",
    description="双锥对撞点火几何验证 2D rz (对向 Au 双锥 + CH 燃料球 + 锥内燃料, MGD 10 群)",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",   # FLASH 源文件在 flash_input/ 子目录
    sim_name="QC/DCI_DoubleCone",
    run_dir_name="outputfiles",
    basenm="dci_",
    flash_setup_args=(
        "-2d +cylindrical -nxb=16 -nyb=16 "
        "+hdf5typeio species=cham,cgas,caps,gold "
        "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    ),
    default_params={
        "tmax": 1.0e-13,
        "dtinit": 1.0e-15,
        "dtmax": 1.0e-13,
        "nend": 500,
        # ── 双锥几何 (cm/度) ──
        "sim_coneHalfAngDeg": 35.0,
        "sim_coneApexZ": 0.06,
        "sim_coneShellThick": 3.0e-3,
        "sim_coneOpenR": 0.15,
        "sim_capRadius": 0.12,
        "sim_capShellThick": 2.0e-2,
        # ── 材料密度 (g/cm^3) ──
        "sim_rhoGold": 19.32,
        "sim_rhoCaps": 1.0,
        "sim_rhoGas": 1.0e-3,
        "sim_rhoVacuum": 1.0e-6,
        # ── 初始温度 (K) ──
        "sim_teleGold": 290.11375,
        "sim_teleCaps": 290.11375,
        "sim_teleGas": 290.11375,
        "sim_teleCham": 290.11375,
        # ── 网格 ──
        "xmin": 0.0,
        "xmax": 0.25,
        "ymin": -0.30,
        "ymax": 0.30,
        "nblockx": 2,
        "nblocky": 4,
        "lrefine_min": 1,
        "lrefine_max": 5,
    },
)
