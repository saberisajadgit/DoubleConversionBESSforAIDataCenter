AILoadProfile.csv is included for the online demonstration. Other raw files remain excluded from Git by default.

The supplied CSV uses `Time_s,Load_pu`. Pass an explicit power base using `--base-power-mw` to convert per-unit values to watts. The loader also supports `time_s,power_w`. Both formats require finite nonnegative power values and strictly increasing times.
