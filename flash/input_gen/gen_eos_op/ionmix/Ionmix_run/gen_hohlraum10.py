#!/usr/bin/env python3
"""
gen_hohlraum10.py — Hohlraum_AuCH 间接驱动场景 10 群表再生脚本

为 flash/scenarios/public/laserfusion/indirect_drive/Hohlraum_AuCH 场景
再生 He / CH / Au 三张 ionmix4 (.cn4) 表，能群统一为 **10 群**
（grupbd 与 layer_tracer VAuTi 场景 rt_mgdBounds_1..11 / au_ionmix10
完全一致，0.1 -> 1e5 eV，每群 0.6 decade）。

背景:
    Hohlraum_AuCH 原用 6 群 He/CH 表 (helium_hires/ch_mix) + 10 群 Au 表
    (au_ionmix10)。FLASH op_readIonmix4Tables 校验:
    (1) 表 ngrups == rt_mgdNumGroups
    (2) 表内 grupbd 与 par rt_mgdBounds_N 逐值相对误差 < 1e-4
    ⇒ 同一算例所有物种群数必须一致。开辐射 (useOpacity=.true.) 前
    需将 He/CH 再生为 10 群；本脚本一并再生 Au 保持同一批次。

温度/密度网格: 与 2026-07-08 / 2026-10-09 现有 Gen 表 **逐点一致**
    (仅换能群，EOS 部分不受能群影响):
    - ntemp=51, dlgtmp=0.08602, tplsma=1.0 eV  -> 1 ~ 2e4 eV
    - ndens=31, dlgden=0.31003
    - densnn: He=1e13 (1e13~2e22 cm^-3), CH/Au=1e16 (1e16~2e25 cm^-3)

用法:
    python gen_hohlraum10.py            # 生成 + 复制到 Gen_eos_op_data
    python gen_hohlraum10.py --no-copy  # 仅生成到 outputfiles

输出:
    outputfiles/cn4/gen_hohlraum10/{He10,CH10,Au10}*/...cn4
    (默认再复制到 eos_op_data/Gen_eos_op_data/<stem>/ 供注册表引用)
"""

import os
import shutil
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from ionmix_core import IONMIXInputGen

# ── eos_op_data 根目录 (Gen_eos_op_data 所在) ──
_EOS_OP_DATA = os.path.normpath(os.path.join(
    _SCRIPT_DIR, "..", "..", "..", "..", "eos_op_data"))

# ── 10 群边界 [eV]: 与 au_ionmix10 / layer_tracer rt_mgdBounds_1..11 一致 ──
GRUPBD_10G = [
    1.000000000e-01, 3.981072000e-01, 1.584893000e+00, 6.309573000e+00,
    2.511886000e+01, 1.000000000e+02, 3.981072000e+02, 1.584893000e+03,
    6.309573000e+03, 2.511886000e+04, 1.000000000e+05,
]


