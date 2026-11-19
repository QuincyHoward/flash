"""test_fe_render.py — fe 文本渲染格式 (官方契约逐项核对)。"""

from __future__ import annotations

import math

import pytest

from flash.input_gen.gen_flychk_his.gen_fe_file import (
    FeFileError, FeModel, build_fe_file, fe_filename_for, render_fe_text,
)

ENERGIES = [4490.0, 4500.0, 4510.0]
RECORDS = [
    (0.0, 1e11, [1e-20, 1.49071e-03, 1e-20]),
    (1e-9, 1e11, [1e-20, 1.49071e-03, 1e-20]),
]


class TestRenderStructure:
    def test_official_example_layout(self):
        """首行 'n_steps n_energies'、第二行能量、时间+密度同行、fe 一行。"""
        text = render_fe_text(ENERGIES, RECORDS)
        lines = text.splitlines()
        assert lines[0] == "2 3"
        assert lines[1] == ("4.490000e+03 4.500000e+03 4.510000e+03")
        assert lines[2] == "0.000000e+00 1.000000e+11"
        assert lines[3] == "1.000000e-20 1.490710e-03 1.000000e-20"
        assert lines[4] == "1.000000e-09 1.000000e+11"
        assert lines[5] == "1.000000e-20 1.490710e-03 1.000000e-20"
        assert len(lines) == 6

    # ── FLYCHK CX (7 Aug 2018) 实测: fe 文件内**任何位置**都不接受注释行 ──
    #    首行注释 → 静默中止无产物; 数据头后注释 → "Error in reading Fe file"。
    #    NIST fe help 文档称"以 c/# 开头的行会被忽略", 在 CX 版上不成立。
    def test_comment_rejected(self):
        """传入 comment 必须抛错 (强制溯源信息走元数据而非 fe 文件)。"""
        with pytest.raises(FeFileError):
            render_fe_text(ENERGIES, RECORDS, comment="beam Te=1keV\nrun 42")

    def test_hash_comment_rejected(self):
        with pytest.raises(FeFileError):
            render_fe_text(ENERGIES, RECORDS, comment="# already marked")

    def test_blank_comment_accepted(self):
        """纯空白 comment 视为无注释。"""
        text = render_fe_text(ENERGIES, RECORDS, comment="   \n  ")
        assert text.splitlines()[0] == "2 3"

    def test_no_comment_lines_anywhere(self):
        """渲染结果里不得出现任何以 c / # 开头的行。"""
        text = render_fe_text(ENERGIES, RECORDS)
        for ln in text.splitlines():
            assert ln.lstrip()[:1] not in ("c", "#")

    def test_single_step_single_energy(self):
        text = render_fe_text([100.0], [(0.0, 1e11, [5e-4])])
        assert text.splitlines()[0] == "1 1"

    def test_fe_file_to_text_consistent(self):
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11,
                    times=[0.0, 1e-9]),
            energies=[500.0, 1000.0, 2000.0, 5000.0],
            comment="maxwellian beam",
        )
        assert fe.to_text() == render_fe_text(fe.energies, fe.records)

    def test_comment_goes_to_meta_only(self):
        """comment 保留在 meta 里供溯源, 但不进入文件内容。"""
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11),
            energies=ENERGIES,
            comment="maxwellian beam",
        )
        assert fe.meta["comment"] == "maxwellian beam"
        assert "maxwellian beam" not in fe.to_text()
        assert fe.to_text().splitlines()[0] == "1 3"


class TestLineWidth:
    def test_500_points_all_lines_within_limit(self):
        """500 点压力: 全部行 <= 120 字符 (自动折行)。"""
        energies = [10.0 + 20.0 * i for i in range(500)]
        fe_values = [1e-6 * math.exp(-i / 100.0) for i in range(500)]
        text = render_fe_text(energies, [(0.0, 1e11, fe_values)])
        for ln in text.splitlines():
            assert len(ln) <= 120

    def test_narrow_grid_keeps_one_line(self):
        text = render_fe_text(ENERGIES, RECORDS)
        assert text.splitlines()[1].count("\n") == 0


class TestFilename:
    def test_fe_filename_for(self):
        assert fe_filename_for("Ti", 22) == "fe_Ti_Z22_input.txt"
        assert fe_filename_for("Au", 79) == "fe_Au_Z79_input.txt"
