# Model transcription status

The supplied photographs are source reference material. They do not include the beginning of the original script. The implemented provisional model does not claim exact reproduction.

## Implemented assumptions and deliberate changes

- Per-unit load base defaults in the documented command to 5.16 MW, not independently confirmed from the profile metadata.
- Battery energy is 7.08 MWh times 0.025, initially 60% SoC. Converter states initially equal 80% rating.
- Missing loss multiplier is assumed 1.0. Conversion losses, current limits, battery resistance, and reactive power are not modeled.
- Frequency uses d(omega)/dt = omega_nom/Tj * [(P_gfm-P_effective)/S_base - D_pu*omega/omega_nom], Tj=5 s, D_pu=20, and droop=0.5 Hz per pu. Damping and droop are assumed. This replaces the unavailable J_load definition with an explicitly normalized model.
- Rectifier startup ends once at the first upward crossing of 82% SoC; the integral is held at zero during startup. PI then uses conditional integration at actuator saturation. These are deliberate corrections to the visible re-entering startup branch and integral accumulation.
- Integration stops at the first 0% or 100% SoC crossing instead of hiding boundary violations by clipping plots. Continued operation at a battery boundary is not modeled.
- The 416S illustrative OCV curve passes through 1,040 V at 0%, 1,385 V at 82%, and 1,500 V at 100%. Intermediate points are assumptions, not manufacturer data. The endpoint voltage-to-SoC assignment is provisional.
- Resistive transformer drop is estimated as R_pu*P_grid_pu, R_pu=0.005, assuming unity power factor. Reactance and upstream network dynamics are absent.
- Radau uses maximum steps no larger than the input sample spacing, rtol=1e-6, and linear profile interpolation. Results include event timestamps.
- Battery net power is positive for charging; inverter frequency represents the reduced swing model even when demand exceeds inverter rating. Load shedding and voltage collapse are not modeled.

Tests cover input validation, balanced steady state, startup handover, and integrated battery energy accounting. The user runs these locally; implementation has not yet been execution-verified.

## Visible implementation

- The photographed baseline has six states: angular-frequency deviation, angle deviation, GFM power, GFL power, SoC in percent, and SoC-error integral. The current implementation adds a seventh state for filtered grid load feedforward.
- Grid and load converter references clipped to 0–5.16 MW; first-order time constants 0.05 s and 0.02 s respectively.
- Below 82% SoC the rectifier reference is maximum power and the error integral continues accumulating.
- Otherwise its reference is effective load plus PI correction; Kp = 20,000 W per percentage point and Ki = 5,000 W per percentage-point-second.
- The visible integral freeze condition is SoC >= 99% or absolute error < 0.1 percentage points. This is not saturation-aware anti-windup.
- Battery power is GFL minus GFM; positive means charging. SoC derivative is 100 times battery power divided by capacity in joules.
- SoC derivative is frozen for outward motion at 0% and 100%. This alone does not enforce battery power feasibility or exact numerical bounds.
- Frequency derivative is (GFM power - effective load - D_load * angular-frequency deviation) / J_load.
- Initial state: [0, 0, 0.8*S_base, 0.8*S_base, 60, 0]. Solver: solve_ivp with Radau.
- Eight panels: frequency, converter/load powers, battery power, SoC, OCV-derived stack voltage, integral state, rectifier loading, and estimated transformer voltage drop.

## Required original definitions

Obtain the actual Python source or missing opening section to recover:

- J_load calculation and damping D_load, including units and normalization.
- Delta_f_rated and loss_multiplier.
- Battery scaling, base energy conversion, and the exact cell OCV lookup points.
- Transformer voltage/impedance bases and R_mvt calculation.
- CSV column selection, units, interpolation, and time bounds.

The background description mentions 416S LFP, 7.08 MWh unscaled capacity, nominal 60 Hz, 34.5 kV utility, and 690 V load bus. These remain reference claims pending comparison with the source.

## Items to assess before scientific use

The SoC-based voltage shown is an OCV estimate, not a dynamic DC-link voltage model. The startup branch re-enters whenever SoC falls below target; it is not a latched startup phase. Integrating throughout startup can produce a large handover transient. Clipping inverter power does not represent unmet-load protection. The photographed transformer drop equation uses active power and resistance only; it does not establish isolation from grid transients. These issues should be evaluated explicitly after reproducing the original baseline.
