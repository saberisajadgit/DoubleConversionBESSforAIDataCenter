# Electrical engineer's guide

## One double-conversion unit

```text
Utility MV bus, 34.5 kV
  | MV delta winding
Grid transformer: ideal ratio + series R+jX (AC equivalent specified only)
  | PCS star winding, no neutral terminal; assumed 690 V line-line
Grid PCS: grid-following active rectifier
  |
Shared DC bus + 416S LFP battery
  |
Load PCS: grid-forming inverter, reduced VSM frequency model
  | PCS star winding, no neutral terminal; assumed 690 V line-line
Load transformer: ideal ratio + series R+jX (AC equivalent specified only)
  | MV delta winding
Isolated load MV bus, assumed 34.5 kV
  |
AI load (downstream distribution not modeled)
```

The two MV buses are separate AC networks linked through the DC system. Both transformer ratios are currently assumed identical. The supplied power profile is applied directly without downstream transformer or cable losses. Confirm the load-side MV voltage and transformer MVA ratings before introducing AC network calculations.

## Where each component lives

| Component | Python file | Present representation |
|---|---|---|
| Grid rectifier / load inverter | `pcs.py` | Saturated active-power references and first-order power response |
| GFM virtual synchronous machine | `pcs.py` | Normalized swing equation and angle integration |
| Energy management | `ems.py` | Maximum-power startup then filtered load feedforward + SoC PI |
| Upstream utility | `grid.py` | Quasi-steady PCC voltage and independent regional frequency response |
| Battery | `battery.py` | Energy balance and illustrative 416S OCV curve |
| Grid/load transformer | `transformer.py` | Connection metadata and series-equivalent parameters; only grid resistive-drop diagnostic is evaluated |
| Parameters and units | `config.py` | One unit's ratings and controller constants |
| System assembly | `simulation.py` | Connects component equations and calls Radau |
| Results | `report.py` | Plotly HTML, CSV and run metadata |

## PCS model

Each PCS is an averaged controlled active-power source:

    tau * dP/dt = clip(P_reference, 0, P_rated) - P

Grid rectifier tau = 0.05 s; load inverter tau = 0.02 s; each rating is 5.16 MW. The load PCS includes a P-f reference correction:

    P_inverter_reference = P_load_effective - (P_rated / droop_Hz) * delta_f_Hz

The present model does not solve PWM, filter currents, PLL, dq current loops, modulation saturation, Q-V droop, or AC voltage amplitude. Calling it GFM refers to its simplified frequency/angle behavior, not a complete voltage-source converter implementation.

## VSM convention and settings

    delta_omega_pu = (omega - omega_nominal) / omega_nominal
    Tj * d(delta_omega_pu)/dt = (P_inverter - P_load_effective)/P_rated
                               - D * delta_omega_pu
    d(delta_theta)/dt = omega - omega_nominal

Tj is in seconds and uses the convention Tj = 2H. D multiplies per-unit speed deviation; a D value from another equation cannot be copied without checking its units. Power imbalance here is inverter output minus load demand; this is a reduced frequency surrogate, not an internal voltage angle coupled through network impedance.

The original working defaults remain Tj = 5 s and D = 20. `configs/vsm_tj10_d1.json` selects Tj = 10 s and D = 1 under this exact convention. P-f droop is still active, so total response is not determined by D alone.

## Transformer model and 7.5%

The user's description is PCS-side star, MV-side delta, no neutral brought out. The reported label `yD1` is retained as supplied. Conventional nameplate notation references the HV winding first; verify the clock reference and terminal phasors before assigning a numerical phase shift. No clock phase shift is currently applied.

Interpret the supplied 7.5% inductance as total leakage reactance X = 0.075 pu at nominal frequency, pending nameplate confirmation. If 7.5% instead specifies impedance magnitude, X must be recovered from X = sqrt(Z²-R²).

    Z_base = V_LL_base² / S_three_phase_base
    Z_series = (R_pu + j X_pu) * Z_base
    L_leakage = X_pu * Z_base / (2*pi*f_nominal)

R = 0.005 pu is inherited from the earlier description and remains assumed. Transformer VA base is provisionally 5.16 MVA, distinct conceptually from the PCS MW rating. The exposed impedance is a positive-sequence equivalent referred to the PCS side, not an individual delta winding's impedance.

The present ODE has no AC voltage/current network: leakage reactance, turns ratio and vector group are specified but do not influence its frequency or energy trajectories. The plotted grid transformer drop remains the unity-power-factor estimate 100*R_pu*P_grid_pu. It does not include reactive drop. Load-transformer voltage drop, losses, zero sequence, grounding, inrush, saturation and faults are not solved.

## Battery and EMS

    P_battery = P_grid_PCS - P_load_PCS       (+ means charging)
    dSoC_percent/dt = 100 * P_battery / E_battery_joules
    E_battery_joules = 7.08 * battery_scale * 3.6e9

The default battery_scale = 0.025 accelerates energy dynamics; full-size capacity uses 1. OCV is a diagnostic and does not control a dynamic DC voltage state.

