"""Explicit provisional parameters; see docs/model-notes.md for provenance."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    rated_power_w: float = 5.16e6
    battery_energy_mwh: float = 7.08
    battery_scale: float = 0.025
    initial_soc_pct: float = 60.0
    target_soc_pct: float = 82.0
    nominal_frequency_hz: float = 60.0
    inertia_time_s: float = 5.0
    damping_pu: float = 20.0
    droop_hz: float = 0.5
    loss_multiplier: float = 1.0
    kp_w_per_pct: float = 20e3
    ki_w_per_pct_s: float = 5e3
    rectifier_tau_s: float = 0.05
    inverter_tau_s: float = 0.02
    transformer_r_pu: float = 0.005
    transformer_x_pu: float = 0.075
    pcs_voltage_ll_v: float = 690.0
    mv_voltage_ll_v: float = 34500.0
    grid_power_filter_s: float = 5.0
    grid_short_circuit_va: float = 200e6
    grid_x_over_r: float = 10.0
    grid_frequency_base_va: float = 1000e6
    grid_inertia_h_s: float = 5.0
    grid_frequency_damping_pu: float = 1.0
    grid_governor_droop_pu: float = 0.05
    grid_governor_tau_s: float = 5.0

    def __post_init__(self):
        from math import isfinite
        from dataclasses import asdict
        if not all(isfinite(v) for v in asdict(self).values()):
            raise ValueError("Configuration values must be finite")
        for key in ("rated_power_w", "battery_energy_mwh", "battery_scale",
                    "nominal_frequency_hz", "inertia_time_s", "droop_hz",
                    "rectifier_tau_s", "inverter_tau_s", "pcs_voltage_ll_v", "mv_voltage_ll_v",
                    "grid_power_filter_s", "grid_short_circuit_va", "grid_x_over_r",
                    "grid_frequency_base_va", "grid_inertia_h_s",
                    "grid_governor_droop_pu", "grid_governor_tau_s"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if not 0 < self.initial_soc_pct < 100 or not 0 < self.target_soc_pct < 100:
            raise ValueError("Initial and target SoC must be strictly between 0 and 100")
        if self.loss_multiplier < 1 or min(self.damping_pu, self.kp_w_per_pct,
                                          self.ki_w_per_pct_s, self.transformer_r_pu,
                                          self.transformer_x_pu,
                                          self.grid_frequency_damping_pu) < 0:
            raise ValueError("Invalid loss multiplier, damping, PI gains, or resistance")
