"""pytest 公共夹具与可选测试分组。

SRIM 安装目录按以下顺序查找：

1. 环境变量 ``SRIM_PATH``
2. ``<repo>/vendor/SRIM``（项目内本地副本，已被 .gitignore 排除）

单元测试在没有 SRIM 的机器上也能运行（``import srim`` 不再在导入期校验
``SRIM_PATH``）；只有需要真实 ``TRIM.exe`` 的集成测试会被跳过。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def locate_srim_dir() -> Path | None:
    """返回包含 TRIM.exe 的 SRIM 安装目录，找不到返回 None。"""
    candidates = []
    env_value = os.environ.get("SRIM_PATH")
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(REPO_ROOT / "vendor" / "SRIM")

    for candidate in candidates:
        if (candidate / "TRIM.exe").is_file():
            return candidate.resolve()
    return None


SRIM_DIR = locate_srim_dir()

if SRIM_DIR is not None:
    os.environ.setdefault("SRIM_PATH", str(SRIM_DIR))


# --------------------------------------------------------------------------- #
# 可选分组：真实 TRIM 调用默认不跑
# --------------------------------------------------------------------------- #
def pytest_addoption(parser):
    parser.addoption(
        "--srim",
        action="store_true",
        default=False,
        help="运行需要真实 SRIM/TRIM.exe 的集成测试（标有 srim/slow，默认跳过）",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--srim"):
        return
    skip = pytest.mark.skip(reason="集成测试默认关闭，用 --srim 开启")
    for item in items:
        if "srim" in item.keywords or "slow" in item.keywords:
            item.add_marker(skip)


# --------------------------------------------------------------------------- #
# 夹具
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def srim_dir() -> Path:
    """SRIM 安装目录（含 TRIM.exe）。"""
    if SRIM_DIR is None:
        pytest.skip("未找到 SRIM 安装（设置 SRIM_PATH 或放置 vendor/SRIM）")
    return SRIM_DIR


@pytest.fixture()
def silicon_target():
    """100 um 厚纯硅靶。"""
    from srim.core.layer import Layer
    from srim.core.target import Target

    return Target([Layer({"Si": 1.0}, density=2.32, width=100_000.0)])


@pytest.fixture()
def hydrogen_ion():
    """1 MeV 氢离子。"""
    from srim.core.ion import Ion

    return Ion("H", energy=1.0e6)


@pytest.fixture(scope="session")
def trim_run(srim_dir, tmp_path_factory):
    """真实执行一次 TRIM 计算，会话内复用。

    TRIM.exe 必须在 SRIM 安装目录内执行（依赖同目录的 ``Data`` 等伴随文件），
    因此计算就地写入安装目录；断言用的副本通过 ``copy_output_files`` 收集到
    临时目录，避免测试依赖上一次的残留文件。

    返回 ``(results, output_dir)``。
    """
    from srim.core.ion import Ion
    from srim.core.layer import Layer
    from srim.core.target import Target
    from srim.output import Results
    from srim.srim import SRIM

    target = Target([Layer({"Si": 1.0}, density=2.32, width=100_000.0)])
    # 100 keV H 在 Si 中的射程约 1 um，确保离子停在 10 um 靶内（1 MeV 会穿靶，
    # RANGE.txt 的离子分布几乎全为 0，不利于断言）
    ion = Ion("H", energy=1.0e5)
    srim = SRIM(
        target,
        ion,
        number_ions=100,
        calculation=2,
        ranges=1,
        collisions=2,
        random_seed=12345,
    )
    srim.run(str(srim_dir))

    output_dir = tmp_path_factory.mktemp("srim-output")
    SRIM.copy_output_files(str(srim_dir), str(output_dir))
    return Results(str(output_dir)), output_dir
