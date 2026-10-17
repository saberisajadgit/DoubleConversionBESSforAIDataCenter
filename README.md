# DoubleConversionBESSforAIDataCenter

Python project for studying a grid rectifier, shared LFP battery/DC bus, and grid-forming inverter supplying an AI data center.

## Run online — no installation required

**[Launch the interactive online model →](https://doubleconversionbessforaidatacenter-4ayyslw7fjymiy5g6l92vx.streamlit.app/)**

1. Open the app and choose a starting configuration in the sidebar.
2. Use the included AI load profile or upload your own CSV. Adjust the engineering parameters as needed.
3. Press **Run simulation**, then open **Simulation results** to explore power flows, battery SoC, and grid-side voltage and frequency.
4. Run another scenario to compare smoothing settings, or download reports and data from **Source & downloads**.

The app includes model equations and a source-code viewer. The default scenario uses a 10-second grid-power filter, load-side VSM Tj = 10 s and D = 1, and scaled battery energy. This is a provisional engineering model; utility parameters and several component characteristics are assumed. See [the electrical model guide](docs/electrical-model.md) for scope and limitations.

## Model scope

A reduced-order simulation of active-power buffering, battery energy management and approximate frequency response. It includes an AI load profile and configurable component and utility parameters. See [model assumptions and limitations](docs/model-notes.md) before interpreting results.

## Setup in Anaconda Prompt

```bat
git clone https://github.com/saberisajadgit/DoubleConversionBESSforAIDataCenter.git
cd DoubleConversionBESSforAIDataCenter
conda env create -f environment.yml
conda activate double-conversion-bess
bess-ai --help
python -m pytest
```

For later dependency changes: `conda env update -f environment.yml --prune`.

## Load data

The included file under `data/raw/` uses `Time_s,Load_pu`. Specify the per-unit power base explicitly. The example below uses 5.16 MW. For other profiles, use their corresponding power base. SI input with `time_s,power_w` is also supported and needs no power base.

```bat
bess-ai validate-profile data/raw/AILoadProfile.csv --base-power-mw 5.16
```

## Layout

```text
src/double_conversion_bess/  Importable package and command line
tests/                       Input validation checks
data/raw/                    Included AI load CSV; other raw inputs ignored
outputs/                     Generated results (Git ignored)
docs/                        Electrical equations, assumptions and limitations
environment.yml              Conda environment
pyproject.toml               Package metadata and installation
```

## Run the simulation

For the circuit, each component's equations, parameter units and parallel-unit roadmap, start with [the electrical model guide](docs/electrical-model.md).

## Local web application

In the activated Conda environment, install Streamlit once and launch from this project folder:

```bat
python -m pip install "streamlit>=1.57"
python -m streamlit run app.py
```

Open the local address printed by Streamlit (normally http://localhost:8501). Stop the app with Ctrl+C in its terminal. For an explicitly local-only listener, launch with `python -m streamlit run app.py --server.address localhost`. Alternatively, use the hosted model linked above.

The workbench provides:

- A responsive system block diagram with electrical connections and ratings.
- Editable filter, battery, PCS, VSM, SoC PI, transformer and utility parameters, grouped by component with engineering units.
- The bundled load profile or an uploaded CSV; optional saved JSON configuration import.
- Explicit Run control, Plotly results grouped by grid impact, battery/microgrid and diagnostics.
- Up to four completed scenarios retained per session, curve overlays and configuration comparisons.
- Downloadable standalone HTML, settings, and a ZIP with results CSV, run metadata and input data.
- In-app model equations, limitations and a read-only Python source browser.

The initial selection is the latest 10 s filter / Tj 10 / D 1 case. Changes run only on submission. Results remain tied to their completed run's configuration. Session history is not permanent; export runs before closing the session or restarting the server. The interface uses the existing solver and does not change its electrical assumptions.

After installing Streamlit, `python -m pytest` also includes an optional UI smoke check.

## Command-line simulation

In the activated project environment:

```bat
python -m pytest
bess-ai simulate data/raw/AILoadProfile.csv --base-power-mw 5.16
start "" "outputs\latest\report.html"
```

Outputs: `report.html` (interactive ten-panel report with embedded Plotly JavaScript for offline viewing), `results.csv`, and `run.json` (parameters and metrics). Repeating a run overwrites these files; use `--output outputs/run02` to preserve another run.

The EMS now filters the load feedforward with a 5 s time constant, so the battery buffers fast demand changes. New plots compare buffered and direct-load 34.5 kV PCC voltage and regional utility frequency using an explicitly assumed finite-strength grid. Grid frequency is distinct from the load PCS VSM frequency. See the electrical model guide for the utility equations, defaults, comparison window, and limitations. There is no site-validated grid data yet, and the upstream network is an observation model without feedback into the PCS.

Use `--battery-scale 1` for full 7.08 MWh capacity, or the default 0.025 for accelerated SoC dynamics. A JSON object supplied with `--config path.json` can override fields in `Config`; rated power must match the explicit CLI base. The assumed input interpolation is linear.

To select Tj = 10 s and D = 1 under the documented normalized VSM convention:

```bat
bess-ai simulate data/raw/AILoadProfile.csv --base-power-mw 5.16 --config configs/vsm_tj10_d1.json --output outputs/vsm_tj10_d1
```

Modules separate configuration, battery OCV, converter/EMS equations and solver, and HTML reporting. No notebook or Matplotlib is required.

## Source repository

The source and demonstration load profile are published on [GitHub](https://github.com/saberisajadgit/DoubleConversionBESSforAIDataCenter). Dependencies are specified but not locked. No open-source license has yet been selected.

## Online deployment

Publish this project folder as the repository root (so app.py, src/, cloud/, docs/ and data/ are at the top level).

1. Create an empty GitHub repository named DoubleConversionBESSforAIDataCenter. Leave its README, license and .gitignore initialization unchecked to avoid conflicts with this project.
2. Upload the project using Git, including hidden .streamlit/ configuration files and the now-allowed data/raw/AILoadProfile.csv. Exclude generated output, caches and environments through .gitignore.
3. Sign in to https://share.streamlit.io/ with GitHub and create an app from this repository and its main branch.
4. Set the main file path to `cloud/streamlit_app.py` and choose Python 3.12 in advanced settings.
5. Deploy and use the generated app URL to test the default profile, Run button, charts and downloads.

The cloud entry point uses cloud/requirements.txt, which takes priority over the root Conda file because it sits beside the entry point. It loads the same app and models as the local version. The source checkout provides the Python package through src/. No API key or other secret is required. The server address is left to the hosting platform.

Shared hosting compute limits can affect solver runtime; start with the bundled 213-second profile. Session history is temporary, and the included source and load profile are public.
