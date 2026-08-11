#!/usr/bin/env python3
"""setuptools shim for ``flash-sim``.

Why this file exists
--------------------
The repository root **is** the ``flash`` package: ``__init__.py`` sits next to
``pyproject.toml`` and there is no ``flash/`` subdirectory to point a build
backend at. That layout cannot be expressed with declarative-only metadata, so
the mapping is computed here:

* ``package_dir={"flash": "."}`` tells setuptools that the project root must be
  imported under the name ``flash``.
* ``find_packages()`` discovers every subpackage; each is re-prefixed with
  ``flash.`` so ``flash.input_gen``, ``flash._core``, ... resolve correctly.

This is also why the build backend is setuptools rather than hatchling:
hatchling refuses editable installs whenever a ``sources`` rewrite *adds* a
path prefix, which is exactly what a root-as-package layout requires.

All project metadata (name, version, dependencies, entry points) stays in
``pyproject.toml`` -- only the layout mapping lives here.
"""

from setuptools import find_packages, setup

# Subpackages that must never be shipped.
#   FLASH Center copyrighted sources (see NOTICE / FLASH License Agreement 3)
#   plus stale "_copy" / backup trees that are not part of the public API.
EXCLUDED = [
    "flash_src",
    "flash_src.*",
    "FLASH4.8",
    "FLASH4.8.*",
    "input_gen.SimulationMain",
    "input_gen.SimulationMain.*",
    "input_gen.gen_eos_op_copy",
    "input_gen.gen_eos_op_copy.*",
    "output_processors_copy",
    "output_processors_copy.*",
    "test.grid_rede_backup_v9",
    "test.grid_rede_backup_v9.*",
    "test.grid_rede_copy_main",
    "test.grid_rede_copy_main.*",
]

_subpackages = find_packages(where=".", exclude=EXCLUDED)

setup(
    package_dir={"flash": "."},
    packages=["flash"] + [f"flash.{name}" for name in _subpackages],
)
