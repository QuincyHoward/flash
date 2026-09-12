#!/usr/bin/env python3
"""t006/flnone_test —— `fl_none` 限流模式在 SNB + 辐射开 下的可行性验证
═══════════════════════════════════════════════════════════════════════════════

测试目标
--------
回答两个问题:
  1. `diff_eleFlMode = "fl_none"` 在 **SNB + 辐射开** 下能否跑通、且无异常?
  2. 它与 `fl_harmonic` 基线（t006 的 SNB radON 腿）**数值上是否相同**?

静态分析给出的**待检验预期**
----------------------------
`snb_package/diff_advanceTherm.F90` 的**各向同性电子分支**中:

    :838  else   ! Do isotropic conduction/diffusion
    :839  !        call Diffuse_fluxLimiter(COND_VAR, Temptodiffuse, FLLM_VAR, ...
    :847  !        call Diffuse_solveScalar(Temptodiffuse, COND_VAR, DFCF_VAR, ...

两处调用**均被注释**; 而本场景 `diff_anisoCondForEle = .false.` → 不进入
各向异性分支（`:818` 那个调用点也不进入）。⇒ `diff_eleFlMode` 在电子路径上
**没有任何存活的消费者**, 故预期二者结果**逐位相同**。

本实验即对该预期做**实测判决**:
  · 逐位相同 → 证实该参数在 SNB 路径上是 no-op,
     `docs/05_坑位清单.md` 的 P1 因果表述需要更正;
  · 出现差异 → 说明存在静态分析未发现的引用路径（重要发现，需回溯）。

阶段
----
    prep     生成 fl_none 的 par（短时 + 正常各一份），并与 snb_radon.par 做键级差分自检
    smoke    短时运行 (tmax = 1e-11, chk 加密到 1e-12) —— 可行性判据
    full     正常时间运行 (tmax = 0.8 ns)
    check    chk 健康检查（dt 钳位 / ρmax 走势 / 守恒）
    compare  fl_none vs fl_harmonic 逐帧逐位比对
    plot     5 腿图（SNB×3 + SH×2）
    all      prep → smoke → full → check → compare → plot

★ 设计约束（沿用 t006 的纪律）
-------------------------------
1. **不改源码 / 不改 setup / 不重编译** —— 辐射与限流模式都是**纯运行时 par 开关**;
   本测试只新增两个 par 文件，其余一切复用 t006 已构建好的 objdir。
2. **键级差分自检** —— 新 par 与基线 par 的差异必须**恰好**是预先声明的键集，
   否则拒绝运行（防止"顺手改坏"而不可察觉）。
3. `dtmax` 保持 **2.0e-14**（t006 三条并列前提之一，不得改动）。

用法
----
    PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
    cd flash/scenarios/private/SNB/SNBtest/Test/t006/flnone_test

    $PY run_flnone_test.py --stage prep       # 生成并自检 par
    $PY run_flnone_test.py --stage smoke      # 短时可行性测试 (~1 min)
    $PY run_flnone_test.py --stage full       # 正常时间 (~25 min)
    $PY run_flnone_test.py --stage check      # chk 健康检查
    $PY run_flnone_test.py --stage compare    # 与基线逐帧比对
    $PY run_flnone_test.py --stage plot       # 5 腿图
    $PY run_flnone_test.py --stage all        # 全流程

    # 若 objdir 已被清理, 需要重建编译:
    $PY run_flnone_test.py --stage full --rebuild
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── 目录布局 ──────────────────────────────────────────────────
_FLN = Path(__file__).resolve().parent          # .../t006/flnone_test
T006 = _FLN.parent                              # .../t006
PY = sys.executable

SCENE = T006 / "scene"
IMAGES = T006 / "images"
LOGS = _FLN / "logs"
RESULTS = _FLN / "results"
DOCS = _FLN / "docs"


def _find_snb_core() -> Path:
    """定位 `SNB/SNB` 核心模块（向上逐级找，不写死层数）。"""
    for anc in [_FLN] + list(_FLN.parents):
        for cand in (anc / "SNB", anc.parent / "SNB"):
            if (cand / "scripts").is_dir() and (cand / "source").is_dir():
                return cand
    raise SystemExit(f"[X] 未找到 SNB 核心模块 (从 {_FLN} 向上搜索)")


SNB = _find_snb_core()
RUN = SNB / "scripts" / "run" / "run_scene.py"
PROBE = SNB / "scripts" / "analysis" / "chk_probe.py"
PLOT5 = _FLN / "plot_5leg.py"

INP_SNB = SCENE / "sim_snb" / "flash_input"
FO_SNB = SCENE / "flash_output" / "sim_snb"
BASE_PAR = INP_SNB / "snb_radon.par"        # fl_harmonic 基线（t006 生成）

# ── 数据目录 tag ──────────────────────────────────────────────
TAG_BASE = "radon"          # t006 已跑好: SNB radON + fl_harmonic
TAG_SMOKE = "smoke_flnone"  # 本测试短时腿
TAG_FULL = "flnone"         # 本测试正常时间腿

# ── 网格 / 时间（与 t006 严格一致；dtmax 为并列前提，不得改动）──
NXB = 128
IPROCS = 8
DTMAX = 2.0e-14
TMAX_FULL = 8.0e-10
TMAX_SMOKE = 1.0e-11

# 预设量: 仅允许这些键与基线不同
ALLOWED_DIFF_SMOKE = {
    "diff_eleFlMode", "basenm", "log_file",
    "tmax", "checkpointFileIntervalTime", "plotFileIntervalTime",
}
ALLOWED_DIFF_FULL = {"diff_eleFlMode", "basenm", "log_file"}


def _e(v: float) -> str:
    return f"{v:.10e}"


PAR_SPECS: Dict[str, Dict[str, str]] = {
    "snb_flnone.par": {
        "diff_eleFlMode": '"fl_none"',
        "basenm": '"snb_flnone_"',
        "log_file": '"snb_flnone.log"',
    },
    "snb_flnone_smoke.par": {
        "diff_eleFlMode": '"fl_none"',
        "basenm": '"snb_flnone_smoke_"',
        "log_file": '"snb_flnone_smoke.log"',
        "tmax": _e(TMAX_SMOKE),
        # ★ 短测必须加密 chk: 否则 5e-11 的间隔在 1e-11 的 tmax 下只有 1~2 帧,
        #   dt 钳位 / ρmax 走势都无法判定（t006 的 smoke 只有 2 帧就是这个原因）。
        "checkpointFileIntervalTime": _e(1.0e-12),
        "plotFileIntervalTime": _e(5.0e-12),
    },
    # ★★ 受控短时基线 —— 与 fl_none 短时腿**逐键对齐**，唯一差别就是 `diff_eleFlMode`。
    #   为什么必须新造一条而不用 t006 早已存在的 `smoke_radon`:
    #     `smoke_radon/par_snb_smoke_radon.par` 里**没有** `gr_hypreUseFloor` 这个键
    #     → 走 FLASH 默认 `.true.` → 它是 **gr_hypreUseFloor 修复之前**产生的数据。
    #     拿它当基线会同时改变两个变量（限流模式 + HYPRE floor），
    #     从而得出**完全虚假的"存在差异"结论**（实测 tele 相对差 0.97）。
    #   本脚本的 `_par_pair_guard` 已加入自动拦截，防止此类错误再次发生。
    "snb_harm_smoke.par": {
        "basenm": '"snb_harm_smoke_"',
        "log_file": '"snb_harm_smoke.log"',
        "tmax": _e(TMAX_SMOKE),
        "checkpointFileIntervalTime": _e(1.0e-12),
        "plotFileIntervalTime": _e(5.0e-12),
    },
}

# ══════════════════════════════════════════════════════════════
# 附录实验 —— **SH 侧** `gr_hypreUseFloor` 单变量 A/B
# ══════════════════════════════════════════════════════════════
# 动机（扫描留存 par 时发现）:
#   `scene/flash_output/sim_flsh/{radon,radoff}` 的 par 里**没有**
#   `gr_hypreUseFloor` 这个键 → 走 FLASH 默认 **`.true.`**;
#   而 `sim_snb/{radon,radoff}` 是**修复后**重新生成的（显式 `.false.`）。
#   即：现有 FL-SH 两腿**早于**该修正。
# 该键在标准树中确实存在且为**运行时参数**:
#   `Grid/GridSolvers/HYPRE/Config:92  PARAMETER gr_hypreUseFloor BOOLEAN TRUE`
#   `Grid/GridSolvers/HYPRE/gr_hypreInit.F90:123  RuntimeParameters_get(...)`
# 因此必须实测界定"SH 侧既有结论是否受它影响"，否则五腿对比的 SH 半边存疑。
#
# 注意: `flsh_radon.par` 模板中**没有**该键，故用 append_missing=True 追加。
BASE_PAR_FLSH = SCENE / "sim_flsh" / "flash_input" / "flsh_radon.par"
FO_FLSH = SCENE / "flash_output" / "sim_flsh"
TAG_SH_HT = "sh_hT_smoke"      # gr_hypreUseFloor = .true.  （= 默认 = 现有 SH 腿）
TAG_SH_HF = "sh_hF_smoke"      # gr_hypreUseFloor = .false. （= SNB 腿采用的修正值）

SH_AB_ALLOWED = {"gr_hypreUseFloor", "basenm", "log_file", "tmax",
                 "checkpointFileIntervalTime", "plotFileIntervalTime"}

SH_AB_PARS: Dict[str, Dict[str, str]] = {
    "flsh_hT_smoke.par": {
        "gr_hypreUseFloor": ".true.",
        "basenm": '"flsh_hT_smoke_"',
        "log_file": '"flsh_hT_smoke.log"',
        "tmax": _e(TMAX_SMOKE),
        "checkpointFileIntervalTime": _e(1.0e-12),
        "plotFileIntervalTime": _e(5.0e-12),
    },
    "flsh_hF_smoke.par": {
        "gr_hypreUseFloor": ".false.",
        "basenm": '"flsh_hF_smoke_"',
        "log_file": '"flsh_hF_smoke.log"',
        "tmax": _e(TMAX_SMOKE),
        "checkpointFileIntervalTime": _e(1.0e-12),
        "plotFileIntervalTime": _e(5.0e-12),
    },
}


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def sh(cmd: List[object], tag: str = "") -> int:
    print(f"\n{'='*78}\n $ {' '.join(str(c) for c in cmd)}\n{'='*78}", flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if tag:
        with (LOGS / f"{tag}.log").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"\n### {' '.join(str(c) for c in cmd)}\n")
    return subprocess.run([str(c) for c in cmd]).returncode


# ══════════════════════════════════════════════════════════════
# par 生成 + 键级差分自检
# ══════════════════════════════════════════════════════════════
def par_kv(p: Path) -> Dict[str, str]:
    """解析 par 为 键→值（去注释、去空白）。"""
    out: Dict[str, str] = {}
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.split("#", 1)[0].strip()
        if s and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def build_par(name: str, spec: Dict[str, str], template: Optional[Path] = None,
              append_missing: bool = False, subdir: str = "sim_snb") -> Path:
    """以模板 par 为基准，仅覆写 spec 中的键，其余逐字保留。

    `append_missing=True`: 模板中**不存在**的键改为追加到文件末尾
    （FLASH 的 par 是 key=value 列表，追加即可生效）。
    """
    tpl = template or BASE_PAR
    if not tpl.exists():
        raise SystemExit(f"[X] 模板 par 不存在: {tpl}\n"
                         f"    请先在 t006 跑 `--stage generate`")
    text = tpl.read_text(encoding="utf-8", errors="replace")
    out_lines: List[str] = []
    applied: set = set()
    for ln in text.splitlines():
        s = ln.split("#", 1)[0].strip()
        key = s.split("=", 1)[0].strip() if (s and "=" in s) else None
        if key and key in spec:
            out_lines.append(f"{key:<41}= {spec[key]}")
            applied.add(key)
        else:
            out_lines.append(ln)
    miss = sorted(set(spec) - applied)
    if miss and not append_missing:
        raise SystemExit(f"[X] 模板中未找到待覆写的键: {miss}")
    for k in miss:
        out_lines.append(f"{k:<41}= {spec[k]}")
    dst = (SCENE / subdir / "flash_input") / name
    dst.write_text("\n".join(out_lines) + "\n", encoding="utf-8", newline="\n")
    return dst


def diff_check(target: Path, allowed: set, ref: Optional[Path] = None) -> bool:
    """★ 键级差分自检: 与参照 par 的差异必须**恰好**落在 allowed 内。"""
    ref = ref or BASE_PAR
    a, b = par_kv(ref), par_kv(target)
    keys = sorted(set(a) | set(b))
    diffs = [k for k in keys if a.get(k) != b.get(k)]
    print(f"\n  ── 键级差分: {target.name} vs {ref.name} ──")
    print(f"     键总数 {len(keys)}；取值不同 {len(diffs)} 个")
    for k in diffs:
        print(f"       {k:<34} {a.get(k, '(缺)'):<24} → {b.get(k, '(缺)')}")
    extra = sorted(set(diffs) - allowed)
    if extra:
        log(f"出现**未声明**的差异键: {extra} → 拒绝使用", "ERROR")
        return False
    if not diffs:
        log("与基线完全相同（未覆盖任何键?）—— 请检查", "WARN")
    log(f"差异键全部在预设范围内 ✓ ({len(diffs)} 个)", "OK")
    return True


def _par_pair_guard(pa: Path, pb: Path, allowed: set, label: str) -> bool:
    """★★ 比对前**必须先做受控性检查**: 两条腿的配置差异只能落在 allowed 内。

    血泪教训（本脚本首版踩坑）: 曾拿 `smoke_radon` 当基线，而那份 par
    **缺 `gr_hypreUseFloor`**（= 修复前的数据）→ 一次改了两个变量 →
    得到 tele 相对差 0.97 的**虚假差异**。关键就是"帧时间戳偏移"暴露了配对错误、
    而"par 键级差分"暴露了基线不干净 —— 两个检查缺一不可。
    """
    print(f"\n  ── 受控性检查: {label} ──")
    if not pa.exists() or not pb.exists():
        log(f"par 缺失: {pa if not pa.exists() else pb}", "ERROR")
        return False
    A, B = par_kv(pa), par_kv(pb)
    diffs = sorted(k for k in (set(A) | set(B)) if A.get(k) != B.get(k))
    for k in diffs:
        print(f"       {k:<34} {A.get(k, '(缺)'):<24} → {B.get(k, '(缺)')}")
    extra = sorted(set(diffs) - allowed)
    if extra:
        log(f"两腿存在**非受控**差异键 {extra} → 拒绝比对（结论会失真）", "ERROR")
        return False
    log(f"受控 ✓ 差异键 {diffs}", "OK")
    return True


def stage_prep(args) -> int:
    """生成 fl_none 的 par（正常 + 短时），并做键级差分自检。"""
    print("\n" + "=" * 78)
    print(" 阶段 prep —— 生成 fl_none par（纯运行时开关，不改源码/不重编译）")
    print("=" * 78)
    log(f"核心模块: {SNB}")
    log(f"场景:     {SCENE}")

    if not BASE_PAR.exists():
        log(f"基线 par 缺失: {BASE_PAR}", "ERROR")
        return 1
    base = par_kv(BASE_PAR)
    if base.get("diff_eleFlMode") != '"fl_harmonic"':
        log(f"基线 diff_eleFlMode = {base.get('diff_eleFlMode')}（预期 \"fl_harmonic\"）",
            "WARN")
    if base.get("dtmax") != _e(DTMAX):
        log(f"基线 dtmax = {base.get('dtmax')}（预期 {_e(DTMAX)}）—— 本测试不改动它",
            "WARN")

    ok = True
    for name, spec in PAR_SPECS.items():
        dst = build_par(name, spec)
        log(f"写出 {dst.relative_to(T006)}", "OK")
        allowed = ALLOWED_DIFF_SMOKE if "smoke" in name else ALLOWED_DIFF_FULL
        ok &= diff_check(dst, allowed)

    # 落盘一份说明
    RESULTS.mkdir(parents=True, exist_ok=True)
    log(f"prep {'通过' if ok else '未通过'}", "OK" if ok else "ERROR")
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════
# 运行
# ══════════════════════════════════════════════════════════════
def verify_environment() -> bool:
    """确认可复用 t006 已编译好的 SNB objdir（否则需要 --rebuild）。"""
    code = subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "bash", "-lc",
         'test -x /root/QC/FLASH/FLASHSNB/FLASH4.8/SNB_SCENE_obj/flash4 '
         '&& echo FLASH4_OK || echo FLASH4_MISSING'],
        capture_output=True, text=True)
    out = (code.stdout or "") + (code.stderr or "")
    if "FLASH4_OK" in out:
        log("SNB objdir/flash4 已就绪 → 可复用（跳过 deploy/setup/make）", "OK")
        return True
    log("SNB objdir/flash4 不可用 —— 需 --rebuild（将重新 setup+make，约 10 min）", "WARN")
    return False


def do_run(par: str, tag: str, rebuild: bool) -> int:
    cmd: List[object] = [
        PY, RUN, "--scene", SCENE, "--side", "snb",
        "--par", par, "--tag", tag,
        "--nxb", NXB, "--iprocs", IPROCS,
        "--out-root", SCENE / "flash_output",
    ]
    if not rebuild:
        # ★ 辐射/限流都是纯 par 开关 → 复用同一份已编译二进制
        cmd += ["--skip-deploy", "--skip-setup", "--skip-make"]
    return sh(cmd, f"run_{tag}")


def _run_leg(args, spec_name: str, tag: str, tmax: float) -> int:
    print("\n" + "=" * 78)
    print(f" 运行 fl_none 腿: par={spec_name}  tag={tag}  tmax={tmax:.3e}")
    print(f" ★ dtmax={DTMAX:.3e}（固定在并列前提值，判据见 t006/README.md）")
    print("=" * 78)
    rc = stage_prep(args)
    if rc:
        log("prep 未通过 → 中止", "ERROR")
        return rc
    t0 = time.time()
    rc = do_run(spec_name, tag, args.rebuild)
    wall = time.time() - t0
    log(f"{tag} 结束 rc={rc}，耗时 {wall:.1f} s", "OK" if rc == 0 else "ERROR")
    return rc


def stage_smoke(args) -> int:
    verify_environment()
    return _run_leg(args, "snb_flnone_smoke.par", TAG_SMOKE, TMAX_SMOKE)


def stage_full(args) -> int:
    verify_environment()
    return _run_leg(args, "snb_flnone.par", TAG_FULL, TMAX_FULL)


# ══════════════════════════════════════════════════════════════
# chk 健康检查
# ══════════════════════════════════════════════════════════════
def stage_check(args) -> int:
    print("\n" + "=" * 78)
    print(" 阶段 check —— chk 健康检查（dt 钳位 / ρmax / 守恒）")
    print("=" * 78)
    rc = 0
    found = False
    for tag in (TAG_SMOKE, TAG_FULL):
        d = FO_SNB / tag
        if not d.is_dir():
            log(f"{tag}: 目录不存在，跳过", "WARN")
            continue
        found = True
        print(f"\n── {tag} ──────────────────────────────────────────")
        rc |= sh([PY, PROBE, "--dir", d,
                  "--expect-dtmax", _e(DTMAX), "--brief"], "")
    if not found:
        log("未找到任何 fl_none 数据目录", "ERROR")
        return 1
    return rc


# ══════════════════════════════════════════════════════════════
# 与 fl_harmonic 基线逐帧比对（本测试的科学核心）
# ══════════════════════════════════════════════════════════════
COMPARE_VARS = ("dens", "tele", "tion", "trad", "pele", "pres")


def _load_frames(d: Path):
    """复用核心模块的 chk 读取（+ug 叶块直读 / 复合 Dataset 解析）。"""
    sys.path.insert(0, str(SNB / "scripts" / "analysis"))
    import compare_4way as C4  # noqa: PLC0415

    frames = []
    for p in C4.list_chk(d):
        try:
            frames.append(C4.load_chk(p, list(COMPARE_VARS)))
        except Exception as exc:                      # noqa: BLE001
            log(f"跳过 {p.name}: {exc}", "WARN")
    frames.sort(key=lambda r: r["t"])
    return frames


def _classify(max_rel: float) -> str:
    """按整体最大相对差给出量级分类 —— 避免"非零即失败"的粗糙判读。"""
    if max_rel == 0.0:
        return "逐位相同 (bit-identical)"
    if max_rel <= 1e-6:
        return "数值噪声级（浮点区间内，物理上无效）"
    if max_rel <= 1e-4:
        return "可忽略（≤1e-4，远小于物理判读精度）"
    if max_rel <= 1e-2:
        return "轻微（≤1%）—— 解读时需注明"
    return "显著（>1%）—— 结论会受影响"


def _compare_dirs(d_base: Path, d_new: Path, label: str, stem: str,
                  same_note: Optional[List[str]] = None,
                  diff_note: Optional[List[str]] = None,
                  fail_on_diff: bool = True) -> int:
    """逐帧比对两个数据目录 —— 单变量 A/B 的通用判决器。

    ★ 判据: 两腿若真的走同一条代码路径, 逐帧差值应**恒等于 0**（逐位相同）。
      任何非零差值都意味着两腿之间存在尚未识别的行为差异。
    """
    import numpy as np  # noqa: PLC0415

    same_note = same_note or [
        "⇒ 证实 `diff_eleFlMode` 在 SNB 电子路径上是 **no-op**;",
        "  `docs/05_坑位清单.md` P1 的因果表述需更正为"
        "「该参数在当前 SNB 配置下不生效」。",
        "⇒ 同时说明 `fl_none` **不会**破坏 SNB 守恒 —— "
        "保护该腿的不是限流器。",
    ]
    diff_note = diff_note or [
        "⇒ 静态分析（839/847 行被注释）不完备 ——",
        "  存在未发现的 `diff_eleFlMode` 引用路径，需回溯核实。",
    ]

    print("\n" + "=" * 78)
    print(f" {label} —— 逐帧比对")
    print(f" 基线: {d_base.relative_to(SCENE).as_posix()}")
    print(f" 新区: {d_new.relative_to(SCENE).as_posix()}")
    print("=" * 78)

    for d in (d_base, d_new):
        if not d.is_dir():
            log(f"数据目录缺失: {d}", "ERROR")
            return 1

    fb, fn = _load_frames(d_base), _load_frames(d_new)
    log(f"帧数: 基线 {len(fb)}，fl_none {len(fn)}")
    if not fb or not fn:
        log("帧数为 0 → 无法比对", "ERROR")
        return 1
    # ★★ 必须按**时间戳**配对，不能按帧序号！
    #    两腿的 chk 间隔（以及帧数）可以不同 —— 那是纯 IO 参数、不影响物理；
    #    但按序号配对会把**不同时刻**的两帧对在一起，从而产生**完全虚假的
    #    "存在差异"结论**（本脚本首版即踩此坑：把 t=1e-12 与 t=1e-11 相比，
    #    得出 tele 相对差 77 的荒谬结果）。
    TOL_T = 1e-17                     # 秒；同 dt 下两腿的落盘时刻应逐位一致
    pairs: List[Tuple[int, int, float]] = []
    used: set = set()
    for i, a in enumerate(fb):
        best, bd = -1, None
        for j, b in enumerate(fn):
            if j in used:
                continue
            dd = abs(a["t"] - b["t"])
            if bd is None or dd < bd:
                best, bd = j, dd
        if best >= 0 and bd is not None and bd <= TOL_T:
            used.add(best)
            pairs.append((i, best, bd))
    n = len(pairs)
    log(f"按时间戳配对: 成功 {n} 帧（基线 {len(fb)} 帧，fl_none {len(fn)} 帧）")
    if not pairs:
        log("没有任何时间戳可配对的帧 → 无法比对", "ERROR")
        return 1
    if n < min(len(fb), len(fn)):
        log(f"有 {min(len(fb), len(fn)) - n} 帧未能配对（时间戳不一致，已跳过）",
            "WARN")

    rows: List[Dict[str, float]] = []
    worst: Dict[str, Tuple[float, float]] = {v: (0.0, 0.0) for v in COMPARE_VARS}
    t_shift = 0.0
    neq_frames = 0

    for i, j, dt_pair in pairs:
        a, b = fb[i], fn[j]
        t_shift = max(t_shift, dt_pair)
        rec: Dict[str, float] = {"frame": i, "t_ns": a["t"] * 1e9}
        allzero = True
        for v in COMPARE_VARS:
            va, vb = a.get(v), b.get(v)
            if va is None or vb is None or va.shape != vb.shape:
                rec[f"{v}_abs"] = float("nan")
                rec[f"{v}_rel"] = float("nan")
                continue
            va = np.asarray(va, float); vb = np.asarray(vb, float)
            dmax = float(np.max(np.abs(va - vb)))
            scale = float(np.max(np.abs(vb))) or 1.0
            rec[f"{v}_abs"] = dmax
            rec[f"{v}_rel"] = dmax / scale
            if dmax > worst[v][0]:
                worst[v] = (dmax, dmax / scale)
            if dmax != 0.0:
                allzero = False
        neq_frames += 0 if allzero else 1
        rows.append(rec)

    # ── 判据 ──────────────────────────────────────────────
    print("\n  ── 逐帧最大绝对差 (同一物理量在整个时间窗上的上确界) ──")
    hdr = f"{'变量':<8}{'max|Δ|':>16}{'max 相对差':>16}   判定"
    print("  " + hdr); print("  " + "-" * len(hdr))
    all_bitwise = True
    for v in COMPARE_VARS:
        da, dr = worst[v]
        same = (da == 0.0)
        all_bitwise &= same
        print(f"  {v:<8}{da:>16.6e}{dr:>16.3e}   "
              f"{'逐位相同' if same else '★ 存在差异'}")

    max_abs = max((worst[v][0] for v in COMPARE_VARS), default=0.0)
    max_rel = max((worst[v][1] for v in COMPARE_VARS), default=0.0)
    cls = _classify(max_rel)
    print(f"\n  帧时间戳最大偏移: {t_shift:.3e} s")
    print(f"  存在差异的帧数:   {neq_frames}/{n}")
    print(f"  整体最大绝对差:   {max_abs:.6e}")
    print(f"  整体最大相对差:   {max_rel:.6e}")
    print(f"  ★ 量级分类:       {cls}")
    if all_bitwise:
        print("\n  [OK] 判决: 两腿**逐位相同 (bit-identical)**")
        for ln in same_note:
            print("        " + ln)
    else:
        print("\n  [!] 判决: 两腿**存在差异**（量级见上）")
        for ln in diff_note:
            print("        " + ln)

    # ── 落盘 ──────────────────────────────────────────────
    RESULTS.mkdir(parents=True, exist_ok=True)
    csv_out = RESULTS / f"{stem}.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "t_ns"] + [f"{v}_{k}" for v in COMPARE_VARS
                                        for k in ("abs", "rel")])
        for r in rows:
            w.writerow([r["frame"], f"{r['t_ns']:.6f}"] +
                       [f"{r[f'{v}_{k}']:.10e}" for v in COMPARE_VARS
                        for k in ("abs", "rel")])
    log(f"逐帧差值表 → {csv_out.relative_to(T006)}", "OK")

    md = RESULTS / f"{stem}.md"
    with md.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# `fl_none` vs `fl_harmonic` —— {label} 逐帧比对\n\n")
        fh.write(f"- 基线: `{d_base.relative_to(SCENE).as_posix()}`（`fl_harmonic`）\n")
        fh.write(f"- 新区: `{d_new.relative_to(SCENE).as_posix()}`（`fl_none`）\n")
        fh.write(f"- 帧数: 基线 {len(fb)}，fl_none {len(fn)}；"
                 f"**按时间戳配对后比对 {n} 帧**\n")
        fh.write(f"- 帧时间戳最大偏移: {t_shift:.3e} s\n")
        fh.write(f"- 存在差异的帧数: {neq_frames}/{n}\n")
        fh.write(f"- 整体最大绝对差: {max_abs:.6e}\n")
        fh.write(f"- 整体最大相对差: {max_rel:.6e}\n")
        fh.write(f"- **量级分类**: {cls}\n\n")
        fh.write("| 变量 | max&#124;Δ&#124; | max 相对差 | 判定 |\n|---|---|---|---|\n")
        for v in COMPARE_VARS:
            da, dr = worst[v]
            fh.write(f"| `{v}` | {da:.6e} | {dr:.3e} | "
                     f"{'逐位相同' if da == 0.0 else '★ 存在差异'} |\n")
        fh.write("\n**判决**: " +
                 ("逐位相同 (bit-identical)" if all_bitwise else "存在差异") + "\n\n")
        fh.write("```\n")
        for ln in (same_note if all_bitwise else diff_note):
            fh.write(ln.rstrip() + "\n")
        fh.write("```\n")
    log(f"比对报告 → {md.relative_to(T006)}", "OK")
    if not fail_on_diff:
        return 0            # 两种结局都有信息量（如附录 A/B），不算失败
    return 0 if all_bitwise else 1


# ★ 短时受控基线: 由本脚本新跑（`--stage smoke-base`），与 fl_none 短时腿逐键对齐。
#   **不要**用 t006 早先的 `smoke_radon` —— 那是 gr_hypreUseFloor 修复前的数据
#   （其 par 里没有该键 → 默认 .true.），拿它当基线会同时改两个变量。
TAG_SMOKE_HARM = "smoke_harmonic"


def stage_smoke_base(args) -> int:
    """跑短时受控基线（fl_harmonic），专供早期判决做同设置对照。"""
    verify_environment()
    return _run_leg(args, "snb_harm_smoke.par", TAG_SMOKE_HARM, TMAX_SMOKE)


def stage_smoke_compare(args) -> int:
    """早期判决: 在 t=1e-11 处比对 fl_none 与 fl_harmonic（受控短时腿）。"""
    pa = FO_SNB / TAG_SMOKE_HARM / f"par_snb_{TAG_SMOKE_HARM}.par"
    pb = FO_SNB / TAG_SMOKE / f"par_snb_{TAG_SMOKE}.par"
    if not _par_pair_guard(pa, pb, ALLOWED_DIFF_SMOKE,
                           "短时腿  fl_harmonic(基线) vs fl_none"):
        return 1
    return _compare_dirs(FO_SNB / TAG_SMOKE_HARM, FO_SNB / TAG_SMOKE,
                         "短时腿 (tmax=1e-11) 早期判决",
                         "smoke_flnone_vs_harmonic")


def stage_compare(args) -> int:
    """正式判决: 全时间窗 (0 → 0.8 ns) 逐帧比对。"""
    pa = FO_SNB / TAG_BASE / f"par_snb_{TAG_BASE}.par"
    pb = INP_SNB / "snb_flnone.par"
    if not _par_pair_guard(pa, pb, ALLOWED_DIFF_FULL,
                           "全长腿  fl_harmonic(基线) vs fl_none"):
        return 1
    return _compare_dirs(FO_SNB / TAG_BASE, FO_SNB / TAG_FULL,
                         "全时间窗 SNB 辐射开腿", "flnone_vs_harmonic")


# ══════════════════════════════════════════════════════════════
def stage_sh_ab(args) -> int:
    """附录实验: **SH 侧** `gr_hypreUseFloor` 单变量 A/B（短时, tmax=1e-11）。

    为什么需要它: 现有 `sim_flsh/{radon,radoff}` 的 par **缺**该键 → 默认 `.true.`,
    而 SNB 腿用的是显式 `.false.`。若该键对 SH 单标量扩散路径也有影响,
    则五腿对比的 SH 半边需要重跑 —— 必须先实测界定, 不能靠推断。
    """
    print("\n" + "=" * 78)
    print(" 附录实验 —— SH 侧 gr_hypreUseFloor 单变量 A/B (短时)")
    print(" 目的: 界定现有 FL-SH 腿（默认 .true.）是否受该键影响")
    print("=" * 78)
    if not BASE_PAR_FLSH.exists():
        log(f"SH 模板 par 缺失: {BASE_PAR_FLSH}", "ERROR")
        return 1

    for name, spec in SH_AB_PARS.items():
        dst = build_par(name, spec, template=BASE_PAR_FLSH,
                        append_missing=True, subdir="sim_flsh")
        log(f"写出 {dst.relative_to(SCENE).as_posix()}", "OK")
        if not diff_check(dst, SH_AB_ALLOWED, ref=BASE_PAR_FLSH):
            return 1

    for par, tag in (("flsh_hT_smoke.par", TAG_SH_HT),
                     ("flsh_hF_smoke.par", TAG_SH_HF)):
        cmd: List[object] = [
            PY, RUN, "--scene", SCENE, "--side", "flsh",
            "--par", par, "--tag", tag,
            "--nxb", NXB, "--iprocs", IPROCS,
            "--out-root", SCENE / "flash_output",
            "--skip-deploy", "--skip-setup", "--skip-make",
        ]
        rc = sh(cmd, f"run_{tag}")
        if rc:
            log(f"{tag} 运行失败 rc={rc}", "ERROR")
            return rc

    pa = FO_FLSH / TAG_SH_HT / f"par_flsh_{TAG_SH_HT}.par"
    pb = FO_FLSH / TAG_SH_HF / f"par_flsh_{TAG_SH_HF}.par"
    if not _par_pair_guard(pa, pb, SH_AB_ALLOWED,
                           "SH  gr_hypreUseFloor .true. vs .false."):
        return 1
    return _compare_dirs(
        FO_FLSH / TAG_SH_HT, FO_FLSH / TAG_SH_HF,
        "SH 侧 gr_hypreUseFloor A/B (tmax=1e-11)", "sh_hypre_ab",
        same_note=[
            "⇒ 该键对 FL-SH 单标量扩散路径**逐位无影响**;",
            "  现有 FL-SH 两腿（默认 .true.）结论有效, 无需重跑。",
        ],
        diff_note=[
            "⇒ 该键对 FL-SH 路径**不是逐位中性**（存在非零差值）;",
            "  但**量级**才是判据（见上方「量级分类」）:",
            "    · 「数值噪声级 / 可忽略」→ 现有 FL-SH 两腿结论仍可用,",
            "      报告中注明该量级即可, 无需重跑;",
            "    · 「轻微 / 显著」→ 必须重跑 SH 两腿后再做五腿对比。",
            "  对照: 同一键在 **SNB** 侧曾造成 1.6× 的物理级差异（崩塌）,",
            "        故不能因 SH 侧量级小就认为该键普遍无害。",
        ],
        fail_on_diff=False)


# ══════════════════════════════════════════════════════════════
def stage_plot(args) -> int:
    if not PLOT5.exists():
        log(f"绘图脚本缺失: {PLOT5}", "ERROR")
        return 1
    cmd: List[object] = [PY, PLOT5, "--scene", SCENE, "--out", IMAGES / "flnone5"]
    return sh(cmd, "plot5")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="t006/flnone_test: fl_none 限流模式在 SNB+辐射开 下的可行性验证")
    ap.add_argument("--stage",
                    choices=["all", "prep", "smoke-base", "smoke", "full",
                             "check", "smoke-compare", "compare", "plot",
                             "sh-hypre-ab"],
                    default="all")
    ap.add_argument("--rebuild", action="store_true",
                    help="重新 deploy/setup/make（objdir 被清理时用）")
    args = ap.parse_args()

    print("\n" + "=" * 78)
    print(" t006/flnone_test —— fl_none 限流模式 可行性验证")
    print("=" * 78)
    print(" 待检验预期: `diff_eleFlMode` 在 SNB 电子路径上无存活消费者")
    print("             （snb_package/diff_advanceTherm.F90:839,847 被注释）")
    print("             ⇒ fl_none 与 fl_harmonic 预期**逐位相同**")
    print("=" * 78)

    t0 = time.time()
    rc = 0
    if args.stage in ("all", "prep"):
        rc |= stage_prep(args)
    if args.stage == "smoke-base":
        rc |= stage_smoke_base(args)
    if args.stage in ("all", "smoke"):
        rc |= stage_smoke(args)
    if args.stage in ("all", "smoke-compare"):
        rc |= stage_smoke_compare(args)
    if args.stage in ("all", "full"):
        rc |= stage_full(args)
    if args.stage in ("all", "check"):
        rc |= stage_check(args)
    if args.stage in ("all", "compare"):
        rc |= stage_compare(args)
    if args.stage == "sh-hypre-ab":
        rc |= stage_sh_ab(args)
    if args.stage in ("all", "plot"):
        rc |= stage_plot(args)

    print("\n" + "=" * 78)
    print(f" flnone_test 完成 — 耗时 {time.time()-t0:.1f} s, rc={rc}")
    print(f" 数据: {FO_SNB}")
    print(f" 结果: {RESULTS}")
    print(f" 图:   {IMAGES / 'flnone5'}")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    sys.exit(main())
