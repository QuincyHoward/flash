"""
build_vti_family — 由 TiTi 主模板派生 V 屏蔽层 + Ti 示踪层场景家族
═══════════════════════════════════════════════════════════════════

主模板: TiTi/TiTi1.py (shld=Ti, tar1=Ti @1um, 辐射开)。家族各脚本除
docstring 与 SCENE VARS 块外逐字节相同 (与 build_titi_family.py /
build_family.py / build_sic_family.py 同机制)。派生变体:

  VTi1   tar1 = Ti @1um, shld=V, 辐射开   (主模板等价物)
  VTi2   tar2 = Ti @2um, shld=V, 辐射开
  VTi3   tar3 = Ti @3um, shld=V, 辐射开

与 TiTi 家族唯一物理差异: shld 层材质 Ti → V。因脚本内材质绑定全部由
SCENE VARS 常量驱动, 换 SHLD_MATERIAL = "V" 即自动同步以下四处
(无需改正文):

  ① 材料表文件   Ti-BADGER-TOPS.cn4 → V-BADGER-TOPS.cn4
     (eos_shldTableFile / op_shldFileName)
  ② 固体密度     4.54 → 6.11 g/cm^3 (sim_rhoShld, 常温固体 V)
  ③ 原子量/电荷  A 47.867 → 50.9415, Z 22 → 23 (species_defs → Config)
  ④ cn4 表复制   清单加入 V-BADGER-TOPS.cn4 (缺失即 DRIVER_ABORT)

Ti 示踪层 (tar1/tar2/tar3) 仍为 Ti-BADGER-TOPS.cn4 / 4.54 g/cm^3。

用法:
  python flash/scenarios/private/tracer/build_vti_family.py
"""

import sys
from pathlib import Path

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
MASTER = HERE / "TiTi" / "TiTi1.py"
OUT_DIR = HERE / "VTi"

_BEGIN = "# ── BEGIN SCENE VARS"
_END_PREFIX = "# ── END SCENE VARS"

# 变体 → (场景名, Ti 示踪层物种, 深度 um)
VARIANTS = [
    ("VTi1", "tar1", 1.0),
    ("VTi2", "tar2", 2.0),
    ("VTi3", "tar3", 3.0),
]


def make_doc(scene: str, ti_layer: str, depth_um: float) -> str:
    """生成场景 docstring (与模板 TiTi1 同构, 屏蔽层 V / Ti 示踪层深度定制)。"""
    depth_txt = f"{depth_um:g}"

    def tar_line(idx: int, L: float) -> str:
        if ti_layer == f"tar{idx}":
            return (f"      L{idx}       < x < L{idx}+delta      tar{idx} [钛 Ti, 4.54]"
                    f"  ← Ti 示踪层 @{L:g}um")
        return f"      L{idx}       < x < L{idx}+delta      tar{idx} [碳氢 CH]"

    lines = [
        f"{scene} 场景 — 1D 多薄层示踪靶 (V 屏蔽层 + {depth_txt}um 深 Ti 示踪层) 仿真",
        "═══════════════════════════════════════════════════════════════════",
        "",
        "由 TiTi1 场景派生 (2026-10-17)：与 TiTi 系列唯一物理差异是 shld 层材质",
        "Ti → V (V-BADGER-TOPS.cn4, rho 6.11 g/cm^3, A=50.9415, Z=23), 其余",
        "设置 (几何/物种标记/激光/辐射/Ti 示踪层深度) 完全一致。",
        "",
        "VTi 家族 (不同深度单独一个脚本):",
        "  VTi1  tar1 = Ti @1um",
        "  VTi2  tar2 = Ti @2um",
        "  VTi3  tar3 = Ti @3um",
        f"全部由 tracer/build_vti_family.py 从 TiTi1 模板换块生成, 本脚本: "
        f"Ti 层={ti_layer} (Ti-BADGER-TOPS.cn4, rho 4.54 g/cm^3)。",
        "",
        "  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096",
        "  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲",
        "  * 8 物种 12 区分层（delta=0.1um, L1=1um, L2=2um, L3=3um, L4=4um,",
        "    L6=6um, D=50um; 示踪层间距均为 samp）:",
        "",
        "      x < 0                        cham [氦 He, 1e-6 g/cm^3]",
        "      0        < x < delta         shld [钒 V, 6.11 g/cm^3]  ← V 屏蔽层 (TiTi 中为 Ti)",
        "      delta    < x < L1            samp [碳氢 CH, 1.0 g/cm^3]",
        tar_line(1, 1.0),
        "      L1+delta < x < L2            samp [碳氢 CH]",
        tar_line(2, 2.0),
        "      L2+delta < x < L3            samp [碳氢 CH]",
        tar_line(3, 3.0),
        "      L3+delta < x < L4            samp [碳氢 CH]",
        "      L4       < x < L4+delta      tar4 [碳氢 CH]",
        "      L4+delta < x < L6            samp [碳氢 CH]",
        "      L6       < x < L6+delta      tar6 [碳氢 CH]",
        "      L6+delta < x < L6+delta+D    samp [碳氢 CH]",
        "      其余 (x<-0.04 域外 / x>56.1um)  cham [氦 He]",
        "",
        "  * 8 物种标记: cham/shld/samp/tar1/tar2/tar3/tar4/tar6。固体层初始均为",
        "    常温 (290.11375 K) 固体密度 (V 6.11, Ti 4.54, CH 1.0); tar* 用独立",
        "    物种标记以便诊断追踪。",
        "  * MGD 10 能群辐射，tabular EOS/opacity (ionmix4)",
        "",
        "用法:",
        "  cd <flash 包目录>",
        f"  python flash/scenarios/private/tracer/VTi/{scene}.py               # 默认 tmax=1.0e-11",
        f"  python flash/scenarios/private/tracer/VTi/{scene}.py --tmax 1.6e-9 # 正式运行",
        f"  # 或 python -m flash.scenarios.private.tracer.VTi.{scene}",
    ]
    # 收尾不带换行 — 与主模板闭合 """ 后紧跟 head 首个 "\n\n" 的结构逐字节一致
    return '"""\n' + "\n".join(lines) + '\n"""'


