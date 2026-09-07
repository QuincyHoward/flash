!!****if* source/Simulation/SimulationMain/LaserSlab_Custom/Grid_markRefineDerefine
!!
!! NAME
!!  Grid_markRefineDerefine
!!
!! SYNOPSIS
!!  call Grid_markRefineDerefine()
!!  
!! DESCRIPTION 
!!  ═══════════════════════════════════════════════════════════════════
!!  模式 C（默认二阶梯度 + 逐块几何区域加密）
!!  ═══════════════════════════════════════════════════════════════════
!!
!!  仿真场景 — 1D 笛卡尔坐标，激光烧蚀多层靶:
!!  ───────────────────────────────────────────────────────────────────
!!  域范围:     x ∈ [sim_xMin, sim_xMax] = [-200, 200] um
!!  
!!  材料布局（对称）:
!!    位置 |x| (um)       材料         目标细化
!!    ─────────────────────────────────────────────
!!    ≤ 0.2             Al 靶材      高精度 (6~8 级)
!!    (0.2, 4]          CH 泡沫      中精度 (1~4 级)
!!    > 4               He 填充      不强制（低精度）
!!
!!  激光条件:
!!    两束 1ns 梯形波（30ps 上升/下降沿, 近似方波）
!!    最大功率密度 5e11 W/cm², 波长 0.351 um
!!    左右两边同时以相同波形入射
!!
!!  细化策略（三层保障）:
!!    ① 二阶梯度加密     — 标准 FLASH 机制，捕获物理量梯度变化
!!    ② 几何区域约束     — 本文件核心，双向约束（refine+derefine）
!!                        ★ 使用边界框重叠（非块中心）判断区域归属
!!                        ★ 解决目标区域 < 最小块尺寸时的失效问题
!!    ③ PARAMESH 邻接限制 — |Δlref| ≤ 1，自然产生平滑空间过渡
!!
!!  目标细化层级（由 lrefine_max 自适应）:
!!    Al 区: lref ∈ [lrefine_max-2, lrefine_max]  (例 lref=8 → [6,8])
!!    CH 区: lref ≤ lrefine_max / 2               (例 lref=8 → ≤4)
!!    He 区: lref ≤ lrefine_min                   (例 lref=1 → ≤1)
!!
!!  分辨率注释（供 .par 文件参考）:
!!  ──────────────────────────────────────────────────────────────
!!  1D: res_min = |xmax - xmin| / (NXB * nblockx * 2^(lrefine_max-1))
!!       res_max = |xmax - xmin| / (NXB * nblockx * 2^(lrefine_min-1))
!!
!!  代入值 xmax=200, xmin=-200, NXB=8 (由 Flash.h 定义), nblockx=1:
!!    lrefine_max=12 → res_min = 400/(8×1×2¹¹) = 400/16384 ≈ 0.0244 um  ✓ (< 0.03 um)
!!    lrefine_max=11 → res_min = 400/(8×1×2¹⁰) = 400/8192  ≈ 0.0488 um  ✗ (> 0.03 um)
!!    lrefine_max=10 → res_min = 400/(8×1×2⁹)  = 400/4096  ≈ 0.0977 um  ✗
!!    lrefine_max=8  → res_min = 400/(8×1×2⁷)  = 400/1024  ≈ 0.391  um  ✗
!!    ────────────────────────────────────────────────────────────────────
!!    lrefine_min=4  → res_max = 400/(8×1×2³)  = 400/64    ≈ 6.25   um
!!    lrefine_min=3  → res_max = 400/(8×1×2²)  = 400/32    ≈ 12.5   um
!!  ──────────────────────────────────────────────────────────────
!!
!!  结论: 满足 Al 分辨率 < 0.03 um 的最小 lrefine_max = 12
!!        推荐: lrefine_max=12, lrefine_min=4, nblockx=1
!!
!! ARGUMENTS
!!  none
!!
!! NOTES
!!  依赖的 Simulation_data 变量:
!!    sim_xMin, sim_xMax       — 计算域边界 (um)
!!    sim_polyHeight           — CH 泡沫层半高 (um)
!!    sim_targHeight           — Al 靶材层半高 (um)
!!
!!  ★ 关键设计说明（2026-07-02）★
!!  区域判断使用边界框重叠（bounding box overlap）而非块中心坐标。
!!  原设计（块中心法）在目标区域宽度 < 最小块尺寸时完全失效：
!!    - Al 区 0.2µm 远小于 lref=1 的块尺寸 50µm
!!    - 没有任何块的中心落在 Al 或 CH 范围内
!!    - 所有块都被归为 He → lref ≤ 1 → 永远达不到高分辨率
!!  新方法检查块的 [LOW, HIGH] 区间是否与目标区域重叠，
!!  即使块远大于目标区域，只要覆盖即触发约束。
!!
!!  参考文件: Grid_markRefineDerefine (11).F90 (AnomalousRefine)
!!            — 模式 C 的完整实现模板
!!
!!***

