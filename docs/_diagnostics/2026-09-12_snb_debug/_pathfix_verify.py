"""验证 SNBOneCH_ml.py 的部署路径修复: 语法 + 无残留字面 ~ 路径。"""
import ast
import re
import sys
from pathlib import Path

TARGET = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash"
              r"\scenarios\private\tracer\SNB\SNBOneCH_ml\SNBOneCH_ml.py")
src = TARGET.read_text(encoding="utf-8")
out = []

# 1) 语法
try:
    ast.parse(src)
    out.append("SYNTAX: OK")
except SyntaxError as e:
    out.append(f"SYNTAX: FAIL line {e.lineno}: {e.msg}")

# 2) 残留字面 ~ 路径 (排除注释行)
bad = []
for i, line in enumerate(src.splitlines(), 1):
    s = line.strip()
    if s.startswith("#"):
        continue
    # 只找 "~/..." 或 '~/...' 形式 (含 f-string)
    if re.search(r"[\"']~/", line):
        bad.append((i, s[:140]))
out.append(f"LITERAL_TILDE_PATHS: {len(bad)}")
for i, s in bad:
    out.append(f"  L{i}: {s}")

# 3) deploy_dir 相关行
out.append("--- deploy_dir / resolve ---")
for i, line in enumerate(src.splitlines(), 1):
    if "deploy_dir" in line or "resolve_deploy_dir" in line:
        out.append(f"  L{i}: {line.strip()[:150]}")

Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_pathfix_verify.txt"
     ).write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
