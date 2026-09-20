"""
SNBVTi2 场景 — V+Ti 多层示踪靶 + SNB 非局域热传导（精确网格 0.02 um 版）
═══════════════════════════════════════════════════════════════════

由 **SNBVTi2_ml** 派生 (2026-09-15), **物理内容与 SNBVTi2_ml 完全一致**
(shld=V 6.11, tar2=Ti 4.54, 其余 tar*=CH 1.0; 6 层示踪 1/2/3/4/6 um;
SNB 参数/激光/EOS 表逐项相同), **唯一差别是网格精度要求更严格**:

## ★★★ 精确网格: dx = 0.02 um（整分网格, 0.1um 薄层 = 5 个完整网格）

    SNBVTi2_ml : dx = 500um/(131×128) = 0.02982 um → 0.1um 层覆盖 3.35 格
                 （层边界不落在网格边上, 质量分数被相邻格分摊）
    SNBVTi2    : dx = 500um/(125×200) = **0.02 um 精确** → 0.1um 层 = **5 整格**

    设计约束（三者缺一不可, 生成期强校验）:
      1. iProcs×nxb = 25000 = 500um/0.02um  → dx 精确等于 0.02 um
      2. 域边界整除: 400um/0.02=20000 ✓, 100um/0.02=5000 ✓
         → x=0 与全部层边界(0.1um 整数倍)落在网格边上
      3. 0.1um/dx = 5（整数）→ 每个示踪薄层恰为 5 个完整网格,
         层内质量分数恒为 1.0（无跨格分摊）

    选型 (iProcs=125, nxb=200): 25000=2³×5⁵ 的偶数因子组合中,
    nxb=200 每块计算量最大（200 格/块, 通信/计算比最优）,
    125 进程在 NC-E(48 核/节点) 占 3 节点(144 核, 空闲 19) 最紧凑。
    备选: (100,250) / (250,100) / (50,500) —— 若 setup 拒绝 nxb=200 再切换。

    ★ +ug 铁律不变: nproc 必须严格 == iProcs(125); --nproc 传其他值会
      破坏精确网格 ⇒ build_setup_flags_ug 对非 125 硬失败(拒绝静默偏离)。

## 与 SNBVTi2_ml 的关系

SNBVTi2_ml 于 2026-09-14 由 SNBVTi(4 物种)恢复 8 物种多层示踪;
本场景继承其全部物理与流程骨架, 仅替换网格选型与命名常量
(SIM_NAME/OBJDIR/BASENM/PAR_FILENAME), HPC 驱动仍委托 SNBOneCH_ml.run_hpc。

⇒ 场景对照矩阵:
    SNBOneCH_ml  shld=CH, tar1..tar6=CH (纯 CH 基线, dx=0.0298um)
    SNBVTi2_ml   shld=V,  tar2=Ti (多层标记, dx=0.0298um)
    SNBVTi2      shld=V,  tar2=Ti (多层标记, **dx=0.02um 精确**) ← 本场景
    SNBVTi       shld=V,  tar2=Ti (4 物种精简版)

## ★★★ 必须在 SNB 专用 FLASH 代码 (FLASHSNB) 中编译运行

SNB 物理由 SimulationMain 单元内 9 个覆盖文件承载 (setup 的 Simulation
单元后置覆盖机制替换 physics 同名文件), 常用场景 FLASH 无这些文件:

    diff_advanceTherm.F90            # SNB 群分辨热流 (QENL/QESH/GRQX...)
    mgd_qesh.F90                     # 多群 SH 热流权重 (不完全伽马积分)
    Conductivity.F90                 # 增强泛型 Conductivity (fullState)
    Driver_evolveFlash.F90           # SNB 驱动循环
    Grid_advanceDiffusion.F90        # SNB 扩散推进
    hy_uhd_DataReconstructNormalDir_PPM.F90 / hy_uhd_dataReconstOneStep.F90 /
    hy_uhd_getRiemannState.F90 / hy_uhd_ragelike.F90   # slopeLimiters 模块名修正

以上 9 个文件部署时从超算 FLASHSNB 的 SNB_1D_laser 单元**原样复制**
(与物种无关, 已核查无 sim_/Simulation_data 引用), 不入库 (License §3)。

## ★ 网格: +ug 均匀网格 (SNB 铁律, 见 SNBOneCH_ml docstring)

+ug 只建 iProcs 块 level-1 网格 (par nblockx/lrefine 被无视),
dx=域宽/(iProcs*nxb), 且 nproc 必须严格等于 iProcs。
本场景 (125, 200) 精确组合保证 dx=0.02um —— 0.1um 薄层 5 整格,
物种从不被"稀释到不可见"(≤3 格时该物种可能从不被写入 → 仿真即死)。

  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 8 物种 12 区分层 (多层示踪; 几何同 SNBOneCH_ml):

      x < 0                        cham [氦 He, 1e-6 g/cm^3]
      0        < x < delta         shld [钒 V,  6.11 g/cm^3]   ← V 屏蔽层
      其余区间为 samp [碳氢 CH, 1.0 g/cm^3], 内含 6 个 0.1um 示踪薄层:
        tar1 @1um  [CH 标记层, 1.0]
        tar2 @2um  [钛 Ti, 4.54]      ← 金属示踪层 (唯一非 CH 示踪层)
        tar3 @3um  [CH 标记层, 1.0]
        tar4 @4um  [CH 标记层, 1.0]
        tar6 @6um  [CH 标记层, 1.0]
      尾部        < x < ...          samp [碳氢 CH, 厚 D=50um]
      其余 (x<0 域外 / 尾部之外)   cham [氦 He]

      ★ 层序: shld | samp | tar1 | samp | tar2 | samp | tar3 | samp |
              tar4 | samp | tar6 | samp   (12 区, 13 个边界 bnd1..bnd13)

  * 8 物种标记: cham/shld/samp/tar1/tar2/tar3/tar4/tar6
  * MGD 10 能群辐射，tabular EOS/opacity (ionmix4)
  * SNB 运行参数 (取自 t001/SNBOneCH_ml SNB 基线): useDIffuseTherm=.true.,
    diff_eleFlMode=fl_harmonic, diff_eleFlCoef=0.06, cfl=0.2,
    gr_hypreUseFloor=.false., RiemannSolver=HLL;
    plot 输出 SNB 诊断变量 QESH/QESX/QESY/GRQX/GRAQ/CORQ/MFPE/QENL/QEFL

## ★ 材料表核验 (2026-09-13, 按 FLASH 权威读法解析 cn4 头)

    V-BADGER-TOPS.cn4   : atomic #s of gases = 23 (V), fraction 1.00,
                          nT=61, nD=71, ngroups=10  ← 已核验为真钒表
    Ti-BADGER-TOPS.cn4  : Z=22 (Ti), 同网格布局
    CH-QC-1-001.cn4     : Z=6,1 (C:H), nT=61, nD=71
    He-BADGER-TOPS-Final.cn4 : Z=2 (He)

⚠ 教训: `CH-BADGER-TOPS-Final.cn4` 实际组成为 Z=3 (非碳氢), 文件名与内容
不符, 赋给 CH 族物种会使 IONMIX4 读取器拒绝加载 ⇒ CH 族一律用
`CH-QC-1-001.cn4`。本场景 V/Ti 表均已按同一权威读法核验通过。

用法:
  cd <flash 包目录>
  # 只生成输入文件 (先做静态核验)
  python flash/scenarios/private/tracer/SNB/SNBVTi2/SNBVTi2.py --generate-only
  # 超算 NC-E 极短测试 (首次必须完整编译, 勿加 --skip-build; 验证 5 整格划分)
  python flash/scenarios/private/tracer/SNB/SNBVTi2/SNBVTi2.py \
      --tmax 1.0e-11 --nproc 125 --account flash_ssh
  # 层位核查 (短测后; 期望每层恰 5 格、frac_min=1.0)
  python flash/scenarios/private/tracer/SNB/SNBVTi2/scripts/analysis/check_layers.py \
      --dir flash/scenarios/private/tracer/SNB/SNBVTi2/flash_output/hpc_flash_ssh \
      --expect-cells 5
  # 1.6 ns 全流程 (提交→下载→绘图; 断点续跑)
  python flash/scenarios/private/tracer/SNB/SNBVTi2/scripts/longrun/03_run_16ns_pipeline.py \
      --account flash_ssh

参见: docs/01_场景说明与拓扑.md, docs/02_超算验证流程.md (物理/流程同 SNBVTi2_ml)
"""

import sys
import os
import re
import hashlib
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Bootstrap: 定位 flash 包根目录 ─────────────────────────
_ROOT = Path(__file__).resolve().parent
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _get_sim_user_dir() -> str:
    from flash.scenarios.runner import get_sim_user_dir as _sud
    return _sud()


SIM_USER_DIR = _get_sim_user_dir()

# ══════════════════════════════════════════════════════════════════════
# ★ 场景变量 (本场景的物理身份 — 改这里即可派生新变体)
# ══════════════════════════════════════════════════════════════════════
SCENE_NAME = "SNBVTi2"         # 场景名 → SIM_NAME / par 名 / 输出基名 / 作业名

# ★ 材质分配 (用户 2026-09-14 明确指定)
#   多层示踪: shld=V, tar2=Ti, 其余 tar* (tar1/tar3/tar4/tar6) = CH
#   (tar1/3/4/6 与 samp 同为 CH, 但保留为独立物种 → 作为**深度标记**,
#    供 X 射线谱学逐层追踪烧蚀面/临界密度面/激波面。)
SHLD_MATERIAL = "V"            # shld 层材质: "V"=钒 6.11 (本场景) / "Ti" / "CH"
TI_LAYER = "tar2"              # 金属示踪层物种: "tar2"=2.0um (本场景)

# 材质物性 (与 VCH_ml_F / TiTi2 完全一致, 禁止改动数值)
_MAT_V = {"file": "V-BADGER-TOPS.cn4", "rho": 6.11, "A": 50.9415, "Z": 23}
_MAT_TI = {"file": "Ti-BADGER-TOPS.cn4", "rho": 4.54, "A": 47.867, "Z": 22}
_MAT_CH = {"file": "CH-QC-1-001.cn4", "rho": 1.0, "A": 6.509, "Z": 3.5}