subroutine Grid_markRefineDerefine()

  ! ─────────────────────────────────────────────────────────────────
  ! ① USE 语句 — 导入 FLASH 模块和仿真参数
  ! ─────────────────────────────────────────────────────────────────

  use Driver_interface, ONLY : Driver_getSimTime
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
  use Simulation_data, ONLY : &
                              sim_polyHeight, sim_targHeight

  implicit none

#include "constants.h"
#include "Flash.h"

  ! ─────────────────────────────────────────────────────────────────
  ! ② 变量声明
  ! ─────────────────────────────────────────────────────────────────

  ! — 二阶梯度加密相关 —
  real    :: ref_cut, deref_cut, ref_filter
  integer :: l, i, iref

  ! — gcMask 相关 —
  logical, save :: gcMaskArgsLogged = .FALSE.
  integer, save :: eosModeLast = 0
  logical :: doEos = .true.
  integer, parameter :: maskSize = NUNK_VARS + NDIM * NFACE_VARS
  logical, dimension(maskSize) :: gcMask

  ! — 时间相关 —
  real :: time

  ! — 逐块几何加密相关 —
  integer :: blockCount
  integer, dimension(MAXBLOCKS) :: blkList
  integer :: lb
  real, dimension(LOW:HIGH, MDIM) :: boundBox
  integer :: al_target_lref, al_lower_lref, ch_max_lref, he_max_lref

  ! ─────────────────────────────────────────────────────────────────
  ! ③ 模式 A：标准二阶梯度加密流程
  ! ─────────────────────────────────────────────────────────────────

  ! ─── ③-a：时间退粗 ───
  if (gr_lrefineMaxRedDoByTime) then
     call gr_markDerefineByTime()
  end if

  ! ─── ③-b：按时间动态调整最大精度 ───
  if (gr_lrefineMaxByTime) then
     call gr_setMaxRefineByTime()
  end if

  ! ─── ③-c：EoS 模式变更检测 ───
  ! 如果 EoS 模式从上个时间步发生了变化，重置 gcMaskArgsLogged 标志
  ! 这样下一次 Grid_fillGuardCells 会重新记录掩码日志
  if (gr_eosModeNow .NE. eosModeLast) then
     gcMaskArgsLogged = .FALSE.
     eosModeLast = gr_eosModeNow
  end if

  ! ─── ③-d：构建 gcMask ───
  ! gcMask 指定 Grid_fillGuardCells 需要填充哪些变量的 GuardCell
  ! 只包含加密判断需要的变量（性能考虑）
  gcMask = .false.
  do i = 1, gr_numRefineVars
     iref = gr_refine_var(i)
     if (iref > 0) gcMask(iref) = .TRUE.
  end do
  ! 同时填充面变量的 GuardCell（如果有）
  gcMask(NUNK_VARS+1:min(maskSize, NUNK_VARS+NDIM*NFACE_VARS)) = .TRUE.

  ! ─── ③-e：记录 gcMask 日志（仅首次或 EoS 变更后）───
  if (.NOT. gcMaskArgsLogged) then
     call Logfile_stampVarMask(gcMask, .true., &
          '[Grid_markRefineDerefine]', 'gcArgs')
  end if

  ! ─── ③-f：填充 GuardCell ───
  ! CENTER_FACES：同时填充 CENTER 和 FACE 变量的 GuardCell
  ! doEos=.true.：填充后自动调用 EoS，保持热力学一致性
  call Grid_fillGuardCells(CENTER_FACES, ALLDIR, doEos=.true., &
       maskSize=maskSize, mask=gcMask, makeMaskConsistent=.true., &
       doLogMask=.NOT.gcMaskArgsLogged, selectBlockType=ACTIVE_BLKS)
  gcMaskArgsLogged = .TRUE.

  ! ─── ③-g：重置 refine/derefine/stay 标志 ───
  ! 重要：所有标志必须每个时间步重置，因为它们是 SAVE 属性数组
  newchild(:) = .FALSE.
  refine(:)   = .FALSE.
  derefine(:) = .FALSE.
  stay(:)     = .FALSE.

  ! ─── ③-h：标准二阶梯度加密循环 ───
  ! 对每个加密变量计算二阶梯度误差，与阈值比较
  ! 误差 > refine_cutoff   → 标记 refine
  ! 误差 < derefine_cutoff → 标记 derefine
  do l = 1, gr_numRefineVars
     iref     = gr_refine_var(l)
     ref_cut  = gr_refine_cutoff(l)
     deref_cut  = gr_derefine_cutoff(l)
     ref_filter = gr_refine_filter(l)
     call gr_markRefineDerefine(iref, ref_cut, deref_cut, ref_filter)
  end do

  ! ─────────────────────────────────────────────────────────────────
  ! ④ 模式 C 附加：逐块几何区域约束（边界框重叠版）
  ! ─────────────────────────────────────────────────────────────────
  !
  !  原理：使用块的边界框（bounding box）与材料区域的交集来判断。
  !        原代码用块中心坐标判断，当材料区域宽度小于最小块尺寸时，
  !        没有块的中心落在目标区域内，导致约束完全失效。
  !        例如 Al 区 0.2µm 远小于最小块 50µm → 约束永远不触发
  !
  !  方法：检查块的 [LOW, HIGH] 区间是否与材料区域重叠：
  !    - 块与 Al 区重叠 → Al 约束（必须加密到高精度）
  !    - 块与 CH 重叠但不与 Al 重叠 → CH 约束
  !    - 其他 → He 约束（退粗）
  !
  !  目标细化层级（由 lrefine_max 自适应，不硬编码）:
  !    Al 区: 下限 = lrefine_max-2, 上限 = lrefine_max
  !           确保亚微米 Al 层有足够分辨率
  !    CH 区: 上限 = lrefine_max/2（≤4 in typical case）
  !           避免密度界面梯度引起非物理过度细化
  !    He 区: 上限 = lrefine_min（自然退粗到最粗网格）
  !
  !  过渡机制：PARAMESH 要求相邻块的细化层级差 |Δlref| ≤ 1。
  !           即使 CH 区 derefine 标记为 4，Al 边界附近的块
  !           会被 PARAMESH 维持在高一级（被动产生平滑过渡带）。
  ! ─────────────────────────────────────────────────────────────────

  ! —— ④-a：计算各材料区域的层级约束 ——
  ! Al 区：下限 = lrefine_max-2, 上限 = lrefine_max
  al_target_lref = lrefine_max
  al_lower_lref  = max(lrefine_min, lrefine_max - 2)
  ! CH 区：上限 = lrefine_max/2（不低于 2）
  ch_max_lref = max(lrefine_min, lrefine_max / 2)
  if (ch_max_lref < 2) ch_max_lref = 2
  ! He 区：上限 = lrefine_min（退粗到最粗）
  he_max_lref = lrefine_min

  ! —— ④-b：获取所有活动块列表 ——
  call Grid_getListOfBlocks(ACTIVE_BLKS, blkList, blockCount)

  ! —— ④-c：逐块判断并标记 ——
  do i = 1, blockCount
     lb = blkList(i)

     ! 只处理叶块（非叶块在末尾统一清理）
     if (nodetype(lb) /= LEAF) cycle

     ! 获取块的包围盒
     call Grid_getBlkBoundBox(lb, boundBox)

     ! ★━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━★★
     !  ★ 关键修改：用边界框重叠替代块中心判断 ★
     !  ★ 当目标区域 < 块尺寸时，块中心法失效    ★
     ! ★━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━★
     !
     ! 判断块是否与 Al 靶材区重叠:
     !   Al 区范围: x ∈ [-sim_targHeight, sim_targHeight]
     !   如果块边界与 Al 区间有交集 → Al 约束
     if (boundBox(HIGH, IAXIS) >= -sim_targHeight .and. &
         boundBox(LOW, IAXIS)  <=  sim_targHeight) then

        ! ═══ Al 靶材区 ═══
        !  约束: lref ∈ [lrefine_max-2, lrefine_max]
        if (lrefine(lb) < al_lower_lref) then
           ! 精度不足 → 强制 refine
           refine(lb)   = .true.
           derefine(lb) = .false.
        else if (lrefine(lb) > al_target_lref) then
           ! 超出上限（罕见，安全网）→ 强制 derefine
           refine(lb)   = .false.
           derefine(lb) = .true.
        end if
        ! lref 在范围内 → 保留梯度加密结果

     ! 判断块是否与 CH 泡沫区重叠（且不与 Al 重叠）:
     !   CH 区范围: x ∈ [-sim_polyHeight, sim_polyHeight]
     !   注: 上面已排除 Al 重叠，此处只需检查 CH 重叠即可
     else if (boundBox(HIGH, IAXIS) >= -sim_polyHeight .and. &
              boundBox(LOW, IAXIS)  <=  sim_polyHeight) then

        ! ═══ CH 泡沫区 ═══
        !  约束: lref ≤ lrefine_max/2
        !  应用: 双向 — 不足时 refine, 过度时 derefine
        if (lrefine(lb) < ch_max_lref) then
           ! 精度不足（靠近 Al 边界可能被退粗）→ 确保最低精度
           refine(lb)   = .true.
           derefine(lb) = .false.
        else if (lrefine(lb) > ch_max_lref) then
           ! ❗ 过度细化（梯度在 CH/He 边界误判）→ 强制退粗
           refine(lb)   = .false.
           derefine(lb) = .true.
        end if

     else
        ! ═══ He 填充区 ═══
        !  约束: lref ≤ lrefine_min
        !  只有 derefine 方向，不主动 refine
        if (lrefine(lb) > he_max_lref) then
           refine(lb)   = .false.
           derefine(lb) = .true.
        end if
     end if
  end do

  ! ─────────────────────────────────────────────────────────────────
  ! ⑤ 标准后处理收尾
  ! ─────────────────────────────────────────────────────────────────

  ! —— ⑤-a：PARAMESH2 兼容 ——
