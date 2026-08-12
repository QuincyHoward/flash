#!/usr/bin/env python3
"""
migrate_imports.py — 将 flash 包中所有硬编码路径导入替换为标准 bootstrap

策略: 找到以 Path(__file__) 或 os.path.dirname(__file__) 为基础的
sys.path.insert/append 块，替换为向上搜索 _bootstrap.py 的标准引导代码。

安全措施:
  - 自动备份 (.bak)
  - 跳过第三方代码 (flash_src, ionmix) 和临时文件
"""

import shutil
import sys
import re as re_mod
from pathlib import Path

FLASH_ROOT = Path(__file__).resolve().parent.parent
print(f"flash project root: {FLASH_ROOT}")

_BOOTSTRAP_BLOCK = """\
# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "_bootstrap.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash project root (_bootstrap.py not found)")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))"""

_SCENARIOS_ADDITION = """\
# Also add test/scenarios/ for local imports (chsich, etc.)
_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"
if _SCENARIOS_ROOT.exists() and str(_SCENARIOS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCENARIOS_ROOT))"""


def should_skip(filepath: Path) -> bool:
    """判断是否应跳过此文件。"""
    rel = filepath.relative_to(FLASH_ROOT)
    parts = list(rel.parts)
    
    # __pycache__
    if any(p in ("__pycache__", ".pytest_cache", ".workbuddy") for p in parts):
        return True
    
    # 第三方源码 (可能在任何层级)
    third_party = {"flash_src", "ionmix"}
    for part in parts:
        if part in third_party:
            return True
    
    # 副本/临时目录
    rel_str = str(rel)
    if " - 副本" in rel_str:
        return True
    if "temp" in parts[:-1]:
        return True
    if "temp_delete" in parts:
        return True
    if rel_str.startswith("output_processors_copy"):
        return True
    if rel_str.startswith("input_gen/gen_eos_op_copy"):
        return True
    
    if filepath.suffix == ".bak":
        return True
    if filepath.name in ("_bootstrap.py", "migrate_imports.py"):
        return True
    
    # 凭据管理用 sys.path 做数据目录, 不涉及 flash 导入
    if len(parts) >= 3 and parts[0] == "_core" and parts[1] == "credentials":
        return True
    
    return False


def find_flash_import_block(lines: list[str]) -> tuple[int, int] | None:
    """
    从 sys.path.insert 行出发, 反向查找 Path(__file__) 计算块。
    
    算法:
    1. 找到 sys.path.insert 行, 检查参数是否源自 __file__ 计算
    2. 反向搜索最近的 Path(__file__)/os.path.dirname 计算行
    3. 块 = [计算行, insert行] (含中间所有行)
    
    Returns:
        (start_line, end_line) 或 None
    """
    n = len(lines)
    calc_kw = ["Path(__file__)", "os.path.abspath", "os.path.dirname"]
    
    for i in range(n):
        if "sys.path.insert" not in lines[i] and "sys.path.append" not in lines[i]:
            continue
        
        insert_line = lines[i]
        # 跳过那些不是 __file__ 驱动的 insert (如临时数据目录)
        if "Path(__file__)" not in insert_line and "os.path" not in insert_line:
            # 检查 insert 的参数变量是否来自 __file__ 计算
            # 提取 insert 行的变量名
            pass  # 继续检查
        else:
            # 直接行内有 __file__ 引用
            return (i, i)  # 单行块
        
        # 提取 insert 行的变量名 (如 sys.path.insert(0, str(_VAR)) → _VAR)
        stripped = lines[i].strip()
        import re
        m = re.search(r'sys\.path\.(?:insert|append)\([^,]+,\s*(?:str\()?([_A-Za-z][_A-Za-z0-9]*)', stripped)
        if not m:
            continue
        var_name = m.group(1)
        
        # 反向搜索 var_name 的定义
        for j in range(i - 1, max(i - 30, -1), -1):
            stripped_j = lines[j].strip()
            if not stripped_j or stripped_j.startswith("#"):
                continue
            if stripped_j.startswith(("import ", "from ")):
                # 如果 insert 行在 if __name__ 块内, 往前找到 import 为止
                continue
            if stripped_j.startswith(var_name + " ="):
                # 找到变量定义
                calc_start = j
                # 再往前找其他相关计算 (如 _PARENT = _FLASH_DIR.parent)
                for k in range(j - 1, max(j - 15, -1), -1):
                    sk = lines[k].strip()
                    if not sk or sk.startswith("#"):
                        continue
                    if sk.startswith(("import sys", "from pathlib")):
                        calc_start = k
                    elif "=" in sk and sk.split("=")[0].strip().startswith("_"):
                        calc_start = k
                    else:
                        break
                
                # 往后扩展到最后一个 insert
                block_end = i
                for k in range(i + 1, min(i + 15, n)):
                    if "sys.path.insert" in lines[k] or "sys.path.append" in lines[k]:
                        block_end = k
                    elif not lines[k].strip() or lines[k].strip().startswith(("#", "for ", "if ", ")", "    ")):
                        continue
                    else:
                        break
                
                return (calc_start, block_end)
    
    return None


