"""Transformer nameplate and positive-sequence series equivalent.

Both grid and load transformers use the same provisional rating/ratio.
The energy simulation currently uses only the resistive drop diagnostic.
R+jX and inductance are exposed for a future AC network model, not coupled
into the present ODE. No zero-sequence, core or saturation model is implied.
"""
from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class Transformer:
    rating_va: float
    pcs_voltage_ll_v: float
    mv_voltage_ll_v: float
    resistance_pu: float
    leakage_reactance_pu: float
    nominal_hz: float
    pcs_connection: str = "star, neutral not brought out"
    mv_connection: str = "delta"
    reported_vector_group: str = "PCS star / MV delta; clock reference unconfirmed"

    @property
    def series_impedance_pu(self):
        return complex(self.resistance_pu, self.leakage_reactance_pu)

    @property
    def pcs_base_impedance_ohm(self):
        """Three-phase base: Z_base = V_LL_base² / S_3phase_base."""
        return self.pcs_voltage_ll_v**2 / self.rating_va

    @property
    def pcs_leakage_inductance_h(self):
        """Total leakage referred to PCS side: L = X_pu*Z_base/(2*pi*f)."""
        return self.leakage_reactance_pu*self.pcs_base_impedance_ohm/(2*pi*self.nominal_hz)

    def resistive_drop_pct(self, active_power_w):
        """Approximate unity-PF diagnostic: 100 * R_pu * P_pu."""
        return 100*self.resistance_pu*active_power_w/self.rating_va


def transformer_from_config(config):
    return Transformer(config.rated_power_w, config.pcs_voltage_ll_v,
                       config.mv_voltage_ll_v, config.transformer_r_pu,
                       config.transformer_x_pu, config.nominal_frequency_hz)
