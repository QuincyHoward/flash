# NewPara — 新参数区域控制与划分测试

## 目标

演示 FLASH 新参数设置的完整 5 步流程，通过运行时参数控制区域划分。

## 新增参数

| 参数名 | 类型 | 默认值 | 用途 |
|--------|------|--------|------|
| `sim_useTwoTargets` | BOOLEAN | FALSE | 启用第二靶区 |
| `sim_polyHeight` | REAL | 0.005 | 第二靶厚度 |
| `sim_rhoPoly` | REAL | 1.0 | 第二靶密度 (CH) |
| `sim_telePoly` | REAL | 290.11375 | 第二靶电子温度 |
| `sim_tionPoly` | REAL | 290.11375 | 第二靶离子温度 |
| `sim_tradPoly` | REAL | 290.11375 | 第二靶辐射温度 |

## 文件清单

```
flash_input/              ← FLASH 源文件（拷贝到 WSL 编译）
├── Config                ← ① 注册新 PARAMETER
├── Simulation_data.F90   ← ② 声明新变量
├── Simulation_init.F90   ← ③ RuntimeParameters_get
├── Simulation_initBlock.F90 ← ④ 增量边界 + 三区逻辑
├── Makefile              ← Simulation += Simulation_data.o
├── laserslab_newpara.par ← ⑤ 新参数赋值
├── al-imx-003.cn4        ← 铝 EOS
├── he-imx-005.cn4        ← 氦 EOS
├── polystyrene-imx-008.cn4 ← 聚苯乙烯 EOS
└── run_flash.sh          ← WSL 部署脚本
run_newpara_test.py       ← Python 编排脚本
analyze_density_indep.py  ← 密度分析脚本
wsl_deploy.sh             ← WSL 一键部署
copy_to_wsl.sh            ← 复制文件到 WSL
output/
└── plots/                ← 密度分析图
```

## 5 步流程（参考 newparaset/README.md）

1. **Config** — 添加 `PARAMETER` 行定义新参数
2. **Simulation_data.F90** — 添加 Fortran 变量声明
3. **Simulation_init.F90** — 添加 `RuntimeParameters_get` 调用
4. **Simulation_initBlock.F90** — 增量边界算法 + 物种逻辑
5. **laserslab_newpara.par** — 设定参数值

## 关键约束

- **物种名不超过 4 个字符**（FLASH 截断限制）
  - `targ2`(5字符) ❌ → `poly`(4字符) ✅
- **增量边界**（ReDo 模式）：`bound = prev + param`
- **setup 命令**必须列出所有物种：`species=cham,targ,poly`

## 测试结果

```
真空区(He): mean ρ ≈ 1e-6   ✅
铝靶区(Al): mean ρ ≈ 2.7    ✅
CH靶区(poly): mean ρ ≈ 1.0  ✅

---

## 相关文档

| 文档 | 位置 | 内容 |
|------|------|------|
| 新参数流程指南 | `input_gen/gen_newpara/README.md` | 5 步流程 + 密度剖面 + 增量边界 |
| **FLASH 内置参数参考** | **`input_gen/gen_newpara/RP_Reference.md`** | **所有 FLASH 4.8 内置参数 (无需重新注册声明)** |
| FLASH 操作规范 | `docs/flash_operation_standard.md` | 绘图/运行/结果处理规范 |
```