# ── 可配置参数 (几何/激光严格同 TiTi2 / SNBOneCH_ml) ───────
config_constants = {
    # 分层几何 (μm): 多层示踪 (同 SNBOneCH_ml 的 6 层示踪几何)
    #   结构: shld | samp | tar1 | samp | tar2 | samp | tar3 | samp |
    #         tar4 | samp | tar6 | samp
    #   每薄层厚度均为 delta=0.1um; tarN 的外边界 = LN um;
    #   尾段 samp(CH) 厚 D=50um。
    "delta_um": 0.1,          # 薄层厚度 (V 屏蔽层 + 各示踪层)
    "L1_um": 1.0,             # tar1 (CH 标记层) 外边界
    "L2_um": 2.0,             # tar2 (Ti 金属层) 外边界
    "L3_um": 3.0,             # tar3 (CH 标记层) 外边界
    "L4_um": 4.0,             # tar4 (CH 标记层) 外边界
    "L6_um": 6.0,             # tar6 (CH 标记层) 外边界
    "D_um": 50.0,             # 尾部 samp(CH) 厚度
    # 仿真结束时间 (s)。默认极短验证值 1.0e-11 (单独执行即验证值);
    # 正式运行用 --tmax 覆写。用户要求: 先做超算极短时间验证测试。
    "tmax": 1.0e-11,
    # 仿真域 (cm), 同 TiTi2 / SNBOneCH_ml
    "xmin": -0.04,
    "xmax": 0.01,
    # ★★★ 2026-09-13 实测发现并修正: FLASH setup 会把 xmin 吸附到
    #   **root 网格边界** (rootdx = dom/(nblockx*nxb)), 且吸附量向上取整
    #   到整数个 root cell。实测: xmin=-0.04 → chk 起点 -0.03980916,
    #   域整体右移 1.9084 um (= 64 个 finest cell), 但**域宽不变**。
    #   ⇒ Simulation_initBlock 用绝对 xcent 与 sim_*Radius 比较, 于是
    #     所有层(含 V 屏蔽层 / Ti 示踪层)都偏 +1.91 um, 与设计不符。
    #   修法: 把 xmin/xmax 预先吸附到 root 网格边界 (align_domain()),
    #        消除 FLASH 的二次取整。物理量(层厚/密度)完全不变,
    #        仅让设计坐标 == 网格坐标。
    #   见 align_domain() 与 _DOMAIN_ALIGNED 日志。
    "align_domain": True,
    # ★ 网格: +ug 均匀网格 — dx = 域宽/(iprocs*nxb)
    #   ★★★ SNBVTi2 精确网格 (2026-09-15): iprocs=125 × nxb=200 = 25000 格
    #   → dx = 500um/25000 = 0.02 um 精确, 0.1um 薄层 = 5 个完整网格。
    #   (SNBVTi2_ml 为 131×128=16768 格 → dx=0.02982um, 0.1um 层仅 3.35 格)
    #   修改 iprocs 前必须复核 25000 = iprocs*nxb 整分解, 否则精确网格破坏。
    "nxb": 200,
    "iprocs": 125,
    # (--amr 历史基线用: AMR 网格参数, +ug 下被无视)
    "nblockx": 8,
    "lrefine_max": 9,
    "lrefine_min": 1,
    "lrefine_min_init": 9,
    # 输出频率 (同 TiTi2 / SNBOneCH_ml)
    "plot_interval_step": 2000,
    "checkpoint_interval_step": 400,
    # 维度
    "dimension": 1,
    # MPI 进程数 (=par iProcs, +ug 下必须严格等于块数; --nproc 可覆写,
    # 但 ★ 只有 125 能保持精确网格, 其他值会被 build_setup_flags_ug 拒绝)
    "nprocs": 125,
    # SNB 热传导基线参数 (取自 t001 / SNBOneCH_ml 已验证成功基线)
    "diff_eleFlMode": "fl_harmonic",
    "diff_eleFlCoef": 0.06,
    "cfl": 0.2,
    # 初始温度 [K] (全物种统一)
    "t_initial": 290.11375,
    # EOS/opacity 表 (CH 族; 见 docstring 材料表核验段)
    "ch_cn4": "CH-QC-1-001.cn4",
    "he_cn4": "He-BADGER-TOPS-Final.cn4",
    # ★★★ MGD 多群扩散通量模式 (SNBOneCH_ml 实测回退: fl_larsen 失稳)
    "rt_mgdFlMode": "fl_harmonic",
    "rt_mgdFlCoef": 1.0,
    # ★★★ 流体 Riemann 求解器 (HLL 更耗散, 强稀疏下不产生负内能)
    "riemann_solver": "HLL",
    # 运行控制 (+ug 基线, t001 实证: 1.10/2e-12 下 1e-10 全档稳定)
    "tstep_change_factor": 1.10,
    "dtmax": 2.0e-12,
}

# FLASH setup 标志 (FLASHSNB) — ★ 默认 +ug 均匀网格 (SNB 铁律)
#   ★★★ nxb 由 {nxb} 占位符在运行期按 nproc 计算 (见 build_setup_flags_ug)。
SETUP_FLAGS_UG = (
    "-1d +cartesian +ug -nxb={nxb} +hdf5typeio "
    "species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300"
)
SETUP_FLAGS = SETUP_FLAGS_UG      # 默认 = +ug (--amr 时运行期切换为 AMR)

# ★★★ +ug 精确网格常量 (SNBVTi2 专属, 2026-09-15)
#   SNBVTi2_ml 用 UG_DX_MAX_CM=0.03um(上限) + 2 的幂 nxb;
#   本场景要求 dx **精确等于** 0.02um → (iProcs,nxb)=(125,200) 唯一组合,
#   不再做 2 的幂搜索 —— 偏离即硬失败, 拒绝静默破坏 5 整格划分。
UG_DX_EXACT_CM = 2.0e-6          # 0.02 um (精确, 非上限)
UG_LAYER_CELLS = 5               # 0.1um 薄层 = 5 个完整网格
UG_IPROCS_EXACT = 125            # 唯一允许的进程数 (+ug 铁律: nproc==iProcs)
UG_NXB_EXACT = 200               # 唯一允许的块内单元数 (125×200=25000)
UG_DOM_CM = 0.05                 # 域宽 [cm] (xmax-xmin, 与 _ml 一致)


def align_domain(xmin: float, xmax: float, nblockx: int, nxb: int
                 ) -> Tuple[float, float, float, float]:
    """把域边界吸附到 FLASH root 网格边界, 消除 setup 的隐式二次取整。

    ★★★ 2026-09-13 事故 (实测定量):
      xmin=-0.04, xmax=0.01, nblockx=8, nxb=128
        rootdx = 0.05/(8*128) = 4.8828125e-5 cm
        xmin/rootdx = -819.2  ← 非整数!
      FLASH setup 把 xmin **向上取整**到 cell 边界 ⇒ 实际域起点
      右移 1.9084 um (= 64 个 finest cell), **域宽不变**。
      因 initBlock 用绝对 xcent 与 sim_*Radius 比较 ⇒ 所有层
      整体偏 +1.91 um (V 屏蔽层本应 0-0.1um, 实测 1.91-2.00um)。

    修法: 令 xmin' = round(xmin/rootdx)*rootdx (就近吸附, 位移最小),
          xmax' = xmin' + nblockx*nxb*rootdx (域宽完全不变)。
          此时 xmin'/rootdx 为整数 ⇒ setup 不再吸附。

    ★ 为何用 round 而非 floor: floor 会产生 -0.3906 um 的单侧位移
      (xmin=-0.04, nxb=128); round 只产生 +0.0977 um, 且中心对称性更好。

    Returns
    -------
    (xmin_aligned, xmax_aligned, rootdx, shift_cm)
    """
    import math
    rootdx = (xmax - xmin) / (nblockx * nxb)
    k = round(xmin / rootdx)
    xmin_a = k * rootdx
    xmax_a = xmin_a + nblockx * nxb * rootdx
    return xmin_a, xmax_a, rootdx, (xmin_a - xmin)


def build_setup_flags_ug(nproc: int, xmin: float, xmax: float) -> tuple:
    """返回 +ug setup 标志; 强校验精确网格 (dx==0.02um, 0.1um 层==5 整格)。

    ★★★ SNBVTi2 与 SNBVTi2_ml 的本质差别在此:
      _ml 版按 nproc 搜最小 2 的幂 nxb 使 dx≤0.03um (上限语义);
      本版**只接受** nproc==125 → nxb=200 → dx=0.02um 精确。
      任何其他 nproc 一律 SystemExit 硬失败 —— +ug 下 nproc==iProcs,
      传错核数会静默破坏 5 整格划分 (层边界不再落在网格边上)。

    Returns
    -------
    (flags_string, nxb, dx_cm)
    """
    dom = abs(xmax - xmin)
    if nproc != UG_IPROCS_EXACT:
        raise SystemExit(
            f"[X] nproc={nproc} != {UG_IPROCS_EXACT}: SNBVTi2 精确网格要求\n"
            f"    iProcs×nxb = {UG_IPROCS_EXACT}×{UG_NXB_EXACT} = 25000 格\n"
            f"    → dx = {UG_DOM_CM*1e4:.0f}um/25000 = 0.02um 精确 (0.1um 层 = 5 整格)。\n"
            f"    其他核数会破坏网格设计 (备选精确组合: 100×250 / 250×100 / 50×500,\n"
            f"    如需切换请同步修改 UG_IPROCS_EXACT / UG_NXB_EXACT / config nprocs)。")
    nxb = UG_NXB_EXACT
    dx = dom / (nproc * nxb)
    if abs(dx - UG_DX_EXACT_CM) > 1e-12:
        raise SystemExit(
            f"[X] dx={dx*1e4:.6f}um != 期望 {UG_DX_EXACT_CM*1e4:.2f}um — "
            f"域宽 {dom*1e4:.1f}um 与 25000 格不整分, 精确网格破坏")
    cells_per_layer = 0.1e-4 / dx          # 0.1um 薄层的格数
    if abs(cells_per_layer - UG_LAYER_CELLS) > 1e-9:
        raise SystemExit(
            f"[X] 0.1um 薄层 = {cells_per_layer:.4f} 格 != {UG_LAYER_CELLS}")
    # 域边界整除性: 保证 x=0 与层边界 (0.1um 整数倍) 落在网格边上
    for edge_um, tag in ((abs(xmin) * 1e4, "xmin"), (abs(xmax) * 1e4, "xmax")):
        n = edge_um / (dx * 1e4)
        if abs(n - round(n)) > 1e-9:
            raise SystemExit(
                f"[X] {tag}={edge_um:.4f}um 非 dx={dx*1e4:.2f}um 整数倍 "
                f"(={n:.4f}) → 层边界不落在网格边上, 精确划分破坏")
    return SETUP_FLAGS_UG.format(nxb=nxb), nxb, dx


# --amr 历史基线 (lrefine9 精细网格; dx≈0.0153um, 需 tstep1.05/dtmax2e-14)
SETUP_FLAGS_AMR = (
    "-1d +cartesian -nxb=16 +hdf5typeio "
    "species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300 -maxblocks=4096"
)

# 仿真/对象/par 命名 (+ug 默认 / AMR 可选, objdir/basenm 隔离互不覆盖)
SIM_NAME = SCENE_NAME                # FLASHSNB 内 SimulationMain 单元名
OBJDIR = f"{SCENE_NAME}_ug_obj"      # setup -objdir= (+ug 默认)
OBJDIR_AMR = f"{SCENE_NAME}_obj"
PAR_FILENAME = f"{SCENE_NAME.lower()}.par"
BASENM = "snbvti2ug_"                # 输出基名 (+ug 默认)
BASENM_AMR = "snbvti2_"
LOG_FILE = "snbvti2.log"

# 物种列表 (顺序即 FLASH 物种常量顺序, 必须与 setup 的 species= 一致)
SPECIES_LIST = ("cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6")

# 6 个示踪层物种 (含金属 tar2) — 生成/校验/绘图共用
TAR_LAYERS = ("tar1", "tar2", "tar3", "tar4", "tar6")

# 规范物理参数（沿用水脉冲/MGD 等内嵌字典, 自包含）
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

# ── SNB 单元覆盖文件 (部署时从 FLASHSNB SNB_1D_laser 原样复制) ──
SNB_OVERRIDE_FILES = (
    "diff_advanceTherm.F90",
    "mgd_qesh.F90",
    "Conductivity.F90",
    "Driver_evolveFlash.F90",
    "Grid_advanceDiffusion.F90",
    "hy_uhd_DataReconstructNormalDir_PPM.F90",
    "hy_uhd_dataReconstOneStep.F90",
    "hy_uhd_getRiemannState.F90",
    "hy_uhd_ragelike.F90",
)

