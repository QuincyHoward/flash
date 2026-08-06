"""
NewParaGenerator — 多区密度剖面 FLASH 输入文件生成器
═══════════════════════════════════════════════════════

生成思路:
  基于 test/newpara/ 系列测试的经验（新参数 5 步流程 + 密度剖面 + 增量边界），
  将已验证的配置模式封装为可复用的 API。

  每个 zone 可以独立设置:
  - zoneHeight: 区域厚度 (cm)
  - zoneProfile: 密度剖面类型 (0-4)
  - zoneP1, zoneP2: 剖面参数

用法:
  >>> gen = NewParaGenerator()
  >>> gen.add_zone(height=0.004, profile=1, p1=0.001, name="exp_decay")
  >>> gen.add_zone(height=0.004, profile=0, name="constant")
  >>> gen.generate(output_dir="./my_sim")

参考:
  test/newpara/flash_profile/multizone_profile/  — 5 区单仿真完整实现
  test/newpara/                                    — 基础 3 区双靶实现
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ═══════════════════════════════════════════════════════════════
# 密度剖面类型定义
# ═══════════════════════════════════════════════════════════════

PROFILE_TYPES = {
    0: ("constant",       "ρ = ρ₀"),
    1: ("exp_decay",      "ρ = ρ₀ × exp(-x_local / p1)"),
    2: ("exp_growth",     "ρ = ρ₀ × exp(+x_local / p1)"),
    3: ("linear",         "ρ = ρ₀ × (p1 + p2 × x_local / w)"),
    4: ("gaussian",       "ρ = ρ₀ × exp(-0.5 × ((x_local-p1×w) / (p2×w))²)"),
}

PROFILE_DEFAULTS = {
    0: {"p1": 0.0, "p2": 0.0},
    1: {"p1": 0.001, "p2": 0.0},
    2: {"p1": 0.001, "p2": 0.0},
    3: {"p1": 0.5, "p2": 1.0},
    4: {"p1": 0.5, "p2": 0.25},
}


# ═══════════════════════════════════════════════════════════════
# Fortran density_profile 函数模板
# ═══════════════════════════════════════════════════════════════

DENSITY_PROFILE_F90 = """
!---------------------------------------------------------------------
! density_profile — 计算密度剖面乘子
!   profile: 0=const, 1=exp_decay, 2=exp_growth, 3=linear, 4=gaussian
!   x_local: 距 zone 左边界的距离 [cm]
!   width:   zone 宽度 [cm]
!   p1, p2:  剖面参数
!   返回: 乘子(乘以 base rho)
!---------------------------------------------------------------------
real function density_profile(profile, x_local, width, p1, p2)
  implicit none
  integer, intent(in) :: profile
  real,    intent(in) :: x_local, width, p1, p2
  real :: arg, x_norm
  select case(profile)
  case(0); density_profile = 1.0
  case(1)
    if (p1 > 0.0) then; density_profile = exp(-x_local / p1)
    else; density_profile = 1.0; end if
  case(2)
    if (p1 > 0.0) then; density_profile = exp(x_local / p1)
    else; density_profile = 1.0; end if
  case(3)
    x_norm = x_local / max(width, 1.0e-30)
    density_profile = p1 + p2 * x_norm
  case(4)
    if (p2 > 0.0) then
      arg = (x_local - p1 * width) / (p2 * width)
      density_profile = exp(-0.5 * arg * arg)
    else; density_profile = 1.0; end if
  case default; density_profile = 1.0
  end select
