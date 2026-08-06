"""Grid_markRefineDerefine.F90 生成器

生成基于模式 C3（边界框重叠法）的自定义网格细化约束代码。
适用于 1D/2D/3D FLASH 仿真中的多层材料 AMR 控制。

用法示例:
    # 先完成 setup 和 .par 文件生成，从中提取参数
    gen = GridMarkRefineDerefineGenerator("my_sim")
    gen.set_domain(xmin=-0.02, xmax=0.02, nxb=16, nblockx=8)
    gen.set_refinement(lrefine_max=8, lrefine_min=1)
    gen.add_zone(ZoneConfig("Al",  "sim_targHeight",
                 lref_lower_ratio=0.75, lref_upper_ratio=1.0))
    gen.add_zone(ZoneConfig("CH",  "sim_polyHeight",
                 lref_lower_ratio=None, lref_upper_ratio=0.5))
    gen.add_zone(ZoneConfig("He",  None,
                 lref_upper_ratio=None))  # fallback
    gen.save("Grid_markRefineDerefine.F90")
"""
from pathlib import Path
from typing import Optional, Union, List
from dataclasses import dataclass


# ── ⚠️ 重要提示 ─────────────────────────────────────────────────────
# 本生成器生成的是自定义 AMR 网格细化约束代码。
# 它不修改任何物理求解器逻辑，只控制网格细化行为。
# 建议进行小批量 flash 仿真进行人工核查后再正式使用。
# ─────────────────────────────────────────────────────────────────────


@dataclass
class ZoneConfig:
    """定义单个材料区域的细化约束。

    Attributes:
        name:           区域名称（如 "Al", "CH", "He"），仅用于注释
        sim_var_name:   Simulation_data 中的半宽变量名
                        如 "sim_targHeight" 表示区域 |x| ≤ sim_targHeight
                        设为 None 表示该区域为 fallback（else 分支）
        lref_lower_ratio: 下限约束。None=不设下限（不主动 refine）
                        比例因子，相对 lrefine_max
                        如 0.75 → lrefine_max × 0.75 = lrefine_max-2(当lrefine_max=8)
                        ⚠️ 薄层材料（厚度 ≤ 几倍 res_min）必须设为 1.0
                        否则初始化阶段可能达不到 lrefine_max。详见 MEMORY.md "初始化阶段的网格细化陷阱"
        lref_upper_ratio: 上限约束。None=不设上限（不强制 derefine）
                        比例因子，相对 lrefine_max
                        如 1.0 → lrefine_max, 0.5 → lrefine_max/2
        use_bounding_box: 使用边界框重叠法（默认 True，推荐）
        zone_margin:     缓冲区扩展系数。>1.0 时区域判断边界向两侧扩展
                        (参数值×zone_margin)，使高精度网格覆盖到物理边界外侧，
                        减少界面处的数值不稳定性（默认 1.0，无扩展）
    """
    name: str
    sim_var_name: Optional[str] = None
    lref_lower_ratio: Optional[float] = None
    lref_upper_ratio: Optional[float] = None
    use_bounding_box: bool = True
    zone_margin: float = 1.0


