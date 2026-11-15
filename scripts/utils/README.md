> 最后核对：2026-11-15 · commit 97d5e5d

# 独立小工具集

## 职责

与主工作流解耦的一次性/低频实用脚本（数据检查、文档格式转换、知识抽取）。

## 内容清单

| 文件 | 说明 |
|---|---|
| `__init__.py` | 包标识（当前未导出任何符号） |
| `check_hdf5_time.py` | 核对各来源（WSL/SSH1）hello_flash 输出 HDF5 的时间戳一致性 |
| `convert_pdf_to_md.py` | PDF → Markdown 转换（文献入库前处理） |
| `convert_text_to_md.py` | 纯文本 → Markdown 转换 |
| `extract_knowledge.py` | 从文档抽取知识条目（知识库预处理） |

## 关联资源

- `flash/output_pro/`（HDF5 正式处理链）；文献工具属用户侧资料库范畴
- **上级导航**：[../README.md](../README.md)