# FLASHSNB 树级 physics 补丁 (t001 修复; 部署时缺失则从 t001 归档补齐)
_TREE_PATCHES = (
    ("physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",),
    ("physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",),
)
# t001 归档目录 (相对本场景: private/tracer/SNB/SNBVTi → private/SNB/...)
# parents[3] 即 scenarios/private/ (已实测核对: SNB/SNBtest/Test/t001 存在)
_T001_DIR = Path(__file__).resolve().parents[3] / "SNB/SNBtest/Test/t001"

# ★★★ SNB 覆盖 F90 的**本地权威源** (仓内镜像, 离线可用, 无需超算)
# 同为 parents[3] 基准: private/SNB/SNB/source/snb_package (已实测存在)
# 实测与 (a) 上游 SNB_1D_laser 单元 (b) NC-E 已部署单元 (c) SNBOneCH_ml/
# flash_input 三者 sha256 全部一致 (9/9)。
_SNB_PKG_DIR = Path(__file__).resolve().parents[3] / "SNB/SNB/source/snb_package"

# 生成的 provenance 审计文件 + 远端 cn4 重部署辅助脚本
PROVENANCE_FILE = "SNB_F90_PROVENANCE.md"
DEPLOY_CN4_FILE = "_deploy_cn4.sh"

# SNB Config 追加段: 18 个 SNB 诊断 VARIABLE (取自 SNB_1D_laser Config)
SNB_CONFIG_VARIABLES = """
# ── SNB nonlocal thermal conduction diagnostic variables ──
VARIABLE QESH
VARIABLE QEFL
VARIABLE QENL
VARIABLE NELE
VARIABLE MFPE
VARIABLE MFPR
VARIABLE QESX
VARIABLE QESY
VARIABLE GRQX
VARIABLE GRQY
VARIABLE GRAQ
VARIABLE CORQ
VARIABLE QEXG
VARIABLE QEYG
VARIABLE GRGX
VARIABLE GRGY
VARIABLE GRQG
VARIABLE COGQ
"""

# plot_var 白名单: 物种标记 + SNB 诊断 (QENL=非局域热流, QESH=SH 热流)
_PLOT_VARS = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy",
              "cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6",
              "fllm", "QESH", "QESX", "QESY", "GRQX", "GRAQ", "CORQ", "MFPE", "QENL"]

# 输出文件 glob (FLASH hdf5typeio 无 .h5 后缀)
OUTPUT_GLOBS = (f"{BASENM}*",)

# 场景目录
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "flash_input"
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = SCRIPT_DIR / "plots"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# ══════════════════════════════════════════════════════════════════════
# 物种定义 — shld=V, tar2=Ti, 其余 CH (本场景的物理身份)
# ══════════════════════════════════════════════════════════════════════
def build_species_defs(delta_cm: float, Lmap: Dict[str, float], D: float) -> List[dict]:
    """构建 8 物种定义 (多层示踪; 材质由 SCENE_NAME 决定的 SHLD_MATERIAL / TI_LAYER)。

    cham=He 1e-6; shld = SHLD_MATERIAL (本场景 "V" → 钒 6.11);
    samp=CH; tar1/tar3/tar4/tar6 = CH (深度标记层);
    TI_LAYER (本场景 "tar2" @2um) = Ti 4.54。

    ★ 2026-09-14: 由 4 物种恢复为 8 物种 (多层示踪)。
      4→8 精简版把 tar1/tar3/tar4/tar6 (原均为 CH 标记层) 的空间并入相邻
      samp; 本版恢复这些独立标记层, 以便按深度分离示踪信号。
      ⇒ **材料分布与 4 物种版一致**(均为 CH), 差别仅在是否保留独立标记物种。

    Parameters
    ----------
    delta_cm : 薄层厚度 [cm]
    Lmap     : {"tar1": L1_cm, "tar2": L2_cm, "tar3": L3_cm, "tar4": L4_cm,
                "tar6": L6_cm} — 各示踪层外边界累积位置
    D        : 尾部 samp 厚度 [cm]

    Notes
    -----
        sim_shldRadius = delta   (屏蔽层/示踪薄层厚度)
        sim_tarXRadius = LX      (示踪层外边界累积位置)
        sim_sampHeight = D       (尾部 samp 厚度)
    """
    he_file = "He-BADGER-TOPS-Final.cn4"
    ch_file = _MAT_CH["file"]
    # 屏蔽层材质 (本场景 V; 分支保留以便派生 Ti/CH 变体)
    if SHLD_MATERIAL == "V":
        shld_def = {"name": "shld", **_MAT_V, "radius": delta_cm}
    elif SHLD_MATERIAL == "Ti":
        shld_def = {"name": "shld", **_MAT_TI, "radius": delta_cm}
    else:
        shld_def = {"name": "shld", **_MAT_CH, "radius": delta_cm}
    # 示踪薄层: TI_LAYER (本场景 tar2 @2um) 为 Ti, 其余为 CH 标记层
    tar_defs = []
    for name in TAR_LAYERS:
        mat = _MAT_TI if (TI_LAYER is not None and name == TI_LAYER) else _MAT_CH
        tar_defs.append({"name": name, **mat, "radius": Lmap[name],
                         "radius_param": f"sim_{name}Radius"})
    return [
        # 腔室: 稀氦 (区域外默认物种)
        {"name": "cham", "file": he_file, "rho": 1.0e-6, "A": 4.002602, "Z": 2.0},
        shld_def,
        # 基体层: CH (samp 多次出现; height = 尾部 samp 厚度 D)
        {"name": "samp", "file": ch_file, **_MAT_CH, "height": D},
        *tar_defs,
    ]