def _base_params(name: str) -> dict:
    """公共参数 (温度/密度网格与现有 Gen 表逐点一致)。"""
    return {
        '_name': name,
        'ntemp': 51,          # 温度点数
        'dlgtmp': 0.08602,    # 温度对数增量 (1 -> 2e4 eV)
        'tplsma': {1: 1.0},   # 起始温度 [eV]
        'ndens': 31,          # 密度点数
        'dlgden': 0.31003,    # 密度对数增量 (x10^9.3)
        'ntrad': 0,           # 辐射温度点数 (0=不变温)
        'trad': 200.0,        # 辐射温度 [eV]
        'nptspg': 200,        # 每群光子能量网格点数
        'nfrqbb': 15,         # 每条线中心附近额外网格点数
        'dtheat': 0.01,       # 热容/dZdT 温度增量分数
        'iplot': {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
        'isw': {
            5: 0,    # 复制输入文件到输出文件
            6: 3,    # 完整三体过程
            8: 3,    # 输出格式: 新 CONRAD 格式
            13: 1,   # 能群边界: 用户指定
            15: 8,   # 电子激发数 (主量子数)
            21: 1,   # 输出 eos.cn4
            24: 1,   # 光子能量网格类型
            25: 1,   # 添加线中心和电离边缘点
        },
        'grupbd': list(GRUPBD_10G),
    }


def build_params_list() -> list:
    """He10 / CH10 / Au10 三个参数字典 (物种组成与现表一致)。"""
    params_list = []

    # ── He10: 氦 (cham 充气/真空 + cgas 靶丸气), densnn=1e13 同现表 ──
    p = _base_params('He10 氦 10群 (Hohlraum_AuCH)')
    p.update({
        'ngases': 1,
        'izgas': {1: 2},
        'atomwt': {1: 4.002602},
        'fracsp': {1: 1.0},
        'densnn': 1.0e13,     # 1e13 ~ 2e22 cm^-3 (同 Z02_1.00-20260708_0851)
    })
    params_list.append(p)

    # ── CH10: 碳氢混合物 C0.5-H0.5 (caps 靶丸壳), densnn=1e16 同现表 ──
    p = _base_params('CH10 碳氢混合物 10群 (Hohlraum_AuCH)')
    p.update({
        'ngases': 2,
        'izgas': {1: 6, 2: 1},
        'atomwt': {1: 12.011, 2: 1.008},
        'fracsp': {1: 0.5, 2: 0.5},
        'densnn': 1.0e16,     # 1e16 ~ 2e25 cm^-3 (同 Z06_...-20260708_0850)
    })
    params_list.append(p)

    # ── Au10: 金 (gold 腔壁/端盖), densnn=1e16 同 au_ionmix10 ──
    p = _base_params('Au10 金 10群 (Hohlraum_AuCH)')
    p.update({
        'ngases': 1,
        'izgas': {1: 79},
        'atomwt': {1: 196.97},
        'fracsp': {1: 1.0},
        'densnn': 1.0e16,     # 1e16 ~ 2e25 cm^-3 (同 Z79_1.00-20261009_1256)
    })
    params_list.append(p)

    return params_list


def copy_to_eos_op_data(cn4_paths: list) -> list:
    """将生成的 cn4 复制到 eos_op_data/Gen_eos_op_data/<stem>/ (注册表约定)。"""
    copied = []
    base = os.path.join(_EOS_OP_DATA, "Gen_eos_op_data")
    for path in cn4_paths:
        if not path or not os.path.isfile(path):
            copied.append("")
            continue
        stem = os.path.splitext(os.path.basename(path))[0]
        dst_dir = os.path.join(base, stem)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(path))
        shutil.copy2(path, dst)
        print(f"  [+] 已复制: {dst}")
        copied.append(dst)
    return copied


def main():
    print("=" * 60)
    print("IONMIX 10 群表再生 — Hohlraum_AuCH (He/CH/Au)")
    print("=" * 60)
    print(f"  能群: 10 群, 边界 {GRUPBD_10G[0]:g} -> {GRUPBD_10G[-1]:g} eV")
    print(f"  网格: ntemp=51 (1->2e4 eV), ndens=31, densnn He=1e13/CH,Au=1e16")
    print()

    output_dir = os.path.join(_SCRIPT_DIR, "outputfiles", "cn4", "gen_hohlraum10")
    print(f"输出目录: {output_dir}")
    print()

    gen = IONMIXInputGen()
    results = gen.batch_run(build_params_list(), output_dir)

    print("=" * 60)
    print("生成汇总:")
    ok = True
    for r in results:
        if r and os.path.isfile(r) and os.path.getsize(r) > 0:
            print(f"  [+] {os.path.basename(r)}  ({os.path.getsize(r):,} bytes)")
        else:
            print(f"  [!] 失败: {r!r}")
            ok = False

    if ok and "--no-copy" not in sys.argv:
        print()
        print("复制到 Gen_eos_op_data (注册表约定位置):")
        final = copy_to_eos_op_data(results)
    else:
        final = results

    print("=" * 60)
    if ok:
        print("全部成功。注册名建议:")
        for path, canonical in zip(final, ["he_10g", "ch_10g", "au_10g"]):
            if path:
                rel = os.path.relpath(path, _EOS_OP_DATA).replace(os.sep, "/")
                print(f"  {canonical:8s} -> {rel}")
    else:
        print("存在失败项, 请检查上方日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()
