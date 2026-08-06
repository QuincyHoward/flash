"""
gen_par 材料数据库 (自包含)
═══════════════════════════

从旧 par/materials.py 提取，硬编码以确保自包含。
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Material:
    """FLASH 仿真材料定义。

    Attributes:
        name: 材料名称
        file: .cn4 EOS 表文件名
        rho: 密度 (g/cm³)
        A: 原子量
        Z: 原子序数
        ZMin: 最小电离度
        opacity_file: 不透明度表文件名（默认同 file）
        ses_file: SESAME 表文件名（可选）
        description: 描述
    """
    name: str
    file: str
    rho: float
    A: float
    Z: float
    ZMin: float = 0.02
    opacity_file: str = ""
    ses_file: str = ""
    description: str = ""


# ── 靶材数据库 ─────────────────────────────────────
MATERIALS: Dict[str, Material] = {
    "aluminum": Material(
        name="Aluminum",
        file="al-imx-003.cn4",
        rho=2.7,
        A=26.9815386,
        Z=13.0,
        ZMin=0.02,
        description="Aluminum target (ρ=2.7 g/cm³, Z=13)",
    ),
    "polystyrene": Material(
        name="Polystyrene",
        file="polystyrene-imx-008.cn4",
        rho=1.1,
        A=6.5,
        Z=3.5,
        ZMin=0.02,
        description="Polystyrene CH target (ρ=1.1 g/cm³, Z=3.5)",
    ),
    "beryllium": Material(
        name="Beryllium",
        file="be-imx-003.cn4",
        rho=1.848,
        A=9.012,
        Z=4.0,
        ZMin=0.02,
        description="Beryllium target (ρ=1.848 g/cm³, Z=4)",
    ),
    "gold": Material(
        name="Gold",
        file="au-imx-003.cn4",
        rho=19.32,
        A=196.97,
        Z=79.0,
        ZMin=0.02,
        description="Gold target (ρ=19.32 g/cm³, Z=79)",
    ),
    "copper": Material(
        name="Copper",
        file="cu-imx-003.cn4",
        rho=8.96,
        A=63.546,
        Z=29.0,
        ZMin=0.02,
        description="Copper target (ρ=8.96 g/cm³, Z=29)",
    ),
    "carbon": Material(
        name="Carbon",
        file="c-imx-003.cn4",
        rho=3.515,
        A=12.01,
        Z=6.0,
        ZMin=0.02,
        description="Carbon target (ρ=3.515 g/cm³, Z=6)",
    ),
}

# ── 腔室气体数据库 ────────────────────────────────
CHAMBER_GASES: Dict[str, Material] = {
    "helium": Material(
        name="Helium",
        file="he-imx-005.cn4",
        rho=1e-6,
        A=4.002602,
        Z=2.0,
        ZMin=0.02,
        description="Helium chamber gas (ρ=1e-6 g/cm³, Z=2)",
    ),
    "hydrogen": Material(
        name="Hydrogen",
        file="h-imx-003.cn4",
        rho=1e-7,
        A=1.008,
        Z=1.0,
        ZMin=0.02,
        description="Hydrogen chamber gas (ρ=1e-7 g/cm³, Z=1)",
    ),
}


def get_material(name: str) -> Optional[Material]:
    """按名称查找材料（靶材优先，然后气体）。"""
    if name in MATERIALS:
        return MATERIALS[name]
    if name in CHAMBER_GASES:
        return CHAMBER_GASES[name]
    return None


def list_materials(category: Optional[str] = None) -> list:
    """列出可用材料。

    Args:
        category: "target" 或 "chamber"，为 None 时列出全部

    Returns:
        材料名称列表
    """
    if category == "target":
        return list(MATERIALS.keys())
    elif category == "chamber":
        return list(CHAMBER_GASES.keys())
    return list(MATERIALS.keys()) + list(CHAMBER_GASES.keys())
