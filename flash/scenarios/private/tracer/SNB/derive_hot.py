# -*- coding: utf-8 -*-
"""derive_hot.py — 从 SNBVTi2um 派生 SNBVTi2um_hot（群分辨落盘变体场景）.

★★ 唯一差别（物理/材料/激光/网格/SNB 参数全部不变）:
    1. diff_advanceTherm.F90 ← gpDump 变体（19 群 Q_g/Λ_g/ν_g → chk 群维变量
       CG01..CG19/MP01..MP19/MR01..MR19，受 par 开关 sim_snbGpDump 控制；
       .false. 时代码路径与基础版逐位一致 —— 变体隔离，基础 SNB F90 不动）
    2. Config 扩展: +57 个群维 VARIABLE + PARAMETER sim_snbGpDump BOOLEAN
    3. par: sim_snbGpDump=.true.（--gpdump-off 可切换为 .false.，开关对照跑用）
    4. checkpoint_interval_step: 400 → 2（极短测试取多帧 chk）
    5. 场景名/输出基名/日志名全隔离（远端 run.sh 的 rm -f {BASENM}* 不波及母场景）
只生成 .py 场景文件与 scene.json；flash_input 由场景自身 --generate-only 生成。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

SNB_DIR = Path(__file__).resolve().parent
SRC, DST = "SNBVTi2um", "SNBVTi2um_hot"

GP_VARS = (
    "\n# ── gpDump: per-group SNB diagnostics (CG=Q_g, MP=Lambda_g, MR=nu_g) ──\n"
    "# 由 diff_advanceTherm_gpDump.F90 变体写入（par 开关 sim_snbGpDump）\n"
    + "".join(f"VARIABLE CG{k:02d}\n" for k in range(1, 20))
    + "".join(f"VARIABLE MP{k:02d}\n" for k in range(1, 20))
    + "".join(f"VARIABLE MR{k:02d}\n" for k in range(1, 20))
    + "D sim_snbGpDump dump per-group SNB diagnostics (Q_g/Lambda_g/nu_g) to chk\n"
    "PARAMETER sim_snbGpDump BOOLEAN FALSE\n"
)

GPDUMP_OVERRIDE = '''    # ★★★ 本场景专属 (gpDump, 2026-11-09): 群分辨落盘变体覆盖 diff_advanceTherm。
    #   19 群 Q_g/Λ_g/ν_g → chk 变量 CG01..CG19/MP01..MP19/MR01..MR19，
    #   受 par 开关 sim_snbGpDump 控制（.false. 与基础版逐位一致）。
    #   基础 SNB F90 不动 —— 变体隔离（同 radON 模式），见 SNB/SNB/variants/。
    gpdump = _SNB_VARIANTS_DIR / "diff_advanceTherm_gpDump.F90"
    if not gpdump.is_file():
        log(f"gpDump 变体缺失: {gpdump}", "ERROR")
        return False
    shutil.copyfile(gpdump, INPUT_DIR / "diff_advanceTherm.F90")
    _gp = (INPUT_DIR / "diff_advanceTherm.F90").read_bytes()
    rows = [(fn, len(_gp), hashlib.sha256(_gp).hexdigest())
            if fn == "diff_advanceTherm.F90" else (fn, nb, dg)
            for fn, nb, dg in rows]
    _gp_names = ([f"CG{k:02d}" for k in range(1, 20)]
                 + [f"MP{k:02d}" for k in range(1, 20)]
                 + [f"MR{k:02d}" for k in range(1, 20)])
    if not (_gp.count(b"sim_snbGpDump") == 1
            and all(_gp.count(f"{n}_VAR".encode()) == 1 for n in _gp_names)):
        log("gpDump 变体异常: sim_snbGpDump / 群变量宏缺失", "ERROR")
        return False
    log("    diff_advanceTherm.F90 ← gpDump 变体 "
        "(sim_snbGpDump + 57 群维变量) ✓", "OK")

'''

GPDUMP_ARG = '''ap.add_argument("--gpdump-off", action="store_true",
                help="生成 par 时 sim_snbGpDump=.false.（开关对照跑用）")
    ap.add_argument("--chk-every", type=int, default=None,
                    help="覆盖 checkpointFileIntervalStep（长跑用 400 与母场景基线对齐；默认沿用 cfg 值 2=极短测试）")
'''

GPDUMP_CFG = '''    if args.gpdump_off:
        cfg["sim_snbGpDump"] = False
        log("    --gpdump-off: par sim_snbGpDump=.false. (开关对照跑)", "OK")
    if args.chk_every is not None:
        cfg["checkpoint_interval_step"] = int(args.chk_every)
        log(f"    --chk-every: checkpointFileIntervalStep={args.chk_every}", "OK")
'''

BANNER = """
## ★★★ 本文件由 {src} 程序化派生 ({date}) —— 群分辨落盘变体 (hot 场景)

    唯一差别（物理/材料/激光/网格/SNB 参数全部不变）:
      1. diff_advanceTherm.F90 ← **gpDump 变体**: 19 群 Q_g/Λ_g/ν_g 落盘到
         chk 群维变量 CG01..CG19 / MP01..MP19 / MR01..MR19（共 57 个），
         受 par 开关 **sim_snbGpDump** 控制；.false. 时代码路径与基础版
         **逐位一致**。基础 SNB F90 不动（变体隔离，同 radON 模式）。
      2. Config: +57 群维 VARIABLE + PARAMETER sim_snbGpDump BOOLEAN FALSE
      3. par: sim_snbGpDump=.true.（CLI --gpdump-off 可切 .false.）
      4. checkpointFileIntervalStep: 400 → 2（极短测试取多帧 chk）
      5. 输出隔离: BASENM=snbvti2umhotug_ / OBJDIR=SNBVTi2um_hot_ug_obj
    用途: FLYCHK fe/fhot 电子分布函数重建的群分辨数据源（Schurtz 2000 群输运
    关系 → f₁(E) → fe(E)=f₀+f₁ → 两麦氏拟合），见 SNB/SNB/scripts/analysis/
    snb_group_pipeline.py。
