# VAuTi — V/Au/Ti 多层示踪靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：1D 多薄层示踪靶（**V 屏蔽层 + Au 样品层 + Ti 示踪层**，5e14 W/cm²）——Au 系新场景

## 物理构型（由 TiTi1 派生，2026-10-09）

| 层 | 材质 | 表/密度 |
|---|---|---|
| cham | He 填充 | — |
| shld | **钒 V**（0.1 µm） | V-BADGER-TOPS.cn4，ρ=6.11 g/cm³ |
| samp | **金 Au 全层** | Z79_1.00-20261009_1256.cn4（ionmix，ntemp=51/ndens=31/ngrups=10），ρ=19.32 g/cm³，A=196.97，Z=79 |
| targ | **钛 Ti**（0.1 µm） | Ti-BADGER-TOPS.cn4，ρ=4.54 g/cm³ |

- 与 TiTi 的物理差异：**4 物种标记**（cham/shld/samp/targ——无 tar1/2/3/4/6）；samp 全部为 Au
- ★ Au EOS/不透明度表必须用 **10 群版**（`grupbd` 精确 = 场景 `rt_mgdBounds`）；6 群版会被 FLASH `op_readIonmix4Tables` 能群校验 abort——引用表层文件时勿换 6 群版
- 激光 5e14 W/cm²；其余分层/激光/网格与 tracer 多薄层家族一致

## 运行

```bash
python -m flash.scenarios.core.entry.cli run VAuTi
```

## 家族关系

由 [TiTi](../../TiTi/README.md)1 派生（Au 系）；V 屏蔽对照 [VTi](../../VTi/README.md)；多薄层基准 [VCH_ml](../../VCH_ml/README.md)。

**上级导航**：[../README.md](../../../../README.md)
