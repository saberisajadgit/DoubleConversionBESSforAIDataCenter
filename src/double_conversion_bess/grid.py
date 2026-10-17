"""Illustrative upstream utility: PCC voltage and regional frequency response.

This is an observation model driven by imported active power, not a coupled
AC network/PLL solution. The same utility is used for buffered/direct cases.
All grid parameters are assumptions until utility data is available.
"""
import numpy as np
from scipy.integrate import solve_ivp


def pcc_voltage_ll_v(power_w, config):
    """High-voltage solution of E = V + Z*conj(S/V), unity PF at PCC.

    Three-phase S=P+j0, E and V are line-line RMS magnitudes. In equivalent
    phase form: E_phase² = (V_phase + R*P/(3*V_phase))²
                          + (X*P/(3*V_phase))².
    Grid impedance is upstream of the 34.5 kV PCC, NOT transformer leakage.
    """
    source_ll_v = config.mv_voltage_ll_v
    z_abs_ohm = source_ll_v**2/config.grid_short_circuit_va
    r_ohm = z_abs_ohm/np.sqrt(1+config.grid_x_over_r**2)
    x_ohm = r_ohm*config.grid_x_over_r
    p_phase_w = np.asarray(power_w)/3
    b = source_ll_v**2/3 - 2*r_ohm*p_phase_w
    discriminant = b*b - 4*(r_ohm*r_ohm+x_ohm*x_ohm)*p_phase_w*p_phase_w
    if np.any(discriminant < 0) or np.any(b <= 0):
        raise ValueError("No high-voltage PCC solution for the configured grid and power")
    return np.sqrt(3*(b+np.sqrt(discriminant))/2)


def regional_frequency_hz(time_s, power_w, config):
    """Linear single-area swing + governor, initialized in equilibrium.

    2H * dx/dt = p_mechanical - delta_p_load - D*x
    tau_g * dp_mechanical/dt = -x/R_governor - p_mechanical
    x = delta_f/f_nominal. Powers use grid_frequency_base_va, not fault MVA.
    Primary droop alone leaves a steady frequency offset for sustained steps.
    This regional frequency is assigned to the PCC; local phasor-angle-rate
    transients, inter-area modes and secondary frequency restoration are absent.
    """
    c = config
    initial_w = power_w[0]

    def rhs(t, state):
        speed_pu, mechanical_pu = state
        load_change_pu = (np.interp(t, time_s, power_w)-initial_w)/c.grid_frequency_base_va
        speed_rate = (mechanical_pu-load_change_pu-c.grid_frequency_damping_pu*speed_pu)/(2*c.grid_inertia_h_s)
        mechanical_rate = (-speed_pu/c.grid_governor_droop_pu-mechanical_pu)/c.grid_governor_tau_s
        return [speed_rate, mechanical_rate]

    sol = solve_ivp(rhs, (time_s[0], time_s[-1]), [0, 0], t_eval=time_s,
                    method="Radau", rtol=1e-7, atol=1e-11,
                    max_step=min(0.1, float(time_s[-1]-time_s[0])))
    if not sol.success:
        raise RuntimeError(sol.message)
    return c.nominal_frequency_hz*(1+sol.y[0])


def grid_observations(time_s, buffered_w, direct_w, config):
    return dict(
        pcc_voltage_kv=pcc_voltage_ll_v(buffered_w, config)/1000,
        direct_pcc_voltage_kv=pcc_voltage_ll_v(direct_w, config)/1000,
        grid_frequency_hz=regional_frequency_hz(time_s, buffered_w, config),
        direct_grid_frequency_hz=regional_frequency_hz(time_s, direct_w, config),
        direct_grid_mw=direct_w/1e6,
    )


def comparison_metrics(result):
    """Matched post-startup window, uniformly sampled to avoid event-time bias."""
    d, c = result.columns, result.config
    start = d["time_s"][0] if c.initial_soc_pct >= c.target_soc_pct else result.startup_end_s
    if start is None:
        return {"status": "No regulation interval: battery never reached target"}
    start += 5*c.grid_power_filter_s
    end = d["time_s"][-1]
    if end-start < 1:
        return {"status": "Insufficient regulation time after five filter time constants"}
    t = np.linspace(start, end, int(np.ceil((end-start)/0.1))+1)
    metrics = dict(status="Regulation only; excludes startup and five filter time constants",
                   window_start_s=float(start), window_end_s=float(end))
    for label, prefix, power_key in [("buffered", "", "grid_mw"),
                                      ("direct", "direct_", "direct_grid_mw")]:
        power = np.interp(t, d["time_s"], d[power_key])
        voltage = np.interp(t, d["time_s"], d[prefix+"pcc_voltage_kv"])
        frequency_key = "grid_frequency_hz" if not prefix else "direct_grid_frequency_hz"
        frequency = np.interp(t, d["time_s"], d[frequency_key])
        metrics[label] = dict(
            power_std_mw=float(np.std(power)),
            rms_ramp_mw_s=float(np.sqrt(np.mean((np.diff(power)/np.diff(t))**2))),
            pcc_voltage_std_v=float(1000*np.std(voltage)),
            frequency_std_mhz=float(1000*np.std(frequency)))
    return metrics
