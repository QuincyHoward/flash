---
name: flash-scenario-family
description: FLASH 场景家族派生（模板 + SCENE VARS 块 + build_family）、运行时关辐射变体（_F）、cn4/IONMIX4 表能群数与密度网格核查、tmax 覆盖守卫与套件批量测试、WSL 环境故障快查。触发词：场景家族、派生场景、build_family、build_sic_family、关辐射、_F 变体、run_ml_suite、SCENE VARS、tmax 覆盖、套件测试、cn4 表、能群数、密度网格。
---

> 最后核对：2026-11-06 · commit 72f6428

# FLASH 场景家族派生 + 关辐射变体工作流

适用：从已有 1D 多层示踪场景派生材质/深度/辐射开关变体家族。
参考实现（已核实存在于 `flash/scenarios/private/tracer/`）：
- CHTi 家族：`tracer/CHTi/CHTi1.py`（模板）+ `build_family.py` + `run_ml_suite.py` + `check_suite_initial.py`
- TiTi 家族：`tracer/TiTi/TiTi1.py` + `build_titi_family.py`（SHLD_MATERIAL 新增 "Ti" 分支，shld CH→Ti 4.54，与 Ti 示踪层同 3 键绑定）
- 单一纯材料家族：`tracer/OneSi_ml.py` + `build_sic_family.py` + `run_sic_suite.py` + `check_sic_initial.py`

## 1. 家族模板架构（替代逐脚本复制）

- 唯一模板脚本内放定界块 `# ── BEGIN SCENE VARS ... END SCENE VARS ──`。
  CHTi 家族 4 常量：`SCENE_NAME` / `SHLD_MATERIAL`("CH"|"V"|"Ti") / `TI_LAYER`("tar1..3"|None) / `RADIATION_OFF`(bool)。
  OneSi/OneC 家族 7 常量：`SCENE_NAME`/`MAT_LABEL`/`MAT_TABLE`/`MAT_RHO`/`MAT_A`/`MAT_Z`/`RADIATION_OFF`。其余逻辑全读常量分支化。
- `build_*.py` 读模板 → 切 docstring（前两个 `"""` 之间）+ SCENE VARS 块 → 按变体表重新拼装生成各脚本（assert 标记各出现一次 + 自检仅这两块不同）。
  ★ 装配时 make_vars 收尾换行只能出现一次（自带 "\n" 就不要再补），否则块后多出空行、head/tail 自检失败。
- 物种 par 绑定链：species_defs → Config PARAMETER 默认；运行时覆写用 `par_gen.set(f"sim_rho{X}", ...)` / `eos_{X}TableFile` / `op_{X}FileName`。
- ★ 数值注入用 `repr(rho)` 而非 `f"{rho:.2f}"`——2.329 会被 :.2f 舍成 2.33。

## 2. 材质表（cn4）必须与 par 引用同源校验

★ 教训（VCH_ml_F 首跑 abort）：par 里引用 V-BADGER-TOPS.cn4 但复制清单漏 V 表
→ `DRIVER_ABORT: no IONMIX4 file found`。
模板 `tables` 复制清单必须覆盖所有 par 引用分支（按 SHLD_MATERIAL/TI_LAYER 各自 append）。

## 3. cn4 表核查（换材质/换密度前必做）

- **能群数**：表头第 4 行 = nEnergyGroups。FLASH 要求全部物种不透明度表能群数一致，
  混用即 `op_readIonmix4Tables: bad size of IONMIX4 energy group grid`
  （报错两数 = 表群数 + par 要求群数）。
  族约定：BADGER 族 10 群（He/CH/V/Ti）；Gen_eos_op_data 族 6 群（Z02/Z06/Z14）
  → 用 6 群表时 `rt_mgdNumGroups=6` + 十倍程 bounds 0.1/1/10/100/1e3/1e4/1e5 eV，
  cham He 表用 Z02_1.00-20260708_0851.cn4（先例：center_evolution/ch_center）。
- **密度网格**：IONMIX4 的密度网格单位是**离子数密度 (#ions/cm³)** 而非 g/cm³
  （FLASH 源码 op_readIonmix4Tables 确认；Gen_eos_op_data 表网格 [1e16, 2e25] ions/cm³，
  温度 [1, 2e4] eV）。表名 `Z{Z}_{rho0}` 中 rho0=1.00 只是生成标称密度，**不构成密度上限**。
  固体密度换算 `n_ion = rho/A*N_A` 核查在网格内即可（Si 2.329→4.99e22 ✓, C 3.515→1.76e23 ✓）。

## 4. 运行时关辐射（纯 par 三开关，源码/编译零改动）

机制学自参考 ReDo042sp_CH042sp*umL8.00e-02（开）vs *umF8.00e-02（关）：

```par
rt_useMGD   .true. → .false.
useOpacity  .true. → .false.
useRadTrans (新增) → .false.
```

rt_mgd*/op_* 参数保留不动（关闭时无害）。FLASH 接受 useRadTrans 运行时参数。

## 5. tmax 覆盖 + 再生守卫

- 每脚本 argparse `--tmax`（家族场景默认 1e-11，单场景 OneCH/VCH 默认 1.6e-9；
  用户会手动改套件默认值——改回/改值以用户当前指令为准）。
- `_par_tmax_ok(tmax)`：正则读现有 par 的 tmax，相对容差 1e-12
  （1.0e-11 在 par 中渲染为 9.999999999999999e-12，靠容差消化）；不符则重新生成输入。
- 共享 flash_input 的家族目录（如 CHTi1/2/3 共用 CHTi/flash_input）→
  main() 必须**无条件全量重生成输入**，防跨变体串味。
- 密度等 SCENE VARS 变更后：`rm -rf` 各场景 flash_input/ 强制全新生成
  （par 再生守卫只看 tmax，不看密度）。

## 6. 套件批量测试

`run_ml_suite.py` / `run_sic_suite.py`：SCENARIOS 列表 + `--only a,b,c` 过滤 +
`--tmax` 统一覆盖（子进程传 `repr(args.tmax)`）+ 每场景计时 PASS/FAIL 汇总表。
验证运行 tmax=1e-11 每场景 ~1 min（WSL）。tmax 极小时单帧守卫跳过时空图属正常。

## 7. 初始帧快检

`check_suite_initial.py`（CHTi 家族，剖面自证匹配 run 归属）与
`check_sic_initial.py`（OneSi/OneC 家族，RHO_SOLID dict 按材质判定；
FlashDataLoader + `extraction_mode="yt"`，禁裸 load()）：chk_0000 检查
各标记层密度、samp 基体、物种 0/1 阶跃（层内均值≈1、层外 max≈1e-99）。
新增场景只需在 SCENARIOS/RHO_SOLID 映射加一行。

## 8. WSL 环境故障快查（FLASH exit=1 且秒退）

- objdir（FLASH 树内 `LaserSlab_*` 目录）检查 `flash4` 可执行存在且 `flash.par` 非 0 字节；
  0 字节 par = 编译/复制被瞬时中断，单独重跑即恢复。（objdir 位置由 FLASH 树部署路径决定，
  环境自检：`python -m flash.scenarios.core.runner --check-env`）
- Windows "页面文件太小"（WinError 1455）会让 HDF5 分析内存分配失败 →
  脚本误判 FAIL（FLASH 本体与分析逻辑均正常），错峰重跑即可。

## 关联资源

- `flash/scenarios/private/tracer/` — 家族实现
- skill `flash-eos-op` — cn4/cnr 表处理细节
- skill `flash-scenario-setup` — SNB 侧铁律与判据
- `flash/output_pro/README.md` — 输出分析入口