def needs_scenarios_path(content: str) -> bool:
    return "from chsich." in content or "import chsich" in content


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # 快速筛选
    if not any(kw in content for kw in ["sys.path.insert", "sys.path.append"]):
        return False
    if not any(kw in content for kw in ["Path(__file__)", "os.path.dirname", "os.path.abspath(__file__)"]):
        return False
    
    block = find_flash_import_block(lines)
    if block is None:
        return False
    
    start, end = block
    
    has_scenarios = needs_scenarios_path(content)
    
    if dry_run:
        tag = "+scenarios" if has_scenarios else "标准"
        print(f"  [DRY-RUN] {tag}: {filepath.relative_to(FLASH_ROOT)} (lines {start}-{end})")
        return True
    
    # 找插入位置: 块之前的非空行之后
    insert_pos = 0
    for i in range(start - 1, -1, -1):
        if lines[i].strip():
            insert_pos = i + 1
            break
    
    # 特殊处理: 如果块在 if __name__ 内部, bootstrap 应放在 if 块之前
    # 检测: start 行有缩进 (块在控制流内部)
    if start > 0:
        # 从 start 往前找最近的非空行
        for i in range(start - 1, -1, -1):
            stripped = lines[i].strip()
            if not stripped:
                continue
            # 如果最近的控制流是 if __name__
            if stripped.startswith("if __name__"):
                insert_pos = i  # 在 if 行之前插入
            break
    
    # 构建新内容
    lines_before = lines[:insert_pos]
    lines_after = lines[end + 1:]
    
    bootstrap_code = _BOOTSTRAP_BLOCK
    if has_scenarios:
        bootstrap_code += "\n\n" + _SCENARIOS_ADDITION
    bootstrap_lines = bootstrap_code.split("\n")
    
    new_content_lines = lines_before + [""] + bootstrap_lines + [""] + lines_after
    new_content = "\n".join(new_content_lines)
    new_content = re_mod.sub(r"\n{4,}", "\n\n\n", new_content)
    
    # 备份
    bak_path = filepath.with_suffix(filepath.suffix + ".bak")
    if not bak_path.exists():
        shutil.copy2(filepath, bak_path)
    
    filepath.write_text(new_content, encoding="utf-8")
    print(f"  ✅ {filepath.relative_to(FLASH_ROOT)}")
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    mode = "DRY-RUN" if dry_run else "MIGRATE"
    print(f"\n{'='*60}")
    print(f"  flash 导入路径迁移 ({mode})")
    print(f"  搜索根: {FLASH_ROOT}")
    print(f"{'='*60}\n")
    
    count_migrated = 0
    errors = []
    
    for pyfile in sorted(FLASH_ROOT.rglob("*.py")):
        if should_skip(pyfile):
            continue
        try:
            if process_file(pyfile, dry_run=dry_run):
                count_migrated += 1
        except Exception as e:
            errors.append((pyfile, str(e)))
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"  ✅ 已迁移: {count_migrated}")
    if errors:
        print(f"  ❌ 错误: {len(errors)}")
        for f, e in errors:
            print(f"     - {f}: {e}")
    if dry_run:
        print(f"  ⚠ 干运行模式. 去掉 --dry-run 应用修改")
        print(f"  运行: python scripts/06_migration/migrate_imports.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
