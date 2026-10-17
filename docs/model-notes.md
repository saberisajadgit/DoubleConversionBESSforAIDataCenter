# Model assumptions and limitations

This reduced-order model studies active-power buffering, battery energy management and approximate frequency response. It supports engineering exploration and controller comparisons. Equipment-specific parameters and utility data are needed for site-specific predictions.

## System states and controls

The PCS/battery simulation integrates seven states: load angular-frequency deviation (rad/s), angle deviation (rad), inverter power (W), rectifier power (W), SoC (%), SoC-error integral (%·s), and filtered effective load (W).

Converter references are limited to 0–5.16 MW by default. Grid and load power-response time constants are 0.05 s and 0.02 s. Initial converter powers are 80% of rating; frequency and angle deviations start at zero.

Startup commands rated rectifier power until the first upward crossing of the SoC target, normally 82%. The SoC integral is held at zero during startup. After handover, filtered load feedforward and a saturation-aware SoC PI determine the rectifier reference. Default PI gains are 20,000 W/% and 5,000 W/(%·s).

Config uses a 5 s filter by default; the web app initially selects 10 s. Stronger filtering can reduce grid-power fluctuations while increasing battery energy excursions. Startup and SoC correction can still produce grid-power changes.

## Battery

- Full battery energy is 7.08 MWh. The default scale of 0.025 gives 0.177 MWh for accelerated SoC dynamics; use 1 for full capacity.
- Initial SoC is 60%. Positive battery power means charging: P_battery = P_grid - P_inverter.
- The illustrative 416S OCV curve passes through 1,040 V at 0%, 1,385 V at 82%, and 1,500 V at 100%. Lookup points and endpoint-to-SoC assignments are approximations, not manufacturer characterization.
- OCV is calculated from SoC for reporting. Dynamic DC voltage, battery resistance, current limits and electrochemical losses are not modeled.
- Integration stops at the first 0% or 100% SoC crossing. Continued operation at an energy boundary is not modeled.

## Load-side VSM

The normalized equation is:

    d(delta_omega)/dt = omega_nominal/Tj *
        [(P_inverter - P_effective_load)/S_base - D*delta_omega/omega_nominal]

Tj uses the 2H convention. D multiplies per-unit speed deviation. Config defaults are Tj = 5 s, D = 20 and droop = 0.5 Hz/pu. The web app initially selects Tj = 10 s and D = 1. These are configurable study settings rather than equipment-validated gains.

Voltage magnitude, reactive power, switching, PLL and current-control dynamics are absent. The integrated angle does not couple through network impedance to determine electrical power. Load shedding and voltage collapse are not modeled when demand exceeds inverter rating.

## Transformers and upstream utility

Both transformers have PCS-side star windings without neutral terminals and MV-side delta windings. Voltage bases are 690 V and 34.5 kV; transformer apparent-power base is assumed equal numerically to PCS active-power rating. The connection clock reference remains unconfirmed and no phase shift is applied.

Transformer resistance is assumed 0.005 pu and leakage reactance 0.075 pu. Their AC network dynamics are not coupled into the PCS/battery ODE. The transformer-drop diagnostic includes resistance only and assumes unity power factor.

The upstream grid is evaluated separately from rectifier import. PCC voltage uses a balanced, quasi-steady Thevenin equivalent. Frequency uses a linear regional swing/governor model, distinct from the load PCS VSM. Utility parameters are illustrative assumptions. These observations do not feed back into PCS limits or controls; local waveform frequency and PLL response are not calculated.

The direct-load comparison applies the same effective AI demand at the PCC without battery buffering. Both cases neglect converter/transformer losses and assume unity PCC power factor. The effective-load multiplier defaults to 1.0.

## Numerical method and comparisons

The PCS/battery model uses scipy.integrate.solve_ivp with Radau, rtol = 1e-6, state-specific absolute tolerances and maximum steps no larger than input sample spacing. Input power is linearly interpolated. Output includes startup and battery-boundary event times.

Summary fluctuation metrics exclude startup and five filter time constants, with the interval stated in the report. When comparing different filters, use the same input and a common evaluation interval. The plots retain startup transients.

Tests cover profile validation, balanced equilibrium, startup handover, battery energy accounting, fast-load buffering, grid-voltage circuit balance and utility-frequency response. An optional Streamlit smoke test checks that opening the app or changing presets does not automatically run the solver. These checks do not establish hardware or site validation.

See [the electrical model guide](electrical-model.md) for equations, utility parameters and the parallel-system extension roadmap.
