"""FLASH environment management tools.

This module provides tools for managing FLASH simulation
environments on different computing platforms.
"""

from flash.flash_run.env.resource_config import FlashResourceConfig, get_resource_config

__all__ = [
    "FlashResourceConfig",
    "get_resource_config",
]
