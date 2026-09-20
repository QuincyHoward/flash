"""检查 EOS 表温度范围 (直接解析 cn4 IONMIX4 头), 确认 290K 是否在表外。"""
import sys
import struct
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
TAB = (FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB"
       / "SNBOneCH_ml" / "flash_input" / "CH-QC-1-001.cn4")

lines = [f"file: {TAB.name} size={TAB.stat().st_size if TAB.exists() else -1}"]

if TAB.exists():
    with open(TAB, "rb") as f:
        head = f.read(1024)
    lines.append("head[0:256] repr:")
    lines.append(repr(head[:256]))
    lines.append("")
    lines.append("head as text:")
    for i in range(0, 256, 64):
        chunk = head[i:i+64]
        txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:4d}: {txt}")
    # IONMIX4 通常前若干 int 为维度
    try:
        ints = struct.unpack("<32i", head[:128])
        lines.append("")
        lines.append(f"first 32 int32: {ints}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"int unpack err: {e}")

(FLASH_ROOT / "_eos_table.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
