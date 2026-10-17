"""Averaged active-power PCS models. Power in W; time in seconds.

These are controlled power actuators, not switching bridges or dq current loops.
The load PCS forms frequency through a reduced VSM; voltage control is not yet solved.
"""
import numpy as np


def power_actuator_rate(actual_w, reference_w, rating_w, time_constant_s):
    """tau * dP/dt = clip(P_reference, 0, P_rated) - P."""
    limited_reference_w = np.clip(reference_w, 0.0, rating_w)
    return (limited_reference_w - actual_w) / time_constant_s


def gfm_power_reference(load_w, frequency_deviation_rad_s, rating_w, droop_hz):
    """P_ref = P_load - (P_rated / droop_Hz) * delta_f_Hz."""
    frequency_deviation_hz = frequency_deviation_rad_s / (2 * np.pi)
    return load_w - rating_w / droop_hz * frequency_deviation_hz


def vsm_frequency_rate(inverter_w, load_w, frequency_deviation_rad_s,
                       rating_w, nominal_hz, tj_s, damping_pu):
    """Tj * d(delta_omega_pu)/dt = delta_P_pu - D * delta_omega_pu.

    delta_omega_pu = (omega - omega_nominal) / omega_nominal.
    Returns d(delta_omega)/dt in rad/s². Tj uses the 2H convention.
    D multiplies per-unit speed deviation, not frequency deviation in Hz.
    """
    nominal_rad_s = 2 * np.pi * nominal_hz
    power_imbalance_pu = (inverter_w - load_w) / rating_w
    speed_deviation_pu = frequency_deviation_rad_s / nominal_rad_s
    return nominal_rad_s / tj_s * (power_imbalance_pu - damping_pu*speed_deviation_pu)