def make_vars(scene: str, ti_layer: str) -> str:
    """生成场景差异参数块 (含首尾标记行; 对齐列与模板一致)。

    首尾标记行的 '─' 填充按主模板实测宽度 (69 / 78 字符) 拉伸, 保持
    与 TiTi 家族脚本一致的视觉框宽。
    """
    def _frame(prefix: str, width: int) -> str:
        return prefix + "─" * max(2, width - len(prefix))

    def _pad(s: str) -> str:
        return s + " " * max(1, 28 - len(s))

    begin_line = _frame(
        "# ── BEGIN SCENE VARS (VTi 家族各脚本仅此块不同; "
        "build_vti_family.py 换块生成) ", 69)
    end_line = _frame(f"{_END_PREFIX} ", 78)

    return (
        begin_line + "\n"
        + _pad(f'SCENE_NAME = "{scene}"')
        + "# 场景名 → SIM_NAME/par 文件名/图题/SLURM 作业名\n"
        + _pad('SHLD_MATERIAL = "V"')
        + '# "V"=钒屏蔽层 (VTi/VCH 系) + V 表 6.11; "Ti"=钛屏蔽层 (TiTi 系); "CH"=无屏蔽层\n'
        + _pad(f'TI_LAYER = "{ti_layer}"')
        + "# Ti 示踪层所在物种; None=无 Ti 层 (tar* 全 CH)\n"
        + _pad("RADIATION_OFF = False")
        + "# True=关闭辐射输运 (F 变体)\n"
        + end_line + "\n"
    )


def split_master(text: str):
    """拆分主模板 → (docstring, 前段, SCENE VARS 块, 后段)。"""
    # docstring: 第一对 """ 之间
    first = text.index('"""')
    second = text.index('"""', first + 3) + 3
    doc = text[:second]
    rest = text[second:]
    # SCENE VARS 块
    b0 = rest.index(_BEGIN)
    b1 = rest.index(_END_PREFIX)
    e1 = rest.index("\n", b1) + 1
    head = rest[:b0]
    block = rest[b0:e1]
    tail = rest[e1:]
    return doc, head, block, tail


def main() -> int:
    text = MASTER.read_text(encoding="utf-8")
    doc, head, block, tail = split_master(text)
    assert block.count(_BEGIN) == 1, "模板 SCENE VARS 块标记异常"
    assert block.count(_END_PREFIX) == 1, "模板 SCENE VARS 块标记异常"

    OUT_DIR.mkdir(exist_ok=True)
    for scene, ti_layer, depth_um in VARIANTS:
        out_path = OUT_DIR / f"{scene}.py"
        # 拼接须精确复刻主模板结构: make_doc 以 """ 结尾 (其后 head 自带
        # "\n\n"), make_vars 以 END 行 + "\n" 收尾 (与 split_master 切出的
        # block 一致, tail 首个 "\n" 还原空行) — 保证 head/tail 与主模板
        # 逐字节相同。
        content = make_doc(scene, ti_layer, depth_um) + head \
            + make_vars(scene, ti_layer) + tail
        out_path.write_text(content, encoding="utf-8", newline="\n")
        print(f"[OK] {out_path}")

    # 自检: 各变体与主模板仅 docstring + SCENE VARS 块不同
    m_doc, m_head, m_block, m_tail = split_master(text)
    ok = True
    for scene, ti_layer, depth_um in VARIANTS:
        v = (OUT_DIR / f"{scene}.py").read_text(encoding="utf-8")
        v_doc, v_head, v_block, v_tail = split_master(v)
        if (v_head, v_tail) != (m_head, m_tail):
            print(f"[X] {scene}: SCENE VARS 块之外存在差异!")
            ok = False
        if v_block == m_block:
            print(f"[X] {scene}: SCENE VARS 块未变 (派生失败)")
            ok = False
        if 'SHLD_MATERIAL = "V"' not in v_block:
            print(f"[X] {scene}: SHLD_MATERIAL 未切到 V")
            ok = False
    print("[OK] 家族自检通过: 变体仅 docstring + SCENE VARS 不同" if ok
          else "[X] 家族自检失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
