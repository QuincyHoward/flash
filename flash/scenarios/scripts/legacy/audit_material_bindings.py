"""
audit_material_bindings — 场景材料绑定五元组审计 (ρ / A / Z / EOS表 / op表)
═══════════════════════════════════════════════════════════════════

为什么需要它: 2026-10-18 的缺陷 (`ms_shldA/Z` 仍是 CH 的 6.509/3.5 而屏蔽层已换成
V/Ti) 说明**只读脚本不可靠** —— 脚本可能改对了表名却漏了原子量, 也可能相反。
判定必须以**重新生成后的 .par 实参**为准, 并把
`(sim_rho<Sp>, ms_<sp>A, ms_<sp>Z, eos_<sp>TableFile, op_<sp>FileName)`
当作一个整体与材质标准值比对。

★ 关键口径: `.par` 只写"被覆写"的参数, 未写的走 `Config` 的 PARAMETER 默认值。
  所以取值必须 **par 优先、Config 回退**, 并记录该值来自哪一侧 ——
  "来自 Config" 本身不是错, 但必须知道它是隐式生效的 (这正是本次缺陷的形态:
  par 显式写了错值, 覆盖了 Config 里本来正确的默认值)。

审计内容 (逐场景):
  1. 每物种五元组 vs 材质标准值, 标注来源 [par]/[Config]
  2. 场景实际引用的 cn4 是否真的落盘在 flash_input/
  3. tmax / 域 / 激光分段数 (只报告)

用法:
  .venv/Scripts/python.exe flash/scenarios/private/tracer/audit_material_bindings.py
  ... --tmax 1.6e-9 --scenes TiTi1,VCH_ml
"""

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent

# 材质标准值: (A, Z, rho[g/cm^3], cn4)
MAT = {
    "He": (4.002602, 2.0, 1.0e-6, "He-BADGER-TOPS-Final.cn4"),
    "CH": (6.509, 3.5, 1.0, "CH-QC-1-001.cn4"),
    "Ti": (47.867, 22.0, 4.54, "Ti-BADGER-TOPS.cn4"),
    "V": (50.9415, 23.0, 6.11, "V-BADGER-TOPS.cn4"),
}
SPECIES = ["cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6"]

SCENES = [
    ("TiTi1", HERE / "TiTi" / "TiTi1.py"),
    ("TiTi2", HERE / "TiTi" / "TiTi2.py"),
    ("TiTi3", HERE / "TiTi" / "TiTi3.py"),
    ("VCH_ml", HERE / "VCH_ml" / "VCH_ml.py"),
    ("VCH_ml_F", HERE / "VCH_ml_F" / "VCH_ml_F.py"),
    ("VTi1", HERE / "VTi" / "VTi1.py"),
]

