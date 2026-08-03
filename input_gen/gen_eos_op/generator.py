"""
EOS/opacity 表文件管理器 — EOSOpacityGenerator (自包含, 别名感知)
════════════════════════════════════════════════════════

设计目标
--------
1. 为每一种 EOS/opacity 材料 (eos_op) 配置 **多个别名**，agent 在复制材料数据时可
   通过任意别名 (元素符号 / 中文 / 文件名 stem / 规范名) 精准定位到磁盘上的 .cn4 文件。
2. 注册表 **只引用实际存在的文件**。脚本中原本指向不存在文件的条目 (gold /
   copper / carbon) 已移除，避免 agent 查不到文件。注意 **beryllium (Be-006-imx.cn4)
   现已真实存在，已重新纳入注册表**。
3. 所有数据文件保存在 ``eos_op_data/`` 下 (可为子目录)，脚本不移动 / 不删除任何
   磁盘文件，后续可直接往该目录追加新 .cn4。
4. 每个材料携带 **辐射能群边界 grupbd** 与一组 **规格参数** (ntemp/dlgtmp/tplsma/
   ndens/dlgden/densnn/trad)，用于辅助确认文件信息；复制文件时一并写出元数据。

辐射能群约束
------------
当前阶段所有材料共用同一组 grupbd (见 DEFAULT_GRUPBD)。FLASH 仿真中 **不同能群不能
同时使用**——同一算例引用的多个材料必须共享相同 grupbd，``validate_grupbd_consistency``
用于在校验阶段发现冲突。

.cn4 文件头格式 (ionmix4)
-------------------------
第 1 行: ``<ntemp>  <ndens>``  (温度点数, 密度点数, 可为整数)
第 2 行: ``atomic #s of gases: <Z1> <Z2> ...``
第 3 行: ``relative fractions: <f1> <f2> ...``
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

# ──────────────────────────────────────────────────────────────────────────
# 全局默认：辐射能群边界 + 材料规格
# ──────────────────────────────────────────────────────────────────────────

# 辐射能群边界 [eV]，当前所有材料共用这一组。
# 注：不同能群不能在同一算例中混用。
DEFAULT_GRUPBD: List[float] = [
    1.0e-1, 1.0e+0, 1.0e+01, 1.0e+02, 1.0e+03, 1.0e+04, 1.0e+05,
]

# 材料规格 (辅助确认文件信息)。取值为用户给定的参考标准：
#   ntemp=61 温度点数, dlgtmp=0.105 温度对数增量,
#   tplsma={1:1e-2} 起始温度[eV], ndens=71 密度点数,
#   dlgden=0.14 密度对数增量, densnn=1.0e16 起始离子数密度[cm^-3],
#   trad=200.0 辐射温度[eV]
# 注：Gen_eos_op_data 中的 Z02/Z06/Z14 于 2026-07-08 重新生成，实际分辨率为
#     ntemp=51, ndens=31；其 EOSMaterial 已用 per-material spec 覆盖 ntemp/ndens，
#     verify_against_spec 对它们返回 match=True。本 DEFAULT_SPEC 仍作为参考基准，
#     供自动发现的未注册文件对照使用 (FLASH 原始表 ntemp≈21 会提示不一致，属正常)。
DEFAULT_SPEC: Dict[str, object] = {
    "ntemp": 61,        # 温度点数 (参考标准; Gen 文件实际 51)
    "dlgtmp": 0.105,    # 温度对数增量
    "tplsma": {1: 1e-2},  # 起始温度 [eV] (索引 1)
    "ndens": 71,        # 密度点数 (参考标准; Gen 文件实际 31)
    "dlgden": 0.14,     # 密度对数增量
    "densnn": 1.0e16,   # 起始离子数密度 [cm^{-3}]
    "trad": 200.0,      # 辐射温度 [eV]
}


def _norm(s: str) -> str:
    """规范化别名：去空白、转小写。"""
    return s.strip().lower()


def _collapsed(s: str) -> str:
    """去掉所有非字母数字字符后的键，用于容错匹配 (al-imx-003 == alimx003)。"""
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass
class EOSMaterial:
    """单个 EOS/opacity 材料条目。

    Attributes:
        canonical: 规范材料名 (如 "polystyrene")，同时作为首要别名。
        filename:  相对 ``eos_op_data/`` 的 .cn4 文件名 (可含子目录)。
        aliases:   该材料的所有别名列表 (含规范名 / 元素符号 / 中文 / 文件名 stem)。
        description: 人类可读描述。
        grupbd:    辐射能群边界 [eV]。
        spec:      规格参数 (ntemp/dlgtmp/tplsma/ndens/dlgden/densnn/trad)。
        registered: 是否为注册表内已知材料 (False 表示自动发现的未注册文件)。
    """

    canonical: str
    filename: str
    aliases: List[str]
    description: str = ""
    grupbd: List[float] = field(default_factory=lambda: list(DEFAULT_GRUPBD))
    spec: Dict[str, object] = field(default_factory=lambda: dict(DEFAULT_SPEC))
    registered: bool = True

    def normalized_aliases(self) -> set:
        out = set()
        for a in self.aliases:
            out.add(_norm(a))
            out.add(_collapsed(a))
        return out


class EOSOpacityGenerator:
    """EOS/opacity 表文件生成管理器 (别名感知, 数据文件发现)。

    从 ``eos_op_data/`` 读取 .cn4 文件。注册表仅引用实际存在的文件，
    并为每种材料配置多个别名与规格参数，使 agent 在复制数据时能精准定位。
    """

    # ── 注册表：仅包含文件实际存在的材料 ───────────────────────────────
    # 数据文件保存在 eos_op_data/ 下，分两类子目录：
    #   FLASH_eos_op_data/  — FLASH 随包原始表 (分辨率较低, ntemp≈21)
    #   Gen_eos_op_data/    — ionmix 新生成表 (Z02/Z06/Z14)
    #       用户于 2026-07-08 重新生成，分辨率改为 ntemp=51, ndens=31
    #       (旧的 20260707 版本 ntemp=61/ndens=71 已删除)
    # 命名约定：文件名以 元素符号(或 Zxx) 开头，便于 agent 按文件名自动发现。
    # 关键说明：
    #   * polystyrene-imx-001.cn4 实为纯氢 (relative fractions 1.0/0.0) → hydrogen
    #   * polystyrene-imx-002.cn4 为 CH 1:1 (0.5/0.5) → polystyrene (主 CH 靶)
    #   * polystyrene-imx-008.cn4 为 CH 早期高分辨 (ntemp=51) → polystyrene_hi 变体
    #   * Be-006-imx.cn4 为铍 (之前 phantom, 现已真实存在) → beryllium
    #   * DD-006-imx.cn4 为氘氢混合物 (H+D 各50%) → deuterium
    #   * matr_009999(.ses).cn4 非标准 ionmix 头 → 不注册, 仅自动发现
    MATERIALS: List[EOSMaterial] = [
        # ── FLASH 原始表 (低分辨率) ──
        EOSMaterial(
            canonical="aluminum",
            filename="FLASH_eos_op_data/al-imx-003.cn4",
            aliases=["aluminum", "aluminium", "al", "铝",
                     "al-imx-003", "al_imx_003", "al-imx"],
            description="铝 (Al, Z=13)，FLASH 原始表 ntemp=21",
        ),
        EOSMaterial(
            canonical="helium",
            filename="FLASH_eos_op_data/he-imx-005.cn4",
            aliases=["helium", "he", "氦",
                     "he-imx-005", "he_imx_005", "he-imx"],
            description="氦 (He, Z=2)，FLASH 原始表 ntemp=21",
        ),
        EOSMaterial(
            canonical="hydrogen",
            filename="FLASH_eos_op_data/polystyrene-imx-001.cn4",
            aliases=["hydrogen", "h", "氢",
                     "polystyrene-imx-001", "polystyrene_imx_001", "h-legacy"],
            description="氢 (H, Z=1)；文件名为 polystyrene-imx-001.cn4，内容实为纯氢 (占比1.0/0.0)",
        ),
        EOSMaterial(
            canonical="polystyrene",
            filename="FLASH_eos_op_data/polystyrene-imx-002.cn4",
            aliases=["polystyrene", "ps", "聚苯乙烯", "ch", "CH靶",
                     "polystyrene-imx-002", "polystyrene_imx_002", "polystyrene-imx"],
            description="聚苯乙烯 / CH 靶 (H0.5-C0.5)，FLASH 原始表 ntemp=21",
        ),
        EOSMaterial(
            canonical="beryllium",
            filename="FLASH_eos_op_data/Be-006-imx.cn4",
            aliases=["beryllium", "be", "铍", "Be-006-imx", "be-006", "Be-006"],
            description="铍 (Be, Z=4)，FLASH 原始表 ntemp=21",
        ),
        EOSMaterial(
            canonical="deuterium",
            filename="FLASH_eos_op_data/DD-006-imx.cn4",
            aliases=["deuterium", "dd", "氘", "重氢",
                     "DD-006-imx", "dd-006", "DD-006"],
            description="氘氢混合物 (H+D 各50%, Z=1×2)，FLASH 原始表 ntemp=21",
        ),
        # ── Gen 新生成表 (2026-07-08 重新生成, ntemp=51, ndens=31) ──
        EOSMaterial(
            canonical="helium_hires",
            filename="Gen_eos_op_data/Z02_1.00-20260708_0851/Z02_1.00-20260708_0851.cn4",
            aliases=["z02", "z02_1.00", "helium_gen", "helium_hires", "he_gen", "氦_生成", "氦高分辨",
                     "z02_1.00-20260708_0851"],
            description="氦 (He, Z=2)，ionmix 新生成表 ntemp=51，与 FLASH he-imx-005 同元素不同分辨率",
            spec={**DEFAULT_SPEC, "ntemp": 51, "ndens": 31},
        ),
        EOSMaterial(
            canonical="ch_mix",
            filename="Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/Z06_0.50-Z01_0.50-20260708_0850.cn4",
            aliases=["ch_mix", "chmix", "碳氢混合物", "碳氢混合物高分辨",
                     "z06", "z06_0.50-z01_0.50", "z06_0.50-z01_0.50-20260708_0850"],
            description="碳氢混合物 (C0.5-H0.5)，ionmix 新生成表 ntemp=51",
            spec={**DEFAULT_SPEC, "ntemp": 51, "ndens": 31},
        ),
        EOSMaterial(
            canonical="silicon",
            filename="Gen_eos_op_data/Z14_1.00-20260708_0850/Z14_1.00-20260708_0850.cn4",
            aliases=["silicon", "si", "硅",
                     "z14", "z14_1.00", "z14_1.00-20260708_0850", "si-eos"],
            description="硅 (Si, Z=14)，ionmix 新生成表 ntemp=51",
            spec={**DEFAULT_SPEC, "ntemp": 51, "ndens": 31},
        ),
        # ── 变体 / 特殊用途 (自动发现同样可用, 加别名便于精准命中) ──
        EOSMaterial(
            canonical="aluminum_v2",
            filename="FLASH_eos_op_data/al-imx-004.cn4",
            aliases=["al-imx-004", "al004", "al-v2", "aluminum_v2"],
            description="铝 (Al, Z=13) 另一版本，FLASH 原始表 ntemp=21",
        ),
        EOSMaterial(
            canonical="polystyrene_hi",
            filename="FLASH_eos_op_data/polystyrene-imx-008.cn4",
            aliases=["polystyrene-imx-008", "polystyrene_imx_008", "polystyrene-008",
                     "ch-hi", "ps-hi", "ch_hi"],
            description="聚苯乙烯 / CH 靶早期高分辨表 (ntemp=51)，FLASH 原始表",
        ),
        EOSMaterial(
            canonical="hydrogen_1grp",
            filename="FLASH_eos_op_data/h-imx-1grp.cn4",
            aliases=["h-imx-1grp", "h-1grp", "hydrogen-1grp", "h1grp", "氢单能群"],
            description="氢 (H, Z=1) 单能群版 (ntemp=17)，FLASH 原始表",
        ),
        EOSMaterial(
            canonical="helium_1grp",
            filename="FLASH_eos_op_data/he-imx-1grp.cn4",
            aliases=["he-imx-1grp", "he-1grp", "helium-1grp", "he1grp", "氦单能群"],
            description="氦 (He, Z=2) 单能群版 (ntemp=16)，FLASH 原始表",
        ),
    ]

    def __init__(self):
        """初始化，使用 ``eos_op_data/`` 作为数据源。"""
        self._data_dir = Path(__file__).parent / "eos_op_data"
        # 别名 -> 规范名 反向索引
        self._alias_index: Dict[str, str] = {}
        for m in self.MATERIALS:
            keys = set(m.normalized_aliases())
            # 规范名本身也作为可查询别名 (含容错形式)，便于直接按 canonical 查找
            keys.add(_norm(m.canonical))
            keys.add(_collapsed(m.canonical))
            for key in keys:
                # 后注册的不覆盖先注册的规范别名
                self._alias_index.setdefault(key, m.canonical)
        # 发现磁盘上所有 .cn4 (含子目录)
        self._discovered: Dict[str, Path] = self._discover_cn4()

    # ── 内部工具 ───────────────────────────────────────────────────────────

    def _discover_cn4(self) -> Dict[str, Path]:
        """递归扫描 ``eos_op_data/`` 下所有 .cn4，返回 {相对posix路径: 绝对路径}。"""
        found: Dict[str, Path] = {}
        if not self._data_dir.exists():
            return found
        for p in self._data_dir.rglob("*.cn4"):
            rel = p.relative_to(self._data_dir).as_posix()
            found[rel] = p
        return found

    def _resolve_material(self, query: str) -> Optional[EOSMaterial]:
        """将查询解析为 EOSMaterial (注册表优先，其次按文件名/stem 自动发现)。"""
        nq = _norm(query)
        cq = _collapsed(query)
        # 1) 注册表别名
        if nq in self._alias_index:
            canon = self._alias_index[nq]
            return next(m for m in self.MATERIALS if m.canonical == canon)
        if cq in self._alias_index:
            canon = self._alias_index[cq]
            return next(m for m in self.MATERIALS if m.canonical == canon)
        # 2) 按磁盘文件名 / stem 自动发现 (未注册文件也可用)
        for rel, p in self._discovered.items():
            if _collapsed(rel) == cq or _collapsed(p.stem) == cq or _norm(rel) == nq:
                return EOSMaterial(
                    canonical=p.stem,
                    filename=rel,
                    aliases=[p.stem],
                    description="(未注册，自动发现)",
                    registered=False,
                )
        return None

    # ── 公共 API ──────────────────────────────────────────────────────────

    @property
    def data_dir(self) -> Path:
        """EOS 数据文件数据库根目录。"""
        return self._data_dir

    def get_eos_file(self, query: str) -> Optional[Path]:
        """按别名/文件名精准查找材料的 EOS 文件路径。

        Args:
            query: 材料别名或 .cn4 文件名 (如 "polystyrene", "al", "氦",
                   "al-imx-003", "Z14_1.00-...")。

        Returns:
            存在的文件路径；未找到或文件不存在返回 None。
        """
        m = self._resolve_material(query)
        if m is None:
            return None
        fpath = self._data_dir / m.filename
        return fpath if fpath.exists() else None

    def copy_eos_file(
        self,
        query: str,
        target_dir: Union[str, Path],
        write_meta: bool = True,
    ) -> Optional[Path]:
        """复制材料的 EOS 文件到目标目录，并可写出辐射能群/规格元数据。

        Args:
            query: 材料别名或文件名。
            target_dir: 目标目录。
            write_meta: 为 True 时额外写出 ``<stem>.eosmeta.json``，包含 grupbd 与
                规格参数，供仿真装配 (.par) 与 agent 确认使用。

        Returns:
            复制后的 .cn4 路径；未找到源文件返回 None。
        """
        src = self.get_eos_file(query)
        if src is None:
            return None

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        dst = target / src.name
        dst.write_bytes(src.read_bytes())

        if write_meta:
            m = self._resolve_material(query)
            meta = self.get_material_config(query) or {}
            meta_path = target / (src.stem + ".eosmeta.json")
            meta_path.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return dst

    def get_material_config(self, query: str) -> Optional[Dict[str, object]]:
        """返回材料的完整配置 (别名/文件名/grupbd/规格/可用性)。

        用于 agent 装配仿真时写入辐射能群等参数。
        """
        m = self._resolve_material(query)
        if m is None:
            return None
        fpath = self._data_dir / m.filename
        return {
            "canonical": m.canonical,
            "filename": m.filename,
            "aliases": m.aliases,
            "description": m.description,
            "grupbd": m.grupbd,
            "spec": m.spec,
            "registered": m.registered,
            "available": fpath.exists(),
        }

    def list_available_materials(self) -> List[str]:
        """列出 eos_op_data/ 中实际可用的 **已注册** 材料规范名。"""
        out = []
        for m in self.MATERIALS:
            if (self._data_dir / m.filename).exists():
                out.append(m.canonical)
        return sorted(out)

    def list_all_materials(self) -> List[str]:
        """列出所有已注册材料规范名 (含文件暂缺的)。"""
        return sorted(m.canonical for m in self.MATERIALS)

    def list_discovered_files(self) -> List[str]:
        """列出磁盘上发现的所有 .cn4 相对路径 (含未注册文件)。"""
        return sorted(self._discovered.keys())

    def verify_eos_file(self, filepath: Union[str, Path]) -> Dict[str, object]:
        """验证 .cn4 文件基本完整性，并返回头两列的 ntemp/ndens。

        Returns:
            dict: {valid, ntemp, ndens, error}
        """
        path = Path(filepath)
        result: Dict[str, object] = {"valid": False, "ntemp": None,
                                     "ndens": None, "error": None}
        if not path.exists() or path.stat().st_size == 0:
            result["error"] = "file missing or empty"
            return result
        try:
            with open(path, "r", errors="replace") as f:
                lines = f.readlines()
            if len(lines) < 1:
                result["error"] = "too few lines"
                return result
            parts = lines[0].strip().split()
            if len(parts) < 2:
                result["error"] = "header missing ntemp/ndens"
                return result
            ntemp = int(parts[0])
            ndens = int(parts[1])
            result["ntemp"] = ntemp
            result["ndens"] = ndens
            result["valid"] = True
        except (ValueError, OSError) as e:
            result["error"] = str(e)
        return result

    def verify_against_spec(self, query: str) -> Dict[str, object]:
        """将材料 .cn4 实际头 (ntemp/ndens) 与其规格参数对照，辅助确认文件信息。

        Returns:
            dict: {found, ntemp_file, ndens_file, ntemp_spec, ndens_spec,
                   match, note}
        """
        m = self._resolve_material(query)
        fpath = self.get_eos_file(query)
        out: Dict[str, object] = {
            "found": fpath is not None,
            "canonical": m.canonical if m else None,
            "ntemp_file": None, "ndens_file": None,
            "ntemp_spec": m.spec.get("ntemp") if m else None,
            "ndens_spec": m.spec.get("ndens") if m else None,
            "match": None, "note": "",
        }
        if fpath is None:
            out["note"] = "源文件不存在"
            out["match"] = False
            return out
        hdr = self.verify_eos_file(fpath)
        out["ntemp_file"] = hdr.get("ntemp")
        out["ndens_file"] = hdr.get("ndens")
        if hdr.get("valid"):
            out["match"] = (hdr.get("ntemp") == m.spec.get("ntemp")
                            and hdr.get("ndens") == m.spec.get("ndens"))
            if not out["match"]:
                out["note"] = (
                    f"文件头 (ntemp={hdr.get('ntemp')}, ndens={hdr.get('ndens')}) "
                    f"与规格 (ntemp={m.spec.get('ntemp')}, ndens={m.spec.get('ndens')}) 不一致"
                )
            else:
                out["note"] = "文件头与规格一致"
        else:
            out["match"] = False
            out["note"] = f"文件头解析失败: {hdr.get('error')}"
        return out

    def validate_grupbd_consistency(self, *queries: str) -> Dict[str, object]:
        """校验多个材料是否共用相同辐射能群 (FLASH 约束：不同能群不可混用)。

        Returns:
            dict: {consistent, grupbd, conflicting: [canonical...]}
        """
        seen: Dict[str, List[str]] = {}
        for q in queries:
            m = self._resolve_material(q)
            if m is None:
                continue
            key = ",".join(repr(x) for x in m.grupbd)
            seen.setdefault(key, []).append(m.canonical)
        groups = list(seen.keys())
        consistent = len(groups) <= 1
        ref = self._resolve_material(queries[0]) if queries else None
        return {
            "consistent": consistent,
            "grupbd": ref.grupbd if ref else list(DEFAULT_GRUPBD),
            "conflicting": [c for g, cs in seen.items() for c in cs]
                          if not consistent else [],
        }

    def generate_via_ionmix(self, material_name: str, output_path: Union[str, Path]):
        """通过 ionmix 工具生成 .cn4 文件。(占位，暂未实现)

        Raises:
            NotImplementedError: 此功能尚未实现
        """
        raise NotImplementedError(
            "ionmix 集成尚未实现。目前请使用 copy_eos_file() 从 eos_op_data/ 复制 .cn4 文件。"
        )


if __name__ == "__main__":
    gen = EOSOpacityGenerator()
    print("data_dir:", gen.data_dir)
    print("available (registered):", gen.list_available_materials())
    print("discovered .cn4 files:")
    for f in gen.list_discovered_files():
        print("  -", f)
    print("\ngrupbd =", DEFAULT_GRUPBD)
