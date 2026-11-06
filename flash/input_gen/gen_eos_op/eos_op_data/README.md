# gen_eos_op/eos_op_data — EOS/不透明度数据目录

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：`.cn4`（ionmix4）表文件数据库——`EOSOpacityGenerator` 递归扫描本目录（层级无关），**纯数据区，无代码**。

## 结构（6 子目录 / 10 个 .cn4，2026-11-05 实测）

| 子目录 | 内容 |
|---|---|
| `Gen_eos_op_data/Z02_1.00-20260708_0851/` | 氦 |
| `Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/` | CH 混合 |
| `Gen_eos_op_data/Z06_1.00-20260902_2228/` | 碳 |
| `Gen_eos_op_data/Z14_1.00-20260708_0850/` | 硅 |
| `Gen_eos_op_data/Z79_1.00-20261009_1256/` | 金（ngrups=10） |
| `Gen_eos_op_data/badger_qc/` | BADGER-TOPS/QC 五表 |

**维护规则**：文件不移动/不删除/不重命名（注册表引用路径）；新增表放任意子目录即可被自动发现，重要材料建议在 `generator.py` 注册别名。材料注册表与别名见 [../README.md](../README.md) §4。

**上级导航**：[../README.md](../README.md)
