# gen_eos_op/ionmix — IONMIX 输入生成与 .cn4 生成

> 最后核对：2026-11-14 · commit c7b2c92（含 _{n}g 群数后缀命名）

**一句话职责**：IONMIX 输入卡生成与运行（`Ionmix_run/` Python 层 + `src/Ionmix/` Fortran 层），产出带群数后缀的 `.cn4` EOS/不透明度数据表。工作流 skill：`.workbuddy/skills/flash-ionmix-gen/`。

## 文件清单

```
ionmix/
├── Ionmix_run/                 ← 生成器（Python 层）
│   ├── ionmix_core.py   (520)  IONMIXInputGen 核心：参数字典 → ionmxinp → WSL 运行 → cn4
│   ├── gen_Si.py        (155)  可运行模板（Si/Au/N 示例）
│   ├── gen_mywork.py    (156)  用户自定义模板（复制改名用）
│   ├── gen_examples.py  (381)  通用示例批量生成
│   ├── gen_paper.py     (170)  文献复现示例
│   ├── gen_hohlraum10.py(187)  腔靶 10 群示例
│   ├── IONMIX用户指南.md       1274 行权威指南（物理模型/参数/输出详解）
│   └── outputfiles/cn4/<脚本名>/  ← 产物（Z.._{n}g-时间戳.cn4 + ionmxinp）
├── src/Ionmix/                 ← Fortran 源码与运行资源
│   ├── abjt_03.f / abjt_03     ← IONMIX 源码（ABJT, CPC 56(1989) 259-278）与 ELF
│   ├── ATOMxx.DAT              ← 默认电离势缺失元素（如 Z>54 部分）的补充文件
│   └── ionmxout / ionmxbug / implot0x
├── docs/                       ← 文档
├── temp_delete/                ← 旧版 eosop_pro 参考实现（勿用，保留备查）
└── README.md                   ← 本文件
```

## 使用入口

```bash
# 生成（输出至 Ionmix_run/outputfiles/cn4/gen_Si/）
python gen_eos_op/ionmix/Ionmix_run/gen_Si.py

# 程序化调用
from ionmix_core import IONMIXInputGen   # 见 IONMIX用户指南.md §6
```

## cn4 命名规范（2026-11-14 起）

```
Z{Z:02d}_{frac:.2f}[-Z...]*_{ngrups}g-{YYYYmmdd_HHMM}.cn4
例: Z06_0.50-Z01_0.50_5g-20261114_1530.cn4
```

群数后缀 `_{n}g` 由参数 `grupbd`（`set_grupbd` 自动 ngrups=len-1）控制；未设 grupbd 则无后缀。

## 与 eosop_pro 的关系

- 生成 → 验证：`eosop_pro/parsers/cn4_io.py` 解析（18 块计数校验）；核查测试
  `eosop_pro/parsers/test/test_cn4_generated.py`（解析统计 + 绘图 + HTML 报告）
- `temp_delete/eosop_pro/` 为早期扁平参考实现，由
  `../../eosop_pro/test/cross_validate_cn4.py` 交叉验证；生产实现见
  [`../../eosop_pro/`](../../eosop_pro/README.md)

## 说明

ionmix 源程序 abjt_03.f 已添加自动输出 cn4 格式及其他自定义功能；运行走 WSL
gfortran（二进制缺失时自动编译）。

**上级导航**：[../../README.md](../../README.md)