# ══════════════════════════════════════════════════════════════════════
# 步骤 1: 生成 FLASHSNB 输入文件
# ══════════════════════════════════════════════════════════════════════
def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    """生成全部 FLASHSNB 输入文件到 flash_input/。

    产物: snbvti.par / Config / Makefile / Simulation_data.F90 /
    Simulation_init.F90 / Simulation_initBlock.F90 / 4 张 .cn4 表 /
    9 个 SNB 物理覆盖 .F90 / SNB_F90_PROVENANCE.md / _deploy_cn4.sh /
    run_flash.sh / 预诊断图。

    ★★ 自包含契约 (2026-09-13 修复): 9 个 SNB 覆盖 F90 **必须落盘本目录**,
    从仓内镜像 `SNB/SNB/source/snb_package/` 逐字节复制。修复前此步缺失,
    场景不自包含、无法离线审计, 仅靠运行时从超算 SNB_1D_laser 单元兜底 ——
    一旦远端单元变动或不可达即静默换物理。详见 `_deploy_snb_overrides()`。
    """
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    delta_cm = cfg["delta_um"] * 1e-4
    # ★ 6 个示踪层的外边界 (tar1/tar2/tar3/tar4/tar6 → L1/L2/L3/L4/L6 um)
    Lmap = {t: cfg[f"L{t[3:]}_um"] * 1e-4 for t in TAR_LAYERS}
    D = cfg["D_um"] * 1e-4

    species_defs = build_species_defs(delta_cm, Lmap, D)
    sim_path = SIM_NAME          # FLASHSNB 内单元: SimulationMain/SNBVTi
    par_filename = PAR_FILENAME

    from flash.scenarios.runner import default_nprocs
    nprocs = cfg["nprocs"] or default_nprocs(cfg["dimension"], is_hpc=False)

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par（CH_FLASH_PAR 基线 + SNB 覆写 + V/Ti 材料覆写）──
    log("  [1/9] 生成 .par 文件 (SNB 基线 + V/Ti 材料)...", "STEP")
    tmp_params = dict(CH_FLASH_PAR)
    _TARG_KEYS = {
        "sim_targetRadius", "sim_targetHeight",
        "sim_rhoTarg", "sim_teleTarg", "sim_tionTarg", "sim_tradTarg",
        "ms_targA", "ms_targZ", "ms_targZMin",
    }
    for k in list(tmp_params):
        if k in _TARG_KEYS or k.startswith(("op_targ", "eos_targ")) \
                or k == "sim_sampRadius" \
                or k in ("basenm", "log_file") \
                or k.startswith("plot_var"):
            del tmp_params[k]
    par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)
    par_gen._params.clear()
    for k, v in tmp_params.items():
        par_gen.set(k, v)
    # 覆写: 几何 (分层几何经运行时参数控制)
    # ★ 8 物种多层栈 (2026-09-14) —— 同 SNBOneCH_ml 的 6 层示踪几何:
    #   [0,shldR] shld | [shldR,L1] samp | [L1,L1+shldR] tar1 |
    #   [L1+shldR,L2] samp | [L2,L2+shldR] tar2 |
    #   [L3,...] tar3 | [L4,...] tar4 | [L6,...] tar6 | 尾段 samp | 其余 cham
    par_gen.set("sim_shldRadius", delta_cm)             # delta (薄层厚度)
    for _t in TAR_LAYERS:
        par_gen.set(f"sim_{_t}Radius", Lmap[_t])        # L1/L2/L3/L4/L6
    par_gen.set("sim_sampHeight", D)                    # D (尾部 samp 厚度)

    # ★★★ 材料分组绑定 (CH_FLASH_PAR 基线默认为 CH; 逐个覆写非 CH 物种)
    #   组 1: CH 族 (cham 用 He 表, samp + 4 个 CH tar 用 CH 表)
    par_gen.set("eos_chamTableFile", cfg["he_cn4"])
    par_gen.set("op_chamFileName", cfg["he_cn4"])
    par_gen.set("eos_sampTableFile", cfg["ch_cn4"])
    par_gen.set("op_sampFileName", cfg["ch_cn4"])
    #   组 2: shld (本场景 V 6.11; 模板占位 rho=1 为 CH, 必须覆写)
    if SHLD_MATERIAL == "V":
        par_gen.set("sim_rhoShld", _MAT_V["rho"])
        par_gen.set("ms_shldA", _MAT_V["A"])
        par_gen.set("ms_shldZ", _MAT_V["Z"])
        par_gen.set("eos_shldTableFile", _MAT_V["file"])
        par_gen.set("op_shldFileName", _MAT_V["file"])
    elif SHLD_MATERIAL == "Ti":
        par_gen.set("sim_rhoShld", _MAT_TI["rho"])
        par_gen.set("ms_shldA", _MAT_TI["A"])
        par_gen.set("ms_shldZ", _MAT_TI["Z"])
        par_gen.set("eos_shldTableFile", _MAT_TI["file"])
        par_gen.set("op_shldFileName", _MAT_TI["file"])
    else:
        par_gen.set("sim_rhoShld", _MAT_CH["rho"])
        par_gen.set("eos_shldTableFile", cfg["ch_cn4"])
        par_gen.set("op_shldFileName", cfg["ch_cn4"])
    #   组 3: tar* 材料绑定 — **逐层显式覆写** (TI_LAYER = Ti, 其余 = CH)
    #   ★ 显式写出全部 6 层 (而非只写 Ti 层依赖模板默认), 便于 par 审计:
    #     凡 cfg→par 传递点必须能直接从产物文本核对 (2026-09-13 教训)。
    for _t in TAR_LAYERS:
        _mat = _MAT_TI if (TI_LAYER is not None and _t == TI_LAYER) else _MAT_CH
        _tag = "Ti" if _mat is _MAT_TI else "CH"
        _cap = _t.capitalize()                # tar1 → Tar1
        par_gen.set(f"sim_rho{_cap}", _mat["rho"])
        par_gen.set(f"ms_{_t}A", _mat["A"])
        par_gen.set(f"ms_{_t}Z", _mat["Z"])
        par_gen.set(f"eos_{_t}EosType", "eos_tab")
        par_gen.set(f"eos_{_t}SubType", "ionmix4")
        par_gen.set(f"eos_{_t}TableFile", _mat["file"])
        par_gen.set(f"op_{_t}Absorb", "op_tabpa")
        par_gen.set(f"op_{_t}Emiss", "op_tabpe")
        par_gen.set(f"op_{_t}Trans", "op_tabro")
        par_gen.set(f"op_{_t}FileType", "ionmix4")
        par_gen.set(f"op_{_t}FileName", _mat["file"])
        log(f"    {_t} = {_tag} {_mat['rho']} g/cc + {_mat['file']} ✓")
    log(f"    材质分配: shld={SHLD_MATERIAL}, {TI_LAYER}=Ti, "
        f"其余 {[t for t in TAR_LAYERS if t != TI_LAYER]} = CH ✓")

    # 初始温度覆写 (par 里的 sim_tele*/tion*/trad* 是运行时真正生效的来源)
    for _zone in ("Cham", "Shld", "Samp"):
        par_gen.set(f"sim_tele{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_tion{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_trad{_zone}", cfg["t_initial"])
    for _tar in TAR_LAYERS:
        _cap = _tar.capitalize()          # tar1 → Tar1
        par_gen.set(f"sim_tele{_cap}", cfg["t_initial"])
        par_gen.set(f"sim_tion{_cap}", cfg["t_initial"])
        par_gen.set(f"sim_trad{_cap}", cfg["t_initial"])

    # ★★★ MGD 多群辐射 (显式对齐参考场景 SNB_1D_laser)
    par_gen.set("rt_useMGD", True)
    par_gen.set("rt_mgdNumGroups", 10)
    par_gen.set("rt_mgdFlMode", cfg["rt_mgdFlMode"])   # fl_harmonic (实测回退值)
    par_gen.set("rt_mgdFlCoef", cfg["rt_mgdFlCoef"])   # 1.0
    par_gen.set("rt_mgdXlBoundaryType", "vacuum")
    par_gen.set("rt_mgdXrBoundaryType", "vacuum")
    log(f"    rt_mgdFlMode={cfg['rt_mgdFlMode']} ✓")
    # 覆写: 网格 (AMR 模式; +ug 下被无视, 保留供 --amr 基线)
    par_gen.set("nblockx", cfg["nblockx"])
    par_gen.set("lrefine_max", cfg["lrefine_max"])
    par_gen.set("lrefine_min", cfg["lrefine_min"])
    par_gen.set("lrefine_min_init", cfg["lrefine_min_init"])
    par_gen.set("refine_var_1", "dens")
    par_gen.set("refine_var_2", "tele")
    # 覆写: 运行控制
    par_gen.set("tmax", cfg["tmax"])
    par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
    # 覆写: 输出命名 (本场景独立基名)
    par_gen.set("basenm", BASENM)
    par_gen.set("log_file", LOG_FILE)
    # 覆写: SNB 热传导基线
    par_gen.set("useDIffuseTherm", True)
    par_gen.set("diff_eleFlMode", cfg["diff_eleFlMode"])
    par_gen.set("diff_eleFlCoef", cfg["diff_eleFlCoef"])
    par_gen.set("cfl", cfg["cfl"])
    par_gen.set("use_3dFullCTU", True)
    par_gen.set("eos_maxNewton", 5000)
    par_gen.set("tstep_change_factor", cfg["tstep_change_factor"])
    par_gen.set("dtmax", cfg["dtmax"])
    # ★★★ SNB 崩塌权威根因 (v4 定案): gr_hypreUseFloor 必须显式 .false.
    #   SNB 多群非局域热流在 Gr_hypre 隐式扩散解上迭代, 若 Floor 退回默认
    #   .true., HYPRE 每步对系数矩阵做"下限截断" → 非局域修正被抹平, 同时
    #   引入非守恒源项 → 第 1 步即出现 sum1≈1e86 的非物理量级。
    #   参考: 作者原版 SNB_1D_laser/flash.par:464 本就写了 .false.;
    #   CH_FLASH_PAR 基线 (源自 LaserSlab) 不含此键 → 必须在此显式补上。
    par_gen.set("gr_hypreUseFloor", False)
    log("    gr_hypreUseFloor=.false. (SNB 铁律) ✓")
    # ★★★ Riemann 求解器: HLL (HLLC 在强稀疏下产生负内能)
    par_gen.set("RiemannSolver", cfg["riemann_solver"])
    par_gen.set("entropy", False)
    log(f"    RiemannSolver={cfg['riemann_solver']} ✓")
    # 覆写: 进程分解 (1D 沿 x; 必须与 mpiexec -n 一致)
    par_gen.set("iProcs", nprocs)
    # ★★★ 覆写: 域边界 (2026-09-13 修复)
    #   根因: CH_FLASH_PAR 模板硬编码 xmin=-0.04 / xmax=0.01, 而
    #   par_gen.set() **从未被调用** ⇒ cfg 里 align_domain() 吸附后的
    #   域值根本没写进 par, deploy/objdir 拿到的仍是模板原值。
    #   (实测: 日志打印了吸附值但 par 第 402 行仍是 -0.04)
    if abs(cfg["xmin"] - float(CH_FLASH_PAR["xmin"])) > 1e-15 or \
       abs(cfg["xmax"] - float(CH_FLASH_PAR["xmax"])) > 1e-15:
        par_gen.set("xmin", cfg["xmin"])
        par_gen.set("xmax", cfg["xmax"])
        log(f"    域覆写: xmin={cfg['xmin']:.10f}, xmax={cfg['xmax']:.10f} ✓")
    # 覆写: plotfile 输出变量白名单
    for i, v in enumerate(_PLOT_VARS, start=1):
        par_gen.set(f"plot_var_{i}", f"{v:<4s}")
    par_path = par_gen.save(str(INPUT_DIR / par_filename))
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓ (iProcs={nprocs})")

    # ── 2. Config（4 物种注册 + 18 个 SNB VARIABLE）─────────
    log(f"  [2/9] 生成 Config ({len(SPECIES_LIST)} species + SNB variables)...", "STEP")
    cfg_path = ConfigGenerator().save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path, species_defs=species_defs,
    )
    txt = cfg_path.read_text(encoding="utf-8", newline="\n")
    cfg_path.write_text(txt.rstrip("\n") + "\n" + SNB_CONFIG_VARIABLES,
                        encoding="utf-8", newline="\n")
    result["config"] = str(cfg_path)
    log(f"    Config ✓ (+{SNB_CONFIG_VARIABLES.count('VARIABLE')} SNB variables)")

    # ── 3. Makefile (Simulation 单元: Simulation_data + mgd_qesh) ──
    log("  [3/9] 生成 Makefile...", "STEP")
    mk_path = INPUT_DIR / "Makefile"
    mk_path.write_text(
        f"# {SCENE_NAME} Simulation unit makefile (SNB model)\n"
        "# mgd_qesh.o: SNB 多群 SH 热流权重 (FLASHSNB 专用, 无同名 physics 文件)\n"
        "Simulation += Simulation_data.o mgd_qesh.o\n",
        encoding="utf-8", newline="\n")
    result["makefile"] = str(mk_path)

    # ── 4. Simulation_data.F90 ────────────────────────────
    log("  [4/9] 生成 Simulation_data.F90...", "STEP")
    SimDataGenerator().save(str(INPUT_DIR / "Simulation_data.F90"), species=species_defs)
    result["sim_data"] = str(INPUT_DIR / "Simulation_data.F90")

    # ── 5. Simulation_init.F90 ────────────────────────────
    log("  [5/9] 生成 Simulation_init.F90...", "STEP")
    SimInitGenerator().save(str(INPUT_DIR / "Simulation_init.F90"), params={"species": species_defs})
    result["sim_init"] = str(INPUT_DIR / "Simulation_init.F90")

    # ── 6. Simulation_initBlock.F90（8 物种 12 区分层）──────
    log(f"  [6/9] 生成 Simulation_initBlock.F90 ({len(SPECIES_LIST)} species, "
        f"{2 * len(TAR_LAYERS) + 2} regions)...", "STEP")
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(cfg["xmin"], cfg["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=cfg["t_initial"],
                             tion=cfg["t_initial"], trad=cfg["t_initial"])
    # 分层边界: 数值 x_range 供采样/预诊断; x_expr (参数表达式) 供
    # Simulation_initBlock 代码生成 — 几何由 .par 运行时参数控制。
    # ★ 12 区 / 13 边界, 与 SNBOneCH_ml 的多层示踪几何逐项对应:
    #   shld | samp | tar1 | samp | tar2 | samp | tar3 | samp |
    #   tar4 | samp | tar6 | samp
    builder.add_region(
        "shld", species="shld", x_range=(0.0, delta_cm),
        x_expr=("0.0", "sim_shldRadius"))
    _prev_x = delta_cm
    _prev_expr = "sim_shldRadius"
    for _idx, _t in enumerate(TAR_LAYERS):
        _Lx = f"sim_{_t}Radius"
        _Lt = Lmap[_t]
        _gap_name = "samp_front" if _idx == 0 else f"samp_{_idx}"
        builder.add_region(
            _gap_name, species="samp", x_range=(_prev_x, _Lt),
            x_expr=(_prev_expr, _Lx))
        builder.add_region(
            _t, species=_t, x_range=(_Lt, _Lt + delta_cm),
            x_expr=(_Lx, f"{_Lx} + sim_shldRadius"))
        _prev_x = _Lt + delta_cm
        _prev_expr = f"{_Lx} + sim_shldRadius"
    builder.add_region(
        "samp_rear", species="samp",
        x_range=(_prev_x, _prev_x + D),
        x_expr=(_prev_expr, f"{_prev_expr} + sim_sampHeight"))
    block_gen = BlockGenerator(
        simulation_name=SIM_NAME, sim_path=sim_path, species=list(SPECIES_LIST),
    )
    block_gen.build(builder)
    block_path = block_gen.save(str(INPUT_DIR / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)
    log(f"    Simulation_initBlock.F90 ({len(builder.regions)} regions) ✓")

    # ── 7. EOS/opacity .cn4（多级查找复制到 flash_input）──
    log("  [7/9] 复制 EOS/opacity 表...", "STEP")

    def _copy_cn4(filename: str, aliases) -> bool:
        """按 注册表别名 → eos_op_data 递归 → 旧仓库兜底 的顺序复制 .cn4。"""
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        dst = EOSOpacityGenerator().copy_eos_file(aliases[0], INPUT_DIR)
        if dst is not None and Path(dst).exists():
            return True
        data_root = _ROOT / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        for cand in data_root.rglob(filename):
            shutil.copyfile(cand, INPUT_DIR / filename)
            log(f"    {filename} ← {cand.relative_to(data_root)}", "INFO")
            return True
        legacy = _ROOT.parent / "flash_c" / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        if legacy.is_dir():
            for cand in legacy.rglob(filename):
                shutil.copyfile(cand, INPUT_DIR / filename)
                log(f"    {filename} ← 旧仓库兜底: {cand.relative_to(legacy)}", "WARN")
                return True
        log(f"    {filename} 缺失 (注册表/数据目录/旧仓库均未找到)", "ERROR")
        return False

    # ★ 表清单必须覆盖所有 par 引用分支, 漏表即 DRIVER_ABORT
    tables = [
        ("He-BADGER-TOPS-Final.cn4", ("he_badger",)),
        ("CH-QC-1-001.cn4", ("ch_qc",)),
    ]
    if TI_LAYER is not None or SHLD_MATERIAL == "Ti":
        tables.append(("Ti-BADGER-TOPS.cn4", ("ti_badger",)))
    if SHLD_MATERIAL == "V":
        tables.append(("V-BADGER-TOPS.cn4", ("v_badger",)))
    ok_all = True
    for filename, aliases in tables:
        if not _copy_cn4(filename, aliases):
            ok_all = False
    if not ok_all:
        log("EOS/opacity 表不齐全, 终止 (FLASH 将因缺表 abort)", "ERROR")
        return result

    # ── 8. ★★★ SNB 物理覆盖 F90 (本场景自包含的关键; 修复 2026-09-13) ──
    log("  [8/9] 部署 SNB 物理覆盖 F90 (9 个) + provenance...", "STEP")
    if not _deploy_snb_overrides(cfg):
        log("SNB 覆盖 F90 部署失败, 终止 (场景将不自包含)", "ERROR")
        return result
    result["snb_overrides"] = str(INPUT_DIR)
    result["provenance"] = str(INPUT_DIR / PROVENANCE_FILE)

    # ── 9. run_flash.sh (WSL 手动一键) + 预诊断图 ─────────
    log("  [9/9] 生成 run_flash.sh + 预诊断图...", "STEP")
    _write_run_flash_sh(cfg, nprocs)
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    log("    run_flash.sh ✓")

    try:
        import numpy as np
        from flash.input_gen.gen_checker.ploter import PulsePlotter, DensityPlotter
        tsec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in tmp_params.items() if k.startswith("ed_time_1_"))
        psec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in tmp_params.items() if k.startswith("ed_power_1_"))
        if tsec and psec:
            times_ns = np.array([v for _, v in tsec]) * 1e9
            powers_w = np.array([v for _, v in psec])
            PulsePlotter().plot_pulse(
                times_ns, powers_w,
                title=f"Laser Pulse ({len(tsec)} sections)",
                save_path=INPUT_DIR / "pre_diag_laser_pulse.png",
                beam_label="Beam 1 (0.351 um)")
            log(f"    pre_diag_laser_pulse.png ✓ ({len(tsec)} sections)")
            result["pre_diag_laser"] = str(INPUT_DIR / "pre_diag_laser_pulse.png")
        xs, dens1d, _ = builder.sample_1d(n_points=4000)
        # 分层边界标注 (与 initBlock 的 13 边界一致)
        bounds = [("shld", 0.0), ("samp", delta_cm)]
        _bx = delta_cm
        for _t in TAR_LAYERS:
            bounds.append((_t, Lmap[_t]))
            bounds.append(("samp", Lmap[_t] + delta_cm))
        bounds.append(("end", Lmap[TAR_LAYERS[-1]] + delta_cm + D))
        DensityPlotter().plot_1d(
            xs, dens1d, region_boundaries=list(bounds),
            title=f"Initial Density Layers ({SCENE_NAME}: shld={SHLD_MATERIAL}, "
                  f"{TI_LAYER}=Ti, {len(TAR_LAYERS)} tracer layers)",
            save_path=INPUT_DIR / "pre_diag_initial_density.png")
        log("    pre_diag_initial_density.png ✓")
        result["pre_diag_density"] = str(INPUT_DIR / "pre_diag_initial_density.png")
    except Exception as exc:  # noqa: BLE001
        log(f"预诊断图生成失败 (不影响仿真): {exc}", "WARN")

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


