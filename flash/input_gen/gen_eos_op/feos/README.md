# feos — FEOS 输入卡生成、运行与 .feos→cn4 转换

> FEOS 16.7（Dr. Steffen Faik，GPL v3）表生成工具的 Python 封装，结构镜像 `ionmix/`。
> FEOS 只产 **EOS 表**（`.feos` 原生格式，P/E/S/F/Zbar，cgs+eV），**无不透明度**。

## 文件清单

```
feos/
├── README.md            本文
├── __init__.py
├── feos_run/
│   ├── feos_core.py     FEOSInputGen 类（.par 生成 → WSL 编译/运行 → 重命名/清理）
│   ├── feos_to_cn4.py   .feos → .cn4 转换器（复用 eosop_pro cn4_io.write_cn4）
│   ├── gen_examples.py  示例驱动：Al + SiO2（= vendored 全部示例），--cn4/--no-copy
│   ├── gen_mywork.py    用户复制改名模板
│   └── FEOS用户指南.md  权威指南（v3.0：目录体系对齐 IONMIX用户指南，全 LaTeX 公式；§2 物理模型——QEOS/TF/Cowan/软球/Maxwell，源码+文献双依据）
├── Documents/           # 文献 PDF：Faik CPC 2018 原文、HEDP 2012 arXiv、PhD 答辩幻灯
├── outputfiles/
│   ├── feos/            .feos 产物（<脚本名>/<basename>-<timestamp>/）
│   └── cn4/             转换出的 .cn4
└── src/FEOS/            vendored 源码（Code/ + EOS-Data/ + Documents/；.gitignore 排除）
```

## 快速上手

```bash
python feos_run/gen_examples.py            # 全部示例（Al + SiO2）
python feos_run/gen_examples.py Al --cn4   # 指定示例 + 联动 cn4 转换
python feos_run/feos_to_cn4.py <in.feos> [out.cn4]   # 单独转换
```

```python
from feos_core import FEOSInputGen
gen = FEOSInputGen()
cn4 = gen.batch_run([{
    '_name': 'Al', '_elements': [(13.0, 1.0)],
    'material_number': 3717, 'rhonorm': 2.7,
}], "outputfiles/feos")[0]
```

## 命名规范

`.feos`/`.cn4` 主干 = `Z{Z:02d}_{x:.2f}[-Z...]-{YYYYmmdd_HHMM}`（x 为原子分数）。
**无群数后缀**（FEOS 不产不透明度），与 ionmix 的 `_{n}g` 后缀相区别。

## .feos→cn4 转换要点

- 布局一手依据：`src/FEOS/Code/FE-01_TABTOOLS.C` `write_FEOS_format`（16 个二维块 + Qtot + Q）；
- 块映射：`p_ion←Pi`、`p_ele←Pe`、`e_ion←Ei`、`e_ele←Ee`（FEOS 内 P=Pi+Pe 守恒）、`zbar←Qtot/Xtot`（Qtot 是每化学式总量，LIB-03_TF_MIXTURE.C:123；每核归一，混合物必须除）、`dzdt←Qtot 对 T 中心差分 ÷Xtot`（FLASH USED）；Q 块 k 最内层交错；其余导数/热容槽位 NaN 占位；
- 单位换算：压强 dyn/cm²→J/cm³（×1e-7），比能 erg/g→J/g（×1e-4）；
- 网格：FEOS 含 Qstart=0.0 前导哨兵点，转换时修剪非正轴点；
- **不透明度块 = 零占位**（ngrups=6，DEFAULT_GRUPBD 7 边界，与现役 ionmix 表同构）——**禁止消费其不透明度**；
- 密度轴：cn4 数密度 n_ion = rho·N_A/⟨A⟩（⟨A⟩=Atot/Xtot）。

## 与其他子体系的关系

- **ionmix**：结构模板与 cn4 格式参照（ionmix 产 EOS+不透明度，feos 仅 EOS）；
- **eosop_pro**：`feos_native.py` 解析 .feos 头部/网格；`cn4_io.write_cn4` 写出 cn4（复用，不新写编码器）；
- **generator.py**：feos 产出的 cn4 丢入 `eos_op_data/` 即可按 stem 自动发现/注册。

## 陷阱速查

1. `feos <name>` 接收**不带 .par 后缀**的名字（代码自动拼接）；
2. `FEOS_Material-DB.dat` / `FEOS_TF-Table_1197.dat` 按 **CWD 相对路径**读取——必须拷入运行目录；
3. Material-Number 必须在 Material-DB 中（1000-9999），运行前有预检；
4. `.feos` 头部 NR/NT 含 Qstart 哨兵语义（首点 0.0）；
5. FEOS 上游代码存在**间歇性 buffer overflow**（glibc 检测，编译警告 sprintf 到 char[70]）——崩溃后重跑即可，产物以 `.feos` 存在为准。

---
**文档版本**: 1.0 · **创建**: 2026-11-14 · **维护**: PhySimX Team
