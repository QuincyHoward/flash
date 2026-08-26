"""
relations._parsers — 关联检查公共解析工具
══════════════════════════════════════════

供各规则复用的辅助函数：
  - unquote            : 去除字符串两端引号
  - par_refs_of_prefix : 收集 .par 中某前缀参数引用的文件（去引号）
  - strip_f90_vars     : 提取 Fortran 中声明的变量名
  - strip_init_gets    : 提取 Simulation_init.F90 中 RuntimeParameters_get 读取的键
  - setup_cmd_from     : 从运行脚本提取 setup 指令
"""

from __future__ import annotations

import re
from typing import Dict, List

__all__ = [
    "unquote",
    "par_refs_of_prefix",
    "f90_save_vars",
    "init_get_keys",
    "setup_cmd_from",
]


def unquote(s: str) -> str:
    """去除字符串两端成对引号（" 或 '）。"""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def par_refs_of_prefix(params: Dict[str, str], *prefixes: str) -> List[str]:
    """收集 .par 中参数名以任一 prefix 开头**且以表文件后缀结尾**的值。

    只把"表文件类"参数（形如 `eos_targTableFile`、`op_chamFileName`、`eos_*TableFile`
    等以 TableFile/FileName 结尾）的取值当作文件引用。避免把 `eos_targEosType`
    (=eos_tab)、`eos_targSubType`(=ionmix4)、`op_targAbsorb`(=op_tabpa) 等
    **模式名/类型名**误当文件。

    Args:
        params:   .par 参数字典（RelationContext.par_params() 结果）
        prefixes: 前缀，如 ("eos_", "op_")

    Returns:
        命中的文件引用值列表（已 unquote、去重、保序）。
    """
    refs: List[str] = []
    for key, val in params.items():
        is_table_file = key.endswith("TableFile") or key.endswith("FileName")
        if is_table_file and any(key.startswith(p) for p in prefixes):
            clean = unquote(val)
            if clean and clean not in refs:
                refs.append(clean)
    return refs


def f90_save_vars(text: str) -> List[str]:
    """提取 Fortran 源码中声明的 `save` 变量名（形如 `real, save :: sim_xxx`）。

    处理两种形式：
      - `real, save :: sim_x, sim_y`
      - `logical, save :: sim_killdivb = .FALSE.`（去掉 `= value` 部分）

    用于对比 Simulation_data.F90 中已声明的模块变量。
    """
    vars_: List[str] = []
    for line in text.splitlines():
        m = re.search(r"save\s*::\s*(.+)$", line, re.IGNORECASE)
        if not m:
            continue
        # 去掉每个声明项的 `= 初值`
        decl = re.split(r",\s*(?=[A-Za-z_])", m.group(1))
        for tok in decl:
            tok = tok.split("=")[0].strip()
            if tok and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tok):
                vars_.append(tok)
    return vars_


def init_get_keys(text: str) -> List[str]:
    """提取 Simulation_init.F90 中 `RuntimeParameters_get('KEY', ...)` 的 KEY 列表。"""
    return re.findall(r"RuntimeParameters_get\(\s*['\"]([^'\"]+)['\"]", text)


def setup_cmd_from(script_text: str) -> str:
    """从运行脚本文本提取 setup 指令行（含 './setup ' 或 'SETUP_CMD='）。"""
    for line in script_text.splitlines():
        s = line.strip()
        if "./setup " in s:
            # 取 'setup' 之后的命令（可能是 SETUP_CMD="..." 内嵌，也可能是裸命令）
            idx = s.find("./setup")
            return s[idx:]
    return ""
