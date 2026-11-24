"""SRIM 目录解析与导入期行为的测试。

历史上 ``import srim`` 在模块级校验 ``SRIM_PATH`` 并 ``input()`` 询问路径，
导致非交互环境直接 EOFError。现在校验推迟到 ``SRIM.run()`` 调用时。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from srim.srim import resolve_srim_directory


@pytest.fixture()
def fake_srim_dir(tmp_path):
    """一个只包含假 TRIM.exe 的目录。"""
    directory = tmp_path / "SRIM"
    directory.mkdir()
    (directory / "TRIM.exe").write_text("")
    return directory


class TestResolveSrimDirectory:
    def test_accepts_existing_directory(self, fake_srim_dir):
        assert resolve_srim_directory(str(fake_srim_dir)) == str(fake_srim_dir)

    def test_falls_back_to_environment(self, fake_srim_dir, monkeypatch):
        monkeypatch.setenv("SRIM_PATH", str(fake_srim_dir))
        assert resolve_srim_directory() == str(fake_srim_dir)

    def test_explicit_path_wins_over_environment(self, fake_srim_dir, tmp_path, monkeypatch):
        other = tmp_path / "other"
        other.mkdir()
        (other / "TRIM.exe").write_text("")
        monkeypatch.setenv("SRIM_PATH", str(fake_srim_dir))
        assert resolve_srim_directory(str(other)) == str(other)

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(ValueError, match="SRIM directory not found"):
            resolve_srim_directory(str(tmp_path / "does-not-exist"))

    def test_directory_without_executable_raises(self, tmp_path):
        with pytest.raises(ValueError, match="TRIM.exe"):
            resolve_srim_directory(str(tmp_path))

    def test_missing_environment_raises(self, monkeypatch):
        monkeypatch.delenv("SRIM_PATH", raising=False)
        with pytest.raises(ValueError, match="not set"):
            resolve_srim_directory()

    def test_custom_executable_is_checked(self, fake_srim_dir):
        with pytest.raises(ValueError, match="SRModule.exe"):
            resolve_srim_directory(str(fake_srim_dir), executable="SRModule.exe")


class TestImportDoesNotTouchSrim:
    def test_import_without_srim_path(self):
        """没有 SRIM_PATH 时 import srim 仍应成功（不再在导入期 input()）。"""
        repo_root = Path(__file__).resolve().parents[1]
        env = {key: value for key, value in os.environ.items() if key != "SRIM_PATH"}
        env["PYTHONPATH"] = str(repo_root)

        result = subprocess.run(
            [sys.executable, "-c", "import srim; print('ok')"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert "ok" in result.stdout
