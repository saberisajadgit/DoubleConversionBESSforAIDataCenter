"""Local engineering workbench. Launch: python -m streamlit run app.py."""
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from double_conversion_bess.config import Config
from double_conversion_bess.dashboard import COLORS, export_bundle, line_chart, system_diagram
from double_conversion_bess.grid import comparison_metrics
from double_conversion_bess.profiles import read_profile
from double_conversion_bess.simulation import simulate

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="BESS Engineering Workbench", page_icon="⚡", layout="wide")
st.html('''<style>
.hero{padding:28px 32px;border-radius:18px;background:#14243b;color:white;margin-bottom:24px}
.hero p{color:#b8cbd9;margin:8px 0 0;max-width:850px;font-size:16px}
.hero h1{font-size:34px;color:white;margin:6px 0;letter-spacing:-1px}
.eyebrow{font-size:11px;letter-spacing:2px;color:#70d0c9;font-weight:700}
</style><div class="hero"><div class="eyebrow">POWER SYSTEMS / SIMULATION LAB</div>
<h1>Double-conversion BESS</h1><p>Explore how energy storage buffers an AI data center’s power demand.
Configure the system, run scenarios, and inspect the utility and microgrid response.</p></div>''')

if "runs" not in st.session_state:
    st.session_state.runs = []

with st.sidebar:
    st.markdown("### Simulation setup")
    st.caption("One unit · balanced active-power model")
    preset_name = st.selectbox("Starting configuration", ["10 s filter · Tj 10 / D 1", "5 s filter · Tj 10 / D 1", "Original VSM defaults"])
    initial = asdict(Config())
    if preset_name != "Original VSM defaults":
        initial.update(inertia_time_s=10.0, damping_pu=1.0,
                       grid_power_filter_s=10.0 if preset_name.startswith("10") else 5.0)
    uploaded_config = st.file_uploader("Optional saved configuration", type=["json"])
    if uploaded_config:
        try:
            overrides = json.loads(uploaded_config.getvalue())
            initial = asdict(Config(**overrides))
        except (ValueError, TypeError) as exc:
            st.error(f"Invalid configuration: {exc}")
            st.stop()
    setup_key = sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest()[:10]
    with st.form("simulation_setup"):
        label = st.text_input("Scenario name", value=preset_name)
        upload = st.file_uploader("AI load CSV (optional)", type=["csv"])
        st.caption("Uses data/raw/AILoadProfile.csv when no file is uploaded. Accepts Time_s,Load_pu or time_s,power_w.")
        options = dict(initial)
        groups = {
            "Grid buffering": ["grid_power_filter_s", "rated_power_w", "initial_soc_pct", "target_soc_pct"],
            "Battery & PCS": ["battery_energy_mwh", "battery_scale", "rectifier_tau_s", "inverter_tau_s", "loss_multiplier"],
            "Load GFM / VSM": ["inertia_time_s", "damping_pu", "droop_hz", "nominal_frequency_hz"],
            "SoC controller": ["kp_w_per_pct", "ki_w_per_pct_s"],
            "Transformers": ["pcs_voltage_ll_v", "mv_voltage_ll_v", "transformer_r_pu", "transformer_x_pu"],
            "Utility assumptions": ["grid_short_circuit_va", "grid_x_over_r", "grid_frequency_base_va", "grid_inertia_h_s", "grid_frequency_damping_pu", "grid_governor_droop_pu", "grid_governor_tau_s"],
        }
        labels = {
            "grid_power_filter_s": ("Grid power filter", "s", 1),
            "rated_power_w": ("PCS rating / load pu base", "MW", 1e6),
            "initial_soc_pct": ("Initial SoC", "%", 1), "target_soc_pct": ("Target SoC", "%", 1),
            "battery_energy_mwh": ("Full battery energy", "MWh", 1), "battery_scale": ("Battery energy scale", "ratio", 1),
            "rectifier_tau_s": ("Grid PCS response time", "s", 1), "inverter_tau_s": ("Load PCS response time", "s", 1),
            "loss_multiplier": ("Effective demand multiplier", "ratio", 1),
            "inertia_time_s": ("Load VSM Tj (=2H)", "s", 1), "damping_pu": ("Load VSM damping D", "pu speed convention", 1),
            "droop_hz": ("Load P–f droop", "Hz/pu", 1), "nominal_frequency_hz": ("Nominal frequency", "Hz", 1),
            "kp_w_per_pct": ("SoC proportional gain", "kW/%", 1000), "ki_w_per_pct_s": ("SoC integral gain", "kW/(%·s)", 1000),
            "pcs_voltage_ll_v": ("PCS line-line voltage", "V", 1), "mv_voltage_ll_v": ("MV line-line voltage", "kV", 1000),
            "transformer_r_pu": ("Transformer resistance", "%", 0.01), "transformer_x_pu": ("Transformer leakage X", "%", 0.01),
            "grid_short_circuit_va": ("Utility fault level", "MVA", 1e6), "grid_x_over_r": ("Utility X/R", "ratio", 1),
            "grid_frequency_base_va": ("Frequency-area power base", "MVA", 1e6), "grid_inertia_h_s": ("Utility inertia H", "s", 1),
            "grid_frequency_damping_pu": ("Utility damping", "pu speed convention", 1),
            "grid_governor_droop_pu": ("Governor droop", "%", 0.01), "grid_governor_tau_s": ("Governor response", "s", 1),
        }
        for group, fields in groups.items():
            with st.expander(group, expanded=group == "Grid buffering"):
                for key in fields:
                    title, unit, factor = labels[key]
                    options[key] = st.number_input(f"{title} ({unit})", value=float(initial[key]/factor),
                                                   format="%.5f", key=f"{setup_key}_{key}")*factor
        run_clicked = st.form_submit_button("Run simulation", type="primary", use_container_width=True)
    st.caption("Simulations run only when you press Run. Adjustments do not overwrite existing output files.")

