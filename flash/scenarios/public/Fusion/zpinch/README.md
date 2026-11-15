# scenarios/public/Fusion/zpinch

> 最后核对：2026-11-08 · commit 96aa10d

**一句话职责**：Z 箍缩专题场景分组——Be-liner 圆柱 Z 箍缩 MHD 几何验证

**内容导航**：`ZPinch_BeLiner/`（1D 圆柱 Be liner + DD 充气 + 真空三区，复用官方 `magnetoHD/ZPinch` 模块，usm3t MHD + MGD 6 群 + Circuit 电流驱动；tmax=1e-12 极短运行；场景名 `zpinch_beliner`，详见其 [README](ZPinch_BeLiner/README.md)）

**说明**：本目录是场景编组层（无独立 scene.json）；场景发现/注册由 manifest 驱动（见 `__init__.py` 头注释）。

**上级导航**：[../README.md](../README.md)
