AILoadProfile.csv is included in Git for the online demonstration, as authorized by the project owner. Other raw files remain excluded by default.

The supplied CSV uses `Time_s,Load_pu`. Pass an explicit power base using `--base-power-mw` to convert per-unit values to watts. The loader also supports `time_s,power_w`. Both formats require finite nonnegative power values and strictly increasing times.
