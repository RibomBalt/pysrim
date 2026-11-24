"""routine 模块的单元测试（不调用 TRIM.exe）。"""

from __future__ import annotations

from pathlib import Path

from srim.routine import _result_directory_name, merge_results


class TestResultDirectoryName:
    def test_without_plot_limits(self):
        class FakeIon:
            symbol = "H"
            energy = 1.0e6

        assert _result_directory_name(FakeIon(), None) == "H-1000000.0"

    def test_with_plot_limits(self):
        class FakeIon:
            symbol = "He"
            energy = 1.0e3

        assert _result_directory_name(FakeIon(), (0, 20000)) == "He-1000.0-0-20000"


class TestMergeResults:
    TABLE = "header\n-----------  ----------\n100 1.0\n200 2.0\n"

    def _make_step(self, root, name, extra_line=""):
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "RANGE.txt").write_text(self.TABLE, encoding="utf-8")
        (directory / "VACANCY.txt").write_text(self.TABLE + extra_line, encoding="utf-8")
        return directory

    def test_merges_only_result_directories(self, tmp_path):
        """目录中混入 __pycache__ 等非结果目录时，不能漏掉相邻的结果目录。"""
        out = tmp_path / "out"
        for name in ("step-a", "step-b", "__pycache__", "step-c"):
            self._make_step(out, name)

        merged = merge_results(str(out))

        assert [Path(directory).name for directory in merged] == ["step-a", "step-b", "step-c"]
        assert (out / "total_range.txt").read_text(encoding="utf-8").count("100 1.0") == 3
        assert (out / "total_vacancy.txt").is_file()

    def test_skips_header_and_trailing_summary(self, tmp_path):
        out = tmp_path / "out"
        self._make_step(out, "step-a", extra_line="summary line\n")

        merge_results(str(out))

        merged_range = (out / "total_range.txt").read_text(encoding="utf-8")
        merged_vacancy = (out / "total_vacancy.txt").read_text(encoding="utf-8")
        assert merged_range.splitlines()[0] == "100 1.0"
        assert "header" not in merged_range
        assert "summary line" not in merged_vacancy

    def test_empty_result_directory(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()

        assert merge_results(str(out)) == []
        assert (out / "total_range.txt").read_text() == ""
