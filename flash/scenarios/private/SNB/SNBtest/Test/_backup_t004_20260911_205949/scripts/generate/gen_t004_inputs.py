"""t004 输入生成器 —— 「辐射开关」2×2 矩阵的输入文件

用法 (在 t004 目录下):
    python scripts/generate/gen_t004_inputs.py                # 四腿
    python scripts/generate/gen_t004_inputs.py --side flsh    # 仅 FL-SH 侧两腿
    python scripts/generate/gen_t004_inputs.py --side snb

产物 (分门别类)
--------------
    t004/sim_flsh/flash_input/   ← FL-SH 侧单元 (两腿共用) + 2 个 par
    t004/sim_snb/flash_input/    ← SNB 侧单元 (含 8 个作者覆盖) + 2 个 par
    t004/variants/               ← 从 t003 同步的 radON Driver 变体 (软引用)

★ 文件来源策略
    **复制** (逐字节, 权威 = `src/SNB/SNB_1D_laser/SNB_1D_laser/`):
      两腿共享: Config Makefile Simulation_*.F90 mgd_qesh.F90 + 2 张 cn4
      SNB 侧  : 7 个作者覆盖 F90 + SNB 版 diff_advanceTherm.F90
    **生成**: 4 个 .par —— 基于 t003 的示例 par 构造器 (几何/激光/材料/时间积分
      全部继承), 仅追加 **辐射三开关** 与腿标识。

★ 关辐射机制 (权威: tracer VCH_ml_F.py:300-303)
    rt_useMGD / useOpacity / useRadTrans 三开关**纯运行时**切换, 源码零改动。
    ⚠ SNB 侧必须先恢复作者 Driver 中被注释的 `call RadTrans` (radON 变体),
      否则辐射永远无法开启, par 开关形同虚设。
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_T004 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T004 / "common"))
sys.path.insert(0, str(_T004.parent / "t003" / "scripts" / "generate"))

import t004_common as C          # noqa: E402
import gen_t003_inputs as GEN3   # noqa: E402  (复用 par 构造器与复制逻辑)


# ══════════════════════════════════════════════════════════════
def build_par_text(model: str, rad_on: bool, nxb: int, iprocs: int,
                   tmax: Optional[float] = None) -> str:
    """t003 示例 par 为基础 + 本腿标识 + 辐射三开关。"""
    leg = C.leg_cfg(model, rad_on)
    text, _ = GEN3.build_par_text(model, nxb, iprocs, tmax)

    # 腿标识 (t004 独立 basenm / log_file, 避免四腿输出互相覆盖)
    text, n1 = re.subn(r"(?m)^basenm\s*=.*$",
                       f'basenm   = "{leg["basenm"]}"', text)
    text, n2 = re.subn(r"(?m)^log_file\s*=.*$",
                       f'log_file = "{leg["log_file"]}"', text)
    if n1 != 1 or n2 != 1:
        raise RuntimeError(f"par 中 basenm/log_file 替换异常: basenm={n1}, log={n2}")

    # 辐射三开关 (关辐射的核心机制; 开辐射时也显式写回真值以消除歧义)
    sw = leg["rad_switches"]
    block = [
        "",
        "# ──────────────────────────────────────────────────────────────",
        f"# 辐射开关 (t004): 本腿 = 辐射{'开启' if rad_on else '关闭'}",
        "#   机制权威: tracer/VCH_ml_F/VCH_ml_F.py:300-303 (纯运行时 par 开关,",
        "#   源码/setup/编译逐字节不变)",
        "#   注: 关辐射时下方 rt_mgd*/op_* 参数原样保留 (不生效), 与基准 par 一致",
        "# ──────────────────────────────────────────────────────────────",
    ]
    for k in ("rt_useMGD", "useOpacity", "useRadTrans"):
        v = sw[k]
        block.append(f"{k} = {'.true.' if v else '.false.'}")
    text = text.rstrip("\n") + "\n" + "\n".join(block) + "\n"

    # ★ 自检: par 中三开关的**最后一个**赋值必须与目标一致
    #   (FLASH 后值生效; 示例 par 里 rt_useMGD/useOpacity 已存在, 必须有我们的覆写)
    for k, v in sw.items():
        got = _last_value(text, k)
        if got != v:
            raise RuntimeError(f"{k} 期望 {v}, 实际生效 {got}")
    return text


def _last_value(text: str, key: str) -> Optional[bool]:
    """取 par 中某 logical 键**最后一个**生效值。"""
    val: Optional[bool] = None
    for line in text.splitlines():
        s = line.split("#", 1)[0].strip()
        if not s or "=" not in s:
            continue
        k, v = s.split("=", 1)
        if k.strip() != key:
            continue
        v = v.strip().lower().replace(".", "")
        if v in ("true", "t"):
            val = True
        elif v in ("false", "f"):
            val = False
    return val


# ══════════════════════════════════════════════════════════════
def generate_side(model: str, nxb: int, iprocs: int,
                  tmax: Optional[float] = None) -> Dict[str, Any]:
    """生成一侧(两腿共用)的单元文件 + 该侧两个 par。"""
    inp = C.leg_input_dir(model)
    inp.mkdir(parents=True, exist_ok=True)
    res: Dict[str, Any] = {}

    C.log(f"【{C.T3.LEGS[model]['label']} 侧】输入生成 → {inp}", "STEP")

    # 1. 两腿 par
    for rad_on in (True, False):
        leg = C.leg_cfg(model, rad_on)
        text = build_par_text(model, rad_on, nxb, iprocs, tmax)
        p = inp / leg["par_file"]
        p.write_text(text, encoding="utf-8", newline="\n")
        res[leg["par_file"]] = str(p)
        C.log(f"    .par → {p.name}  辐射={'开启' if rad_on else '关闭'} "
              f"(rt_useMGD/useOpacity/useRadTrans = "
              f"{'.true.' if rad_on else '.false.'})", "OK")

    # 2. 共享件 (两腿逐字节相同)
    shared = GEN3._copy_shared(inp)
    res["shared"] = shared
    C.log(f"    共享件 {len(shared)}/{len(C.SHARED_FILES)+len(C.SHARED_CN4)} ✓")

    # 3. SNB 侧: 作者覆盖 F90
    if model == "snb":
        ov = GEN3._copy_snb_overrides(inp)
        res["overrides"] = ov
        C.log(f"    SNB 覆盖 {len(ov)}/{len(C.SNB_OVERRIDES)+1} ✓")
    else:
        for f in list(C.SNB_OVERRIDES) + [C.DIFF_THERM_FILE]:
            p = inp / f
            if p.exists():
                p.unlink()
        C.log("    FL-SH 侧: 无覆盖件 (用标准树原生实现) ✓")

    return res


# ══════════════════════════════════════════════════════════════
def sync_variant() -> bool:
    """从 t003 取 radON Driver 变体 (SNB 侧两腿共用)。

    ⚠ 若 t003 变体缺失, 说明尚未生成 → 提示先跑 t003 的
      `scripts/generate/make_therm_variant.py`。
    """
    src = C.T003_VARIANTS / "Driver_evolveFlash_radON.F90"
    if not src.exists():
        C.log(f"radON 变体缺失: {src}\n      请先运行: "
              f"python ../t003/scripts/generate/make_therm_variant.py", "ERROR")
        return False
    dst_dir = C.T004_DIR / "variants"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "Driver_evolveFlash_radON.F90"
    shutil.copyfile(src, dst)
    # 断言: 变体必须含 2 处**生效**的 call RadTrans
    n = 0
    for ln in dst.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.lstrip().startswith("!"):
            continue
        if "call RadTrans" in ln:
            n += 1
    if n != 2:
        C.log(f"radON 变体校验失败: call RadTrans 生效数 = {n} (期望 2)", "ERROR")
        return False
    C.log(f"radON 变体已同步并校验 ✓ (call RadTrans 生效 ×{n})", "OK")
    return True


def setup_flags_for(model: str, nxb: int) -> str:
    return C.setup_flags(nxb)


# ══════════════════════════════════════════════════════════════
def check_controlled() -> bool:
    """四腿受控性自检:
       ① 同侧两 par 除 basenm/log_file/辐射三开关外**逐键相同**;
       ② 跨侧两 par 除上述加 leg 专属键外逐键相同。
    """
    def kv(p: Path) -> Dict[str, str]:
        d: Dict[str, str] = {}
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.split("#", 1)[0].strip()
            if not s or "=" not in s:
                continue
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
        return d

    pars = {k: kv(C.leg_input_dir(v["model"]) / v["par_file"])
            for k, v in C.LEGS.items()}

    print("\n  ── 四腿 par 受控性自检 ───────────────────────────────")
    allowed_common = {"basenm", "log_file"}
    allowed_rad = set(C.RAD_OFF_SWITCHES)
    ok = True

    # ① 同侧对比: 只允许 basenm/log_file/辐射三开关不同
    for side in ("flsh", "snb"):
        a, b = pars[f"{side}_on"], pars[f"{side}_off"]
        diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
        bad = [k for k in diff if k not in allowed_common | allowed_rad
               and not k.startswith("plot_var")]
        print(f"    [{side}] 键数 {len(a)} vs {len(b)}; 差异键: "
              f"{sorted(diff) if diff else '无'}")
        for k in sorted(diff):
            flag = "OK  " if (k in allowed_common | allowed_rad) else "!!  "
            print(f"      {flag}{k}: {diff[k][0]} → {diff[k][1]}")
        if bad:
            for k in bad:
                C.log(f"[{side}] 非预期差异: {k}", "ERROR")
            ok = False

    # ② 跨侧对比 (SNB 侧额外含 SNB 诊断白名单, 允许差异键并集)
    a, b = pars["flsh_on"], pars["snb_on"]
    diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
    allowed_x = {"basenm", "log_file"}
    bad_x = [k for k in diff if k not in allowed_x and not k.startswith("plot_var")]
    print(f"    [跨侧] 键数 {len(a)} vs {len(b)}; 差异键: {sorted(diff) or '无'}")
    for k in sorted(diff):
        flag = "OK  " if (k in allowed_x or k.startswith("plot_var")) else "!!  "
        print(f"      {flag}{k}: {diff[k][0]} → {diff[k][1]}")
    if bad_x:
        for k in bad_x:
            C.log(f"[跨侧] 非预期差异: {k}", "ERROR")
        ok = False

    if ok:
        C.log("四腿 par 受控性自检通过 ✓ (差异仅限 腿标识 + 辐射三开关)", "OK")
    return ok


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="t004 输入生成器 (辐射开关 2×2 矩阵)")
    ap.add_argument("--side", choices=["flsh", "snb", "both"], default="both")
    ap.add_argument("--nxb", type=int, default=None)
    ap.add_argument("--iprocs", type=int, default=None)
    ap.add_argument("--tmax", type=float, default=None)
    args = ap.parse_args()

    nxb = C.GRID["nxb"] if args.nxb is None else int(args.nxb)
    iprocs = C.GRID["iprocs"] if args.iprocs is None else int(args.iprocs)

    print("\n" + "=" * 78)
    print(f" t004 输入生成器 —— 辐射开关 2×2 矩阵   {C.stamp()}")
    print(f" 几何/激光/材料: 继承 t003 (= 作者示例 SNB_1D_laser)")
    print(f" 域 [{C.PARAMS['xmin']*1e4:.1f}, {C.PARAMS['xmax']*1e4:.1f}] µm   "
          f"CH 靶 [-50,0] µm | He 腔 [0,250] µm")
    print(f" 网格 +ug: iProcs={iprocs} × nxb={nxb} = {iprocs*nxb} 格, "
          f"dx≈{C.dx_um(nxb, iprocs):.4f} µm")
    print(f" 关辐射机制: par 三开关 rt_useMGD/useOpacity/useRadTrans "
          f"(权威 tracer VCH_ml_F.py:300-303)")
    print("=" * 78)

    sides = ["flsh", "snb"] if args.side == "both" else [args.side]

    # 变体自检 (SNB 侧需要 radON Driver)
    if "snb" in sides and not sync_variant():
        return 1

    for m in sides:
        generate_side(m, nxb, iprocs, args.tmax)

    ok = check_controlled() if len(sides) == 2 else True
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