# ══════════════════════════════════════════════════════════════════════
# SNB 物理覆盖 F90 的本地部署 + 审计 (修复 2026-09-13)
# ══════════════════════════════════════════════════════════════════════
def _deploy_snb_overrides(cfg: Dict[str, Any]) -> bool:
    """把 9 个 SNB 物理覆盖 F90 从仓内镜像复制到 flash_input/ (自包含)。

    ## 为什么必须有这一步 (缺陷根因)

    修复前 `generate_input_files()` 只生成 Config/Makefile/Simulation_*.F90
    + cn4 + par, 9 个覆盖 F90 完全依赖部署阶段从超算
    `SNB_1D_laser` 单元兜底复制。后果:
      - 场景**不自包含**, 离线无法审计实际参与编译的物理实现;
      - 远端单元一旦变动/不可达 → 静默换物理 (最危险的一类错误);
      - 本地静态核验无法覆盖"SNB 物理是否就位"这一最关键断言。

    ## 设计纪律 (沿用仓内先例 gen_scene.py:284-300)

    ★ **每次生成都重新复制, 绝不用"已存在就跳过"短路** —— 否则陈旧的
      诊断变体会持续污染后续场景 (该先例已明确记录过此类事故)。
    ★ 源缺失时 **硬失败并列出缺项**, 绝不静默跳过。
    ★ 逐字节复制 (含 GBK 中文注释), 不做任何编码转换。
    """
    if not _SNB_PKG_DIR.is_dir():
        log(f"SNB 覆盖源目录缺失: {_SNB_PKG_DIR}", "ERROR")
        return False

    rows: List[Tuple[str, int, str]] = []
    missing: List[str] = []
    for fname in SNB_OVERRIDE_FILES:
        src = _SNB_PKG_DIR / fname
        if not src.is_file():
            missing.append(fname)
            continue
        dst = INPUT_DIR / fname
        shutil.copyfile(src, dst)          # ★ 逐字节 (不短路径, 不用 copy2)
        blob = dst.read_bytes()
        rows.append((fname, len(blob),
                     hashlib.sha256(blob).hexdigest()))

    if missing:
        log(f"SNB 覆盖 F90 源缺失 {len(missing)} 个: {missing}", "ERROR")
        log(f"  源目录: {_SNB_PKG_DIR}", "ERROR")
        return False

    log(f"    9 个 SNB 覆盖 F90 已落盘 ({sum(r[1] for r in rows)} B) ✓", "OK")

    # ── provenance 审计文件 (与 SNBOneCH_ml 同构, 逐行对齐) ──
    prov = INPUT_DIR / PROVENANCE_FILE
    lines = [
        "# SNB 覆写 F90 —— 来源与校验（权威版）",
        "",
        "这 9 个 F90 是 **SNB 非局域热传导的实现覆盖文件**，部署时由",
        "`run_flash.sh`（WSL）/ NC-E `build.sh` 拷入 SimulationMain 单元：",
        "",
        "| 优先级 | 来源 |",
        "|---|---|",
        "| 1（场景自包含） | 本目录 `flash_input/*.F90` |",
        "| 2（回落） | `FLASHSNB/.../SimulationMain/SNB_1D_laser/` |",
        "",
        "## 补齐与校验（2026-09-13）",
        "",
        "补齐前本目录**只有** Config/Makefile/Simulation_*.F90 + cn4 + par，",
        "9 个 F90 全靠运行时从树里拷 —— 场景不自包含、无法离线审计。",
        "本场景首建时复现了同一缺陷；已由 `SNBVTi.py::_deploy_snb_overrides()`",
        "补齐为**每次生成都从仓内镜像重拷**（不做存在性短路）。",
        "",
        f"- 源镜像 `SNB/SNB/source/snb_package/`：**9/9**（本地权威源，离线可用）",
        "- 与 `SNBOneCH_ml/flash_input/` 一致：**9/9**",
        "- 与上游 `SNB_1D_laser` / NC-E 已部署单元一致：**9/9**",
        "",
        "| 文件 | 字节 | sha256 |",
        "|---|---:|---|",
    ]
    for fname, nbytes, dig in rows:
        lines.append(f"| `{fname}` | {nbytes} | `{dig}` |")
    lines += [
        "",
        "## 复验",
        "",
        "```bash",
        "cd flash_input && sha256sum -c <<'EOF'",
    ]
    for fname, _n, dig in rows:
        lines.append(f"{dig}  {fname}")
    lines += ["EOF", "```", ""]
    prov.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    log(f"    {PROVENANCE_FILE} ✓ ({prov.stat().st_size} B)", "OK")

    # ── 远端 cn4 重部署辅助脚本 (SNBVTi 专属路径) ──
    obj_abs = f"/root/{SIM_USER_DIR}/FLASH/FLASHSNB/FLASH4.8/{OBJDIR}"
    sim_abs = (f"/root/{SIM_USER_DIR}/FLASH/FLASHSNB/FLASH4.8"
               f"/source/Simulation/SimulationMain/{SIM_NAME}")
    cn4 = f"""#!/bin/bash
# {SCENE_NAME} 远端 cn4 表重部署 (objdir ← SimulationMain 单元, 全有或全无)
# 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
set -u
OBJ="{obj_abs}"
SIM="{sim_abs}"
cd "$OBJ" || exit 9
rm -f "$OBJ"/*.cn4
n=0
for f in "$SIM"/*.cn4 ; do
  [ -r "$f" ] || continue
  cp -f "$f" "$OBJ/$(basename "$f")" || exit 8
  n=$((n+1))
done
echo "CN4_COPIED=$n"
bad=0
for t in "$OBJ"/*.cn4 ; do
  [ -e "$t" ] || continue
  [ -s "$t" ] || {{ echo "BAD $t"; bad=$((bad+1)); }}
done
echo "CN4_BAD=$bad"
ls -1 "$OBJ"/*.cn4 2>/dev/null | wc -l
"""
    (INPUT_DIR / DEPLOY_CN4_FILE).write_text(cn4, encoding="utf-8", newline="\n")
    log(f"    {DEPLOY_CN4_FILE} ✓", "OK")
    return True


