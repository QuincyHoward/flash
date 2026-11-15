> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

test/ —— 零依赖测试套件（54 文件 / 691 测试，run_all.py 全绿）

`_runner.py` 为零依赖运行器（不依赖 pytest）：测试文件头两行
`import _runner` + `from _runner import ...`；_runner 导入时把 gen_eos_op
（使 `import eosop_pro` 生效）与 test/ 注入 sys.path。
`_bootstrap.py`/`_migrate_bootstrap.py` 支持任意深度子目录单文件裸跑。

汇总运行（在 eosop_pro/ 或 gen_eos_op/ 下）：

    python test/run_all.py          # 退出码 = 失败数

子包按功能划分：core/registry/parsers/plotting/io/pipeline/hygiene/
eosopdata（step01_cn4/step02_families/step03_transcn4）/sound_velocity。
hygiene/ 为守护测试（config 单源扫描、bat CRLF、包装脚本一致性）。
cross_validate_cn4.py 为 cn4 与参考实现（ionmix/ionmix/eosop_pro/core）的
独立交叉验证（非 test_ 前缀，不进 run_all）。

## 子包

- `_bootstrap.py`
- `_migrate_bootstrap.py`
- `_runner.py`
- `core/`（子包）
- `cross_validate_cn4.py`
- `eosopdata/`（子包）
- `hygiene/`（子包）
- `io/`（子包）
- `parsers/`（子包）
- `pipeline/`（子包）
- `plotting/`（子包）
- `registry/`（子包）
- `run_all.py`
- `sound_velocity/`（子包）
