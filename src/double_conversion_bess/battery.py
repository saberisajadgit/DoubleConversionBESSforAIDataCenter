"""Illustrative resting-voltage curve, not manufacturer cell characterization."""
import numpy as np


def state_of_charge_rate(grid_power_w, inverter_power_w, energy_capacity_j):
    """dSoC_percent/dt = 100*(P_grid - P_inverter)/E_capacity.

    Positive battery power means charging. This is an ideal energy bucket;
    OCV does not feed back into battery current or PCS voltage limits.
    """
    return 100*(grid_power_w-inverter_power_w)/energy_capacity_j


def stack_ocv(soc_pct):
    # Assumed intermediate points; 82% anchor follows the source description.
    return 416 * np.interp(soc_pct, [0, 5, 10, 20, 50, 82, 90, 95, 100],
                          [2.5, 3.0, 3.15, 3.22, 3.28, 1385 / 416,
                           3.35, 3.45, 1500 / 416])