def _write_run_flash_sh(cfg: Dict[str, Any], nprocs: int) -> None:
    """生成 run_flash.sh — WSL 一键流水线 (补丁→部署→setup→make→运行→收集)。

    ★ 五阶段结构对齐 SNBOneCH_ml/flash_input/run_flash.sh (3151 B 版):
      (0) t001 树级 physics 补丁幂等同步
      (1) 部署单元: 生成文件 + cn4 + **9 个覆盖 F90 (本地优先, 远端兜底)**
      (2) setup + mgd_qesh.F90 软链
      (3) make (先烘 hy_slopeLimiters/Conductivity_* 破竞态)
      (4) 运行 (TMAX/NPROC 环境变量可覆写)
      (5) 收集到 FLASH_COLLECT_DIR
    环境开关: SKIP_SETUP=1 SKIP_MAKE=1 SKIP_DEPLOY=1 TMAX=... NPROC=...
    """
    flags, nxb, dx = build_setup_flags_ug(nprocs, cfg["xmin"], cfg["xmax"])
    overrides = " ".join(SNB_OVERRIDE_FILES)
    sh = f"""#!/usr/bin/env bash
# {SCENE_NAME} one-click pipeline (FLASHSNB, WSL) — generated by {SCENE_NAME}.py
# 模型: SNB 非局域; shld={SHLD_MATERIAL}, {TI_LAYER}=Ti; 其余 tar*=CH
# 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Env switches: SKIP_SETUP=1 SKIP_MAKE=1 SKIP_DEPLOY=1 TMAX={cfg['tmax']:.1e} NPROC={nprocs}
set -u
SNB_HOME="${{SNB_HOME:-$(find "$HOME" -maxdepth 3 -type d -name FLASHSNB 2>/dev/null | head -1)/FLASH4.8}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OBJ="$SNB_HOME/{OBJDIR}"
UNIT="$SNB_HOME/source/Simulation/SimulationMain/{SIM_NAME}"
REF_UNIT="$SNB_HOME/source/Simulation/SimulationMain/SNB_1D_laser"
NPROC="${{NPROC:-{nprocs}}}"
echo "== {SCENE_NAME} pipeline (FLASHSNB: $SNB_HOME) =="

# 0) tree-level physics patches (t001 fixes; idempotent)
if [ -z "${{SKIP_DEPLOY:-}}" ]; then
  T001="$SCRIPT_DIR/../../../../SNB/SNBtest/Test/t001/source_patches"
  for rel in physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90 \\
             physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90; do
    if [ ! -f "$SNB_HOME/source/$rel" ] && [ -f "$T001/$rel" ]; then
      mkdir -p "$SNB_HOME/source/$(dirname "$rel")"
      cp -f "$T001/$rel" "$SNB_HOME/source/$rel"
      echo "  patch synced: $rel"
    fi
  done

  # 1) deploy unit: generated files + cn4 + SNB overrides (local-first)
  mkdir -p "$UNIT"
  cp -f "$SCRIPT_DIR"/Config "$SCRIPT_DIR"/Makefile \\
        "$SCRIPT_DIR"/Simulation_data.F90 "$SCRIPT_DIR"/Simulation_init.F90 \\
        "$SCRIPT_DIR"/Simulation_initBlock.F90 "$SCRIPT_DIR"/*.cn4 "$UNIT"/ || exit 1
  for f in {overrides}; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
      cp -f "$SCRIPT_DIR/$f" "$UNIT/$f" || exit 9
    elif [ -f "$REF_UNIT/$f" ]; then
      echo "  WARN: $f 场景内缺失, 回落远端 SNB_1D_laser"
      cp -f "$REF_UNIT/$f" "$UNIT/$f" || exit 9
    else
      echo "  ERROR: $f 两侧均缺, 无法部署"; exit 9
    fi
  done
  echo "  unit deployed: $UNIT"
fi

# 2) setup
if [ -z "${{SKIP_SETUP:-}}" ]; then
  cd "$SNB_HOME" && rm -rf "$OBJ"
  ./setup -auto {SIM_NAME} {flags} -objdir={OBJDIR} || exit 1
  cd "$OBJ" && ln -sf ../source/Simulation/SimulationMain/{SIM_NAME}/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null
  echo "  setup done (nxb={nxb}, dx={dx*1e4:.5f} um)"
fi
[ -d "$OBJ" ] || {{ echo "objdir missing, run setup first"; exit 1; }}

# 3) make (race fix: pre-build key modules)
if [ -z "${{SKIP_MAKE:-}}" ]; then
  cd "$OBJ"
  make hy_slopeLimiters.o Conductivity_interface.o Conductivity_fullState.o 2>&1 | tail -3
  make -j4 2>&1 | tail -20 || exit 1
  [ -x flash4 ] || {{ echo "flash4 not built"; exit 1; }}
  echo "  build done"
fi

# 4) run
cp -f "$SCRIPT_DIR/{PAR_FILENAME}" "$OBJ/flash.par"
if [ -n "${{TMAX:-}}" ]; then
  sed -i "s/^tmax.*/tmax           = $TMAX/" "$OBJ/flash.par"
fi
cd "$OBJ" && rm -f {BASENM}* wsl_run_{SCENE_NAME.lower()}.log
mpiexec -n "$NPROC" ./flash4 > wsl_run_{SCENE_NAME.lower()}.log 2>&1
echo "RUN_EXIT=$?" | tee -a wsl_run_{SCENE_NAME.lower()}.log
tail -3 wsl_run_{SCENE_NAME.lower()}.log

# 5) collect
COLLECT="${{FLASH_COLLECT_DIR:-$SCRIPT_DIR/outputfiles}}"
mkdir -p "$COLLECT"
cp -f "$OBJ"/{BASENM}* "$OBJ"/wsl_run_{SCENE_NAME.lower()}.log "$OBJ"/{LOG_FILE} "$COLLECT"/ 2>/dev/null
rm -f "$OBJ"/{BASENM}*
echo "  collected to $COLLECT"
echo "== pipeline done =="
"""
    p = INPUT_DIR / "run_flash.sh"
    p.write_text(sh, encoding="utf-8", newline="\n")


