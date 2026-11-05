# gen_f90 — F90 生成器预留模块

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：FLASH Fortran 自定义组件生成器的**空预留位**（当前仅 `__init__.py`，无可执行代码）。

规划中的生成方向：FLASH 自定义 F90 组件（如 `Grid_markRefineDerefine`、`Simulation_data` 等）的参数化生成。同类已实现的先例见 [`../gen_Grid_markRefineDerefine/README.md`](../gen_Grid_markRefineDerefine/README.md)（AMR 细化约束生成器）与 [`../gen_sim_initblock/`](../gen_sim_initblock/GEN_SIM_INITBLOCK_GUIDE.md)（initBlock 生成器）。

**上级导航**：[../README.md](../README.md)（input_gen）
