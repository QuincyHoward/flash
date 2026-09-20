# FLASH 质子射线照相工具

## 概述

质子射线照相分析工具位于 `tools/protonRad/`，包含两个源自 Flash Center GitHub 仓库的 Python 包：

| 包 | 来源 | 说明 |
|----|------|------|
| **PRaLine** | [flash-center/PRaLine](https://github.com/flash-center/PRaLine) | 质子射线照相重建代码（Graziani et al., 2017） |
| **PRadReader** | [flash-center/PRadReader](https://github.com/flash-center/PRadReader) | PRaLine 的依赖，质子辐射数据读取器 |

## 目录结构

```
protonRad/
├── README.txt                # 主说明文档
├── PRaLine/                  # 质子射线照相重建
│   ├── README.md             # 详细文档
│   ├── LICENSE
│   ├── MANIFEST.in
│   ├── setup.py              # 安装脚本
│   ├── examples/             # 示例
│   │   ├── README.txt
│   │   ├── test_input.p      # 示例输入（pickle, ~1MB）
│   │   ├── test_input.txt    # 示例输入文本
│   │   └── reference_images/ # 参考结果图像
│   └── praline/              # Python 包
│       ├── __init__.py
│       ├── Bplot2.py         # 磁场绘图
│       ├── algorithm.py      # 重建算法
│       ├── analysis.py       # 分析函数
│       ├── constants.py      # 常数
│       ├── image.py          # 图像处理
│       ├── path.py           # 射线路径
│       ├── rad_ut.py         # 辐射实用函数
│       └── reconstruct.py    # 磁场重建
└── PRadReader/               # 质子辐射数据读取器
    ├── README.md
    ├── LICENSE
    ├── setup.py              # 安装脚本
    ├── bin/
    │   └── pr-read.py        # 命令行读取工具
    ├── examples/
    │   ├── example0_createRad1.py
    │   ├── example1_readCSV.py
    │   ├── example2a_loadIntermediate.py
    │   └── example2b_loadPickle.py
    └── pradreader/           # Python 包
        ├── __init__.py
        ├── fluxmap.py        # 通量图生成
        ├── rdcarlo.py        # Carlo 辐射数据
        ├── rdflash.py        # FLASH 辐射数据
        ├── rdgeneric.py      # 通用读取器
        ├── rdmit.py          # MIT 格式读取器
        └── reader.py         # 基类读取器
```

## 安装

### 推荐方式（在线安装最新版本）

```bash
pip install git+https://github.com/flash-center/PRadReader.git
pip install git+https://github.com/flash-center/PRaLine.git
```

### 本地安装

```bash
# 依赖
pip install future numpy scipy matplotlib pandas

# 安装 PRadReader
cd tools/protonRad/PRadReader
python setup.py install

# 安装 PRaLine
cd tools/protonRad/PRaLine
python setup.py install
```

## PRaLine — 质子射线照相重建

### 概述

基于 Graziani et al., 2017 方法的质子射线照相重建代码，从质子照相数据反演磁场结构。

### 包模块

| 模块 | 功能 |
|------|------|
| `reconstruct.py` | 磁场重建主算法（迭代反演） |
| `algorithm.py` | 重建算法核心 |
| `analysis.py` | 重建结果分析 |
| `image.py` | 图像处理（通量图、对比度等） |
| `path.py` | 射线路径计算 |
| `Bplot2.py` | 重建磁场的可视化绘图 |
| `rad_ut.py` | 辐射传输实用函数 |
| `constants.py` | 物理常数 |

### 使用示例

```bash
cd examples

# 生成通量图
lin-analyze test_input.p

# 重建磁场（4000 次迭代）
lin-reconstruct test_input.p
```

**输出**: 同一目录下的结果文件，包含重建磁场图像。

### 参考结果

`examples/reference_images/` 包含 Graziani et al., 2017 论文中的参考图像：
- `Fluence.png` — 通量分布
- `Flux.png` — 辐射通量
- `B_True.png` — 真实磁场
- `B_Reconstructed.png` — 重建磁场

## PRadReader — 质子辐射数据读取器

### 概述

PRaLine 的依赖包，用于读取多种格式的质子辐射数据。

### 包模块

| 模块 | 功能 |
|------|------|
| `reader.py` | 基类读取器，提供通用接口 |
| `rdflash.py` (12KB) | 读取 FLASH 仿真生成的质子辐射数据 |
| `rdcarlo.py` (7KB) | 读取 Carlo 格式质子辐射数据 |
| `rdmit.py` (3KB) | 读取 MIT 格式数据 |
| `rdgeneric.py` | 通用数据读取器 |
| `fluxmap.py` (4KB) | 通量图生成与分析 |

### 命令行工具

```bash
# pr-read.py — 读取和显示质子辐射数据
pr-read.py <input_file>
```

### 示例脚本

| 脚本 | 功能 |
|------|------|
| `example0_createRad1.py` | 创建辐射数据（方法1） |
| `example1_readCSV.py` | 读取 CSV 格式辐射数据 |
| `example2a_loadIntermediate.py` | 加载中间格式数据 |
| `example2b_loadPickle.py` | 加载 Pickle 格式数据 |