class GridMarkRefineDerefineGenerator:
    """Grid_markRefineDerefine.F90 生成器。

    生成基于模式 C3 的自定义网格细化约束 F90 代码。
    支持链式调用。

    ⚠️ 注意：生成的代码是指导 AMR 行为的"建议"，
        实际细化结果还受以下因素影响:
        ① refine_var 梯度判据（.par 文件中的 refine_var_*）
        ② PARAMESH 邻接限制 (|Δlref| ≤ 1)
        ③ lrefine_max / lrefine_min 全局限制
    """

    def __init__(self, simulation_name: str = "grid_rede",
                 sim_src_subdir: Optional[str] = None):
        """初始化生成器。

        所有仿真参数（域范围、块数、细化层级）均须通过 set_domain() 和
        set_refinement() 方法传入，不从其它文件自动读取。
        这样确保生成的 F90 注释中的分辨率与实际 setup 命令一致。

        Args:
            simulation_name: 仿真名称（仅用于 F90 头注释中的路径）
            sim_src_subdir: FLASH source/Simulation/SimulationMain/ 下的
                            用户算例子目录名 (None = 从 flash._core.credentials
                            读取, 读取不到回退默认; 勿硬编码用户名)。
        """
        self._sim_name = simulation_name
        if sim_src_subdir is None:
            try:
                from flash._core.credentials import get_user_name
                sim_src_subdir = get_user_name()
            except Exception:
                sim_src_subdir = "hello"  # 读取不到 → 默认用户名
        self._sim_src_subdir = sim_src_subdir
        self._xmin = None      # 须通过 set_domain() 设置
        self._xmax = None      # 须通过 set_domain() 设置
        self._nxb = None       # 须通过 set_domain() 设置
        self._nblockx = None   # 须通过 set_domain() 设置
        self._lrefine_max = None   # 须通过 set_refinement() 设置
        self._lrefine_min = None   # 须通过 set_refinement() 设置
        self._zones: List[ZoneConfig] = []

    # ── 基础配置 ────────────────────────────────────────────────────

    def set_domain(
        self, xmin: float, xmax: float, nxb: int, nblockx: int
    ) -> "GridMarkRefineDerefineGenerator":
        """设置计算域参数（用于注释中的分辨率计算）。

        所有参数均无默认值，须从 setup 命令和 .par 文件中读取。

        Args:
            xmin: 域下限 [cm]（与 .par 中的 xmin 一致）
            xmax: 域上限 [cm]（与 .par 中的 xmax 一致）
            nxb: 每块单元数（与 setup 命令中的 -nxb= 一致）
            nblockx: x 方向初始块数（与 .par 中的 nblockx 一致）
        """
        self._xmin = xmin
        self._xmax = xmax
        self._nxb = nxb
        self._nblockx = nblockx
        return self

    def set_refinement(
        self, lrefine_max: int, lrefine_min: int
    ) -> "GridMarkRefineDerefineGenerator":
        """设置细化层级参数（用于注释中的分辨率计算）。

        应在 .par 文件生成后调用，从其中读取 lrefine_max / lrefine_min。
        这样生成的 F90 注释中的理论分辨率与实际 .par 设置一致。

        Args:
            lrefine_max: 最大细化层级（与 .par 文件中的 lrefine_max 一致）
            lrefine_min: 最小细化层级（与 .par 文件中的 lrefine_min 一致）
        """
        self._lrefine_max = lrefine_max
        self._lrefine_min = lrefine_min
        return self

    def add_zone(self, zone: ZoneConfig) -> "GridMarkRefineDerefineGenerator":
        """添加材料区域细化约束（按添加顺序决定 if-else 优先级）。"""
        self._zones.append(zone)
        return self

    # ── 核心生成方法 ────────────────────────────────────────────────

    def generate(self) -> str:
        """生成 Grid_markRefineDerefine.F90 内容字符串。"""
        res_min, res_max = self._calc_resolution()

        code  = self._header(res_min, res_max)
        code += self._use_section()
        code += self._variable_section()
        code += self._gradient_section()
        code += self._zone_section()
        code += self._postprocess_section()
        code += self._footer()
        return code

    def save(self, output_path: Union[str, Path]) -> Path:
        """生成并保存 Grid_markRefineDerefine.F90 文件（强制 LF 换行）。"""
        content = self.generate()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
        return out

    # ── 内部方法 ────────────────────────────────────────────────────

    def _calc_resolution(self) -> tuple:
        """计算理论网格分辨率（只用于注释信息，不影响实际仿真）。

        必须在 set_domain() 和 set_refinement() 之后调用。
        所有参数均在调用时显式传入，不从外部自动读取。

        公式:
            res_min = span / (nxb * nblockx * 2^(lrefine_max-1))
            res_max = span / (nxb * nblockx * 2^(lrefine_min-1))

        Returns:
            (res_min_um, res_max_um): 理论最小/最大网格间距 [µm]
        """
        if self._xmin is None or self._xmax is None:
            raise RuntimeError(
                "必须调用 set_domain(xmin, xmax, nxb, nblockx) 设置域参数。"
                "这些值应从 setup 命令和 .par 文件中读取。"
            )
        if self._nxb is None or self._nblockx is None:
            raise RuntimeError(
                "必须调用 set_domain(xmin, xmax, nxb, nblockx) 设置网格参数。"
                "nxb 来自 setup 命令的 -nxb=，nblockx 来自 .par 文件的 nblockx。"
            )
        if self._lrefine_max is None or self._lrefine_min is None:
            raise RuntimeError(
                "必须调用 set_refinement(lrefine_max, lrefine_min) "
                "设置细化层级。lrefine_max/lrefine_min 应从 .par 文件中读取。"
            )
        span = abs(self._xmax - self._xmin) * 1e4
        r_min = span / (self._nxb * self._nblockx * 2 ** (self._lrefine_max - 1))
        r_max = span / (self._nxb * self._nblockx * 2 ** (self._lrefine_min - 1))
        return r_min, r_max

    def _ratio_desc(self, r: Optional[float]) -> str:
        """比例因子描述文本。0.75 → 'lrefine_max × 0.75', None → '无约束'"""
        if r is None:
            return "无约束"
        return f"lrefine_max × {r}"

    def _ratio_to_f90(self, r: Optional[float]) -> Optional[str]:
        """比例因子 → F90 表达式。
        0.75 → 'lrefine_max * 3 / 4', 0.5 → 'lrefine_max / 2',
        1.0 → 'lrefine_max', None → None
        """
        if r is None:
            return None
        if r <= 0.0 or r >= 1.0:
            return "lrefine_max"
        from fractions import Fraction
        f = Fraction(r).limit_denominator(10)
        # 使用整数运算: lrefine_max * numerator / denominator
        if f.numerator == 1:
            return f"lrefine_max / {f.denominator}"
        else:
            return f"lrefine_max * {f.numerator} / {f.denominator}"

    # ── F90 代码块生成 ──────────────────────────────────────────────

    def _header(self, res_min: float, res_max: float) -> str:
        zones_desc = []
        for z in self._zones:
            lower = self._ratio_desc(z.lref_lower_ratio)
            upper = self._ratio_desc(z.lref_upper_ratio)
            desc = f"  !!    {z.name:8s}: 下限={lower:20s}  上限={upper:20s}"
            if z.sim_var_name:
                desc += f"  (|x| ≤ {z.sim_var_name})"
            desc += f"  {'[边界框重叠]' if z.use_bounding_box else '[块中心法]'}"
            zones_desc.append(desc)

        sim_vars = [z.sim_var_name for z in self._zones if z.sim_var_name]
        var_line = ", ".join(sim_vars) if sim_vars else "（无，见代码中的区域定义）"

        return f"""!!****if* source/Simulation/SimulationMain/{self._sim_src_subdir}/{self._sim_name}/Grid_markRefineDerefine
!!
!! NAME
!!  Grid_markRefineDerefine
!!
!! SYNOPSIS
!!  call Grid_markRefineDerefine()
!!
!! DESCRIPTION
!!  ═══════════════════════════════════════════════════════════════════
!!  模式 C3：二阶梯度加密 + 逐块边界框重叠区域约束
!!  ═══════════════════════════════════════════════════════════════════
!!
!!  用途: 对 FLASH AMR 网格细化施加逐材料区域的层级约束。
!!        这是可选的自定义组件，不修改物理求解器逻辑。
!!
!!  生成工具: GridMarkRefineDerefineGenerator
!!  模板参考: gen_Grid_markRefineDerefine/refs/
!!
!!  区域约束定义（按优先级从高到低）:
!!
{chr(10).join(zones_desc)}
!!
!!  ★ 关键设计（2026-07-02）★
!!  区域判断使用边界框重叠（bounding box overlap）而非块中心坐标。
!!  原设计（块中心法）在目标区域宽度 < 最小块尺寸时完全失效。
!!  新方法检查块的 [LOW, HIGH] 区间是否与目标区域重叠，
!!  即使块远大于目标区域，只要覆盖即触发约束。
!!
!!  理论分辨率（仅供 .par 文件参考）:
!!    res_min = |xmax-xmin|/(nxb×nblockx×2^(lrefine_max-1))
!!           = {res_min:.4f} um  (lrefine_max={self._lrefine_max})
!!    res_max = |xmax-xmin|/(nxb×nblockx×2^(lrefine_min-1))
!!           = {res_max:.4f} um  (lrefine_min={self._lrefine_min})
!!
!!  ⚠️ 重要提示
!!  ───────────────────────────────────────────────────────────────────
!!  本文件是自定义 AMR 细化约束器。实际细化结果受以下因素影响:
!!    ① refine_var 梯度判据（.par 文件中的 refine_var_*）
!!    ② PARAMESH 邻接限制 (|Δlref| ≤ 1)
!!    ③ lrefine_max / lrefine_min 全局限制
!!  建议进行小批量 flash 仿真进行人工核查后再正式使用。
!!
!! NOTES
!!  依赖的 Simulation_data 变量: {var_line}
!!
!!***
!!
subroutine Grid_markRefineDerefine()
"""

    def _use_section(self) -> str:
        sim_vars = [z.sim_var_name for z in self._zones if z.sim_var_name]
        import_line = ", ".join(sim_vars) if sim_vars else ""
        return f"""  use Driver_interface, ONLY : Driver_getSimTime
  use Grid_data, ONLY : gr_refine_cutoff, gr_derefine_cutoff, &
                        gr_refine_filter, &
                        gr_numRefineVars, gr_refine_var, &
                        gr_refineOnParticleCount, &
                        gr_enforceMaxRefinement, gr_maxRefine, &
                        gr_lrefineMaxByTime, &
                        gr_lrefineMaxRedDoByTime, &
                        gr_lrefineMaxRedDoByLogR, &
                        gr_lrefineCenterI, gr_lrefineCenterJ, gr_lrefineCenterK, &
                        gr_eosModeNow
  use tree, ONLY : newchild, refine, derefine, stay, nodetype, &
                   lrefine, lrefine_max, lrefine_min, lnblocks
  use Logfile_interface, ONLY : Logfile_stampVarMask
  use Grid_interface, ONLY : Grid_fillGuardCells, &
                             Grid_getListOfBlocks, &
                             Grid_getBlkBoundBox
  use Particles_interface, ONLY : Particles_sinkMarkRefineDerefine
  use Simulation_data, ONLY : {import_line}

  implicit none

#include "constants.h"
#include "Flash.h"
"""

    def _variable_section(self) -> str:
        """变量声明区，包含 zone_margin 所需的扩展边界变量。"""
        # 收集所有 zone_margin > 1.0 的区域，为它们添加 *_zone_half 变量声明
        margin_vars = []
        for z in self._zones:
            if z.sim_var_name and z.zone_margin > 1.0:
                margin_vars.append(f"  real :: {z.sim_var_name}_zone_half")

        margin_decl = "\n".join(margin_vars)
        margin_decl = "\n" + margin_decl if margin_vars else ""

        return f"""
  ! ── 变量声明 ───────────────────────────────────────────────
  real    :: ref_cut, deref_cut, ref_filter
  integer :: l, i, iref
  logical, save :: gcMaskArgsLogged = .FALSE.
  integer, save :: eosModeLast = 0
  logical :: doEos = .true.
  integer, parameter :: maskSize = NUNK_VARS + NDIM * NFACE_VARS
  logical, dimension(maskSize) :: gcMask
  real :: time
  integer :: blockCount
  integer, dimension(MAXBLOCKS) :: blkList
  integer :: lb
  real, dimension(LOW:HIGH, MDIM) :: boundBox
  integer :: target_lref, lower_lref, ch_max_lref, he_max_lref{margin_decl}
"""

    def _gradient_section(self) -> str:
        return """
  ! ── 步骤 1: 标准 FLASH 二阶梯度加密流程 ───────────────────

  if (gr_lrefineMaxRedDoByTime) call gr_markDerefineByTime()
  if (gr_lrefineMaxByTime) call gr_setMaxRefineByTime()

  if (gr_eosModeNow .NE. eosModeLast) then
     gcMaskArgsLogged = .FALSE.
     eosModeLast = gr_eosModeNow
  end if

  gcMask = .false.
  do i = 1, gr_numRefineVars
     iref = gr_refine_var(i)
     if (iref > 0) gcMask(iref) = .TRUE.
  end do
  gcMask(NUNK_VARS+1:min(maskSize, NUNK_VARS+NDIM*NFACE_VARS)) = .TRUE.

  if (.NOT. gcMaskArgsLogged) then
     call Logfile_stampVarMask(gcMask, .true., &
          '[Grid_markRefineDerefine]', 'gcArgs')
  end if

  call Grid_fillGuardCells(CENTER_FACES, ALLDIR, doEos=.true., &
       maskSize=maskSize, mask=gcMask, makeMaskConsistent=.true., &
       doLogMask=.NOT.gcMaskArgsLogged, selectBlockType=ACTIVE_BLKS)
  gcMaskArgsLogged = .TRUE.

  newchild(:) = .FALSE.
  refine(:)   = .FALSE.
  derefine(:) = .FALSE.
  stay(:)     = .FALSE.

  do l = 1, gr_numRefineVars
     iref     = gr_refine_var(l)
     ref_cut  = gr_refine_cutoff(l)
     deref_cut  = gr_derefine_cutoff(l)
     ref_filter = gr_refine_filter(l)
     call gr_markRefineDerefine(iref, ref_cut, deref_cut, ref_filter)
  end do
"""

    def _zone_section(self) -> str:
        """生成区域约束代码块，包含 zone_margin 缓冲区初始化。"""
        # 收集 zone_margin 初始化语句
        margin_inits = []
        for z in self._zones:
            if z.sim_var_name and z.zone_margin > 1.0:
                margin_inits.append(
                    f"  {z.sim_var_name}_zone_half = {z.sim_var_name} * {z.zone_margin}"
                )
        margin_code = "\n".join(margin_inits)
        margin_code = "\n" + margin_code if margin_inits else ""

        lines = [
            "",
            "  ! ── 步骤 2: 区域约束 ════════════════════════════════",
            "  !",
            "  !  使用边界框重叠法判断区域归属。",
            "  !  排在前面的区域优先匹配（if → else if → else）。",
            "  !",
            "",
            "  target_lref = lrefine_max",
            "  lower_lref  = max(lrefine_min, lrefine_max - 2)",
            "  ch_max_lref = max(lrefine_min, lrefine_max / 2)",
            "  if (ch_max_lref < 2) ch_max_lref = 2",
            "  he_max_lref = lrefine_min",
            margin_code,
            "",
            "  call Grid_getListOfBlocks(ACTIVE_BLKS, blkList, blockCount)",
            "",
            "  do i = 1, blockCount",
            "     lb = blkList(i)",
            "     if (nodetype(lb) /= LEAF) cycle",
            "     call Grid_getBlkBoundBox(lb, boundBox)",
            "",
        ]

        # 生成每个区域的 if/else 分支
        first = True
        for z in self._zones:
            if z.sim_var_name is None:
                # fallback
                lines.append(self._else_branch(z))
            else:
                lines.append(self._if_branch(z, first))
                first = False

        lines.append("     end if")
        lines.append("")
        lines.append("  end do")
        lines.append("")
        return "\n".join(lines)

    def _if_branch(self, zone: ZoneConfig, first: bool) -> str:
        """生成 if/else-if 分支，支持 zone_margin 缓冲区扩展。"""
        var = zone.sim_var_name
        name = zone.name
        indent = "     "
        keyword = "if" if first else "else if"
        margin = zone.zone_margin

        lower_code = self._ratio_to_f90(zone.lref_lower_ratio)
        upper_code = self._ratio_to_f90(zone.lref_upper_ratio)

        # 判断边界: 原始值 或 扩展值
        if margin > 1.0:
            cmp_expr = f"({var} * {margin})"
            desc_ext = f" (扩展至 ±{var}×{margin})"
            var_half_var = f"{var}_zone_half"
        else:
            cmp_expr = var
            desc_ext = ""
            var_half_var = var

        lines = [
            f"     ! ═══ {name} 区 (|x| ≤ {var}){desc_ext} ═══",
            f"     !   下限: {self._ratio_desc(zone.lref_lower_ratio)}",
            f"     !   上限: {self._ratio_desc(zone.lref_upper_ratio)}",
        ]

        if margin > 1.0:
            # 使用局部变量 + 乘法，避免 F90 中重复计算
            # 生成器会在变量声明区为该区域生成 *_zone_half 变量
            lines.append(f"     !   zone_margin={margin}: 判断区扩大至 ±{var}×{margin}")
            lines.append(f"     {keyword} (boundBox(HIGH, IAXIS) >= -({cmp_expr}) .and. &")
            lines.append(f"         boundBox(LOW, IAXIS)  <=  ({cmp_expr})) then")
        else:
            lines.append(f"     {keyword} (boundBox(HIGH, IAXIS) >= -{var} .and. &")
            lines.append(f"         boundBox(LOW, IAXIS)  <=  {var}) then")

        has_lower = zone.lref_lower_ratio is not None
        has_upper = zone.lref_upper_ratio is not None

        if has_lower and has_upper:
            lines.extend([
                f"        if (lrefine(lb) < {lower_code}) then",
                "           refine(lb)   = .true.",
                "           derefine(lb) = .false.",
                f"        else if (lrefine(lb) > {upper_code}) then",
                "           refine(lb)   = .false.",
                "           derefine(lb) = .true.",
                "        end if",
            ])
        elif has_lower and not has_upper:
            lines.extend([
                f"        if (lrefine(lb) < {lower_code}) then",
                "           refine(lb)   = .true.",
                "           derefine(lb) = .false.",
                "        end if",
            ])
        elif not has_lower and has_upper:
            lines.extend([
                f"        if (lrefine(lb) > {upper_code}) then",
                "           refine(lb)   = .false.",
                "           derefine(lb) = .true.",
                "        end if",
            ])
        else:
            lines.append("        ! 无约束，保留梯度加密结果")

        return "\n".join(lines)

    def _else_branch(self, zone: ZoneConfig) -> str:
        """生成 else（fallback）分支。"""
        name = zone.name
        lines = [
            f"     else",
            f"        ! ═══ {name} 区（fallback）═══",
        ]
        if zone.lref_upper_ratio is not None:
            upper_code = self._ratio_to_f90(zone.lref_upper_ratio)
            lines.extend([
                f"        if (lrefine(lb) > {upper_code}) then",
                "           refine(lb)   = .false.",
                "           derefine(lb) = .true.",
                "        end if",
            ])
        else:
            lines.append("        ! 无约束，保留梯度加密结果")
        lines.append("")
        return "\n".join(lines)

    def _postprocess_section(self) -> str:
        return """
  ! ── 步骤 3: 标准后处理 ─────────────────────────────────

#ifdef FLASH_GRID_PARAMESH2
  if (gr_numRefineVars .LE. 0) then
     call gr_markRefineDerefine(-1, 0.0, 0.0, 0.0)
  end if
#endif

  if (gr_refineOnParticleCount) call gr_ptMarkRefineDerefine()
  if (gr_enforceMaxRefinement) call gr_enforceMaxRefine(gr_maxRefine)
  if (gr_lrefineMaxRedDoByLogR) &
       call gr_unmarkRefineByLogRadius(gr_lrefineCenterI, &
                                       gr_lrefineCenterJ, gr_lrefineCenterK)
  call Particles_sinkMarkRefineDerefine()

  where (nodetype(:) .NE. LEAF)
     refine(:)   = .false.
     derefine(:) = .false.
  end where

  return
end subroutine Grid_markRefineDerefine
"""

    def _footer(self) -> str:
        return f"""
! ═══════════════════════════════════════════════════════════════════
! 本文件由 GridMarkRefineDerefineGenerator 自动生成。
! 模板参考: gen_Grid_markRefineDerefine/refs/
! ═══════════════════════════════════════════════════════════════════
"""
