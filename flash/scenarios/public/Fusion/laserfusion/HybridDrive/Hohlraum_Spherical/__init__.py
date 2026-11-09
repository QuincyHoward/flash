"""hybrid_hohlraum — 混合驱动球腔几何验证场景 (2D rz)。

Au 球形黑腔 (两极 LEH) + 中心 CH 靶丸 + 低密度 He 充气。
混合驱动 (贺贤土 HD 方案) 参考: ID 束经 LEH 入射球腔内壁转 X 射线预压缩,
DD 束沿径向直照预压缩靶丸 (MRE 10, 057401 (2025); Nat. Commun. HD 实验)。
入口: run_hybrid_verify.py (tmax=1e-13 s 极短验证; 辐射 MGD 10 群已开)。
FLASH 源文件 (Config/F90/par/cn4) 直接存放于 flash_input/ 子目录。
"""

from pathlib import Path

from flash.scenarios.core.engine.base import SimulationScenario

_HERE = Path(__file__).resolve().parent

scenario = SimulationScenario(
    name="hybrid_hohlraum",
    description="混合驱动球腔几何验证 2D rz (Au 球壳 + 双极 LEH + CH 靶丸 + He 充气, MGD 10 群)",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",   # FLASH 源文件在 flash_input/ 子目录
    sim_name="QC/Hohlraum_Spherical_HD",
    run_dir_name="outputfiles",
    basenm="hyhohl_",
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
        # ── 球形腔几何 (cm) ──
        "sim_cavInnerR": 0.272,
        "sim_cavOuterR": 0.275,
        "sim_lehCosZ": 0.8510,
        "sim_capRadius": 0.1,
        "sim_capShellThick": 1.5e-2,
        # ── 材料密度 (g/cm^3) ──
        "sim_rhoGold": 19.32,
        "sim_rhoCaps": 1.0,
        "sim_rhoGas": 1.0e-3,
        "sim_rhoFill": 9.6e-4,
        "sim_rhoVacuum": 1.0e-6,
        # ── 初始温度 (K) ──
        "sim_teleGold": 290.11375,
        "sim_teleCaps": 290.11375,
        "sim_teleGas": 290.11375,
        "sim_teleCham": 290.11375,
        # ── 网格 ──
        "xmin": 0.0,
        "xmax": 0.34,
        "ymin": -0.34,
        "ymax": 0.34,
        "nblockx": 2,
        "nblocky": 2,
        "lrefine_min": 1,
        "lrefine_max": 5,
    },
)
