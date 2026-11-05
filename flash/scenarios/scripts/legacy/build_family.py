"""
build_family — CHTi 家族场景脚本派生器
═══════════════════════════════════════════════════════════════════

从主模板 CHTi/CHTi1.py 派生家族其余脚本。家族各脚本 **仅两处不同**:
  1. 文件头 docstring (场景说明);
  2. "BEGIN SCENE VARS ... END SCENE VARS" 场景差异参数块
     (SCENE_NAME / SHLD_MATERIAL / TI_LAYER / RADIATION_OFF)。
其余全部代码逐字节相同 — 修改公共逻辑只改模板后重跑本脚本即可。

家族清单 (生成目标):
  CHTi/CHTi2.py        tar2 = Ti @2um, shld=CH, 辐射开
  CHTi/CHTi3.py        tar3 = Ti @3um, shld=CH, 辐射开
  VCH_ml_F/VCH_ml_F.py shld=V (钒屏蔽层), 无 Ti, 辐射关
  CHTi_F/CHTi1_F.py    tar1 = Ti @1um, shld=CH, 辐射关
  CHTi_F/CHTi2_F.py    tar2 = Ti @2um, shld=CH, 辐射关
  CHTi_F/CHTi3_F.py    tar3 = Ti @3um, shld=CH, 辐射关

用法 (在 flash 包根目录):
  python flash/scenarios/private/tracer/build_family.py

关辐射机制 (学习自参考 ReDo042sp_CH042sp*umF8.00e-02 vs *umL8.00e-02):
源码/setup/编译完全不变 (Makefile 与全部 F90 逐字节相同), 纯运行时在 .par
中置 rt_useMGD=.false. / useOpacity=.false. 并补 useRadTrans=.false.。
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "CHTi" / "CHTi1.py"

_BEGIN = "# ── BEGIN SCENE VARS (CHTi 家族各脚本仅此块不同; build_family.py 换块生成) ──"
_END_PREFIX = "# ── END SCENE VARS"


def make_doc(scene: str, shld: str, ti_layer, rad_off: bool,
             pkg: str) -> str:
    """生成场景 docstring (与模板同构, 按差异参数定制)。"""
    ti_desc = (f"{ti_layer} (Ti-BADGER-TOPS.cn4, rho 4.54 g/cm^3)"
               if ti_layer else "无 (tar* 全 CH)")
    if shld == "V":
        mat_desc, shld_line = "CH 基体 + V 屏蔽层", "shld [钒 V, 6.11]  (V 屏蔽层, 同 VCH_ml)"
    else:
        mat_desc, shld_line = "纯 CH 基体 (无屏蔽层)", "shld [碳氢 CH, 1.0]  (无 V 屏蔽层)"
    rad_desc = "关闭 (F 变体: rt_useMGD/useOpacity/useRadTrans 均 .false.)" \
        if rad_off else "MGD 10 能群开启"

    def tar_line(idx, L):
        if ti_layer == f"tar{idx}":
            return f"      L{idx:.<{max(2, 8 - len(str(L)))}}".replace(".", "") \
                if False else (
                    f"      L{idx}       < x < L{idx}+delta      tar{idx} [钛 Ti, 4.54]"
                    f"  ← Ti 示踪层 @{L}um")
        return f"      L{idx}       < x < L{idx}+delta      tar{idx} [碳氢 CH]"

    lines = [
        f"{scene} 场景 — 1D 多薄层示踪靶 ({mat_desc}) 仿真",
        "═══════════════════════════════════════════════════════════════════",
        "",
        "由 CHTi1 模板 (源出 OneCH_ml) 经 tracer/build_family.py 生成。",
        "家族: CHTi1/CHTi2/CHTi3 仅 Ti 层深度不同 (tar1@1um/tar2@2um/tar3@3um);",
        "* _F 后缀 = 关辐射变体 (RADIATION_OFF=True, 机制同参考 ReDo042sp_*umF);",
        "VCH_ml_F = V 屏蔽层 + 关辐射。",
        f"本脚本: shld={shld}, Ti 层={ti_desc}, 辐射: {rad_desc}。",
        "",
        "  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096",
        "  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲",
        "  * 8 物种 12 区分层（delta=0.1um, L1=1um, L2=2um, L3=3um, L4=4um,",
        "    L6=6um, D=50um; 示踪层间距均为 samp）:",
        "",
        "      x < 0                        cham [氦 He, 1e-6 g/cm^3]",
        f"      0        < x < delta         {shld_line}",
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
        "    常温 (290.11375 K) 固体密度 (Ti 4.54, V 6.11, CH 1.0); tar* 用独立",
        "    物种标记以便诊断追踪。",
        f"  * 辐射: {rad_desc}；tabular EOS/opacity (ionmix4)",
        "",
        "用法:",
        "  cd <flash 包目录>",
        f"  python flash/scenarios/private/tracer/{pkg}/{scene}.py               # 默认 tmax=1.0e-11",
        f"  python flash/scenarios/private/tracer/{pkg}/{scene}.py --tmax 1.6e-9 # 正式运行",
        f"  # 或 python -m flash.scenarios.private.tracer.{pkg}.{scene}",
    ]
    return '"""\n' + "\n".join(lines) + '\n"""\n'


def make_vars(scene: str, shld: str, ti_layer, rad_off: bool) -> str:
    """生成场景差异参数块 (含首尾标记行)。"""
    ti_repr = f'"{ti_layer}"' if ti_layer else "None"
    end_tail = "─" * (76 - len(_END_PREFIX) + 8)
    return (
        f"{_BEGIN}\n"
        f'SCENE_NAME = "{scene}"'
        f'{" " * max(1, 16 - len(scene) - 3)}# 场景名 → SIM_NAME/par 文件名/图题/SLURM 作业名\n'
        f'SHLD_MATERIAL = "{shld}"'
        f'{" " * max(1, 12 - len(shld) - 3)}# "CH"=无屏蔽层 (纯 CH, OneCH 系); "V"=钒屏蔽层 (VCH 系)\n'
        f"TI_LAYER = {ti_repr}"
        f'{" " * max(1, 15 - len(ti_repr) - 2)}# Ti 示踪层所在物种; None=无 Ti 层 (tar* 全 CH)\n'
        f"RADIATION_OFF = {rad_off}"
        f'{" " * (4 if rad_off else 5)}# True=关闭辐射输运 (F 变体)\n'
        f"{_END_PREFIX}{end_tail}\n"
    )


def build() -> int:
    text = TEMPLATE.read_text(encoding="utf-8")
    if text.count(_BEGIN) != 1 or not text.count(_END_PREFIX) == 1:
        print("[X] 模板场景参数块标记异常 (须恰出现一次)")
        return 1

    # 切分模板: 头 docstring | 主体 (含 SCENE VARS 块)
    first = text.index('"""')
    second = text.index('"""', first + 3) + 3
    doc_old = text[:second]
    body_old = text[second:]

    # 替换 SCENE VARS 块
    b0 = body_old.index(_BEGIN)
    b1 = body_old.index("\n", body_old.index(_END_PREFIX)) + 1
    body_tpl = body_old[:b0] + "{VARS}" + body_old[b1:]

    variants = [
        # (scene, pkg, shld, ti_layer, rad_off)
        ("CHTi2", "CHTi", "CH", "tar2", False),
        ("CHTi3", "CHTi", "CH", "tar3", False),
        ("VCH_ml_F", "VCH_ml_F", "V", None, True),
        ("CHTi1_F", "CHTi_F", "CH", "tar1", True),
        ("CHTi2_F", "CHTi_F", "CH", "tar2", True),
        ("CHTi3_F", "CHTi_F", "CH", "tar3", True),
    ]
    for scene, pkg, shld, ti, rad in variants:
        out_dir = HERE / pkg
        out_dir.mkdir(parents=True, exist_ok=True)
        content = make_doc(scene, shld, ti, rad, pkg) + body_tpl.replace(
            "{VARS}", make_vars(scene, shld, ti, rad))
        out = out_dir / f"{scene}.py"
        out.write_text(content, encoding="utf-8", newline="\n")
        print(f"[OK] {out.relative_to(HERE)}")
    print(f"\n共生成 {len(variants)} 个家族脚本 (模板: {TEMPLATE.name})")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(build())
