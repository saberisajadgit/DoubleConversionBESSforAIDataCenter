"""Validated load profiles with explicitly specified SI units."""

from pathlib import Path

import numpy as np


def read_profile(
    path: str | Path, *, base_power_w: float | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Read SI data or Time_s,Load_pu with an explicit power base."""
    data = np.genfromtxt(path, delimiter=",", names=True, encoding="utf-8-sig")
    columns = set(data.dtype.names or ())
    if {"time_s", "power_w"}.issubset(columns):
        time = np.atleast_1d(data["time_s"])
        power = np.atleast_1d(data["power_w"])
    elif {"Time_s", "Load_pu"}.issubset(columns):
        if base_power_w is None or not np.isfinite(base_power_w) or base_power_w <= 0:
            raise ValueError("Load_pu requires a finite, positive power base in watts")
        time = np.atleast_1d(data["Time_s"])
        power = np.atleast_1d(data["Load_pu"]) * base_power_w
    else:
        raise ValueError("Expected time_s,power_w or Time_s,Load_pu columns")
    if len(time) < 2:
        raise ValueError("At least two samples are required")
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(power)):
        raise ValueError("Profile must contain finite values")
    if np.any(np.diff(time) <= 0):
        raise ValueError("Time must be strictly increasing")
    if np.any(power < 0):
        raise ValueError("Load power must be nonnegative")
    return time, power
