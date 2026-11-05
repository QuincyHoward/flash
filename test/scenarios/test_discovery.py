# -*- coding: utf-8 -*-
"""discovery 场景发现器测试（2026-10-27 去注册化）

★ 每条新护栏/校验规则必须证明能失败 —— 本文件就是"证明"。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from flash.scenarios.core.scene_reg.discovery import (
    ManifestError,
    SceneMeta,
    iter_scene_manifests,
    load_manifest,
)


def _make_base(tmp_path: Path, part: str = "public") -> Path:
    base = tmp_path / "scenarios"
    (base / part).mkdir(parents=True)
    return base


def _write(base: Path, scene_dir: str, data: dict, part: str = "public") -> Path:
    d = base / part / scene_dir
    d.mkdir(parents=True, exist_ok=True)
    mf = d / "scene.json"
    mf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return mf


VALID_ENGINE = {
    "name": "demo_engine",
    "kind": "engine",
    "module": "flash.scenarios.public.demo",
    "attr": "scenario",
}


class TestLoadManifest:
    def test_valid_engine(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo", VALID_ENGINE)
        meta = load_manifest(mf)
        assert meta.name == "demo"                     # 位置派生（目录名）
        assert "demo_engine" in meta.aliases           # 显式 name 降级为别名
        assert meta.kind == "engine"
        assert meta.module == "flash.scenarios.public.demo"
        assert meta.policy == "default"

    def test_missing_name_now_derived(self, tmp_path):
        """★ 2026-11-05: name 可选 —— 缺省由 manifest 位置派生（目录名）。"""
        base = _make_base(tmp_path)
        mf = _write(base, "my_scene_dir",
                    {"kind": "engine", "attr": "s", "module": "x"})
        meta = load_manifest(mf, base=base)
        assert meta.name == "my_scene_dir"

    def test_variant_manifest_name_derived_from_stem(self, tmp_path):
        """★ scene.<变体>.json → name 派生为变体名（多场景同目录形态）。"""
        base = _make_base(tmp_path)
        d = base / "public" / "TiTi"
        d.mkdir(parents=True, exist_ok=True)
        mf = d / "scene.TiTi9.json"
        mf.write_text(json.dumps({"kind": "engine", "attr": "s",
                                  "module": "x"}), encoding="utf-8")
        meta = load_manifest(mf, base=base)
        assert meta.name == "TiTi9"

    def test_location_priority_explicit_name_demoted_to_alias(self, tmp_path):
        """★ 位置优先：显式 name ≠ 目录名 → 目录名为身份，显式名并入别名
        （复制目录零改 manifest 的关键语义）。"""
        base = _make_base(tmp_path)
        mf = _write(base, "some_dir",
                    {"name": "old_name_ref", "kind": "engine",
                     "attr": "s", "module": "x"})
        meta = load_manifest(mf, base=base)
        assert meta.name == "some_dir"
        assert "old_name_ref" in meta.aliases

    def test_missing_kind(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo", {"name": "n",
                                                   "module": "x", "attr": "s"})
        with pytest.raises(ManifestError, match="kind"):
            load_manifest(mf)

    def test_bad_kind(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo", {"name": "n", "kind": "weird"})
        with pytest.raises(ManifestError, match="kind"):
            load_manifest(mf)

    def test_engine_without_module(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo",
                    {"name": "n", "kind": "engine", "attr": "s"})
        with pytest.raises(ManifestError, match="module"):
            load_manifest(mf)

    def test_engine_without_attr(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo",
                    {"name": "n", "kind": "engine", "module": "x"})
        with pytest.raises(ManifestError, match="attr"):
            load_manifest(mf)

    def test_script_without_script(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo", {"name": "n", "kind": "script"})
        with pytest.raises(ManifestError, match="script"):
            load_manifest(mf)

    def test_unknown_policy(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo",
                    dict(VALID_ENGINE, policy="nope"))
        with pytest.raises(ManifestError, match="policy"):
            load_manifest(mf)

    def test_unknown_field(self, tmp_path):
        mf = _write(_make_base(tmp_path), "demo", dict(VALID_ENGINE, wat=1))
        with pytest.raises(ManifestError, match="未知字段"):
            load_manifest(mf)

    def test_bad_json(self, tmp_path):
        d = _make_base(tmp_path) / "public" / "demo"
        d.mkdir(parents=True)
        mf = d / "scene.json"
        mf.write_text("{not json", encoding="utf-8")
        with pytest.raises(ManifestError, match="JSON"):
            load_manifest(mf)

    def test_policy_object_resolution(self):
        from flash.flash_run.execution import DEFAULT_POLICY
        from flash.scenarios.core.scene_reg.policies import PUBLIC_SCENE_POLICY, SNB_POLICY
        assert SceneMeta(name="a", kind="main").policy_object() is DEFAULT_POLICY
        assert SceneMeta(name="a", kind="main",
                         policy="public_scene").policy_object() is PUBLIC_SCENE_POLICY
        assert SceneMeta(name="a", kind="main",
                         policy="snb").policy_object() is SNB_POLICY


class TestIterManifests:
    def test_discovers_and_sorts(self, tmp_path):
        base = _make_base(tmp_path)
        _write(base, "b_scene", dict(VALID_ENGINE, name="b"))
        _write(base, "a_scene", dict(VALID_ENGINE, name="a"))
        _write(base, "s_scene", {"name": "s", "kind": "script",
                                 "script": "x/y.py"}, part="private")
        metas = list(iter_scene_manifests(bases=(base,)))
        assert [m.name for m in metas] == ["a_scene", "b_scene", "s_scene"]

    def test_explicit_name_demoted_keeps_unique(self, tmp_path):
        """显式 name ≠ 目录名 → 降级为别名，不再触发重名护栏。"""
        base = _make_base(tmp_path)
        _write(base, "one", dict(VALID_ENGINE, name="dup"))
        _write(base, "two", dict(VALID_ENGINE, name="dup"))
        metas = list(iter_scene_manifests(bases=(base,)))
        assert [m.name for m in metas] == ["one", "two"]
        assert all("dup" in m.aliases for m in metas)

    def test_duplicate_alias_tolerated(self, tmp_path):
        """★ 2026-11-05: 别名重复不再阻塞发现（非独占提示，歧义延迟到
        catalog 按别名查找时显式报错）—— 复制场景携带旧别名不会弄哑整棵树。"""
        base = _make_base(tmp_path)
        _write(base, "one", dict(VALID_ENGINE, name="n1", aliases=["shared"]))
        _write(base, "two", dict(VALID_ENGINE, name="n2", aliases=["shared"]))
        metas = list(iter_scene_manifests(bases=(base,)))
        assert [m.name for m in metas] == ["one", "two"]

    def test_duplicate_derived_name_raises(self, tmp_path):
        """★ 同目录名复制到别处 → 派生 name 冲突 → 显式报错（需改名或显式设 name）。"""
        base = _make_base(tmp_path)
        for part in ("public", "private"):
            d = base / part / "same_name"
            d.mkdir(parents=True, exist_ok=True)
            (d / "scene.json").write_text(
                json.dumps({"kind": "engine", "attr": "s", "module": "x"}),
                encoding="utf-8")
        with pytest.raises(ManifestError, match="重复"):
            list(iter_scene_manifests(bases=(base,)))

    def test_missing_optional_private_skipped(self, tmp_path):
        base = _make_base(tmp_path)   # 无 private 分区
        _write(base, "one", VALID_ENGINE)
        metas = list(iter_scene_manifests(bases=(base,)))
        assert [m.name for m in metas] == ["one"]

    def test_invalid_manifest_raises_not_swallowed(self, tmp_path):
        base = _make_base(tmp_path)
        _write(base, "good", VALID_ENGINE)
        _write(base, "bad", {"name": "x", "kind": "weird"})
        with pytest.raises(ManifestError):
            list(iter_scene_manifests(bases=(base,)))


class TestRealRepo:
    """真仓冒烟：当前 5 个可执行场景都应被纯文件扫描发现（零 import）。"""

    def test_real_repo_discovers_scenes(self):
        metas = list(iter_scene_manifests())
        # 真仓 2026-10-27：基础 5 + SNBVTi 6 + 私有 ml/triplet 族 23 ≈ 34；
        # 至少应发现基础 5 个（防止发现器回归到"扫不到"）
        names = {m.name for m in metas}
        base5 = {"ch_center", "grad_dens_sandwich",
                 "thin_layer_sandwich", "SNBOneCH_m", "SNBOneCH_ml"}
        assert base5 <= names, f"基础场景缺失: {base5 - names}"
