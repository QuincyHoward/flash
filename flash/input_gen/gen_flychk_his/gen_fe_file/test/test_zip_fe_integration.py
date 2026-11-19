"""test_zip_fe_integration.py — 含 fe 成员的完整 zip 集成核对。"""

from __future__ import annotations

import zipfile

import pytest

from flash.input_gen.gen_flychk_his.gen_fe_file import (
    FeModel, build_fe_file, fe_filename_for, render_fe_text,
    write_history_zip_with_fe,
)
from flash.input_gen.gen_flychk_his.zip_writer import (
    HistoryZipWriter, ZipWriterError, render_runfile,
)

FE_ENERGIES = [4490.0, 4500.0, 4510.0]


class TestZipWithFe:
    def test_three_members_in_order(self, history_table, out_dir):
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0, 1e-9]),
            energies=FE_ENERGIES,
        )
        fe_name = fe_filename_for(history_table.element, history_table.z)
        zp = out_dir / "with_fe.zip"
        HistoryZipWriter().write(history_table, str(zp),
                                 fe_text=fe.to_text(), fe_filename=fe_name)
        with zipfile.ZipFile(zp) as zf:
            assert zf.namelist() == [
                "runfile.txt", "history_Ti_Z22_input.txt", fe_name]

    def test_runfile_fe_line_position(self, history_table, out_dir):
        """runfile 含 `fe file` 行, 位于 fhot/history 数据行之前、end 之前。"""
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11),
            energies=FE_ENERGIES,
        )
        fe_name = fe_filename_for(history_table.element, history_table.z)
        zp = out_dir / "runfile_pos.zip"
        HistoryZipWriter().write(history_table, str(zp),
                                 fe_text=fe.to_text(), fe_filename=fe_name)
        with zipfile.ZipFile(zp) as zf:
            lines = zf.read("runfile.txt").decode("utf-8").splitlines()
        fe_idx = lines.index(f"fe file {fe_name}")
        history_idx = next(i for i, ln in enumerate(lines)
                           if ln.startswith("history "))
        end_idx = lines.index("end")
        assert 0 < fe_idx < history_idx < end_idx

    def test_fe_content_char_exact(self, history_table, out_dir):
        """fe 成员内容与 fe.to_text() 逐字符相等。"""
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0, 2e-9]),
            energies=FE_ENERGIES,
            comment="integration test",
        )
        fe_name = fe_filename_for(history_table.element, history_table.z)
        zp = out_dir / "char_exact.zip"
        HistoryZipWriter().write(history_table, str(zp),
                                 fe_text=fe.to_text(), fe_filename=fe_name)
        with zipfile.ZipFile(zp) as zf:
            assert zf.read(fe_name).decode("utf-8") == fe.to_text()

    def test_verify_zip_with_fe_ok(self, history_table, out_dir):
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11), energies=FE_ENERGIES)
        fe_name = fe_filename_for(history_table.element, history_table.z)
        zp = out_dir / "verify_ok.zip"
        HistoryZipWriter().write(history_table, str(zp),
                                 fe_text=fe.to_text(), fe_filename=fe_name)
        res = HistoryZipWriter().verify_zip(
            history_table, str(zp), fe_text=fe.to_text(), fe_filename=fe_name)
        assert res["ok"]
        assert res["checks"]["fe_member_exists"]
        assert res["checks"]["fe_content"]
        assert res["checks"]["runfile_fe_line"]
        assert res["checks"]["fe_contract"] == "flychk-history-fe-v1"

    def test_verify_zip_detects_tampered_fe(self, history_table, out_dir):
        """篡改 fe 成员后 verify 失败。"""
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11), energies=FE_ENERGIES)
        fe_name = fe_filename_for(history_table.element, history_table.z)
        zp = out_dir / "tampered.zip"
        HistoryZipWriter().write(history_table, str(zp),
                                 fe_text=fe.to_text(), fe_filename=fe_name)
        bad_text = fe.to_text().replace("4.490000e+03", "4.000000e+03")
        assert bad_text != fe.to_text()
        res = HistoryZipWriter().verify_zip(
            history_table, str(zp), fe_text=bad_text, fe_filename=fe_name)
        assert not res["ok"] and res["checks"]["fe_content"] is False

    def test_fe_pair_required(self, history_table, out_dir):
        """fe_text/fe_filename 必须成对给出。"""
        zp = out_dir / "pair.zip"
        with pytest.raises(ZipWriterError):
            HistoryZipWriter().write(history_table, str(zp),
                                     fe_text="x", fe_filename=None)
        with pytest.raises(ZipWriterError):
            HistoryZipWriter().write(history_table, str(zp),
                                     fe_text=None, fe_filename="fe.txt")


class TestBackwardCompat:
    def test_no_fe_two_members_unchanged(self, history_table, out_dir):
        """fe=None 路径: 成员恰两个, runfile 与无 fe 渲染逐字节相同。"""
        zp = out_dir / "no_fe.zip"
        HistoryZipWriter().write(history_table, str(zp))
        with zipfile.ZipFile(zp) as zf:
            members = zf.namelist()
            runfile = zf.read("runfile.txt").decode("utf-8")
        assert members == ["runfile.txt", "history_Ti_Z22_input.txt"]
        assert runfile == render_runfile(
            history_table.element, history_table.z,
            history_table.columns, "history_Ti_Z22_input.txt")

    def test_bridge_function_end_to_end(self, history_table, out_dir):
        """write_history_zip_with_fe 桥接函数端到端 + 回读自检。"""
        fe = build_fe_file(
            FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0]),
            energies=FE_ENERGIES,
        )
        zp = out_dir / "bridge.zip"
        path = write_history_zip_with_fe(history_table, fe, str(zp))
        assert path == zp
        fe_name = fe_filename_for(history_table.element, history_table.z)
        res = HistoryZipWriter().verify_zip(
            history_table, str(zp), fe_text=fe.to_text(), fe_filename=fe_name)
        assert res["ok"]
        # fe 行文件名与桥接函数生成的文件名一致
        with zipfile.ZipFile(zp) as zf:
            assert f"fe file {fe_name}" in \
                zf.read("runfile.txt").decode("utf-8")

    def test_render_fe_text_pure_function_alias(self):
        """render_fe_text 与 zip 侧渲染无耦合 (纯函数可独立调用)。"""
        text = render_fe_text(FE_ENERGIES, [(0.0, 1e11, [1e-20] * 3)])
        assert text.splitlines()[0] == "1 3"
