"""ZPinch (magnetoHD/ZPinch) Config 生成器 —— 官方 stock 逐字快照 (v1 模板)。

隔离说明: 与激光系 ConfigGenerator (species_defs 物种模型) 完全独立,
零 import、零共享状态; 避免激光参数污染 ZPinch 参数集。

源: FLASH4.8 source/Simulation/SimulationMain/magnetoHD/ZPinch (随 Gitee 分发的
官方文件快照; EOS 表 Be/DD-006-imx.cn4 不在此, 随 setup DATAFILES 获取)。
"""

from pathlib import Path

ZPINCH_CONFIG = r'''## Configuration file for ZPinch example problem

## UG setup command:
## ./setup -auto magnetoHD/ZPinch -1d +cylindrical +ug species=fill,line,vacu +mtmmmt +usm3t +mgd mgd_meshgroups=6 +hdf5typeio 

REQUIRES Driver
REQUIRES physics/Hydro

## for the logLambda function
REQUIRES physics/utilities/PlasmaState

## typical units for HEDP
USESETUPVARS ThreeT
IF ThreeT
   REQUESTS physics/Diffuse/DiffuseMain/Unsplit
   REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
   REQUESTS physics/materialProperties/Conductivity/ConductivityMain/JiHeld
   REQUESTS physics/materialProperties/MagneticResistivity/MagneticResistivityMain/DaviesWen
ENDIF

REQUIRES physics/sourceTerms/Circuit/CircuitMain/FileInput
##REQUIRES physics/sourceTerms/Circuit/CircuitMain/McBride


DATAFILES Be-006-imx.cn4
DATAFILES DD-006-imx.cn4
DATAFILES current.dat
##DATAFILES Voc_example.dat

##########################
#                        #
#   RUNTIME PARAMETERS   #
#                        #
##########################
# These are just defaults and can be overridden in the .par file.
# A gen format for numbers is: PARAMETER <name> REAL <value> [<min> to <max>], where the bracket values limit the variable. Can be something like [0 to ] also.

## FILL
D sim_fill_dens  density of fill
PARAMETER sim_fill_dens  REAL  9.8e-03

D sim_fill_tele  electron temperature of fill
PARAMETER sim_fill_tele  REAL  23210.

D sim_fill_tion  ion temperature of fill
PARAMETER sim_fill_tion  REAL  23210.

D sim_fill_trad  radiation temperature of fill
PARAMETER sim_fill_trad  REAL  23210.

D sim_fill_maxTemp maximum electron and ion tempeature allowed in fill
PARAMETER sim_fill_maxTemp  REAL  1.e12

D sim_fill_minTemp minimum electron and ion tempeature allowed in fill
PARAMETER sim_fill_minTemp  REAL  1.e-12

D sim_fill_ctr center of Gaussian density profile for fill species
PARAMETER sim_fill_ctr  REAL  0.0

D sim_fill_sigma controls width of Gaussian density profile for fill species
PARAMETER sim_fill_sigma  REAL  0.082

D sim_fill_minDens min density used in Gaussian
PARAMETER sim_fill_minDens  REAL 0.0


## LINER
D sim_line_dens  density of liner
PARAMETER sim_line_dens  REAL  0.6

D sim_line_tele  electron temperature of liner
PARAMETER sim_line_tele  REAL  23210.

D sim_line_tion  ion temperature of liner
PARAMETER sim_line_tion  REAL  23210.

D sim_line_trad  radiation temperature of liner
PARAMETER sim_line_trad  REAL  23210.

D sim_line_maxTemp maximum electron and ion tempeature allowed in liner
PARAMETER sim_line_maxTemp  REAL  1.e12

D sim_line_minTemp minimum electron and ion tempeature allowed in liner
PARAMETER sim_line_minTemp  REAL  1.e-12

D sim_line_ctr center of Gaussian density profile for liner species
PARAMETER sim_line_ctr  REAL  1.0

D sim_line_sigma controls width of Gaussian density profile for liner species
PARAMETER sim_line_sigma  REAL  0.220

D sim_line_minDens min density used in Gaussian
PARAMETER sim_line_minDens  REAL 0.0


## VACUUM
D sim_vacu_dens  density of vacuum
PARAMETER sim_vacu_dens  REAL  1.e-06

D sim_vacu_tele  electron temperature of vacuum
PARAMETER sim_vacu_tele  REAL  290.11375

D sim_vacu_tion  ion temperature of vacuum
PARAMETER sim_vacu_tion  REAL  290.11375

D sim_vacu_trad  radiation temperature of vacuum
PARAMETER sim_vacu_trad  REAL  290.11375

D sim_vacu_maxTemp maximum electron and ion tempeature allowed in vacuum
PARAMETER sim_vacu_maxTemp  REAL  1.e12

D sim_vacu_minTemp minimum electron and ion tempeature allowed in vacuum
PARAMETER sim_vacu_minTemp  REAL  1.e-12


## Density profile parameters
D sim_rhoType type of initial density profile
PARAMETER sim_rhoType  INTEGER 0

D sim_innerRadius  inner radius of liner
PARAMETER sim_innerRadius  REAL  0.3

D sim_thickness  thickness of liner
PARAMETER sim_thickness  REAL  0.1

D sim_pert  density perturbation of liner
PARAMETER sim_pert  REAL  0.01

D sim_seed  seed for random density perturbation (makes sims repeatable)
PARAMETER sim_seed  INTEGER  1


## Trajectory output parameters
D sim_trajOutputInterval  trajectory output interval (s)
PARAMETER sim_trajOutputInterval  REAL 1.e-10

D sim_trajOutputIntervalNearStag  trajectory output interval near stagnation (s)
PARAMETER sim_trajOutputIntervalNearStag  REAL 5.e-12

D sim_rNearStag  radius defining "near stagnation", increased trajectory output frequency
PARAMETER sim_rNearStag  REAL 50.e-4
'''


class ZPinchConfigGenerator:
    """Config 生成器 (官方 stock 逐字快照)。"""

    def generate(self) -> str:
        """返回文件文本 (与官方 stock 逐字节一致, LF 行尾)。"""
        return ZPINCH_CONFIG

    def save(self, output_path) -> Path:
        """写出文件, 返回路径。"""
        p = Path(output_path)
        p.write_text(self.generate(), encoding="utf-8", newline="\n")
        return p