end function density_profile
"""


# ═══════════════════════════════════════════════════════════════
# Zone 数据结构
# ═══════════════════════════════════════════════════════════════

class ZoneConfig:
    """单个区域的配置。

    Attributes:
        height: 区域厚度 [cm]
        profile: 密度剖面类型 (0-4)
        p1: 剖面参数 1
        p2: 剖面参数 2
        name: 区域名称（用于注释）
    """

    def __init__(
        self,
        height: float = 0.004,
        profile: int = 0,
        p1: Optional[float] = None,
        p2: Optional[float] = None,
        name: str = "",
    ):
        self.height = height
        self.profile = profile
        defaults = PROFILE_DEFAULTS.get(profile, {"p1": 0.0, "p2": 0.0})
        self.p1 = p1 if p1 is not None else defaults["p1"]
        self.p2 = p2 if p2 is not None else defaults["p2"]
        self.name = name

    def to_params(self, idx: int) -> Dict[str, Any]:
        """转换为 Config PARAMETER 参数字典。"""
        return {
            f"sim_zone{idx}Height": self.height,
            f"sim_zone{idx}Profile": self.profile,
            f"sim_zone{idx}P1": self.p1,
            f"sim_zone{idx}P2": self.p2,
        }

    def validate(self) -> List[str]:
        """验证 zone 配置，返回错误列表。"""
        errors = []
        if self.height <= 0:
            errors.append(f"zone height must be positive, got {self.height}")
        if self.profile not in PROFILE_TYPES:
            errors.append(f"profile type {self.profile} not in {list(PROFILE_TYPES.keys())}")
        if self.profile in (1, 2) and self.p1 <= 0:
            errors.append(f"exp decay/growth needs p1 > 0, got {self.p1}")
        if self.profile == 4 and self.p2 <= 0:
            errors.append(f"gaussian needs p2 > 0, got {self.p2}")
        return errors


# ═══════════════════════════════════════════════════════════════
# 主生成器
# ═══════════════════════════════════════════════════════════════

class NewParaGenerator:
    """多区密度剖面 FLASH 输入文件生成器。

    封装了 test/newpara/ 中验证的:
    - 5 步新参数流程 (Config → .F90 → .par)
    - 增量边界 (ReDo 风格)
    - 密度剖面 (5 种类型)
    - 物种质量分数
    """

    def __init__(self):
        self.zones: List[ZoneConfig] = []
        self.vacuum_height: float = 0.005  # cm
        self.base_density: float = 2.7     # g/cm^3 (TARG_SPEC)
        self.chamber_density: float = 1e-6
        self.species_list: List[str] = ["cham", "targ"]
        self.xmax: float = 0.0  # auto-calculated

    def add_zone(
        self,
        height: float = 0.004,
        profile: int = 0,
        p1: Optional[float] = None,
        p2: Optional[float] = None,
        name: str = "",
    ) -> "NewParaGenerator":
        """添加一个区域。"""
        self.zones.append(ZoneConfig(height=height, profile=profile, p1=p1, p2=p2, name=name))
        self._update_xmax()
        return self

    def _update_xmax(self):
        total = self.vacuum_height + sum(z.height for z in self.zones)
        self.xmax = total * 1.05  # 5% margin

    def validate(self) -> List[str]:
        """验证所有 zone 配置，返回所有错误。"""
        errors = []
        if not self.zones:
            errors.append("at least one zone required")
        for i, z in enumerate(self.zones):
            for e in z.validate():
                errors.append(f"Zone {i+1}: {e}")
        if self.vacuum_height <= 0:
            errors.append("vacuum_height must be positive")
        # 检查参数名冲突
        seen = set()
        for z in self.zones:
            for i in range(1, len(self.zones) + 1):
                for k in z.to_params(i):
                    if k in seen:
                        errors.append(f"duplicate parameter: {k}")
                    seen.add(k)
        return errors

    def generate_config(self) -> str:
        """生成 Config 文件内容（含 Zone 参数）。"""
        lines = [
            "# Configuration file — Generated by NewParaGenerator",
            'REQUIRES Driver',
            'REQUIRES physics/Hydro',
            '',
            'USESETUPVARS ThreeT',
            'IF ThreeT',
            '   REQUESTS physics/Diffuse/DiffuseMain/Unsplit',
            '   REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer',
            '   REQUESTS physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ',
            'ENDIF',
            '',
            f'# species={",".join(self.species_list)}',
            '',
            'DATAFILES al-imx-003.cn4',
            'DATAFILES he-imx-005.cn4',
            '',
            '##########################',
            '#   RUNTIME PARAMETERS   #',
            '##########################',
            '',
            'D sim_initGeom Use a spherical target if sphere, default to slab',
            'PARAMETER sim_initGeom STRING "slab" ["slab","sphere"]',
            '',
            f'D sim_rhoTarg Base density for target zones',
            f'PARAMETER sim_rhoTarg REAL {self.base_density}',
            '',
            'D sim_teleTarg Initial target electron temperature',
            'PARAMETER sim_teleTarg  REAL 290.11375',
            '',
            'D sim_tionTarg Initial target ion temperature',
            'PARAMETER sim_tionTarg  REAL 290.11375',
            '',
            'D sim_tradTarg Initial target radiation temperature',
            'PARAMETER sim_tradTarg  REAL 290.11375',
            '',
            'D sim_rhoCham Initial chamber density',
            f'PARAMETER sim_rhoCham REAL {self.chamber_density}',
            '',
            'D sim_teleCham Initial chamber electron temperature',
            'PARAMETER sim_teleCham  REAL 290.11375',
            '',
            '# ===== Multi-Zone Profile Parameters =====',
        ]

        for i, z in enumerate(self.zones, 1):
            ptype_name = PROFILE_TYPES.get(z.profile, ("unknown", ""))[0]
            comment = z.name or f"zone{i}_{ptype_name}"
            lines.extend([
                f'# Zone {i}: {comment} (profile={z.profile})',
                f'D sim_zone{i}Height Thickness of zone {i}',
                f'PARAMETER sim_zone{i}Height REAL {z.height}',
                f'D sim_zone{i}Profile Profile type for zone {i}',
                f'PARAMETER sim_zone{i}Profile INTEGER {z.profile}',
                f'D sim_zone{i}P1 Profile param 1 for zone {i}',
                f'PARAMETER sim_zone{i}P1 REAL {z.p1}',
                f'D sim_zone{i}P2 Profile param 2 for zone {i}',
                f'PARAMETER sim_zone{i}P2 REAL {z.p2}',
                '',
            ])

        lines.append(
            'D lase_variable saves (density of) the irradiated energy from EnergyDeposition unit'
        )
        lines.append('VARIABLE lase TYPE: PER_VOLUME')
        lines.append('')
        lines.append('USESETUPVARS ThscDemo')
        lines.append('IF ThscDemo')
        lines.append('   REQUIRES diagnostics/ThomsonScattering')
        lines.append('   VARIABLE pwin')
        lines.append('   VARIABLE pwia')
        lines.append('   VARIABLE pwde')
        lines.append('   VARIABLE pwd1')
        lines.append('   VARIABLE pwi2')
        lines.append('   VARIABLE pwd2')
        lines.append('ENDIF')

        return "\n".join(lines)

    def generate_sim_data(self) -> str:
        """生成 Simulation_data.F90。"""
        lines = [
            'module Simulation_data',
            '  implicit none',
            '#include "constants.h"',
            '',
            '  real, save :: sim_rhoTarg',
            '  real, save :: sim_teleTarg',
            '  real, save :: sim_tionTarg',
            '  real, save :: sim_tradTarg',
            '',
            '  real, save :: sim_rhoCham',
            '  real, save :: sim_teleCham',
            '  real, save :: sim_tionCham',
            '  real, save :: sim_tradCham',
            '',
            '  ! ===== Multi-Zone Profile Variables =====',
        ]
        for i, z in enumerate(self.zones, 1):
            lines.extend([
                f'  real,    save :: sim_zone{i}Height',
                f'  integer, save :: sim_zone{i}Profile',
                f'  real,    save :: sim_zone{i}P1, sim_zone{i}P2',
            ])
        lines.extend([
            '',
            '  logical, save :: sim_killdivb = .FALSE.',
            '  real, save :: sim_smallX',
            "  character(len=MAX_STRING_LENGTH), save :: sim_initGeom",
            '',
            'end module Simulation_data',
        ])
        return "\n".join(lines)

    def generate_sim_init(self) -> str:
        """生成 Simulation_init.F90。"""
        lines = [
            'subroutine Simulation_init()',
            '  use Simulation_data',
            '  use RuntimeParameters_interface, ONLY : RuntimeParameters_get',
            '  implicit none',
            '#include "constants.h"',
            '#include "Flash.h"',
            '',
            '  call RuntimeParameters_get("sim_rhoTarg", sim_rhoTarg)',
            '  call RuntimeParameters_get("sim_teleTarg", sim_teleTarg)',
            '  call RuntimeParameters_get("sim_tionTarg", sim_tionTarg)',
            '  call RuntimeParameters_get("sim_tradTarg", sim_tradTarg)',
            '',
            '  call RuntimeParameters_get("sim_rhoCham", sim_rhoCham)',
            '  call RuntimeParameters_get("sim_teleCham", sim_teleCham)',
            '  call RuntimeParameters_get("sim_tionCham", sim_tionCham)',
            '  call RuntimeParameters_get("sim_tradCham", sim_tradCham)',
            '',
            '  call RuntimeParameters_get("smallX", sim_smallX)',
            '  call RuntimeParameters_get("sim_initGeom", sim_initGeom)',
            '',
            '  ! ===== Read Multi-Zone Profile Parameters =====',
        ]
        for i in range(1, len(self.zones) + 1):
            lines.extend([
                f'  call RuntimeParameters_get("sim_zone{i}Height", sim_zone{i}Height)',
                f'  call RuntimeParameters_get("sim_zone{i}Profile", sim_zone{i}Profile)',
                f'  call RuntimeParameters_get("sim_zone{i}P1", sim_zone{i}P1)',
                f'  call RuntimeParameters_get("sim_zone{i}P2", sim_zone{i}P2)',
            ])
        lines.extend([
            '',
            'end subroutine Simulation_init',
        ])
        return "\n".join(lines)

    def generate_init_block(self) -> str:
        """生成 Simulation_initBlock.F90（含增量边界 + 密度剖面）。"""
        n = len(self.zones)
        lines = [
            'subroutine Simulation_initBlock(blockId)',
            '  use Simulation_data',
            '  use Grid_interface, ONLY : Grid_getBlkIndexLimits,',
            '       Grid_getCellCoords, Grid_putPointData',
            '  implicit none',
            '',
            '#include "constants.h"',
            '#include "Flash.h"',
            '',
            '  integer, intent(in) :: blockId',
            '  integer :: i, j, k, n',
            '  integer :: blkLimits(2, MDIM), blkLimitsGC(2, MDIM)',
            '  integer :: axis(MDIM)',
            '  real, allocatable :: xcent(:), ycent(:), zcent(:)',
            '  real :: rho, tele, trad, tion',
            '  integer :: species',
        ]
        # Zone boundaries
        bvars = ", ".join([f"b{i}" for i in range(n + 1)])
        lines.append(f"  real :: {bvars}")
        lines.append('')
        lines.append('#ifndef CHAM_SPEC')
        lines.append('  integer :: CHAM_SPEC = 1, TARG_SPEC = 2')
        lines.append('#endif')
        lines.append('')
        lines.append('  real :: density_profile')
        lines.append('')
        lines.append('  ! get coordinates')
        lines.append('  call Grid_getBlkIndexLimits(blockId,blkLimits,blkLimitsGC)')
        lines.append('  allocate(xcent(blkLimitsGC(HIGH, IAXIS)))')
        lines.append('  call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., &')
        lines.append('       xcent, blkLimitsGC(HIGH, IAXIS))')
        lines.append('')

        # Incremental boundary computation
        lines.append('  ! Incremental zone boundaries')
        lines.append(f'  b0 = 0.005  ! vacuum right edge')
        for i in range(n):
            if i == 0:
                lines.append(f'  b1 = b0 + sim_zone1Height')
            else:
                lines.append(f'  b{i+1} = b{i} + sim_zone{i+1}Height')
        lines.append('')

        # Cell loop
        lines.append('  ! Loop over cells — zone assignment + density profile')
        lines.append('  do k = blkLimits(LOW,KAXIS),blkLimits(HIGH,KAXIS)')
        lines.append('     do j = blkLimits(LOW,JAXIS),blkLimits(HIGH,JAXIS)')
        lines.append('        do i = blkLimits(LOW,IAXIS),blkLimits(HIGH,IAXIS)')
        lines.append('           axis(IAXIS) = i')
        lines.append('           species = CHAM_SPEC')
        lines.append('           rho = sim_rhoCham')
        lines.append('')

        for i in range(n):
            if i == 0:
                cond = f'b0 .and. xcent(i) < b1'
            else:
                cond = f'b{i} .and. xcent(i) < b{i+1}'

            lines.extend([
                f'           if (xcent(i) >= {cond}) then',
                f'              species = TARG_SPEC',
                f'              rho = sim_rhoTarg * density_profile({i+1}, &',
                f'                   xcent(i) - b{i}, b{i+1} - b{i},',
                f'                   sim_zone{i+1}P1, sim_zone{i+1}P2)',
            ])
            if i == n - 1:
                # Last zone — close and final else
                lines.append('           else')
                lines.append('              ! vacuum')
                lines.append('              species = CHAM_SPEC')
                lines.append('              rho = sim_rhoCham')
                lines.append('           endif')
            else:
                lines.append('')
        lines.append('')

        lines.extend([
            '           tele = sim_teleTarg',
            '           tion = sim_tionTarg',
            '           trad = sim_tradTarg',
            '           if (species == CHAM_SPEC) then',
            '              tele = sim_teleCham',
            '              tion = sim_tionCham',
            '              trad = sim_tradCham',
            '           end if',
            '',
            '           call Grid_putPointData(blockId, CENTER, DENS_VAR, EXTERIOR, axis, rho)',
            '           call Grid_putPointData(blockId, CENTER, TEMP_VAR, EXTERIOR, axis, tele)',
            '',
            '           if (NSPECIES > 0) then',
            '              do n = SPECIES_BEGIN,SPECIES_END',
            '                 if (n==species) then',
            '                    call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, &',
            '                         1.0e0-(NSPECIES-1)*sim_smallX)',
            '                 else',
            '                    call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, sim_smallX)',
            '                 end if',
            '              enddo',
            '           end if',
            '         enddo',
            '     enddo',
            '  enddo',
            '',
            '  deallocate(xcent)',
            '  return',
            '',
            'end subroutine Simulation_initBlock',
        ])

        # Append Fortran density_profile function
        lines.append(DENSITY_PROFILE_F90)

        return "\n".join(lines)

    # ═════════════════════════════════════════════════════
    #  .par 格式化工具 (与 gen_par/generator.py 保持一致)
    # ═════════════════════════════════════════════════════

    @staticmethod
    def _format_value(value) -> str:
        """格式化为 FLASH .par 格式的值部分。

        规则同 gen_par.ParGeneratorExtended：
          - bool → .true. / .false.
          - str  → "string"
          - float 0.0 → "0.0"
          - float |v|≥10000 或 ≤0.01 → 科学计数法 1.0e+10
          - float 整数值 → 保留小数点 (1.0)
          - 其余 float → repr 保留完整精度
        """
        if isinstance(value, bool):
            return ".true." if value else ".false."
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, float):
            v = float(value)
            abs_v = abs(v)
            if abs_v == 0.0:
                return "0.0"
            if abs_v >= 10000 or abs_v <= 0.01:
                return f"{v:.1e}"
            if v == int(v) and abs_v < 10000:
                return f"{v:.1f}"
            return repr(v)
        else:
            return str(value)

    @staticmethod
    def _section_header(title: str) -> List[str]:
        """生成带 # 号边框的 section 标题 (同 gen_par 格式)。"""
        width = len(title) + 12
        border = "#" * width
        content = f"#     {title:^{width - 12}s}     #"
        blank = f"#     {'':^{width - 12}s}     #"
        return ["", border, blank, content, blank, border, ""]

    @staticmethod
    def _subsection_header(title: str) -> str:
        return f"### {title} ###"

    def _format_param_line(self, key: str, value, key_width: int = 0) -> str:
        val_str = self._format_value(value)
        if key_width > 0:
            return f"{key:<{key_width}} = {val_str}"
        return f"{key} = {val_str}"

    # ═════════════════════════════════════════════════════
    #  .par 内容生成 (格式化后)
    # ═════════════════════════════════════════════════════

    def generate_par_content(self) -> str:
        """生成 .par 文件内容片段（初始条件 + 多区剖面 + 网格部分）。"""
        n = len(self.zones)
        total = self.vacuum_height + sum(z.height for z in self.zones)
        lines = []

        # ── INITIAL CONDITIONS ────────────────────────────────
        lines.extend(self._section_header("INITIAL CONDITIONS"))

        # 靶材材料
        lines.append("")
        lines.append(self._subsection_header("Target Material Defaults"))
        lines.append("")

        targ_keys = ["sim_rhoTarg", "sim_teleTarg", "sim_tionTarg", "sim_tradTarg"]
        targ_vals = [self.base_density, 290.11375, 290.11375, 290.11375]
        max_targ = max(len(k) for k in targ_keys)
        for k, v in zip(targ_keys, targ_vals):
            lines.append(self._format_param_line(k, v, max_targ))

        # 腔室材料
        lines.append("")
        lines.append(self._subsection_header("Chamber Material Defaults"))
        lines.append("")

        cham_keys = ["sim_rhoCham", "sim_teleCham", "sim_tionCham", "sim_tradCham"]
        cham_vals = [self.chamber_density, 290.11375, 290.11375, 290.11375]
        max_cham = max(len(k) for k in cham_keys)
        for k, v in zip(cham_keys, cham_vals):
            lines.append(self._format_param_line(k, v, max_cham))

        # 多区剖面
        lines.append("")
        lines.append(self._subsection_header("Multi-Zone Profile Settings"))
        lines.append("")

        bounds_cm = [self.vacuum_height]
        for z in self.zones:
            bounds_cm.append(bounds_cm[-1] + z.height)

        for i, z in enumerate(self.zones, 1):
            ptype_name = PROFILE_TYPES.get(z.profile, ("unknown", ""))[0]
            lines.append(f"# Zone {i}: {z.name or ptype_name}")
            lines.append(
                f"#   x=[{bounds_cm[i-1]*1e4:.1f}, {bounds_cm[i]*1e4:.1f}] um, "
                f"profile={z.profile}"
            )

            zone_keys = [f"sim_zone{i}Height", f"sim_zone{i}Profile",
                         f"sim_zone{i}P1", f"sim_zone{i}P2"]
            zone_vals = [z.height, z.profile, z.p1, z.p2]
            max_z = max(len(k) for k in zone_keys)
            for k, v in zip(zone_keys, zone_vals):
                lines.append(self._format_param_line(k, v, max_z))
            lines.append("")

        # ── MESH PARAMETERS ──────────────────────────────────
        lines.extend(self._section_header("MESH PARAMETERS"))

        lines.append("")
        lines.append(self._subsection_header("Coordinate System"))
        lines.append("")
        lines.append('geometry = "cartesian"')

        lines.append("")
        lines.append(self._subsection_header("Domain"))
        lines.append("")

        domain_keys = ["xmin", "xmax"]
        domain_vals = [0.0, total * 1.05]
        max_d = max(len(k) for k in domain_keys)
        for k, v in zip(domain_keys, domain_vals):
            lines.append(self._format_param_line(k, v, max_d))

        lines.append("")
        lines.append(self._subsection_header("Blocks"))
        lines.append("")
        lines.append("nblockx = 4")

        lines.append("")
        lines.append(self._subsection_header("Refinement"))
        lines.append("")
        lines.append("lrefine_max = 3")

        return "\n".join(lines)

    def generate_all(self, output_dir: Union[str, Path]) -> Dict[str, Path]:
        """生成所有 FLASH 源文件到指定目录。

        Returns:
            {文件类型: 路径} 字典
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        files = {}
        files["config"] = (out / "Config").write_text(self.generate_config(), encoding="utf-8")
        files["sim_data"] = (out / "Simulation_data.F90").write_text(
            self.generate_sim_data(), encoding="utf-8"
        )
        files["sim_init"] = (out / "Simulation_init.F90").write_text(
            self.generate_sim_init(), encoding="utf-8"
        )
        files["init_block"] = (out / "Simulation_initBlock.F90").write_text(
            self.generate_init_block(), encoding="utf-8"
        )
        # .par content (just the generated section, user merges with full .par)
        par_path = out / "gen_zones.par"
        par_path.write_text(self.generate_par_content(), encoding="utf-8")
        files["par"] = par_path

        return {k: Path(v) if isinstance(v, str) else out / k for k, v in files.items()}