#ifdef FLASH_GRID_PARAMESH2
  if (gr_numRefineVars .LE. 0) then
     call gr_markRefineDerefine(-1, 0.0, 0.0, 0.0)
  end if
#endif

  ! —— ⑤-b：粒子计数加密 ——
  if (gr_refineOnParticleCount) call gr_ptMarkRefineDerefine()

  ! —— ⑤-c：最大精度强制 ——
  ! 确保任何块的 refine 层级不超过 gr_maxRefine（安全网）
  if (gr_enforceMaxRefinement) call gr_enforceMaxRefine(gr_maxRefine)

  ! —— ⑤-d：对数半径退粗限制（可选） ——
  if (gr_lrefineMaxRedDoByLogR) &
       call gr_unmarkRefineByLogRadius(gr_lrefineCenterI, &
                                       gr_lrefineCenterJ, gr_lrefineCenterK)

  ! —— ⑤-e：Sink 粒子加密 ——
  call Particles_sinkMarkRefineDerefine()

  ! —— ⑤-f：★ 最关键：非叶块标志清理 ★ ——
  ! 只有 nodetype == LEAF 的块才能被 refine 或 derefine
  ! 父块（有子块的块）如果被标记了 refine，PARAMESH 会崩溃
  where (nodetype(:) .NE. LEAF)
     refine(:)   = .false.
     derefine(:) = .false.
  end where

  return
end subroutine Grid_markRefineDerefine