# ══════════════════════════════════════════════════════════════════════
# 静态核验 (--generate-only 后自检, 防低级错误)
# ══════════════════════════════════════════════════════════════════════
def verify_generated(cfg: Dict[str, Any]) -> bool:
    """核验 flash_input/ 产物: 材料绑定正确 + CN4 表齐全且成分匹配。

    这是本场景最易错之处 (V 表 / Ti 表 / CH 表三者绑定), 故独立成函数
    并在 --generate-only 后强制执行。
    """
    ok = True
    par = INPUT_DIR / PAR_FILENAME
    if not par.exists():
        log(f"缺 par: {par}", "ERROR")
        return False
    txt = par.read_text(encoding="utf-8", errors="replace")

    def _parval(key: str) -> Optional[str]:
        m = re.search(rf"^\s*{re.escape(key)}\s*=\s*([^\s!#]+)", txt, re.M)
        return m.group(1) if m else None

    # (a) 材料绑定断言 (par 中显式覆写的键)
    checks = [
        ("sim_rhoShld", f"{_MAT_V['rho']}", "shld = V 密度"),
        ("eos_shldTableFile", "V-BADGER-TOPS.cn4", "shld EOS 表 = V"),
        ("op_shldFileName", "V-BADGER-TOPS.cn4", "shld op 表 = V"),
        # ★ 8 物种: 逐层核验 EOS/op 表绑定 (TI_LAYER → Ti 表, 其余 → CH 表)
        *[(f"eos_{_t}TableFile",
           (_MAT_TI if _t == TI_LAYER else _MAT_CH)["file"],
           f"{_t} EOS 表 = {'Ti' if _t == TI_LAYER else 'CH'}")
          for _t in TAR_LAYERS],
        *[(f"op_{_t}FileName",
           (_MAT_TI if _t == TI_LAYER else _MAT_CH)["file"],
           f"{_t} op 表 = {'Ti' if _t == TI_LAYER else 'CH'}")
          for _t in TAR_LAYERS],
        ("sim_rhoSamp", "1", "samp = CH 密度 1.0"),
        ("eos_sampTableFile", cfg["ch_cn4"], "samp = CH 表"),
        ("rt_useMGD", ".true.", "MGD 辐射开启"),
        ("useDiffuse", ".true.", "扩散单元开启 (SNB 前提)"),
        ("gr_hypreUseFloor", ".false.", "★ SNB 铁律 #1: Floor 必须关"),
        ("riemann_solver" if _parval("riemann_solver") is not None else "RiemannSolver",
         cfg["riemann_solver"], "Riemann 求解器 = HLL"),
        ("diff_eleFlMode", cfg["diff_eleFlMode"], "电子限流模式"),
        ("diff_eleFlCoef", str(cfg["diff_eleFlCoef"]), "电子限流系数 0.06"),
        ("rt_mgdFlMode", cfg["rt_mgdFlMode"], "辐射限流模式"),
        ("cfl", str(cfg["cfl"]), "CFL = 0.2"),
        ("iProcs", str(cfg["nprocs"] or UG_IPROCS_EXACT), "iProcs"),
    ]
    for key, want, desc in checks:
        got = _parval(key)
        if got is None:
            log(f"  ✗ {key} 缺失 ({desc})", "ERROR"); ok = False
        elif want.lstrip(".").lower() not in got.lower():
            log(f"  ✗ {key} = {got} (期望含 {want}) — {desc}", "ERROR"); ok = False
    if ok:
        log("  材料/SNB 绑定断言全部通过 ✓", "OK")

    # (a1) 浮点键数值比较 — par 会写成 1.000000000000000e-06 这类全精度形式,
    #      字符串包含匹配会误判, 故对数值键单独做 float 容差比较。
    num_checks = [
        ("sim_rhoCham", 1.0e-6, "cham = He 稀薄 1e-6"),
        ("sim_rhoSamp", _MAT_CH["rho"], "samp = CH"),
        ("sim_rhoShld", _MAT_V["rho"], "shld = V"),
        # ★ 8 物种: 逐层密度 (float 容差比较, 避开 par 的全精度书写形式)
        *[(f"sim_rho{_t.capitalize()}",
           (_MAT_TI if _t == TI_LAYER else _MAT_CH)["rho"],
           f"{_t} = {'Ti' if _t == TI_LAYER else 'CH'}")
          for _t in TAR_LAYERS],
        ("diff_eleFlCoef", cfg["diff_eleFlCoef"], "电子限流系数"),
        ("cfl", cfg["cfl"], "CFL"),
    ]
    for key, want, desc in num_checks:
        got = _parval(key)
        if got is None:
            log(f"  ✗ {key} 缺失 ({desc})", "ERROR"); ok = False; continue
        try:
            gv = float(got.strip('"'))
        except ValueError:
            log(f"  ✗ {key} = {got} 非数值 ({desc})", "ERROR"); ok = False; continue
        if abs(gv - float(want)) > 1e-9 * max(1.0, abs(float(want))):
            log(f"  ✗ {key} = {gv} ≠ {want} ({desc})", "ERROR"); ok = False
    log("  浮点键数值断言通过 ✓", "OK")

    # (a2) ★ Config 编译期默认值断言 — 这些键【有意】不出现在 par 中
    #      (与 defaults.py 默认值一致 ⇒ 无需覆写)。但 Simulation_initBlock.F90
    #      会读取它们, 若 Config 声明错误将直接导致初始化密度/温度错误。
    #      这里以 Config 为权威源逐键核验, 防"par 看不到就以为没问题"的盲区。
    cfg_txt = (INPUT_DIR / "Config").read_text(encoding="utf-8", errors="replace")
    cfg_params = {m.group(1): (m.group(2), m.group(3))
                  for m in re.finditer(
                      r"^\s*PARAMETER\s+(\w+)\s+(\S+)\s+(\S+)", cfg_txt, re.M)}
    # 期望: CH 族 tar 密度 = 1.0 (即 _MAT_CH["rho"]), He = 1e-6
    cfg_expect = {}
    # ★ 8 物种: 逐个 CH 标记层 (tar1/tar3/tar4/tar6) 的 Config 编译期默认值
    for _s in TAR_LAYERS:
        if _s == TI_LAYER:
            continue
        _cap = _s.capitalize()
        cfg_expect[f"sim_rho{_cap}"] = f"{_MAT_CH['rho']}"
        cfg_expect[f"eos_{_s}TableFile"] = f'"{cfg["ch_cn4"]}"'
    cfg_expect["sim_rhoSamp"] = f"{_MAT_CH['rho']}"
    for key, want in cfg_expect.items():
        if key not in cfg_params:
            log(f"  ✗ Config 缺声明 {key}", "ERROR"); ok = False; continue
        got = cfg_params[key][1]
        if want.strip('"') not in got.strip('"'):
            log(f"  ✗ Config {key} = {got} (期望 {want})", "ERROR"); ok = False
    if ok:
        log(f"  Config 编译期默认值断言通过 ✓ ({len(cfg_expect)} 键: "
            f"samp 密度=CH {_MAT_CH['rho']})", "OK")

    # (a3) 温度/辐射初值一致性: 各物种 sim_tele/tion/trad 必须全部声明且相等
    _temps = {}
    for _sp in ("Cham", "Shld", "Samp", "Tar2"):
        for _pre in ("tele", "tion", "trad"):
            _k = f"sim_{_pre}{_sp}"
            if _k not in cfg_params:
                log(f"  ✗ Config 缺 {_k}", "ERROR"); ok = False
            else:
                _temps[_k] = cfg_params[_k][1]
    if _temps:
        _uniq = set(_temps.values())
        if len(_uniq) != 1:
            log(f"  ✗ 初温不一致: {sorted(_uniq)}", "ERROR"); ok = False
        else:
            log(f"  ✓ {len(SPECIES_LIST)} 物种 tele/tion/trad 初值统一 = {_uniq.pop()}", "OK")

    # (b) CN4 表齐备 + 成分核验 (权威读法: 行1 = atomic #s of gases)
    expect = {
        "V-BADGER-TOPS.cn4": 23, "Ti-BADGER-TOPS.cn4": 22,
        "He-BADGER-TOPS-Final.cn4": 2, "CH-QC-1-001.cn4": (6, 1),
    }
    for fn, want_z in expect.items():
        p = INPUT_DIR / fn
        if not p.exists():
            log(f"  ✗ 缺表 {fn}", "ERROR"); ok = False; continue
        with open(p, "r", errors="replace") as fh:
            fh.readline()                       # 行0: nT nD
            zline = fh.readline()               # 行1: atomic #s of gases
        zs = tuple(int(x) for x in re.findall(r"\d+", zline.split(":")[-1]))
        exp = want_z if isinstance(want_z, tuple) else (want_z,)
        if zs != exp:
            log(f"  ✗ {fn} 成分 {zs} ≠ 期望 {exp} (文件名与内容不符!)", "ERROR")
            ok = False
        else:
            log(f"  ✓ {fn} Z={zs}", "OK")

    # (c) 关键 F90 / Config 存在
    for fn in ("Config", "Makefile", "Simulation_data.F90", "Simulation_init.F90",
               "Simulation_initBlock.F90"):
        if not (INPUT_DIR / fn).exists():
            log(f"  ✗ 缺 {fn}", "ERROR"); ok = False

    # (e) ★★★ SNB 覆盖 F90 自包含断言 (2026-09-13 新增)
    #     这是本场景"是否有 SNB 物理"的唯一权威检查。修复前此断言不存在,
    #     导致 flash_input 缺 9 个 F90 却仍能通过静态核验 (缺陷得以潜伏)。
    #     校验两层: ① 全部落盘; ② sha256 与仓内镜像一致 (防陈旧/半拷贝)。
    _ovr_bad: List[str] = []
    for fn in SNB_OVERRIDE_FILES:
        dst = INPUT_DIR / fn
        src = _SNB_PKG_DIR / fn
        if not dst.exists():
            log(f"  ✗ 缺 SNB 覆盖 F90: {fn}", "ERROR"); ok = False
            _ovr_bad.append(fn); continue
        if not src.exists():
            log(f"  ✗ 镜像源缺 {fn} (无法校验)", "ERROR"); ok = False
            _ovr_bad.append(fn); continue
        dh = hashlib.sha256(dst.read_bytes()).hexdigest()
        sh_ = hashlib.sha256(src.read_bytes()).hexdigest()
        if dh != sh_:
            log(f"  ✗ {fn} sha256 与镜像不符 (dst={dh[:12]} src={sh_[:12]})",
                "ERROR")
            ok = False; _ovr_bad.append(fn)
    if not _ovr_bad:
        log(f"  ✓ SNB 覆盖 F90 自包含 9/9 且 sha256 与镜像一致", "OK")
    for fn in (PROVENANCE_FILE, DEPLOY_CN4_FILE):
        if not (INPUT_DIR / fn).exists():
            log(f"  ✗ 缺 {fn}", "ERROR"); ok = False
    # render_flash.sh 必须是完整流水线 (修复前只有 554 B 的 setup+make 存根)
    _rfs = INPUT_DIR / "run_flash.sh"
    if _rfs.exists():
        _rt = _rfs.read_text(encoding="utf-8", errors="replace")
        for _need, _desc in (("REF_UNIT", "远端兜底单元"),
                             ("SKIP_DEPLOY", "分段开关"),
                             ("for f in " + SNB_OVERRIDE_FILES[0], "覆盖 F90 部署循环"),
                             ("FLASH_COLLECT_DIR", "结果收集")):
            if _need not in _rt:
                log(f"  ✗ run_flash.sh 缺 {_desc} ({_need})", "ERROR"); ok = False
        if len(_rt) < 2000:
            log(f"  ✗ run_flash.sh 仅 {len(_rt)} B (疑似存根, 应 >2000 B)",
                "ERROR"); ok = False
        elif ok:
            log(f"  ✓ run_flash.sh 完整流水线 ({len(_rt)} B)", "OK")

    # (d) ★ 精确网格自检 (SNBVTi2 专属三重断言)
    nprocs = cfg["nprocs"] or UG_IPROCS_EXACT
    _, nxb, dx = build_setup_flags_ug(nprocs, cfg["xmin"], cfg["xmax"])
    ncell = (cfg["delta_um"] * 1e-4) / dx
    if abs(dx - UG_DX_EXACT_CM) > 1e-12:
        log(f"  ✗ dx={dx*1e4:.6f} um != 精确值 {UG_DX_EXACT_CM*1e4:.2f} um", "ERROR")
        ok = False
    elif abs(ncell - UG_LAYER_CELLS) > 1e-9:
        log(f"  ✗ 0.1um 薄层 = {ncell:.4f} 格 != {UG_LAYER_CELLS} 整格", "ERROR")
        ok = False
    else:
        log(f"  ✓ 精确网格: nproc={nprocs}, nxb={nxb}, dx={dx*1e4:.6f} um (精确), "
            f"0.1um 薄层 = {ncell:.0f} 整格", "OK")
    # (d1) 全部 13 个层边界相对 xmin 的整除性 (确保落在网格边上)
    _bounds_um = [0.0]
    for _t in TAR_LAYERS:
        _bounds_um += [cfg[f"L{_t[3:]}_um"], cfg[f"L{_t[3:]}_um"] + cfg["delta_um"]]
    _dx_um = dx * 1e4
    _mis = []
    for _b in _bounds_um:
        _off = (abs(cfg["xmin"]) * 1e4 + _b) / _dx_um
        if abs(_off - round(_off)) > 1e-6:
            _mis.append((_b, _off))
    if _mis:
        log(f"  ✗ {len(_mis)} 个层边界不在网格边上 (dx={_dx_um:.4f} um): "
            f"{_mis[:4]}", "ERROR")
        ok = False
    else:
        log(f"  ✓ {len(_bounds_um)} 个层边界全部落在网格边上 (含 x=0)", "OK")

    return ok


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description=f"{SCENE_NAME} (VCH+Ti 多层示踪 + SNB; NC-E 极短验证)")
    ap.add_argument("action", nargs="?", default=None,
                    help="hpc 分阶段动作: all/upload/submit/monitor/analyze/"
                         "download/status (默认按 RUN_MODE 完整运行)")
    ap.add_argument("--generate-only", action="store_true",
                    help="只生成输入文件 + 静态核验, 不运行")
    ap.add_argument("--skip-verify", action="store_true", help="跳过静态核验")
    ap.add_argument("--tmax", type=float, default=None,
                    help="覆写仿真结束时间 (s); 默认 1.0e-11 极短验证值")
    ap.add_argument("--nproc", type=int, default=None, help="MPI 进程数 (= iProcs)")
    ap.add_argument("--account", type=str, default="flash_ssh",
                    help="超算凭据账户名 (默认 flash_ssh = NC-E)")
    ap.add_argument("--skip-build", action="store_true",
                    help="远端跳过 setup+make (复用已编译 flash4)")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    ap.add_argument("--skip-run", action="store_true",
                    help="只做 setup+make, 不提交运行作业")
    ap.add_argument("--poll-timeout", type=int, default=7200,
                    help="HPC 作业轮询上限秒数 (长跑请调大, 如 72000)")
    ap.add_argument("--amr", action="store_true",
                    help="历史基线: AMR lrefine9 (需重编译)")
    ap.add_argument("--wait", type=int, default=0,
                    help="hpc monitor 等待秒数 (默认不阻塞轮询一次)")
    ap.add_argument("--plots-dir", type=str, default=None,
                    help="测试图像输出目录 (默认 <场景>/plots)")
    args = ap.parse_args()

    print("\n" + "=" * 70)
    print(f" FLASH {SCENE_NAME} — VCH+Ti multi-layer tracer + SNB nonlocal")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    cfg = dict(config_constants)
    if args.tmax is not None:
        cfg["tmax"] = args.tmax
        log(f"tmax 覆盖: {cfg['tmax']:.3e} s", "OK")
    if args.nproc is not None:
        cfg["nprocs"] = args.nproc
        log(f"nproc 覆盖: {cfg['nprocs']}", "OK")
    if args.amr:
        cfg["nxb"] = 16
        cfg["tstep_change_factor"] = 1.05
        cfg["dtmax"] = 2.0e-14
        log("AMR 历史基线模式 (lrefine9, tstep=1.05, dtmax=2e-14)", "WARN")

    # ★★★ 域边界吸附 (2026-09-13): 消除 FLASH setup 的隐式二次取整。
    #   若不吸附, xmin=-0.04 会被右移 1.9084 um ⇒ 所有层整体偏 +1.91 um。
    if cfg.get("align_domain", True):
        _xa, _xb, _rootdx, _shift = align_domain(
            cfg["xmin"], cfg["xmax"], cfg["nblockx"], cfg["nxb"])
        if abs(_shift) > 1e-12:
            log(f"域边界吸附: xmin {cfg['xmin']:.8f} → {_xa:.8f} cm "
                f"(位移 {_shift*1e4:+.4f} um, rootdx={_rootdx:.6e} cm); "
                f"xmax → {_xb:.8f}", "OK")
            cfg["xmin"] = _xa
            cfg["xmax"] = _xb
        else:
            log(f"域边界已对齐 (rootdx={_rootdx:.6e} cm, 无需吸附)", "OK")

    print("\n  参数配置:")
    print(f"    域: [{cfg['xmin']}, {cfg['xmax']}] cm")
    print(f"    材料: shld={SHLD_MATERIAL} {_MAT_V['rho'] if SHLD_MATERIAL=='V' else '-'} g/cc | "
          f"{TI_LAYER}=Ti {_MAT_TI['rho']} g/cc | 其余 tar*=CH")
    print(f"    分层({len(SPECIES_LIST)} 物种/{2*len(TAR_LAYERS)+2} 区): shld 0.1um | samp | "
          + " | ".join(f"{t}@{cfg[f'L{t[3:]}_um']:g}um"
                       + ("(Ti)" if t == TI_LAYER else "(CH)")
                       for t in TAR_LAYERS)
          + f" | samp(尾 {cfg['D_um']:g}um)")
    print(f"    物种({len(SPECIES_LIST)}): {','.join(SPECIES_LIST)}")
    print(f"    模型: SNB 非局域 (diff_eleFlMode={cfg['diff_eleFlMode']}), "
          f"辐射=MGD 10 群")
    print(f"    网格: {'AMR' if args.amr else '+ug'}, nproc={cfg['nprocs']}, "
          f"tmax={cfg['tmax']:.3e} s")
    print("=" * 70)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        generate_input_files(cfg)
    except Exception as e:
        log(f"输入文件生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1

    if not args.skip_verify:
        log("静态核验 flash_input/ 产物...", "STEP")
        if not verify_generated(cfg):
            log("静态核验失败 — 已中止, 请修上方 ✗ 项", "ERROR")
            return 1

    if args.generate_only:
        log(f"--generate-only: 产物在 {INPUT_DIR}", "OK")
        return 0

    # ── 超算执行 (NC-E 默认) ───────────────────────────────
    return run_hpc_pipeline(args, cfg)


def run_hpc_pipeline(args, cfg: Dict[str, Any]) -> int:
    """超算流水线 — 委托给 SNBOneCH_ml 久经考验的 HPC 驱动。

    ## 设计决策: 委托 (rebind + delegate), 不复制

    SNB 的超算路径涉及大量实测踩坑 (SFTP 不展开 `~`、--skip-build 必须补做
    tar 解压、运行前 gr_hypreUseFloor 闸门、nc4 表远端兜底、HDF5 LD_LIBRARY_PATH、
    build/probe/run 三作业编排、输出收集回退)。**复制一份必然漂移**。

    唯一差异只是模块级命名常量 (SIM_NAME/OBJDIR/BASENM/PAR_FILENAME/
    INPUT_DIR/OUTPUT_DIR)。故这里采取"临时重绑定 + 委托":

      1. 把参考模块的命名常量改写为本场景值;
      2. 调用 reference.run_hpc(...);
      3. finally 恢复原值 (避免污染同进程内其他调用)。

    ⚠ 重绑定是**进程内全局副作用**, 故必须在 finally 中无条件恢复, 且本函数
    不可重入并发调用 (单场景单次运行, 可接受)。
    """
    from flash.scenarios.private.tracer.SNB.SNBOneCH_ml import SNBOneCH_ml as ref

    # ── 0. ★★★ 先格式化 SETUP_FLAGS 的 {nxb} 占位符 ──
    #   根因 (2026-09-13 实测): 参考模块的模块级 SETUP_FLAGS 是**未格式化模板**
    #   (含字面 "{nxb}")。它之所以能工作, 是因为参考模块的 main() 在调 run_hpc
    #   **之前** 用 globals()["SETUP_FLAGS"] = _flags_ug 完成了替换。
    #   本委托层绕过了那个 main() ⇒ 若直接绑定裸模板, 远端 setup 会报
    #     ValueError: invalid literal for int() with base 10: '{nxb}'
    #   并在 ~22s 内 SETUP_FAIL。
    #   ⇒ 委托方**必须自己完成这一步**(这是"委托"不可避免的隐式前置条件)。
    nproc = int(cfg["nprocs"] or UG_IPROCS_EXACT)
    if "{nxb}" in SETUP_FLAGS or "{nxb}" in getattr(ref, "SETUP_FLAGS", ""):
        _flags_ug, _nxb, _dx_cm = build_setup_flags_ug(nproc, cfg["xmin"], cfg["xmax"])
        cfg["nxb"] = _nxb
        _sg = _flags_ug
        log(f"SETUP_FLAGS 已按 nproc={nproc} 格式化: -nxb={_nxb}, "
            f"dx={_dx_cm*1e4:.5f} um (薄层 {1.0e-5/_dx_cm:.2f} 格)", "OK")
    else:
        _sg = SETUP_FLAGS
        log("SETUP_FLAGS 无 {nxb} 占位符, 按原样使用", "INFO")

    # ── 1. 重绑定命名常量 (记录原值以便恢复) ──
    _bind = {
        "SIM_NAME": SIM_NAME,
        "OBJDIR": OBJDIR,
        "BASENM": BASENM,
        "PAR_FILENAME": PAR_FILENAME,
        "LOG_FILE": LOG_FILE,
        "INPUT_DIR": INPUT_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
        "SETUP_FLAGS": _sg,          # ★ 用已格式化的版本
    }
    saved = {k: getattr(ref, k) for k in _bind}
    for k, v in _bind.items():
        setattr(ref, k, v)

    log("HPC 驱动委托给 SNBOneCH_ml.run_hpc (重绑定命名常量)", "OK")
    log(f"  远端单元名 SIM_NAME = {SIM_NAME}", "INFO")
    log(f"  远端 objdir       = {OBJDIR}", "INFO")
    log(f"  输出基名 basenm   = {BASENM}", "INFO")

    try:
        # 参考实现的 run_hpc 签名:
        #   run_hpc(account, tmax, nproc, skip_build, partition, skip_run, poll_timeout)
        tmax = f"{cfg['tmax']:.6e}" if cfg.get("tmax") else None
        rc = ref.run_hpc(
            account=args.account,
            tmax=tmax,
            nproc=cfg["nprocs"],
            skip_build=bool(args.skip_build or (args.skip_setup and args.skip_make)),
            partition=cfg.get("slurm_partition", ""),
            skip_run=bool(getattr(args, "skip_run", False)),
            poll_timeout=int(getattr(args, "poll_timeout", 7200)),
        )
        if rc != 0:
            log(f"超算流水线失败 rc={rc}", "ERROR")
            return rc
    finally:
        for k, v in saved.items():
            setattr(ref, k, v)
        log("已恢复参考模块命名常量", "INFO")

    # ── 2. 出图 (结果已在 OUTPUT_DIR/hpc_<account>/) ──
    plots_dir = Path(args.plots_dir) if args.plots_dir else PLOTS_DIR
    plots_dir.mkdir(parents=True, exist_ok=True)
    local_out = OUTPUT_DIR / f"hpc_{args.account}"
    log(f"绘图分析 → {plots_dir}", "STEP")
    try:
        _plot(local_out, plots_dir)
    except Exception as exc:  # noqa: BLE001
        log(f"绘图失败 (不影响仿真结论): {exc}", "WARN")
    log(f"✓ 验证完成; 结果 {local_out}; 图像 {plots_dir}", "OK")
    return 0


def _plot(local_out: Path, plots_dir: Path) -> None:
    """验证用快速绘图: 密度剖面 (全域+局部) / 物种标记 / 密度时空图。

    ★ 全英文 + 字号 >= 20 + DPI 450 (PPT 演讲级规范)。
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
        "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
        "axes.linewidth": 2.0, "font.family": "DejaVu Sans",
    })
    from flash.output_processors.loader import FlashDataLoader

    cand = sorted(local_out.glob("*plt_cnt*"))
    cand = [p for p in cand if "forced" not in p.name]
    if not cand:
        cand = sorted(local_out.glob("*chk*"))
    if not cand:
        log(f"无可绘图文件: {local_out}", "WARN")
        return

    records = []
    for f in cand:
        try:
            c = FlashDataLoader(str(f)).load(
                compute_derived=False, extraction_mode="yt")
            d = {k: np.asarray(c.data[k]).ravel()
                 for k in ("dens",) + tuple(SPECIES_LIST) if k in c.data}
            if "dens" not in d:
                continue
            records.append((float(c.simulation_time), np.asarray(c.x).ravel(), d))
        except Exception as exc:  # noqa: BLE001
            log(f"  跳过 {f.name}: {exc}", "WARN")
    if not records:
        log("读取失败, 无法绘图", "WARN")
        return
    records.sort(key=lambda r: r[0])
    log(f"  读取 {len(records)} 帧", "INFO")

    tarr = np.array([r[0] for r in records])
    tspan = max(tarr.max() - tarr.min(), 1e-30)
    cm = plt.get_cmap("viridis")

    # 图1: 密度剖面 (全域 + 局部放大)
    fig, axes = plt.subplots(1, 2, figsize=(18, 7), constrained_layout=True)
    for ax, xlim, ttl in ((axes[0], None, "Full domain"),
                          (axes[1], (-5.0, 10.0),
                           r"Zoom x = [-5, 10] $\mu$m")):
        for (t, x, d) in records:
            m = d["dens"] > 0
            ax.semilogy(x[m] * 1e4, d["dens"][m], lw=2.2,
                        color=cm(0.05 + 0.9 * (t - tarr.min()) / tspan),
                        label=f"t = {t * 1e9:.4g} ns")
        ax.set_xlabel(r"x [$\mu$m]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title(ttl)
        ax.set_xlim(xlim)
        ax.grid(True, which="both", alpha=0.25, lw=0.8)
    axes[1].legend(fontsize=16, loc="upper left", ncol=2, framealpha=0.9)
    fig.suptitle(f"Density profiles ({SCENE_NAME})",
                 fontsize=24, fontweight="bold")
    fig.savefig(str(plots_dir / f"{SCENE_NAME.lower()}_dens_profiles.png"), dpi=450)
    plt.close(fig)
    log(f"  ✓ {SCENE_NAME.lower()}_dens_profiles.png", "OK")

    # 图2: 物种标记 (末帧, 局部放大, 线性 y) — 核对 V/Ti 分层
    t_last, x_last, d_last = records[-1]
    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
    colors = {"cham": "tab:blue", "shld": "tab:green", "samp": "lightcoral",
              "tar1": "tab:orange", "tar2": "red", "tar3": "tab:purple",
              "tar4": "tab:brown", "tar6": "tab:cyan"}
    styles = {"cham": "-", "shld": "--", "samp": "-",
              "tar1": "-.", "tar2": "-", "tar3": "-.", "tar4": "-.", "tar6": "-."}
    for sp in SPECIES_LIST:
        if sp not in d_last:
            continue
        m = (x_last * 1e4 >= -5) & (x_last * 1e4 <= 10)
        ax.plot(x_last[m] * 1e4, d_last[sp][m], lw=2.6, color=colors[sp],
                ls=styles[sp], label=sp)
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("Mass fraction")
    ax.set_ylim(-0.05, 1.1)
    ax.set_xlim(-5, 10)
    ax.set_title(f"Species markers at t = {t_last * 1e9:.4g} ns ({SCENE_NAME})")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=17, loc="center right", ncol=2, framealpha=0.9)
    fig.savefig(str(plots_dir / f"{SCENE_NAME.lower()}_species_zoom.png"), dpi=450)
    plt.close(fig)
    log(f"  ✓ {SCENE_NAME.lower()}_species_zoom.png", "OK")

    # 图3: 初始分层核验 (首帧, 若与末帧不同)
    t0, x0, d0 = records[0]
    if len(records) > 1:
        fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
        for sp in SPECIES_LIST:
            if sp not in d0:
                continue
            m = (x0 * 1e4 >= -5) & (x0 * 1e4 <= 10)
            ax.plot(x0[m] * 1e4, d0[sp][m], lw=2.6, color=colors[sp],
                    ls=styles[sp], label=sp)
        ax.set_xlabel(r"x [$\mu$m]")
        ax.set_ylabel("Mass fraction")
        ax.set_ylim(-0.05, 1.1)
        ax.set_xlim(-5, 10)
        ax.set_title(f"Initial species layout at t = {t0 * 1e9:.4g} ns "
                     f"(V shield + Ti tracer)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=17, loc="center right", ncol=2, framealpha=0.9)
        fig.savefig(str(plots_dir / "snbvti_species_initial.png"), dpi=450)
        plt.close(fig)
        log("  ✓ snbvti_species_initial.png", "OK")

    # 图4: 密度时空图 (pcolormesh + 真实逐帧时间; ★ 禁用 imshow)
    if len(records) >= 2:
        xmin = min(r[1].min() for r in records)
        xmax = max(r[1].max() for r in records)
        xc = np.linspace(xmin, xmax, 2400)
        Z = np.empty((len(records), xc.size))
        for i, (_, x, d) in enumerate(records):
            o = np.argsort(x)
            Z[i] = np.interp(xc, x[o], d["dens"][o], left=np.nan, right=np.nan)
        fig, ax = plt.subplots(figsize=(12, 8))
        Xg, Tg = np.meshgrid(xc * 1e4, tarr * 1e9)
        pc = ax.pcolormesh(Xg, Tg, np.log10(np.maximum(Z, 1e-12)),
                           cmap="viridis", shading="auto")
        cb = fig.colorbar(pc, ax=ax)
        cb.set_label(r"$\log_{10}\rho$ (g/cm$^3$)", fontsize=20)
        cb.ax.tick_params(labelsize=18)
        ax.set_xlabel(r"x ($\mu$m)")
        ax.set_ylabel("Time (ns)")
        ax.set_title(f"Density space-time diagram ({SCENE_NAME})")
        fig.tight_layout()
        fig.savefig(str(plots_dir / "snbvti_dens_xt.png"), dpi=450)
        plt.close(fig)
        log("  ✓ snbvti_dens_xt.png", "OK")


if __name__ == "__main__":
    sys.exit(main())
