> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# core/ —— eosop_pro 格式无关底层：配置单源、文本/数值内核与盲读推断

core 是 eosop_pro 包的地基层，被上层 tables/、registry/、ops/ 与各 CLI 全面依赖；
它自身只依赖标准库（docsrc/guess 另用 numpy）。分层：`config`（唯一常量来源）
→ `text`（字节/文本 I/O）→ `numbers`（Fortran 数值解析）→ `profile`（行/列剖面）
→ `infer`（语义反演）→ `docsrc`（文档抽取）。

## 模块

### config.py
全项目**唯一**允许出现路径、阈值、网格/压缩参数、跳过规则的地方；其他模块一律
`from eosop_pro import config` 取值，不得硬编码。常量分组：层级推导
（PACKAGE_ROOT/PROJECT_ROOT/MULTIXD_INNER/WORKSPACE_ROOT）、源数据
（MULTI_HOME/MATTER_DIR 及材料注册表三源 material.base/material.user/DatabaseIndex.xml）、
产物（OUTPUTS_DIR 及其下 h5/reports/plots/logs）、文档抽取阈值（DOC_MAX_BYTES 等）、
编码链 `ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "latin-1")`（latin-1 永不失败）、
物理包络（RHO_MIN/MAX_G_CM3、TE_MIN/MAX_EV、P_MIN/MAX_MBAR）、物理常量
（N_A、EV_PER_K、MBAR_PER_GPA 等）、统一网格（N_X_UNIFIED/N_TE_UNIFIED=128、log10 间距）、
插值（INTERP_METHOD/EXTRAPOLATION/MONOTONIC_POLICY）、HDF5（SCHEMA_VERSION、gzip+shuffle、
f8、AXIS_ORDER）、非数值文件跳过规则、绘图样式（PPT 级：字号全 ≥20pt、DPI=450）。

任意常量都可用 `MULTI_EOSOP_<NAME>` 环境变量覆盖（`_env()` 实现），
如 `MULTI_EOSOP_MATTER_DIR`、`MULTI_EOSOP_TE_MAX`、`MULTI_EOSOP_N_X_UNIFIED`。

关键 API：
- `ensure_output_dirs() -> None` —— 幂等创建全部输出目录（h5/_unindexed、reports、plots、logs、inference_reports）
- `MATTER(relpath) -> Path` —— 把 `matter++` 下相对路径解析为绝对路径并断言存在；测试与解析器统一用它引用真实源文件
- `matter_rel(path) -> str` —— 绝对路径转相对 `matter++` 的 POSIX 风格相对路径

用法示例：
```python
from eosop_pro.core import config

config.ensure_output_dirs()                      # 建好 outputs 全家
src = config.MATTER("ATOMIC/Al.txt")             # 断言存在的源文件
print(config.N_X_UNIFIED, config.ENCODINGS)      # 128 ('utf-8-sig', 'utf-8', 'gb18030', 'latin-1')
```

### docsrc.py
文档抽取：把 `doc/`、`matter++/` 下的 docx/pptx/xlsx/xls/doc/pdf/xmind/纯文本
转成可审计、可引用的纯文本，落盘 `docs/extracted/`，每份记录来源相对路径 +
字节数 + sha256 + 抽取方式。零第三方依赖（zipfile/zlib/正则）；`.doc` 做
双对齐 UTF-16LE 游程扫描，PDF 抽不出文本层时如实记 warning、绝不编造内容。

关键 API：
- `extract(path) -> DocText` —— 抽取单份文档；任何异常都转 warning 不抛出
- `scan_documents(root=None, *, ...) -> list[Path]` —— 递归列出可抽取文档；四道闸门（无扩展名白名单/体积上限/文本体积上限/数值闸门 `looks_like_data`）
- `extract_all(root=None, *, outdir=None, write=True) -> list[DocText]` —— 批量抽取并落盘 + 写 manifest
- `write_manifest(results, outdir=None) -> Path` —— 写 `MANIFEST.md`（人读）+ `manifest.json`（机读）
- `looks_like_data(path, *, sample=None, ratio=None) -> tuple[bool, float]` —— 判断纯文本是数值表还是说明文档
- `DocText` —— 抽取结果容器（src/relpath/kind/text/method/sha256/warnings；`out_name()`、`describe()`、`to_row()`）

CLI 入口：
```bash
python -m eosop_pro.core.docsrc [--root DIR] [--outdir DIR] [--list]
#   --list  只列文件不抽取；默认 root=Multi1D++Portable20241128（扫 doc/ + matter++）
```

用法示例：
```python
from eosop_pro.core.docsrc import extract, scan_documents

for p in scan_documents():            # 默认扫 config.DOC_SCAN_ROOTS
    r = extract(p)
    print(r.describe())               # [OK ] kind chars lines relpath
```

## 子包

- [text/](text/README.md) —— 字节分类、编码链、文本读取、哈希、异常、审计快照
- [numbers/](numbers/README.md) —— Fortran 数值正则与定宽切分
- [profile/](profile/README.md) —— 行结构剖面与列占用剖面
- [infer/](infer/README.md) —— 布局反演、物理包络、锚点库、注释证据、盲读猜测
