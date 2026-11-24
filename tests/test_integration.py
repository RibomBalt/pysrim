"""真实调用 TRIM.exe 的集成测试（可选分组，默认跳过）。

运行方式::

    pytest --srim

TRIM.exe 必须在 SRIM 安装目录内执行，因此会向该目录写入 ``TRIM.IN`` 与输出
文件；断言使用通过 ``copy_output_files`` 拷贝到临时目录的副本。
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = [pytest.mark.slow, pytest.mark.srim]

NUM_IONS = 100


@pytest.fixture(scope="module")
def results(trim_run):
    return trim_run[0]


def test_output_files_and_sections(trim_run):
    """一次真实计算应产出全部已知输出文件，并能被 Results 解析出各小节。"""
    results, output_dir = trim_run

    for filename in ("RANGE.txt", "VACANCY.txt", "IONIZ.txt", "PHONON.txt", "TRIM.IN"):
        assert (output_dir / filename).is_file(), filename

    for section in ("range", "vacancy", "ioniz", "phonons"):
        assert getattr(results, section) is not None

    # 四个小节的深度分箱必须一致，否则说明表格解析错位
    bins = results.range.depth.size
    assert bins > 0
    for section in ("vacancy", "ioniz", "phonons"):
        assert getattr(results, section).depth.size == bins


def test_range_ion_distribution(results):
    """100 keV H 在 Si 中的射程约 1 um，离子应停在 10 um 靶内。"""
    depth = results.range.depth
    ions = results.range.ions

    assert depth.ndim == 1 and ions.ndim == 1
    assert depth.size == ions.size
    assert np.all(np.diff(depth) > 0)  # 深度分箱单调递增
    assert np.all(ions >= 0)
    assert ions.sum() > 0
    assert np.count_nonzero(ions) >= 1

    assert results.range.ion.symbol == "H"
    assert results.range.ion.energy == pytest.approx(1.0e5)
    # 注意：RANGE.txt 的 “Total Ions calculated” 是 TRIM 自己的统计值，
    # 穿透靶材的离子可能不被计入，因此只在这里做弱断言
    assert results.range.num_ions > 0


def test_full_cascade_damage_profile(results):
    """calculation=2（Full Cascade）应产生非零且非负的损伤分布。"""
    assert np.sum(results.vacancy.vacancies) > 0
    assert np.sum(results.phonons.ions) > 0
    assert np.all(results.ioniz.ions >= 0)
    assert np.all(results.phonons.ions >= 0)


class TestRoutine:
    def test_run_calculation_with_default_plot_limits(self, silicon_target, hydrogen_ion, tmp_path, srim_dir):
        """plot_limits 默认 None 时应能完成并写入结果目录。"""
        from srim.routine import run_calculation

        local_dir = run_calculation(
            hydrogen_ion,
            silicon_target,
            20,
            calculation=1,
            save_directory=str(tmp_path),
            SRIM_dir=str(srim_dir),
        )
        assert (tmp_path / "H-1000000.0").is_dir()
        assert (tmp_path / "H-1000000.0" / "RANGE.txt").is_file()
        assert local_dir == str(tmp_path / "H-1000000.0")

    def test_auto_steps_and_merge_results(self, silicon_target, tmp_path, srim_dir):
        """分步计算 + 结果合并：每步都要有 RANGE.txt，合并后要有 total_* 文件。"""
        from srim.routine import auto_steps, merge_results

        out = tmp_path / "out"
        out.mkdir()
        auto_steps(
            {"identifier": "H", "energy": 1.0e5},
            silicon_target,
            NUM_IONS,
            1,
            str(out),
            str(srim_dir),
            False,
            [(0, 50_000), (50_000, 100_000)],
            0,
        )

        step_dirs = sorted(p for p in out.iterdir() if p.is_dir())
        assert len(step_dirs) == 2
        for step_dir in step_dirs:
            assert (step_dir / "RANGE.txt").is_file()
            assert (step_dir / "TRIM.IN").is_file()

        merge_results(str(out))
        assert (out / "total_range.txt").read_text().strip() != ""
        assert (out / "total_vacancy.txt").is_file()
