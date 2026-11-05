# gen_eos_op/ionmix/ionmix — IONMIX 输入生成与 .cn4 后处理（参考实现）

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：IONMIX 输入卡生成（`src/Ionmix_run/`）与 IONMIX `.cn4` 结果后处理的**参考实现**（`eosop_pro/core/`，扁平脚本架构）。注意目录为**双层同名嵌套** `ionmix/ionmix/`（历史原因，进入本目录后路径含两级 ionmix）。

## 文件清单

```
ionmix/ionmix/
├── docs/IONMIX用户指南.md      1274 行权威用户指南（唯一正式文档）
├── src/Ionmix_run/             输入卡生成
│   ├── ionmix_core.py   (504)  IONMIXInputGen 核心输入生成与运行
│   ├── gen_examples.py  (382)  通用示例批量生成
│   ├── gen_mywork.py    (157)  用户自定义模板
│   ├── gen_Si.py        (157)  硅专用模板
│   └── gen_paper.py     (171)  文献复现示例
└── eosop_pro/                  .cn4 后处理参考实现（与 ../../eosop_pro/ 目标实现并存，
    ├── core/                    cross_validate_cn4.py 专门验证两者一致性）
    │   ├── cn4_parser.py (400)  CN4Data 解析
    │   ├── eos_paths.py  (843)  EOS 路径研究（任务 E）
    │   ├── plot_heatmaps/plot_time_series/plot_curves/plot_eosop/plot_utils
    │   ├── fit_relations.py (196) 拟合（任务 D）
    │   └── units.py             单位约定
    └── test/
        ├── test_all.py (430)    任务 A-E 全局测试
        ├── run_tests.py         一键运行 + HTML 报告（generate_report.py 260）
        └── E4data/              Hugoniot 任务数据
```

## 使用入口

```bash
# IONMIX 输入卡生成（详见 docs/IONMIX用户指南.md）
python ionmix/ionmix/src/Ionmix_run/gen_examples.py

# .cn4 后处理测试 + HTML 报告
python ionmix/ionmix/eosop_pro/test/run_tests.py
```

## 与目标实现的关系

`eosop_pro/core/`（本目录）是**早期扁平参考实现**；生产级目标实现在 [`../../eosop_pro/`](../../eosop_pro/README.md)（分层包架构：parsers 17 解析器/统一网格/双轨 HDF5）。两者由 `../../eosop_pro/eosop_pro/test/cross_validate_cn4.py` 交叉验证一致性。新功能请进目标实现。

**上级导航**：[../../GEN_EOS_OP_GUIDE.md](../../GEN_EOS_OP_GUIDE.md)
