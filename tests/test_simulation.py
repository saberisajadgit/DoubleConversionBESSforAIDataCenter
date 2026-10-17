import numpy as np
import pytest

from double_conversion_bess.config import Config
from double_conversion_bess.simulation import simulate


def test_balanced_system_remains_at_equilibrium():
    c = Config(initial_soc_pct=82)
    t = np.linspace(0, 1, 11)
    result = simulate(t, np.full_like(t, 0.8*c.rated_power_w), c)
    assert result.columns["frequency_hz"] == pytest.approx(np.full_like(t, 60))
    assert result.columns["soc_pct"] == pytest.approx(np.full_like(t, 82))
    assert result.columns["battery_mw"] == pytest.approx(np.zeros_like(t))


def test_startup_handover_and_energy_accounting():
    c = Config(initial_soc_pct=81.99)
    t = np.linspace(0, 2, 201)
    result = simulate(t, np.full_like(t, 0.5*c.rated_power_w), c)
    d = result.columns
    assert result.startup_end_s is not None
    assert 0 < result.startup_end_s < t[-1]
    assert np.all(np.diff(d["time_s"]) > 0)
    stored = (d["soc_pct"][-1]-c.initial_soc_pct)/100 * c.battery_energy_mwh*c.battery_scale*3.6e9
    transferred = np.trapezoid(d["battery_mw"]*1e6, d["time_s"])
    assert stored == pytest.approx(transferred, rel=0.01)
    assert d["grid_mw"].max() <= c.rated_power_w/1e6 + 1e-5


def test_fast_load_step_is_buffered_by_battery():
    c = Config(initial_soc_pct=82)
    t = np.linspace(0, 2, 201)
    load = np.where(t < 1, 0.8*c.rated_power_w, 0.9*c.rated_power_w)
    result = simulate(t, load, c)
    d = result.columns
    i = np.searchsorted(d["time_s"], 1.2)
    # After inverter settles, the slow grid reference leaves the battery discharging.
    assert d["grid_mw"][i] < d["inverter_mw"][i]
    assert d["battery_mw"][i] < 0
    assert abs(d["battery_mw"][i]) > 0.2
