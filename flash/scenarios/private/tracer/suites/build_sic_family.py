"""
build_sic_family — 由 OneSi_ml 主模板派生单一纯材料场景家族
═══════════════════════════════════════════════════════════════════

主模板: OneSi_ml/OneSi_ml.py (Si, 辐射开)。
家族各脚本除 docstring 与 SCENE VARS 块外逐字节相同 (与 build_family.py
同机制)。派生变体:

  OneSi_ml_F   Si,  辐射关 (RADIATION_OFF=True)
  OneC_ml      C,   辐射开
  OneC_ml_F    C,   辐射关

材料数据 (表名 "Z{Z}_{rho0}" 约定: Z=核电荷数, rho0=表生成密度 g/cm^3):
  Si: Z14_1.00-20260708_0850.cn4, rho=2.329 (常温固体), A=28.0855, Z=14
  C : Z06_1.00-20260902_2228.cn4, rho=3.515 (金刚石密度), A=12.011,  Z=6
  (C 表暂未收录 gen_eos_op 注册表, 场景脚本经 eos_op_data rglob 兜底查找)

用法:
  python flash/scenarios/private/tracer/build_sic_family.py
"""

import sys
from pathlib import Path

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
MASTER = HERE / "OneSi_ml" / "OneSi_ml.py"

# 材料 → (标签, 表文件, rho, A, Z)
MATERIALS = {
    "Si": ("Si", "Z14_1.00-20260708_0850.cn4", 2.329, 28.0855, 14.0),
    "C": ("C", "Z06_1.00-20260902_2228.cn4", 3.515, 12.011, 6.0),
}

# 变体 → (目录名, 材料键, 辐射关)
VARIANTS = [
    ("OneSi_ml_F", "Si", True),
    ("OneC_ml", "C", False),
    ("OneC_ml_F", "C", True),
]

# 材料中文名 (docstring 用)
MAT_CN = {"Si": "硅", "C": "碳"}


def make_doc(scene: str, mat_key: str, rad_off: bool) -> str:
    label, table, rho, a, z = MATERIALS[mat_key]
    cn = MAT_CN[mat_key]
    rad_line = ("辐射: 关闭 (F 变体: rt_useMGD/useOpacity/useRadTrans 均 .false.)"
                if rad_off else
                "MGD 6 能群辐射（Gen_eos_op_data 表族结构, 十倍程边界 0.1 eV → 1e5 eV;\n"
                "    腔室 He 表同步采用同族 6 群 Z02 表, 与 ch_center 场景先例一致）,\n"
                "    tabular EOS/opacity (ionmix4)")
    return f'''"""
{scene} 场景 — 1D 多薄层单一纯材料 ({cn} {label}) 示踪靶烧蚀仿真
═══════════════════════════════════════════════════════════════════

由 OneSi_ml 场景派生 (2026-09-02)：结构/物种/几何完全一致, 唯一物理差异是
**全部固体层 (shld/samp/tar1/tar2/tar3/tar4/tar6) 为同一种纯材料 {label}**
(密度 {rho!r} g/cm^3 常温固体密度, EOS/不透明度表 {table},
A={a}, Z={z:g}) — 单一纯材料烧蚀仿真, shld/tar* 物种标记仅用于
诊断追踪不同深度的材料运动 (无成分界面, 只有物种标记界面)。

与 OneCH_ml 的唯一物理差异: 固体层材质 CH → {label} (含 shld/samp/tar* 全部
固体物种); 腔室 cham 仍为稀氦 He (1e-6 g/cm^3)。

  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096
  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 8 物种 12 区分层（delta=0.1um, L1=1um, L2=2um, L3=3um, L4=4um,
    L6=6um, D=50um; 示踪层间距均为 samp）:

      x < 0                        cham [氦 He, 1e-6 g/cm^3]
      0        < x < delta         shld [{cn} {label}, {rho:.2f} g/cm^3]  ← 表面层标记
      delta    < x < L1            samp [{cn} {label}, {rho:.2f} g/cm^3]
      L1       < x < L1+delta      tar1 [{cn} {label}]  ← 示踪薄层 1
      L1+delta < x < L2            samp [{cn} {label}]
      L2       < x < L2+delta      tar2 [{cn} {label}]  ← 示踪薄层 2
      L2+delta < x < L3            samp [{cn} {label}]
      L3       < x < L3+delta      tar3 [{cn} {label}]  ← 示踪薄层 3
      L3+delta < x < L4            samp [{cn} {label}]
      L4       < x < L4+delta      tar4 [{cn} {label}]  ← 示踪薄层 4
      L4+delta < x < L6            samp [{cn} {label}]
      L6       < x < L6+delta      tar6 [{cn} {label}]  ← 示踪薄层 6
      L6+delta < x < L6+delta+D    samp [{cn} {label}]
      其余 (x<-0.04 域外 / x>56.1um)  cham [氦 He]

  * 8 物种标记: cham/shld/samp/tar1/tar2/tar3/tar4/tar6。固体层初始均为
    常温 (290.11375 K) 密度 {rho:.2f} g/cm^3 纯 {label}; 各标记层物质相同, 用独立
    物种标记以便诊断追踪 (材质单一 → 烧蚀过程无材料界面)。
  * {rad_line}
  * 时间: 默认 tmax=1.0e-11 s (极短验证); 正式物理运行手动改 1.6e-9
    或用 --tmax 覆盖。

用法:
  cd <flash 包目录>
  python -m flash.scenarios.private.tracer.{scene}.{scene}   # 默认 tmax=1.0e-11
  python flash/scenarios/private/tracer/{scene}/{scene}.py --tmax 1.6e-9
"""'''