At startup the grid PCS is commanded to maximum power until SoC reaches 82%. After a one-time handover, its reference is filtered effective load plus SoC PI correction. The PI integral freezes when further integration would increase saturation.

    tau_filter * dP_filtered/dt = P_load_effective - P_filtered
    P_grid_reference = P_filtered + Kp*SoC_error + Ki*integral

The default filter time constant is 5 s. Fast load changes are supplied by the battery instead of being passed directly to the rectifier. SoC correction, converter limits, and startup can still cause grid-side transients; perfect isolation is not assumed. Startup is still max-power charging, not a smooth grid ramp. A filter state runs throughout startup so it is ready at handover.

## Grid-side measurements at the 34.5 kV PCC

```text
Utility equivalent internal source E, f_region
       |
Upstream grid impedance Z_grid = R_grid + jX_grid
       |
34.5 kV PCC <-- voltage and regional-frequency observation point
       |
Grid transformer (its 7.5% leakage is separate from Z_grid)
       |
Rectifier -> DC battery -> load inverter -> AI load
```

The new grid model is evaluated after the energy simulation using the imported power. It does not feed back into PCS power capability, angle, battery behavior or PLL dynamics. Transformer losses are neglected in PCC power. Frequency is an assigned regional response at the PCC, not a calculation of local phasor-angle derivative or waveform frequency.

The utility model uses assumed parameters, all editable through Config / a JSON override:

| Parameter | Illustrative default | Role |
|---|---:|---|
| grid_short_circuit_va | 200 MVA | Upstream voltage-source impedance magnitude |
| grid_x_over_r | 10 | Splits source impedance into resistance/reactance |
| grid_frequency_base_va | 1000 MVA | Aggregate regional frequency power base, independent of fault level |
| grid_inertia_h_s | 5 s | Regional inertia H, distinct from the load PCS Tj |
| grid_frequency_damping_pu | 1 | Load-frequency damping |
| grid_governor_droop_pu | 0.05 | Primary generation governor droop |
| grid_governor_tau_s | 5 s | Governor response time |

Voltage is a balanced, quasi-steady high-voltage solution at unity PCC power factor:

    |Z_grid| = V_LL_nominal² / S_short_circuit
    R_grid = |Z_grid| / sqrt(1 + (X/R)²)
    E_phase² = (V_phase + R_grid*P/(3*V_phase))²
               + (X_grid*P/(3*V_phase))²

It does not model switching ripple, electromagnetic transients, unbalance or Q control. Source voltage magnitude is fixed. A non-solvable operating point raises an error rather than producing a fabricated voltage.

Frequency uses a separate linear single-area swing/governor model:

    x = (f - f_nominal)/f_nominal
    delta_p_load = (P_import - P_import_initial)/S_frequency_base
    2H * dx/dt = p_mechanical - delta_p_load - D_grid*x
    tau_governor * dp_mechanical/dt = -x/R_governor - p_mechanical

Each case starts in equilibrium at its initial import. No secondary frequency restoration is included: sustained load changes can leave a droop offset. In an infinite-grid limit, the grid frequency is fixed; BESS does not directly set utility frequency. These illustrative results should not be interpreted as a measured prediction for a real interconnection.

The report compares actual rectifier import against the same effective AI load directly connected at the PCC without storage. Both use the same upstream grid parameters and assume unity PF and negligible transformer/converter losses. This is a reference scenario, not an uncontrolled double-conversion system.

All startup transients remain visible in the plots. Summary fluctuation metrics use a clearly stated common interval starting five filter time constants after startup handover (or after the initial time for an already-charged system). Standard deviations are about each case's own mean, not voltage/frequency limit compliance. RMS power ramps use a common approximately 0.1 s sampling interval; they are not instantaneous converter slew limits. If there is no usable regulation interval, the report says so. Battery energy, finite headroom and SoC control mean smoothing performance is not guaranteed for every profile.

## Future parallel units

For ten identical units, each has its own two transformers, two PCSs, battery, controller and states. Grid-transformer MV windings connect to a common utility bus; load-transformer MV windings connect to a separate common isolated load bus. There is no AC tie between those two common buses.

With equal sharing, ten units provide 51.6 MW aggregate converter capacity and ten times the battery energy. For a tenfold load, each unit sees the original per-unit loading. This is a useful aggregate sanity check, not a parallel-network simulation.

Actual sharing requires a common AC network solution with transformer R+jX, voltage magnitudes, synchronized angles, reactive-power control and consistent vector-group phase shifts. Circulating currents and unequal sharing cannot be predicted by running ten independent copies or simply multiplying the rating. Those network equations are a future model extension; parallel operation is not yet implemented.

## References

- [MathWorks: per-unit system and transformer bases](https://www.mathworks.com/help/simscape-electrical/ug/per-unit-system-of-units.html)
- [MathWorks: three-phase transformer equivalent circuit](https://www.mathworks.com/help/simscape-electrical/ref/twowindingtransformerthreephase.html)
- [ABB: winding symbols, neutral terminals and clock notation](https://library.e.abb.com/public/7dca4ffad2206d36c1257be30048d4be/DAHandbook_Section_3_Power_distribution_systems_757959_ENa.pdf)
