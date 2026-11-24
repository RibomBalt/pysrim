# PySrim

PySrim is a code written in python to simulate via Monte Carlo ion treveling through a target. The ions are stopped through the collisions of ions with the nucleus of an atom within the material and excitation of the electron clouds of each atom.

# About this fork (By @RibomBalt)

Basically fixed everything I found that doesn't work with new Python 3.11-3.13 or anything that makes me feel uncomfortable. 

Now with modern `pyproject.yaml` one can simply use `uv pip install -e .` to install this package.

A new `SRIM_PATH` environment variable is introduced to specify the SRIM path. You are also prompted to enter it if you didn't set it.

Also I make this work on Windows as well ... no `xvfb` or `wine`, just execute the exe and that's all.

There could be more *inconsistency* until I found them ... If you find any fire an issue and I may have a look (or may not).

# About this fork I'm based on (By Original Author: @victorgarric)

## Introduction

This fork is a modified version of the original code of pysrim. This version in only intended to work on a unix machine. The use of a linux machine allow you to get rid of one main disadvanage : as SRIM is poorly written in visual basic, the simple display of the calculation window, even without any plot, slow down the calculation.
In order to speed up calculations, this forked pysrim warp the display using the "xvfb-run" command. All the display tasks are hidden and the calculation only is running.

## Benchmarking

Assessing the speed up, we choose to launch two calculations on the same machine (10k Ne ions in a 10 micrometers zircone layer using a range of energy from 1 to 20 MeV with a step of 1 MeV, full cascade calculation) : dummy screen method is, on average, 48% faster than windows based calculation.

## New in this fork

Added from usual pysrim and largely inspired example files from the original author, "routine" functions have been added :
* run_calculation : a modified import from the original example files of the author
* auto_ions : a function that run many calculations based on a list of ions
* auto_steps : a function that run one calculation where the layer is divided in many plot to increase spatial resolution
* merge_results : a function to merge the "RANGE" and "VACANCY" files from a stepped calculation
* unique_name and multilayers and elements : using a unique_name variable for each element allow you to create multiple layers with the same element in different states

# Installation

## Unix Dependencies

* wine
* xvfb

## Python Dependencies
* docopt
* matplotlib
* numpy
* pandas
* mpi4py

## Installation

Install SRIM from <http://www.srim.org> (Windows) or run it through `wine`/`xvfb` on
Unix, then point `SRIM_PATH` at the installation directory and install the package:

<pre>
export SRIM_PATH=/path/to/SRIM   # directory containing TRIM.exe
uv pip install -e .
</pre>

The legacy `install_pysrim.py` downloader has been removed: SRIM is no longer
available from the URL it used.

# Known issues and future developments

* Bha ! Displays are mostly in french and so example file is

# Development

## Setup

`SRIM_PATH` must point to a directory containing `TRIM.exe`. It is validated when a
calculation runs, not at import time, so `import srim` works without SRIM; a copy of
the installation can also be placed under `vendor/SRIM` (git-ignored) and picked up
automatically by the test suite.

```bash
uv sync            # installs runtime + dev dependencies (pytest, ruff)
uv run ruff check srim tests
```

## Tests

The suite is split in two groups:

```bash
uv run pytest             # unit tests only (data model + TRIM.IN/SR.IN generation), < 2 s
uv run pytest --srim      # also run the integration tests that execute TRIM.exe
```

Integration tests are opt-in (`--srim`) because they spawn `TRIM.exe` inside the SRIM
installation directory: they are slower and they overwrite `TRIM.IN` and the output
files in that directory. The unit tests do not need SRIM at all; only the `--srim`
group does, and it is skipped with a clear message when no installation is found.

## Usage

See [`docs/usage.md`](docs/usage.md) for a working guide: environment setup, the three
API levels (`SRIM` / `routine` helpers / a custom scan loop), result fields and units,
all settings, and the behaviour worth knowing before trusting a run (100 bins, output
file locations, when `RANGE.txt` reports an empty ion distribution, performance).