if run_clicked:
    try:
        config = Config(**options)
        profile_bytes = upload.getvalue() if upload else (ROOT/"data/raw/AILoadProfile.csv").read_bytes()
        t, power = read_profile(StringIO(profile_bytes.decode("utf-8-sig")), base_power_w=config.rated_power_w)
        if len(t) > 100000 or len(t) > 1 and (t[-1]-t[0])/np.min(np.diff(t)) > 200000:
            raise ValueError("Profile is too large or has excessively close timestamps for this interactive workbench")
        with st.spinner("Solving PCS and battery dynamics, then evaluating the utility response…"):
            result = simulate(t, power, config)
            html, bundle = export_bundle(result, profile_bytes)
        stamp = datetime.now().strftime("%H:%M:%S")
        record = dict(name=f"{label.strip() or 'Scenario'} · {stamp}", result=result,
                      html=html, bundle=bundle, profile_hash=sha256(profile_bytes).hexdigest(),
                      samples=len(t), duration=float(t[-1]-t[0]))
        st.session_state.runs = (st.session_state.runs + [record])[-4:]
        st.session_state.selected_run = len(st.session_state.runs)-1
        st.success("Simulation complete. Results and downloads are ready.")
    except (OSError, UnicodeError, ValueError, TypeError, RuntimeError) as exc:
        st.error(f"Simulation could not complete: {exc}")

runs = st.session_state.runs
record = None
if runs:
    selected = st.selectbox("Saved in this session", range(len(runs)),
                            format_func=lambda i: runs[i]["name"], key="selected_run")
    record = runs[selected]
    config = record["result"].config
else:
    try:
        config = Config(**options)
    except (ValueError, TypeError):
        config = Config()

overview, results_tab, comparison_tab, models_tab, source_tab = st.tabs([
    "System configuration", "Simulation results", "Compare scenarios", "Models & equations", "Source & downloads"])

with overview:
    st.subheader("From utility to AI load")
    st.caption("Diagram shows the selected completed run, or the setup preview before the first run.")
    st.html(system_diagram(config))
    columns = st.columns(4)
    columns[0].metric("PCS rating", f"{config.rated_power_w/1e6:g} MW")
    columns[1].metric("Grid smoothing", f"{config.grid_power_filter_s:g} s")
    columns[2].metric("Modeled battery", f"{config.battery_energy_mwh*config.battery_scale:.3f} MWh")
    columns[3].metric("SoC target", f"{config.target_soc_pct:g}%")
    st.info("Provisional engineering model. Utility voltage/frequency depend on assumed grid parameters. Transformer AC dynamics, voltage control, current limits and parallel-unit sharing are not solved.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Energy buffering")
        st.markdown("The grid rectifier receives filtered demand plus SoC correction. The battery absorbs the difference while the GFM PCS supplies the AI load. Startup charges at rated grid power until the SoC target is reached.")
    with right:
        st.markdown("#### Measurement boundary")
        st.markdown("PCC voltage is measured in the model on the utility side of the grid transformer. Regional utility frequency is modeled separately from load-side VSM frequency. The two AC networks are connected through the DC system.")
    if not runs:
        st.info("Ready to begin: select a configuration in the sidebar and press Run simulation.")

