### PYSRIM : Python wrapper for SRIM calculation
### Project initiated by : Christopher Ostrouchov
### Modified by : Victor Garric : victor.garric@gmail.com, 2018

import datetime
import os
from pathlib import Path
from random import randint

from .core.ion import Ion
from .srim import SRIM


def _result_directory_name(ion, plot_limits):
    """Build the per-step result directory name.

    ``plot_limits`` is optional: when it is ``None`` the whole target is
    computed in one go, so only the ion symbol and energy are used.
    """
    if plot_limits is None:
        return "{}-{}".format(ion.symbol, ion.energy)
    return "{}-{}-{}-{}".format(ion.symbol, ion.energy, plot_limits[0], plot_limits[1])


def run_calculation(
    ion,
    target,
    num_ions,
    calculation=2,
    save_directory=None,
    SRIM_dir="~/SRIM",
    subbing=False,
    plot_limits=None,
    angle_ions=0,
):
    """Run one SRIM calculation and copy its results into ``save_directory``.

    :return: path of the directory holding this run's output files
    """
    print(
        "\t%s\t%s\t%s\t\t%d\t\t%s\t\t%s"
        % (
            datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            ion.symbol,
            ion.energy,
            num_ions,
            plot_limits,
            angle_ions,
        )
    )
    settings = {
        "number_ions": num_ions,
        "calculation": calculation,
        "collisions": 2,
        "random_seed": randint(0, 100000),
        "angle_ions": angle_ions,
    }
    if plot_limits is not None:
        settings["plot_xmin"] = plot_limits[0]
        settings["plot_xmax"] = plot_limits[1]
    srim = SRIM(target, ion, **settings)
    srim.run(SRIM_dir, subbing=subbing)

    if save_directory is None:
        save_directory = os.path.join(os.getcwd(), "output")
        os.makedirs(save_directory, exist_ok=True)

    local_dir = os.path.join(save_directory, _result_directory_name(ion, plot_limits))
    os.makedirs(local_dir, exist_ok=True)
    SRIM.copy_output_files(SRIM_dir, local_dir)
    print("\t%s\t\t Results saved to %s" % (datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), local_dir))
    return local_dir


def _print_header():
    print("*** Automated SRIM on Python : Starting ***")
    print("\n")
    print("\t%s\t\t\t%s\t%s\t%s\t%s\t\t%s" % ("Date", "Symbole", "Energie (eV)", "Ions calculés", "Step", "Angle"))


def auto_steps(ions, target, num_ions, calculation, save_directory, SRIM_dir, subbing, steps, angle_ions):
    """Run the same ion over several target depth windows."""
    _print_header()
    results = []
    for step in steps:
        results.append(
            run_calculation(
                Ion(**ions),
                target,
                num_ions,
                calculation=calculation,
                save_directory=save_directory,
                SRIM_dir=SRIM_dir,
                subbing=subbing,
                plot_limits=step,
                angle_ions=angle_ions,
            )
        )
    print("*** Automated SRIM on Python : End ***")
    return results


def auto_ions(ions, target, num_ions, calculation, save_directory, SRIM_dir, subbing, steps, angle_ions):
    """Run several ions against the same target."""
    _print_header()
    results = []
    for ion in ions:
        results.append(
            run_calculation(
                Ion(**ion),
                target,
                num_ions,
                calculation=calculation,
                save_directory=save_directory,
                SRIM_dir=SRIM_dir,
                subbing=subbing,
                angle_ions=angle_ions,
            )
        )
    print("*** Automated SRIM on Python : End ***")
    return results


def auto_angle(ions, target, num_ions, calculation, save_directory, SRIM_dir, subbing, steps, angle_ions):
    """Run the same ion and target over a list of incident angles."""
    _print_header()
    results = []
    for angle in angle_ions:
        results.append(
            run_calculation(
                Ion(**ions),
                target,
                num_ions,
                calculation=calculation,
                save_directory=save_directory,
                SRIM_dir=SRIM_dir,
                subbing=subbing,
                angle_ions=angle,
            )
        )
    print("*** Automated SRIM on Python : End ***")
    return results


def _table_start(lines):
    """Index of the first data row in a SRIM output table."""
    for index, line in enumerate(lines):
        if line.startswith("-----------  "):
            return index + 1
    raise ValueError("unable to locate the data table separator in SRIM output")


def merge_results(result_directory=None):
    """Merge the per-step RANGE/VACANCY tables into two flat files.

    :param str result_directory: directory holding one sub-directory per step
    :return: list of the step directories that were merged
    """
    if result_directory is None:
        result_directory = os.path.join(os.getcwd(), "output")

    result_directory = os.path.abspath(result_directory)
    # Only keep sub-directories that actually hold SRIM results, skipping cache and
    # VCS metadata.  The previous implementation removed entries from `dirs` while
    # iterating over it, which silently skipped results next to an excluded dir.
    excluded = {"__pycache__", ".git"}
    dirs = [
        directory
        for directory, _subdirs, files in os.walk(result_directory)
        if directory != result_directory
        and not excluded.intersection(Path(directory).parts)
        and "RANGE.txt" in files
        and "VACANCY.txt" in files
    ]
    dirs.sort()

    total_range = ""
    total_vacancy = ""

    for directory in dirs:
        with open(os.path.join(directory, "RANGE.txt"), "r") as f:
            local_range = f.readlines()
        with open(os.path.join(directory, "VACANCY.txt"), "r") as f:
            local_vacancy = f.readlines()

        total_range += "".join(local_range[_table_start(local_range) :])
        # VACANCY.txt ends with a summary line that is not part of the table
        total_vacancy += "".join(local_vacancy[_table_start(local_vacancy) : len(local_vacancy) - 1])

    with open(os.path.join(result_directory, "total_range.txt"), "w") as file_range:
        file_range.write(total_range)

    with open(os.path.join(result_directory, "total_vacancy.txt"), "w") as file_vacancy:
        file_vacancy.write(total_vacancy)

    return dirs
