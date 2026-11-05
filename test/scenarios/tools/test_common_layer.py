# -*- coding: utf-8 -*-
"""common/ 共享层单元测试：scene_ref 按名加载器 + anchors 锚点表。
（场景收纳整理 2026-11-05 共享区整理 3/3）
"""
from __future__ import annotations

import pytest

from flash.scenarios.common.scene_ref import (
    clear_scene_ref_cache,
    scene_module,
)
from flash.scenarios.core.anchors import anchor, anchors_table, try_anchor


class TestSceneRef:
    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        clear_scene_ref_cache()
        yield
        clear_scene_ref_cache()

    def test_load_by_name(self):
        """按场景名加载其主模块（真实仓库树）。"""
        mod = scene_module("OneCH_ml")
        assert hasattr(mod, "config_constants")

    def test_single_instance_cache(self):
        """同名两次加载返回同一模块对象（重绑定委托依赖此语义）。"""
        a = scene_module("OneCH_ml")
        b = scene_module("OneCH_ml")
        assert a is b

    def test_stem_override(self):
        """stem 参数：加载场景目录下非主名模块（thin interpolator）。"""
        mod = scene_module("thin_layer_sandwich_si", stem="interpolator")
        assert hasattr(mod, "build_variable_grid")

    def test_unknown_scene_raises(self):
        with pytest.raises(ImportError, match="未注册"):
            scene_module("no_such_scene_xyz")

    def test_missing_module_raises(self):
        with pytest.raises(ImportError, match="主模块不存在"):
            scene_module("thin_layer_sandwich_si")   # 无 thin_layer_sandwich_si.py


class TestAnchors:
    def test_table_loads_and_underscore_skipped(self):
        tbl = anchors_table()
        assert isinstance(tbl, dict)
        assert "_comment" in tbl          # 元数据键存在
        # 业务锚点均为相对 POSIX 路径
        for k, v in tbl.items():
            if k.startswith("_"):
                continue
            assert not str(v).startswith("/")

    def test_anchor_resolves(self):
        p = anchor("SNB.t001")
        assert p.is_absolute()
        assert p.name == "t001"

    def test_anchor_missing_key_raises(self):
        with pytest.raises(KeyError, match="未知场景锚点"):
            anchor("no.such.anchor")

    def test_try_anchor_none(self):
        assert try_anchor("no.such.anchor") is None
