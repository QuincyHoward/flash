---
name: flash-ionmix-gen
description: IONMIX 生成 EOS/不透明度 cn4 数据表的完整工作流：IONMIXInputGen 参数字典、ionmxinp 生成、WSL gfortran 编译/运行 abjt_03、cn4 文件命名规范（Z 占比 + _{n}g 群数后缀）、gen_Si/gen_mywork 模板复制流程、0 字节输出与电离势缺失排查、生成后用 eosop_pro 解析验证与绘图。触发词：生成 cn4、IONMIX 生成、生成 EOS 数据、gen_Si、gen_mywork、ionmxinp、IONMIXInputGen、abjt_03、群数后缀、能群边界生成、eosop 数据生成。
---

> 最后核对：2026-11-14 · commit c7b2c92（含 _{n}g 群数后缀命名）

# IONMIX 生成 eosop 数据工作流（ionmix/Ionmix_run）

权威参考：
- `flash/input_gen/gen_eos_op/ionmix/Ionmix_run/IONMIX用户指南.md` — 物理模型/参数详解（1274 行）
- `flash/input_gen/gen_eos_op/ionmix/README.md` — 包概览
- 解析/绘图侧见 **flash-eos-op** skill（eosop_pro）

## 1. 目录结构

```
gen_eos_op/ionmix/
├── Ionmix_run/                 ← 生成器（Python 层）
│   ├── ionmix_core.py          ← IONMIXInputGen 类（唯一核心）
│   ├── gen_Si.py               ← 可运行模板（Si/Au/N 示例）
│   ├── gen_mywork.py           ← 用户自定义模板（复制改名用）
│   ├── gen_examples.py / gen_paper.py / gen_hohlraum10.py
│   ├── IONMIX用户指南.md
│   └── outputfiles/cn4/<脚本名>/   ← 产物落这里
├── src/Ionmix/                 ← Fortran 源码与二进制
│   ├── abjt_03.f / abjt_03     ← IONMIX 源码（ABJT, CPC 1989）与 ELF 可执行
│   ├── ATOMxx.DAT              ← 默认电离势缺失时的补充文件
│   └── ionmxout / ionmxbug / implot0x
└── temp_delete/                ← 旧版遗留（勿用）
```

## 2. 核心用法（IONMIXInputGen）

```python
import sys; sys.path.insert(0, r"<...>/gen_eos_op/ionmix/Ionmix_run")
from ionmix_core import IONMIXInputGen

gen = IONMIXInputGen()
params = {
    '_name': 'CH 泡沫',
    'ngases': 2,
    'izgas':  {1: 6, 2: 1},          # 原子序数
    'atomwt': {1: 12.011, 2: 1.008}, # 原子量 amu
    'fracsp': {1: 0.5, 2: 0.5},      # 原子数占比
    'ntemp': 21, 'dlgtmp': 0.105, 'tplsma': {1: 1.0},   # Te 起点与对数增量
    'ndens': 21, 'dlgden': 0.14, 'densnn': 1.0e16,      # densnn 是数密度 cm^-3
    'ntrad': 0, 'trad': 200.0,       # 0 = 辐射温度固定
    'nptspg': 5, 'nfrqbb': 5, 'dtheat': 0.01,
    'isw': {5: 0, 6: 3, 8: 3, 13: 1, 21: 1, 24: 1, 25: 1},  # 21=1 才输出 eos.cn4
    'grupbd': [0.1, 1, 10, 100, 1000, 10000, 100000],  # 群边界 eV
}
cn4 = gen.run_single(params, output_base_dir)   # 返回 cn4 绝对路径
# 批量: gen.batch_run(params_list, output_base_dir)
```

关键约定：
- `set_grupbd(boundaries)` 自动设 `ngrups = len(boundaries)-1`
- `isw(21)=1` 必须，否则无 eos.cn4 输出
- EOS 规范（eos_op_data 固化）：ntemp=61/dlgtmp=0.105/ndens=71/dlgden=0.14/densnn=1e16/trad=200.0

## 3. 文件命名规范（2026-11-14 起）

```
Z{Z:02d}_{frac:.2f}[-Z...]*_{ngrups}g-{YYYYmmdd_HHMM}.cn4
例: Z06_0.50-Z01_0.50_5g-20261114_1530.cn4
```

- `_6g` `_10g` 群数后缀 = 参数 `ngrups`（由 grupbd 长度自动决定），未设 grupbd 则无后缀
- 同名目录存放 `ionmxinp` 与 cn4；运行后自动清理只留 abjt_03(.f)/ionmxinp/ionmxout/ionmxbug/*.cn4

## 4. 运行机制与排查

- 运行走 **WSL**：`wsl --cd <win_to_wsl(work_dir)> ./abjt_03`（Linux ELF）
- 二进制缺失/0 字节时自动用 WSL gfortran 编译：`gfortran -O2 -ffixed-line-length-132`
- **0 字节输出** → 读 ionmxout 查电离势为 0 的元素 → 需在源目录建 `ATOM{Z:02d}.DAT`
- eos.cn4 未生成 → 读 `_stderr.log` 查 "Fortran runtime error"
- 单次运行秒级~分钟级；21×21 网格 × 6 群实测 <1 min

## 5. 生成 → 验证 → 报告 联动（eosop_pro）

1. 生成后立刻用 eosop_pro 验证：`from eosop_pro.parsers.cn4_io import load_cn4; load_cn4(<cn4>)` 计数校验（18 块、4e12.6 定宽）
2. 绘图核查：`python -m eosop_pro.pipeline.cli cn4-plot <cn4>` 或 parsers/test 核查套件
3. 产物核查测试在 `eosop_pro/parsers/test/test_cn4_io.py`（byte-identical 往返等）；生成数据专项报告见 `test_cn4_generated.py`
4. 表文件入库用 generator.py 注册（见 flash-eos-op skill）

## 6. 硬纪律

1. 新任务 = 复制 gen_mywork.py 改 `build_params_list()`，勿改 ionmix_core.py 语义
2. grupbd 群数 ≤50；nptspg/nfrqbb 与群边界搭配需查指南 §4
3. 产物目录以脚本名分组（outputfiles/cn4/<脚本名>/），勿手动散放
4. eos_op_data 已有同名旧格式文件（无 _{n}g 后缀）不回填改名，新文件才用新命名
