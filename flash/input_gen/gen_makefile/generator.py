"""
FLASH Makefile 生成器 (自包含)
═══════════════════════════════

Makefile 内容从 LaserSlab/Makefile 模板提取后硬编码。
"""

from pathlib import Path
from typing import Optional, Union


DEFAULT_MAKEFILE_CONTENT = "Simulation += Simulation_data.o\n"


class MakefileGenerator:
    """FLASH Makefile 生成器 (自包含)。"""

    def generate(self, sim_path: str = "hello/LaserSlab1d_new") -> str:
        """生成 Makefile 内容。"""
        return DEFAULT_MAKEFILE_CONTENT

    def save(
        self,
        output_path: Union[str, Path],
        sim_path: str = "hello/LaserSlab1d_new",
    ) -> Path:
        """生成并保存 Makefile。"""
        content = self.generate(sim_path=sim_path)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", newline="\n")
        return out