"""


def rep1(text: str, old: str, new: str) -> str:
    n = text.count(old)
    assert n == 1, f"锚点 {old!r} 出现 {n} 次 (期望 1)"
    return text.replace(old, new)


def derive() -> None:
    src_path = SNB_DIR / SRC / f"{SRC}.py"
    text = io.open(src_path, encoding="utf-8").read()

    # ── 1. 名字替换（先大写后小写；小写仅 3 处常量，自动得到隔离命名）──
    text = text.replace(SRC, DST)
    text = text.replace(SRC.lower(), "snbvti2umhot")
    # 终态断言（与母场景 run.sh rm -f {BASENM}* 完全隔离）
    assert 'BASENM = "snbvti2umhotug_"' in text
    assert 'BASENM_AMR = "snbvti2umhot_"' in text
    assert 'LOG_FILE = "snbvti2umhot.log"' in text
    assert 'SCENE_NAME = "SNBVTi2um_hot"' in text
    assert 'snbvti2umhotug_' in text and text.count('snbvti2umug_') == 0

    # ── 2. Config 扩展: 57 群变量 + sim_snbGpDump 参数 ──
    text = rep1(text, "VARIABLE COGQ\n\"\"\"", "VARIABLE COGQ\n" + GP_VARS + "\"\"\"")

    # ── 3. par 开关注入（gr_hypreUseFloor 铁律之后）──
    anchor = 'par_gen.set("gr_hypreUseFloor", False)'
    text = rep1(text, anchor,
                anchor + '\n    par_gen.set("sim_snbGpDump", cfg.get("sim_snbGpDump", True))')

    # ── 4. gpDump 变体部署（radON 覆盖块之后、收尾 log 之前）──
    anchor9 = '    log(f"    9 个 SNB 覆盖 F90 已落盘'
    text = rep1(text, anchor9, GPDUMP_OVERRIDE + anchor9)

    # ── 4b. 静态核验: diff_advanceTherm 按 gpDump 变体校验（而非基础版镜像）──
    anchor_pkg = "        src = _SNB_PKG_DIR / fn\n"
    gpdump_verify = '''        if fn == "diff_advanceTherm.F90":
            # ★ gpDump: diff_advanceTherm 校验 gpDump 变体而非基础版镜像
            src = _SNB_VARIANTS_DIR / "diff_advanceTherm_gpDump.F90"
            if not src.exists():
                log(f"  ✗ gpDump 变体缺失: {src}", "ERROR"); ok = False
                _ovr_bad.append(fn); continue
            dh = hashlib.sha256(dst.read_bytes()).hexdigest()
            sh_ = hashlib.sha256(src.read_bytes()).hexdigest()
            if dh != sh_:
                log(f"  ✗ {fn} 不是 gpDump 变体 (dst={dh[:12]} "
                    f"期望={sh_[:12]})", "ERROR")
                ok = False; _ovr_bad.append(fn)
                continue
            if dst.read_bytes().count(b"sim_snbGpDump") != 1:
                log("  ✗ gpDump 变体缺 sim_snbGpDump 开关", "ERROR")
                ok = False; _ovr_bad.append(fn)
            continue
'''
    text = rep1(text, anchor_pkg, gpdump_verify + anchor_pkg)
    old_msg = ('log(f"  ✓ SNB 覆盖 F90 自包含 9/9 (8 个与镜像一致 + "\n'
               '            f"Driver=radON 变体, 辐射联动 ✓)", "OK")')
    new_msg = ('log(f"  ✓ SNB 覆盖 F90 自包含 9/9 (7 个与镜像一致 + "\n'
               '            f"Driver=radON 辐射联动 + diff=gpDump 群落盘 ✓)", "OK")')
    text = rep1(text, old_msg, new_msg)

    # ── 5. CLI --gpdump-off + cfg 覆写 ──
    text = rep1(text, 'ap.add_argument("--account"',
                GPDUMP_ARG.rstrip("\n") + '\n' + '    ap.add_argument("--account"')
    text = rep1(text, 'cfg["tmax"] = args.tmax',
                'cfg["tmax"] = args.tmax\n' + GPDUMP_CFG.rstrip("\n"))

    # ── 6. 极短测试取多帧 chk ──
    text = rep1(text, '"checkpoint_interval_step": 400,',
                '"checkpoint_interval_step": 2,')

    # ── 7. docstring 头部插 banner ──
    lines = text.split("\n")
    assert lines[0].startswith('"""'), DST
    banner = BANNER.format(src=SRC, date="2026-11-09").rstrip("\n")
    text = "\n".join([lines[0], banner] + lines[1:])

    dst_dir = SNB_DIR / DST
    dst_dir.mkdir(exist_ok=True)
    out = dst_dir / f"{DST}.py"
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(f"[OK] {SRC} -> {out.name} ({len(text.splitlines())} 行)")

    # ── 8. scene.json 改名 ──
    sj_path = dst_dir / "scene.json"
    sj = json.loads(sj_path.read_text(encoding="utf-8"))
    sj["name"] = DST
    sj["aliases"] = [DST.lower()]
    sj["description"] = (
        "SNB 群分辨落盘变体场景（gpDump）：物理与 SNBVTi2um 完全相同，"
        "diff_advanceTherm ← gpDump 变体，19 群 Q_g/Λ_g/ν_g → chk（sim_snbGpDump 开关）；"
        "FLYCHK fe/fhot 电子分布函数重建数据源"
    )
    sj["script"] = f"./{DST}.py"
    sj["sim_name"] = DST
    sj["hpc"]["gen_script"] = f"./{DST}.py"
    sj["hpc"]["flash_unit"] = DST
    sj["hpc"]["par_file"] = f"{DST.lower()}.par"
    sj["hpc"]["archive_patterns"] = ["snbvti2umhotug_*"]
    sj_path.write_text(json.dumps(sj, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print(f"[OK] scene.json 已更新 ({sj_path.name})")


def main() -> int:
    derive()
    # ── 9. 清理陈旧母场景 par ──
    stale = SNB_DIR / DST / "flash_input" / f"{SRC.lower()}.par"
    if stale.exists():
        stale.unlink()
        print(f"[OK] 删除陈旧母场景 par: {stale.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