def make_vars(scene: str, mat_key: str, rad_off: bool) -> str:
    label, table, rho, a, z = MATERIALS[mat_key]
    scene_pad = " " * max(1, 9 - len(scene))
    lab_pad = " " * max(1, 4 - len(label))
    num_pad = " " * max(1, 13 - len(repr(rho)))
    a_pad = " " * max(1, 13 - len(f"{a}"))
    z_pad = " " * max(1, 15 - len(f"{z:g}"))
    rad_str = "True" if rad_off else "False"
    return (
        "# ── BEGIN SCENE VARS (家族各脚本仅此块+docstring 不同; build_sic_family.py 换块生成) ──\n"
        f'SCENE_NAME = "{scene}"{scene_pad}# 场景名 → SIM_NAME/par 文件名/图题/SLURM 作业名\n'
        f'MAT_LABEL = "{label}"{lab_pad}# 固体材料标签 ({MAT_CN[mat_key]})\n'
        f'MAT_TABLE = "{table}"   # EOS/不透明度表 (表名 1.00 为生成标称密度)\n'
        f'MAT_RHO = {rho!r}{num_pad}# 固体密度 g/cm^3 (常温固体密度; 表内密度网格为离子数密度, 覆盖充足)\n'
        f'MAT_A = {a}{a_pad}# 摩尔质量 g/mol\n'
        f'MAT_Z = {z:g}{z_pad}# 核电荷数\n'
        f'RADIATION_OFF = {rad_str} # True=关闭辐射输运 (F 变体: 三开关 .false.)\n'
        "# ── END SCENE VARS ──────────────────────────────────────────────────────────"
    )


def split_master(text: str):
    """拆分主模板 → (docstring, 前段, SCENE VARS 块, 后段)。"""
    # docstring: 第一对 """ 之间
    first = text.index('"""')
    second = text.index('"""', first + 3) + 3
    doc = text[:second]
    rest = text[second:]
    # SCENE VARS 块
    b0 = rest.index("# ── BEGIN SCENE VARS")
    b1 = rest.index("# ── END SCENE VARS")
    e1 = rest.index("\n", b1) + 1
    head = rest[:b0]
    block = rest[b0:e1]
    tail = rest[e1:]
    return doc, head, block, tail


def main() -> int:
    text = MASTER.read_text(encoding="utf-8")
    doc, head, block, tail = split_master(text)
    assert block.count("# ── BEGIN SCENE VARS") == 1
    assert block.count("# ── END SCENE VARS") == 1

    for scene, mat_key, rad_off in VARIANTS:
        out_dir = HERE / scene
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"{scene}.py"
        # 拼接须精确复刻主模板结构: make_doc 以 """ 结尾 (其后 head 自带
        # "\n\n"), make_vars 以 END 行结尾 (补 "\n" 使 block 以换行收尾,
        # tail 首个 "\n" 还原空行) — 保证 head/tail 与主模板逐字节相同。
        content = (make_doc(scene, mat_key, rad_off) + head
                   + make_vars(scene, mat_key, rad_off) + "\n" + tail)
        out_path.write_text(content, encoding="utf-8", newline="\n")
        print(f"[OK] {out_path}")

    # 自检: 各变体与主模板仅 docstring + SCENE VARS 块不同
    m_doc, m_head, m_block, m_tail = split_master(text)
    ok = True
    for scene, mat_key, rad_off in VARIANTS:
        v = (HERE / scene / f"{scene}.py").read_text(encoding="utf-8")
        v_doc, v_head, v_block, v_tail = split_master(v)
        if (v_head, v_tail) != (m_head, m_tail):
            print(f"[X] {scene}: SCENE VARS 块之外存在差异!")
            ok = False
        if v_block == m_block:
            print(f"[X] {scene}: SCENE VARS 块未变 (派生失败)")
            ok = False
    print("[OK] 家族自检通过: 变体仅 docstring + SCENE VARS 不同" if ok
          else "[X] 家族自检失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