# 没有 SHLD_MATERIAL 常量的老脚本, 用显式覆盖声明其屏蔽层材质
SHLD_OVERRIDE = {"VCH_ml": "V"}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location("audit_" + name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def getp(txt: str, key: str):
    m = re.search(rf"^{key}\s*=\s*([^\s#]+)", txt, re.M)
    return m.group(1).strip('"') if m else None


def config_defaults(cfg_path: Path):
    """解析 Config 的 `PARAMETER <name> REAL <value>` 默认值。"""
    out = {}
    if not cfg_path.is_file():
        return out
    for line in cfg_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^PARAMETER\s+(\w+)\s+REAL\s+([^\s!]+)", line, re.I)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def expected_roles(mod, scene: str):
    """按场景常量推出每个物种应有的材质名。"""
    shld = getattr(mod, "SHLD_MATERIAL", None) or SHLD_OVERRIDE.get(scene, "CH")
    if shld not in MAT:
        shld = "CH"
    ti = getattr(mod, "TI_LAYER", None)
    roles = {"cham": "He", "shld": shld, "samp": "CH"}
    for sp in ("tar1", "tar2", "tar3", "tar4", "tar6"):
        roles[sp] = "Ti" if ti == sp else "CH"
    return roles


def audit_scene(name: str, script: Path, tmax: float):
    mod = load(name, script)
    cfg = dict(mod.config_constants)
    cfg["tmax"] = tmax
    mod.generate_input_files(cfg)

    par = mod.INPUT_DIR / mod.PAR_FILENAME
    txt = par.read_text(encoding="utf-8")
    cdef = config_defaults(mod.INPUT_DIR / "Config")
    roles = expected_roles(mod, name)

    rows, bad, used_tables = [], 0, set()
    for sp in SPECIES:
        mat = roles[sp]
        ra, rz, rr, rt = MAT[mat]
        used_tables.add(rt)
        cap = sp.capitalize()
        vals, src = {}, {}
        for label, key in (("rho", f"sim_rho{cap}"), ("A", f"ms_{sp}A"),
                           ("Z", f"ms_{sp}Z"), ("eos", f"eos_{sp}TableFile"),
                           ("op", f"op_{sp}FileName")):
            v = getp(txt, key)
            if v is not None:
                vals[label], src[label] = v, "par"
            else:
                vals[label], src[label] = cdef.get(key), "Config"
        try:
            ok = (abs(float(vals["rho"]) - rr) < 1e-6
                  and abs(float(vals["A"]) - ra) < 1e-4
                  and abs(float(vals["Z"]) - rz) < 1e-3
                  and vals["eos"] == rt and vals["op"] == rt)
        except (TypeError, ValueError):
            ok = False
        bad += 0 if ok else 1
        rows.append((name, sp, mat, vals, src, ok))

    missing = [t for t in sorted(used_tables) if not (mod.INPUT_DIR / t).is_file()]
    nlaser = len(re.findall(r"^ed_time_1_\d+", txt, re.M))
    info = dict(par=par.name, tmax=getp(txt, "tmax"), xmin=getp(txt, "xmin"),
                xmax=getp(txt, "xmax"), nlaser=nlaser)
    return rows, bad, missing, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmax", type=float, default=1.6e-9)
    ap.add_argument("--scenes", default=None, help="逗号分隔, 默认全部")
    ap.add_argument("--csv", default=str(HERE / "material_audit.csv"))
    args = ap.parse_args()

    sel = SCENES
    if args.scenes:
        want = {s.strip() for s in args.scenes.split(",")}
        sel = [(n, p) for n, p in SCENES if n in want]

    total_bad = 0
    csv_rows = [("scene", "species", "material", "rho", "A", "Z", "eos", "op",
                 "src_rho", "src_A", "src_Z", "verdict")]
    for name, script in sel:
        if not script.is_file():
            print(f"[!] 跳过 (缺脚本): {name}")
            continue
        rows, bad, missing, info = audit_scene(name, script, args.tmax)
        total_bad += bad
        mark = "OK" if bad == 0 and not missing else f"❌ {bad} 项不符"
        print(f"\n[{name}] {mark}   par={info['par']}  tmax={info['tmax']}  "
              f"域=[{info['xmin']}, {info['xmax']}] cm  激光段={info['nlaser']}")
        print(f"  {'物种':<6}{'应为':<5}{'rho':>10}{'A':>9}{'Z':>6}  "
              f"{'EOS/op 表':<26}{'来源(rho/A/Z)':<16}判定")
        for scene, sp, mat, vals, src, ok in rows:
            s = f"{src['rho']}/{src['A']}/{src['Z']}"
            print(f"  {sp:<6}{mat:<5}{str(vals['rho']):>10}{str(vals['A']):>9}"
                  f"{str(vals['Z']):>6}  {str(vals['eos']):<26}{s:<16}"
                  f"{'OK' if ok else '❌'}")
            csv_rows.append((scene, sp, mat, vals["rho"], vals["A"], vals["Z"],
                             vals["eos"], vals["op"], src["rho"], src["A"], src["Z"],
                             "OK" if ok else "MISMATCH"))
        if missing:
            print(f"  ❌ cn4 缺失: {missing}")
            for t in missing:
                csv_rows.append((name, "-", "-", "-", "-", "-", t, "-",
                                 "-", "-", "-", "MISSING_CN4"))

    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(csv_rows)
    print(f"\n{'=' * 62}\n审计结论: "
          f"{'全部通过' if total_bad == 0 else f'{total_bad} 处不符'}"
          f"   (明细 → {Path(args.csv).name})")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
