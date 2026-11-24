"""材料体系核心模型（元素、材料、层、靶、离子）的单元测试。

这组测试不调用 TRIM，只验证数据模型与输入校验；但 ``import srim`` 仍要求
``SRIM_PATH`` 有效，由 conftest.py 负责。
"""

from __future__ import annotations

import pytest

from srim.core.element import Element
from srim.core.elementdb import ElementDB
from srim.core.ion import Ion
from srim.core.layer import Layer
from srim.core.material import Material
from srim.core.target import Target


class TestElementDB:
    @pytest.mark.parametrize("identifier", ["Si", "Silicon", 14])
    def test_lookup_by_symbol_name_and_atomic_number(self, identifier):
        entry = ElementDB.lookup(identifier)
        assert entry["symbol"] == "Si"
        assert entry["name"] == "Silicon"
        assert entry["z"] == 14

    def test_lookup_invalid_identifier_raises(self):
        with pytest.raises(ValueError):
            ElementDB.lookup("si")

    def test_lookup_unknown_atomic_number_raises(self):
        with pytest.raises(IndexError):
            ElementDB.lookup(999)


class TestElement:
    def test_properties_come_from_database(self):
        element = Element("Si")
        assert element.symbol == "Si"
        assert element.name == "Silicon"
        assert element.atomic_number == 14
        assert element.mass == pytest.approx(28.0855, rel=1e-4)

    def test_unique_name_defaults_to_empty_string(self):
        assert Element("Si").unique_name == ""

    def test_unique_name_is_preserved(self):
        assert Element("Zr", unique_name="ZrOxyde").unique_name == "ZrOxyde"

    def test_equality_and_hash(self):
        assert Element("Si") == Element("Si")
        assert hash(Element("Si")) == hash(Element("Si"))


class TestMaterial:
    def test_stoichiometry_is_normalised_to_one(self):
        material = Material({"Zr": 0.34, "O": 0.66}, density=5.68)
        total = sum(props["stoich"] for props in material.elements.values())
        assert total == pytest.approx(1.0)

    def test_defaults_for_unset_properties(self):
        material = Material({"Si": 1.0}, density=2.32)
        props = next(iter(material.elements.values()))
        assert props["stoich"] == pytest.approx(1.0)
        assert props["E_d"] == pytest.approx(25.0)
        assert props["lattice"] == pytest.approx(0.0)
        assert props["surface"] == pytest.approx(3.0)

    def test_negative_stoichiometry_raises(self):
        with pytest.raises(ValueError):
            Material({"Si": -1.0}, density=2.32)

    def test_negative_density_raises(self):
        with pytest.raises(ValueError):
            Material({"Si": 1.0}, density=-2.32)

    def test_phase_is_stored(self):
        assert Material({"Si": 1.0}, density=2.32, phase=1).phase == 1


class TestLayer:
    def test_width_is_required_and_stored(self):
        layer = Layer({"Si": 1.0}, density=2.32, width=1000.0)
        assert layer.width == pytest.approx(1000.0)

    def test_from_formula_parses_stoichiometry(self):
        layer = Layer.from_formula("SiO2", density=2.32, width=1000.0)
        symbols = sorted(element.symbol for element in layer.elements)
        assert symbols == ["O", "Si"]
        stoich = {element.symbol: props["stoich"] for element, props in layer.elements.items()}
        assert stoich["O"] / stoich["Si"] == pytest.approx(2.0)

    def test_explicit_name_is_preserved(self):
        layer = Layer({"Si": 1.0}, density=2.32, width=10.0, name="Oxyde")
        assert layer.name == "Oxyde"

    def test_default_name_falls_back_to_chemical_formula(self):
        layer = Layer({"Si": 1.0}, density=2.32, width=10.0)
        assert layer.name == "Si 1.00"

    def test_name_is_not_stringified_when_none(self):
        layer = Layer({"Si": 1.0}, density=2.32, width=10.0)
        assert layer._name is None
        assert "None" not in layer.name

    def test_repr_uses_chemical_formula(self):
        layer = Layer.from_formula("SiO2", density=2.32, width=10.0)
        assert "Si" in repr(layer) and "O" in repr(layer)


class TestTarget:
    def test_width_is_sum_of_layers(self):
        layers = [
            Layer({"Si": 1.0}, density=2.32, width=1000.0),
            Layer({"O": 1.0}, density=1.43, width=500.0),
        ]
        assert Target(layers).width == pytest.approx(1500.0)

    def test_layers_are_kept_as_list(self):
        layers = [Layer({"Si": 1.0}, density=2.32, width=1000.0)]
        assert Target(layers).layers == layers


class TestIon:
    def test_energy_is_stored_in_ev(self):
        assert Ion("H", energy=1.0e6).energy == pytest.approx(1.0e6)

    def test_zero_or_negative_energy_raises(self):
        with pytest.raises(ValueError):
            Ion("H", energy=0.0)
        with pytest.raises(ValueError):
            Ion("H", energy=-1.0)

    def test_velocity_is_positive(self):
        assert Ion("H", energy=1.0e6).velocity > 0.0

    def test_default_mass_comes_from_database(self):
        assert Ion("H", energy=1.0e6).mass == pytest.approx(1.0079, rel=1e-4)

    def test_custom_mass_is_not_swallowed_by_unique_name(self):
        ion = Ion("H", energy=1.0e6, mass=2.014)
        assert ion.mass == pytest.approx(2.014)
        assert ion.unique_name == ""


class TestSRIMSettings:
    """SRIM.run() 的输入校验（不执行 TRIM）。"""

    def _settings(self, **kwargs):
        from srim.srim import SRIMSettings

        return SRIMSettings(**kwargs)

    def test_diskfile_flags_are_independent(self):
        settings = self._settings(ranges=0, sputtered=1, transmit=1, backscattered=1)
        assert (settings.ranges, settings.sputtered, settings.transmit, settings.backscattered) == (
            0,
            1,
            1,
            1,
        )

    def test_plot_range_must_be_ordered(self):
        with pytest.raises(ValueError):
            self._settings(plot_xmin=100.0, plot_xmax=10.0)

    @pytest.mark.parametrize("angle", [0, 15.5, 89.9])
    def test_angle_is_accepted_below_ninety_degrees(self, angle):
        assert self._settings(angle_ions=angle).angle_ions == pytest.approx(angle)

    @pytest.mark.parametrize("angle", [-1.0, 90.0])
    def test_angle_outside_range_is_rejected(self, angle):
        with pytest.raises(ValueError):
            self._settings(angle_ions=angle)

    def test_description_must_not_contain_quotes(self):
        with pytest.raises(ValueError):
            self._settings(description='a "quoted" run')
