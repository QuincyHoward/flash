"""
FLASH 仿真空间网格和物质划分定义
════════════════════════════════

提供 Region, GridSpec, GridBuilder 等数据结构，
让用户以 Pythonic 方式定义仿真域的空间结构。

支持 1D, 2D, 3D 几何，包括:
  - 笛卡尔坐标 (cartesian)
  - 柱坐标 (cylindrical)
  - 球坐标 (spherical)

用法:
  from flash.input_gen.gen_sim_initblock.grid import GridBuilder
  
  # 1D slab 几何
  builder = GridBuilder(dim=1, geometry="cartesian", domain=(0, 160e-4))
  builder.add_region("vacuum_left", x_range=(0, 140e-4), species="cham")
  builder.add_region("target", x_range=(140e-4, 160e-4), species="targ")
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union, Dict, Any
import numpy as np
from copy import deepcopy


@dataclass
class Region:
    """仿真域中的一个区域（真空、靶材等）。
    
    Attributes:
        name: 区域名称
        species: 物质种类名 (如 "cham", "targ")
        x_range: x 坐标范围 (x_min, x_max)
        y_range: y 坐标范围 (y_min, y_max) - 2D/3D 使用
        z_range: z 坐标范围 (z_min, z_max) - 3D 使用
        rho: 密度 (g/cm³)
        tele: 电子温度 (K)
        tion: 离子温度 (K)
        trad: 辐射温度 (K)
        is_target: 是否为主靶区 (用于 isTarg 逻辑)
    """
    name: str
    species: str = "cham"
    x_range: Optional[Tuple[float, float]] = None
    y_range: Optional[Tuple[float, float]] = None
    z_range: Optional[Tuple[float, float]] = None
    rho: float = 1.0e-06
    tele: float = 290.11375
    tion: float = 290.11375
    trad: float = 290.11375
    is_target: bool = False
    
    def contains(self, x: float, y: float = 0, z: float = 0) -> bool:
        """检查点是否在此区域内."""
        if self.x_range and not (self.x_range[0] <= x <= self.x_range[1]):
            return False
        if self.y_range and not (self.y_range[0] <= y <= self.y_range[1]):
            return False
        if self.z_range and not (self.z_range[0] <= z <= self.z_range[1]):
            return False
        return True


@dataclass
class GridSpec:
    """仿真网格规格。
    
    Attributes:
        dim: 维度 (1, 2, 3)
        geometry: 几何类型 ("cartesian", "cylindrical", "spherical")
        domain_x: x 域范围 (cm)
        domain_y: y 域范围 (cm) - 2D/3D
        domain_z: z 域范围 (cm) - 3D
        nblocks_x: x 方向 block 数
        nblocks_y: y 方向 block 数
        nblocks_z: z 方向 block 数
        nxb: 每 block x 方向网格数
        nyb: 每 block y 方向网格数
        nzb: 每 block z 方向网格数
    """
    dim: int = 1
    geometry: str = "cartesian"
    domain_x: Tuple[float, float] = (0.0, 160.0e-04)
    domain_y: Tuple[float, float] = (0.0, 80.0e-04)
    domain_z: Tuple[float, float] = (0.0, 1.0)
    nblocks_x: int = 4
    nblocks_y: int = 1
    nblocks_z: int = 1
    nxb: int = 16
    nyb: int = 16
    nzb: int = 16


class GridBuilder:
    """仿真网格构建器。
    
    定义仿真域中的区域（真空、靶材等），每个区域对应一种物质。
    支持 1D/2D/3D 几何。
    
    用法:
        builder = GridBuilder(dim=1, domain=(0, 160e-4))
        builder.add_region("vacuum", x_range=(0, 140e-4), species="cham")
        builder.add_region("target", x_range=(140e-4, 160e-4), species="targ",
                           rho=2.7, is_target=True)
    """
    
    def __init__(
        self,
        dim: int = 1,
        geometry: str = "cartesian",
        domain: Optional[Tuple[float, float]] = None,
        **kwargs
    ):
        self.spec = GridSpec(dim=dim, geometry=geometry)
        if domain:
            self.spec.domain_x = domain
        
        for key, val in kwargs.items():
            if hasattr(self.spec, key):
                setattr(self.spec, key, val)
        
        self.regions: List[Region] = []
        self._material_properties: Dict[str, Dict[str, Any]] = {}
        
        # 默认物质属性
        self.set_material("cham", rho=1.0e-06, tele=290.11375, 
                          tion=290.11375, trad=290.11375)
        self.set_material("targ", rho=2.7, tele=290.11375,
                          tion=290.11375, trad=290.11375)
    
    def set_material(self, species: str, **props):
        """设置物质属性."""
        if species not in self._material_properties:
            self._material_properties[species] = {}
        self._material_properties[species].update(props)
        return self
    
    def add_region(self, name: str, species: str = "cham", **kwargs):
        """添加一个区域。
        
        Args:
            name: 区域名称
            species: 物质种类
            x_range: x 范围 (xmin, xmax)
            y_range: y 范围 (ymin, ymax) - 仅 2D/3D
            z_range: z 范围 (zmin, zmax) - 仅 3D
            rho: density (从 material 继承，可覆盖)
            tele, tion, trad: 温度 (从 material 继承，可覆盖)
            is_target: 是否是靶区
        """
        # 从 material 继承属性
        mat_props = self._material_properties.get(species, {}).copy()
        mat_props.update(kwargs)
        
        region = Region(
            name=name,
            species=species,
            **mat_props
        )
        self.regions.append(region)
        return self
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    def get_species_at(self, x: float, y: float = 0, z: float = 0) -> Optional[str]:
        """查询某位置属于哪种物质."""
        for region in reversed(self.regions):  # 后添加的优先
            if region.contains(x, y, z):
                return region.species
        return None
    
    def get_properties_at(self, x: float, y: float = 0, z: float = 0) -> Dict[str, float]:
        """查询某位置的物理属性."""
        for region in reversed(self.regions):
            if region.contains(x, y, z):
                return {"rho": region.rho, "tele": region.tele,
                        "tion": region.tion, "trad": region.trad}
        return {"rho": 1e-6, "tele": 290.11375, "tion": 290.11375, "trad": 290.11375}
    
    def is_target(self, x: float, y: float = 0, z: float = 0) -> bool:
        """查询某位置是否是靶."""
        for region in reversed(self.regions):
            if region.contains(x, y, z):
                return region.is_target
        return False
    
    # ============================================================
    # 网格采样
    # ============================================================
    
    def sample_1d(self, n_points: int = 100) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """在 1D 域上均匀采样。
        
        Returns:
            x: 坐标数组
            density: 密度数组  
            species: 物质种类列表
        """
        x = np.linspace(self.spec.domain_x[0], self.spec.domain_x[1], n_points)
        density = np.zeros(n_points)
        species = []
        
        for i, xi in enumerate(x):
            sp = self.get_species_at(xi)
            species.append(sp or "unknown")
            props = self.get_properties_at(xi)
            density[i] = props["rho"]
        
        return x, density, species
    
    def sample_2d(self, nx: int = 100, ny: int = 50) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """在 2D 域上均匀采样。
        
        Returns:
            X, Y: 网格坐标
            density: 密度数组
        """
        x = np.linspace(self.spec.domain_x[0], self.spec.domain_x[1], nx)
        y = np.linspace(self.spec.domain_y[0], self.spec.domain_y[1], ny)
        X, Y = np.meshgrid(x, y)
        density = np.zeros_like(X)
        
        for i in range(nx):
            for j in range(ny):
                props = self.get_properties_at(x[i], y[j])
                density[j, i] = props["rho"]
        
        return X, Y, density
    
    # ============================================================
    # Clone / Presets
    # ============================================================
    
    def copy(self) -> "GridBuilder":
        """深拷贝."""
        return deepcopy(self)
    
    @classmethod
    def from_laserslab_1d(cls) -> "GridBuilder":
        """从 LaserSlab 1D 示例创建 GridBuilder (默认配置)."""
        builder = cls(dim=1, geometry="cartesian", domain=(0, 160e-04))
        
        builder.set_material("cham", rho=1.0e-06, tele=290.11375,
                             tion=290.11375, trad=290.11375)
        builder.set_material("targ", rho=2.7, tele=290.11375,
                             tion=290.11375, trad=290.11375)
        
        builder.add_region("vacuum", species="cham",
                           x_range=(0, 140e-04), is_target=False)
        builder.add_region("target", species="targ",
                           x_range=(140e-04, 160e-04), is_target=True)
        
        return builder
    
    @classmethod
    def from_laserslab_2d(cls) -> "GridBuilder":
        """从 LaserSlab 2D 示例创建 GridBuilder."""
        builder = cls(dim=2, geometry="cylindrical",
                      domain=(0, 40e-04))
        builder.spec.domain_y = (0, 80e-04)
        
        builder.set_material("cham", rho=1.0e-06, tele=290.11375,
                             tion=290.11375, trad=290.11375)
        builder.set_material("targ", rho=2.7, tele=290.11375,
                             tion=290.11375, trad=290.11375)
        
        # Target: x <= 200 um, y 在 [60 um, 80 um]
        builder.add_region("vacuum", species="cham",
                           x_range=(0, 200e-04), y_range=(0, 60e-04))
        builder.add_region("target", species="targ",
                           x_range=(0, 200e-04), y_range=(60e-04, 80e-04),
                           is_target=True)
        
        return builder
