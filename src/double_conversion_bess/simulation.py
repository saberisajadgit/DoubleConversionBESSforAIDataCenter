"""Reduced-order energy model with explicit startup handover and SoC events."""
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .battery import stack_ocv, state_of_charge_rate
from .config import Config
from .ems import grid_power_reference
from .pcs import power_actuator_rate, gfm_power_reference, vsm_frequency_rate
from .transformer import transformer_from_config
from .grid import grid_observations


@dataclass
class Result:
    columns: dict
    startup_end_s: float | None
    termination: str
    config: Config


def simulate(time, load_w, config: Config) -> Result:
    c = config
    time, load_w = np.asarray(time, float), np.asarray(load_w, float)
    if (time.ndim != 1 or load_w.shape != time.shape or len(time) < 2
            or not np.all(np.isfinite(time)) or not np.all(np.isfinite(load_w))
            or np.any(np.diff(time) <= 0) or np.any(load_w < 0)):
        raise ValueError("Invalid simulation profile")
    base = c.rated_power_w
    energy_j = c.battery_energy_mwh * c.battery_scale * 3.6e9
    startup = c.initial_soc_pct < c.target_soc_pct

    def rhs(charging):
        def evaluate(t, y):
            # State order: delta_omega [rad/s], delta_theta [rad],
            # P_load_PCS [W], P_grid_PCS [W], SoC [%], PI integral [%*s],
            # filtered effective load [W].
            delta_omega, delta_theta, inverter_w, rectifier_w, soc_pct, integral, filtered_load_w = y
            load_demand_w = np.interp(t, time, load_w) * c.loss_multiplier

            # 1. EMS schedules the grid-side GFL rectifier.
            grid_reference_w, integral_rate = grid_power_reference(
                filtered_load_w, soc_pct, integral, charging, c)
            rectifier_rate = power_actuator_rate(
                rectifier_w, grid_reference_w, base, c.rectifier_tau_s)

            # 2. Load-side GFM PCS: P-f droop plus averaged power response.
            inverter_reference_w = gfm_power_reference(
                load_demand_w, delta_omega, base, c.droop_hz)
            inverter_rate = power_actuator_rate(
                inverter_w, inverter_reference_w, base, c.inverter_tau_s)

            # 3. Reduced VSM sets frequency deviation and integrates angle.
            frequency_rate = vsm_frequency_rate(
                inverter_w, load_demand_w, delta_omega, base,
                c.nominal_frequency_hz, c.inertia_time_s, c.damping_pu)

            # 4. Shared DC battery absorbs the active-power difference.
            soc_rate = state_of_charge_rate(rectifier_w, inverter_w, energy_j)
            return [frequency_rate, delta_omega, inverter_rate,
                    rectifier_rate, soc_rate, integral_rate,
                    (load_demand_w-filtered_load_w)/c.grid_power_filter_s]
        return evaluate

    def empty(t, y): return y[4]
    def full(t, y): return y[4] - 100
    def handover(t, y): return y[4] - c.target_soc_pct
    empty.terminal = full.terminal = handover.terminal = True
    empty.direction, full.direction, handover.direction = -1, 1, 1
    state = [0, 0, 0.8*base, 0.8*base, c.initial_soc_pct, 0,
             load_w[0]*c.loss_multiplier]
    start, end = float(time[0]), float(time[-1])
    times, states = [], []
    startup_end = None
    termination = "Completed profile"
    while start < end:
        events = [empty, full] + ([handover] if startup else [])
        sol = solve_ivp(rhs(startup), (start, end), state, method="Radau",
                        dense_output=True, events=events, rtol=1e-6,
                        atol=[1e-8, 1e-8, 0.01, 0.01, 1e-8, 1e-8, 0.01],
                        max_step=float(np.min(np.diff(time))))
        if not sol.success:
            raise RuntimeError(sol.message)
        stop = sol.t[-1]
        sample = np.unique(np.concatenate(([start], time[(time > start) & (time < stop)], [stop])))
        values = sol.sol(sample)
        if times:
            sample, values = sample[1:], values[:, 1:]
        times.extend(sample)
        states.extend(values.T)
        if sol.t_events[0].size or sol.t_events[1].size:
            termination = "Stopped at battery SoC boundary; continued operation is not modeled"
            break
        if startup and sol.t_events[2].size:
            startup_end = stop
            startup = False
            state, start = sol.y[:, -1], stop
        else:
            break
    t, y = np.asarray(times), np.asarray(states).T
    load = np.interp(t, time, load_w)
    cols = dict(time_s=t, frequency_hz=c.nominal_frequency_hz+y[0]/(2*np.pi),
                angle_deviation_rad=y[1], grid_mw=y[3]/1e6, inverter_mw=y[2]/1e6,
                load_mw=load/1e6, effective_load_mw=load*c.loss_multiplier/1e6,
                battery_mw=(y[3]-y[2])/1e6, soc_pct=y[4],
                stack_ocv_v=stack_ocv(y[4]), integral_pct_s=y[5],
                grid_loading_pct=100*y[3]/base,
                transformer_drop_pct=transformer_from_config(c).resistive_drop_pct(y[3]),
                filtered_load_mw=y[6]/1e6)
    cols.update(grid_observations(t, y[3], load*c.loss_multiplier, c))
    return Result(cols, startup_end, termination, c)
