> 最后核对：2026-11-06 · commit 20337b6（flash-readme-sync 首轮补写）

# flash 包内快速数学/冒烟测试

## 职责

包内轻量级数学函数自检与 1D 快速冒烟数据，独立于仓库根 `test/` 三套件。

## 内容清单

| 文件 | 说明 |
|---|---|
| `math_test.py` | 数学函数快速自检（Planck/Saha 等闭式公式，配合 mock 模式） |
| `flash_mathtest_custom01.py` | 自定义数学测试变体 |
| `quick_test_1d.h5` | 1D 快速冒烟用 HDF5 样例数据 |

## 运行

```bash
.venv-win\Scripts\python.exe flash/test/math_test.py
```

## 关联资源

- `test/`（仓库根测试三套件）
