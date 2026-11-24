### PYSRIM : Python wrapper for SRIM calculation
### Project initiated by : Christopher Ostrouchov
### Modified by : Victor Garric : victor.garric@gmail.com, 2018


"""Read output files of SRIM simulation

TODO: Read header information
"""

import os
import re
from io import BytesIO

import numpy as np

from .core.ion import Ion

# Valid double_regex [4, 4.0, 4.0e100
double_regex = r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?"
symbol_regex = r"[A-Z][a-z]?"
int_regex = r"[+-]?\d+"


class SRIMOutputParseError(Exception):
    pass


class SRIM_Output(object):
    def _read_ion(self, output):
        ion_regex = r"Ion\s+=\s+({})\s+Energy\s+=\s+({})\s+keV".format(symbol_regex, double_regex)
        match = re.search(ion_regex.encode("utf-8"), output)
        if match:
            symbol = str(match.group(1).decode("utf-8"))
            energy = float(match.group(2))  # keV
            return Ion(symbol, 1000.0 * energy)
        raise SRIMOutputParseError("unable to extract ion from file")

    def _read_num_ions(self, output):
        match = re.search(rb"Total Ions calculated\s+=(\d+.\d+)", output)
        if match:
            # Cast string -> float -> round down to nearest int
            z = str(match.group(1))
            z = z.replace("'", "")
            z = z.replace("b", "")
            z = z.replace(",", ".")
            return int(float(z))
        raise SRIMOutputParseError("unable to extract total ions from file")

    def _read_table(self, output):
        match = re.search(
            (
                rb"=+(.*)"
                rb"-+(?:\s+-+)+"
            ),
            output,
            re.DOTALL,
        )
        # Read Data from table

        if match:
            # Headers TODO: name the columns in table
            # Data
            data = np.genfromtxt(BytesIO(output[match.end() :]), max_rows=100)
            return data
        raise SRIMOutputParseError("unable to extract table from file")


class Results(object):
    """Gathers all results from folder"""

    def __init__(self, directory):
        """Retrives all the calculation files in a given folder"""
        self.ioniz = Ioniz(directory)
        self.vacancy = Vacancy(directory)

        try:
            self.novac = NoVacancy(directory)
        except ValueError:
            self.novac = None

        self.etorecoils = EnergyToRecoils(directory)
        self.phonons = Phonons(directory)
        self.range = Range(directory)


class Ioniz(SRIM_Output):
    def __init__(self, directory, filename="IONIZ.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()
            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._ions = data[:, 1]
        self._recoils = data[:, 2]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def ions(self):
        """Ionization energy [eV/(Angstrom Ion)] lost to electronic stopping
        in incident ions

        """
        return self._ions

    @property
    def recoils(self):
        """Ionization energy [eV/(Angstrom Ion)] lost to electronic stopping
        in recoil ions
        """
        return self._recoils


class Vacancy(SRIM_Output):
    """Table of the final distribution of vacancies"""

    def __init__(self, directory, filename="VACANCY.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()
            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._ion_knock_ons = data[:, 1]
        self._vacancies = data[:, 2:]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def knock_ons(self):
        """Vacancies produced [Vacancies/(Angstrom-Ion) by ion]"""
        return self._ion_knock_ons

    @property
    def vacancies(self):
        """Vacancies [Vacancies/(Angstrom-Ion)] produced of element in layer

        TODO: improve interface
        """
        return self._vacancies


class NoVacancy(SRIM_Output):
    """Table of Replacement Collisions"""

    def __init__(self, directory, filename="NOVAC.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()

            # Check if it is KP calculation
            if re.search(b"Recoil/Damage Calculations made with Kinchin-Pease Estimates", output):
                raise ValueError("NOVAC has no data for KP calculations")

            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._number = data[:, 1]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def number(self):
        """Replacement Collisions [Number/(Angstrom-Ion)]"""
        return self._number


class EnergyToRecoils(SRIM_Output):
    """Energy transfered to atoms through binary collision"""

    def __init__(self, directory, filename="E2RECOIL.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()
            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._ions = data[:, 1]
        self._recoils = data[:, 2:]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def ions(self):
        """Energy [eV/(Angstrom-Ion)] transfered to material through ion collisions"""
        return self._ions

    @property
    def absorbed(self):
        """Energy [eV/(Angstrom-Ion)] absorbed from collisions with Atom

        TODO: fix terminology
        """
        return self._recoils


class Phonons(SRIM_Output):
    """Distribution of Phonons"""

    def __init__(self, directory, filename="PHONON.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()
            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._ions = data[:, 1]
        self._recoils = data[:, 2]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def ions(self):
        """Number of phonons [Phonons/(Angstrom Ion)] created from ions collisions"""
        return self._ions

    @property
    def recoils(self):
        """Number of phonons [Phonons/(Angstrom Ion)] created from recoils
        resulting from ion collisions

        """
        return self._recoils


class Range(SRIM_Output):
    """Table of the final distribution of the ions, and any recoiling target atoms"""

    def __init__(self, directory, filename="RANGE.txt"):
        with open(os.path.join(directory, filename), "rb") as f:
            output = f.read()
            ion = self._read_ion(output)
            num_ions = self._read_num_ions(output)
            data = self._read_table(output)

        self._ion = ion
        self._num_ions = num_ions
        self._depth = data[:, 0]
        self._ions = data[:, 1]
        self._elements = data[:, 2:]

    @property
    def ion(self):
        """Ion used in SRIM calculation

        **mass** could be wrong
        """
        return self._ion

    @property
    def num_ions(self):
        """Number of Ions in SRIM simulation"""
        return self._num_ions

    @property
    def depth(self):
        """Depth [Ang] of bins in SRIM Calculation"""
        return self._depth

    @property
    def ions(self):
        """Ion final distribution [(Atoms/cm3)/(Atoms/cm2)]"""
        return self._ions

    @property
    def elements(self):
        """Per elements [(Atoms/cm3)/(Atoms/cm2)] distribution of each element"""
        return self._elements