with results_tab:
    if not record:
        st.info("Your interactive plots will appear here after the first run.")
    else:
        result = record["result"]
        d = result.columns
        st.subheader(record["name"])
        st.caption(f"{result.termination} · {record['samples']:,} input samples · {record['duration']:g} s profile. Displayed settings belong to this completed run.")
        cards = st.columns(4)
        cards[0].metric("Final SoC", f"{d['soc_pct'][-1]:.2f}%")
        cards[1].metric("SoC range", f"{d['soc_pct'].min():.1f}–{d['soc_pct'].max():.1f}%")
        cards[2].metric("Peak battery power |P|", f"{np.abs(d['battery_mw']).max():.2f} MW")
        cards[3].metric("Grid PCC minimum", f"{d['pcc_voltage_kv'].min():.3f} kV")
        sections = [
            ("Grid impact", [([("grid_mw", "Buffered grid import"), ("direct_grid_mw", "Direct AI demand")], "MW", "Utility power"),
                             ([("pcc_voltage_kv", "Buffered"), ("direct_pcc_voltage_kv", "Direct load")], "kV L-L RMS", "Utility-side PCC voltage"),
                             ([("grid_frequency_hz", "Buffered"), ("direct_grid_frequency_hz", "Direct load")], "Hz", "Regional utility frequency · assumed model")]),
            ("Battery & microgrid", [([("battery_mw", "Battery (+ charging)")], "MW", "Battery energy exchange"),
                                     ([("soc_pct", "Battery SoC")], "%", "State of charge"),
                                     ([("frequency_hz", "Load-side GFM frequency")], "Hz", "Microgrid VSM frequency")]),
            ("Diagnostics", [([("stack_ocv_v", "Estimated OCV")], "V", "416S illustrative OCV"),
                              ([("integral_pct_s", "SoC PI integral")], "%·s", "SoC controller"),
                              ([("grid_loading_pct", "Grid rectifier")], "%", "PCS loading"),
                              ([("transformer_drop_pct", "Resistive drop")], "%", "Transformer diagnostic · R only"),
                              ([("inverter_mw", "Load inverter"), ("effective_load_mw", "Effective demand"), ("filtered_load_mw", "Filtered demand")], "MW", "Load tracking & scheduling")]),
        ]
        view = st.radio("Plot group", [item[0] for item in sections], horizontal=True)
        for title, charts in sections:
            if title == view:
                for i, (series, unit, heading) in enumerate(charts):
                    st.plotly_chart(line_chart(result, series, unit, heading), use_container_width=True,
                                    key=f"plot_{selected}_{view}_{i}")
        metrics = comparison_metrics(result)
        st.markdown("#### Buffered versus direct-load metrics")
        st.caption(metrics["status"])
        if "buffered" in metrics:
            st.caption(f"Matched interval: {metrics['window_start_s']:.2f}–{metrics['window_end_s']:.2f} s. Startup remains visible in the charts; dashed vertical lines mark handover.")
            st.dataframe([dict(case=case, **metrics[case]) for case in ("direct", "buffered")], hide_index=True)

with comparison_tab:
    st.subheader("Compare smoothing scenarios")
    st.caption("Up to four completed runs are kept in browser-session memory. Export any runs you want to preserve.")
    if len(runs) < 2:
        st.info("Run a second scenario, for example with a 5 s rather than 10 s filter. Then compare the curves here.")
    else:
        chosen = st.multiselect("Scenarios", range(len(runs)), default=list(range(len(runs))),
                                format_func=lambda i: runs[i]["name"])
        if len({runs[i]["profile_hash"] for i in chosen}) > 1:
            st.warning("These scenarios use different input files; this is not a controlled filter-only comparison.")
        quantity = st.selectbox("Quantity", ["grid_mw", "battery_mw", "soc_pct", "pcc_voltage_kv", "grid_frequency_hz"])
        fig = go.Figure()
        for j, i in enumerate(chosen):
            r = runs[i]["result"]
            fig.add_trace(go.Scatter(x=r.columns["time_s"], y=r.columns[quantity], name=runs[i]["name"],
                                    line=dict(color=COLORS[j % len(COLORS)])))
        fig.update_layout(template="plotly_white", height=450, hovermode="x unified", xaxis_title="Time (s)", yaxis_title=quantity,
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Overlay uses each run’s own time axis. Compare the same interval and input, and check all settings before attributing a difference to the filter.")
        st.dataframe([dict(scenario=runs[i]["name"], **asdict(runs[i]["result"].config)) for i in chosen], hide_index=True)

with models_tab:
    st.markdown((ROOT/"docs/electrical-model.md").read_text(encoding="utf-8"))

with source_tab:
    st.subheader("Inspect the model. Keep the evidence.")
    if record:
        left, middle, right = st.columns(3)
        left.download_button("Download HTML report", record["html"], "bess-report.html", "text/html")
        middle.download_button("Download run bundle", record["bundle"], "bess-run.zip", "application/zip")
        right.download_button("Download settings", json.dumps(asdict(record["result"].config), indent=2), "config.json", "application/json")
        st.caption("Run bundle contains the standalone HTML, numeric CSV, metadata, configuration and original input CSV. Uploaded data is included only in your local export.")
    sources = sorted((ROOT/"src/double_conversion_bess").glob("*.py")) + [ROOT/"app.py"]
    source = st.selectbox("Python source", sources, format_func=lambda p: p.name)
    st.code(source.read_text(encoding="utf-8"), language="python")
    with st.expander("Model provenance & assumptions"):
        st.markdown((ROOT/"docs/model-notes.md").read_text(encoding="utf-8"))

st.caption("BESS Engineering Workbench · Local simulation · No hardware connection · No automatic publication")
