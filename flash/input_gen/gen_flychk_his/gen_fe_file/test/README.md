# gen_fe_file/test — 测试说明

> 最后核对：2026-11-18

## 运行

```bash
# pytest 全量
python -m pytest flash/input_gen/gen_flychk_his/gen_fe_file/test -q

# 端到端（S1~S6, 产物写 out/REPORT.md）
python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py

# 联跑 pytest
python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py --pytest
```

## 文件

| 文件 | 覆盖 |
|---|---|
| `conftest.py` | sys.path 注入（`_ROOT = parents[4]`，比父级多一层）+ `out_dir`/`history_table` fixtures |
| `test_fe_model.py` | `maxwell_fe` 手算精确值、细网格积分 ≈ n_beam、密度缩放比、drift/mono 模型、normalize_to_density、非法 te/model 拒绝 |
| `test_fe_render.py` | 官方格式逐行核对（首行 "n_steps n_energies"、时间+密度同行、%.6e）、注释行、500 点行宽 ≤120、文件名 |
| `test_fe_validate.py` | error/warning 逐条触发（501 点/降序/非正能量/NaN/负 fe/重复时间/长度不匹配/零密度/归一偏差） |
| `test_zip_fe_integration.py` | 含 fe zip 三成员顺序、runfile `fe file` 行位置、fe 内容逐字符相等、verify_zip 新 checks、篡改检测、fe=None 向后兼容、桥接函数端到端 |
| `run_test.py` | 端到端 S1~S6（下表），报告写 `out/REPORT.md` |

## 端到端场景矩阵

| 场景 | 内容 | 通过判据 |
|---|---|---|
| S1 maxwell 小网格 | Te=1keV × 2 时间步 → 完整 zip | 成员数=3、runfile 含 fe 行、fe 文本逐字符比对、verify ok |
| S2 显式数组 | 3 时间步手工 fe 数组 → zip | 回读 fe 与输入逐字符一致 |
| S3 500 点压力 | 500 能量点 | 全部行宽 ≤120 + verify ok |
| S4 时间序列密度 | densities 随时间衰减 | 每步 fe 缩放比 == 密度比 |
| S5 非法输入拒绝 | 501 点/降序网格/负 fe/重复时间/不成对参数 | 抛 ConfigError/FeFileError 且零 zip 产物 |
| S6 回读自检+篡改 | verify 全 checks 通过；篡改 fe 成员 | 篡改后 verify 失败 |

## 产物

- `out/REPORT.md` — 端到端报告（每次运行重建）
- `out/<场景>/` — 各场景 zip 产物
