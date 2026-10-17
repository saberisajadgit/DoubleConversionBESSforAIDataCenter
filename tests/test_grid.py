import numpy as np
import pytest

from double_conversion_bess.config import Config
from double_conversion_bess.grid import pcc_voltage_ll_v, regional_frequency_hz


def test_no_load_voltage_and_constant_load_frequency():
    c = Config()
    assert pcc_voltage_ll_v(0, c) == pytest.approx(c.mv_voltage_ll_v)
    t = np.linspace(0, 1, 11)
    assert regional_frequency_hz(t, np.full_like(t, 4e6), c) == pytest.approx(np.full_like(t, 60))


def test_voltage_equivalent_circuit_balance():
    c = Config()
    power = np.array([1e6, 5e6])
    voltage = pcc_voltage_ll_v(power, c)/np.sqrt(3)
    z_abs = c.mv_voltage_ll_v**2/c.grid_short_circuit_va
    resistance = z_abs/np.sqrt(1+c.grid_x_over_r**2)
    reactance = resistance*c.grid_x_over_r
    current = power/(3*voltage)
    source_squared = (voltage+resistance*current)**2+(reactance*current)**2
    assert source_squared == pytest.approx(np.full(2, c.mv_voltage_ll_v**2/3))
    assert voltage[1] < voltage[0]


def test_load_increase_initially_reduces_grid_frequency():
    c = Config()
    t = np.linspace(0, 2, 21)
    power = np.where(t < 1, 1e6, 5e6)
    frequency = regional_frequency_hz(t, power, c)
    assert frequency[-1] < frequency[0]
