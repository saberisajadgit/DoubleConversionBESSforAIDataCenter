"""Portable interactive Plotly report and machine-readable run artifacts."""
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .grid import comparison_metrics


def write_report(result, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    d, c = result.columns, result.config
    titles = ["Microgrid frequency", "Power flows", "Battery power (+ charging)",
              "Battery state of charge", "Estimated stack OCV", "SoC error integral",
              "Rectifier loading", "Approximate resistive transformer drop",
              "34.5 kV grid PCC voltage · buffered vs direct load",
              "Utility frequency at PCC · illustrative regional model"]
    fig = make_subplots(rows=10, cols=1, shared_xaxes=True, subplot_titles=titles,
                        vertical_spacing=0.025)
    curves = [(1, "frequency_hz", "Frequency", "Hz"),
              (2, "grid_mw", "Grid rectifier", "MW"),
              (2, "inverter_mw", "Load inverter", "MW"),
              (2, "load_mw", "AI demand", "MW"),
              (2, "effective_load_mw", "Demand with losses", "MW"),
              (3, "battery_mw", "Battery", "MW"), (4, "soc_pct", "SoC", "%"),
              (5, "stack_ocv_v", "416S OCV estimate", "V"),
              (6, "integral_pct_s", "PI integral", "%·s"),
              (7, "grid_loading_pct", "Rectifier loading", "%"),
              (8, "transformer_drop_pct", "Resistive drop estimate", "%"),
              (9, "pcc_voltage_kv", "PCC voltage · buffered", "kV L-L RMS"),
              (9, "direct_pcc_voltage_kv", "PCC voltage · direct load", "kV L-L RMS"),
              (10, "grid_frequency_hz", "Utility frequency · buffered", "Hz"),
              (10, "direct_grid_frequency_hz", "Utility frequency · direct load", "Hz")]
    for row, key, name, unit in curves:
        fig.add_trace(go.Scatter(x=d["time_s"], y=d[key], name=name, mode="lines",
                                line=dict(dash="dot" if key.startswith("direct_") else "solid")), row=row, col=1)
        fig.update_yaxes(title_text=unit, row=row, col=1)
    for row, value in [(1, c.nominal_frequency_hz), (2, c.rated_power_w/1e6),
                       (3, 0), (4, c.target_soc_pct), (5, 1385), (7, 100),
                       (9, c.mv_voltage_ll_v/1000), (10, c.nominal_frequency_hz)]:
        fig.add_hline(y=value, line_dash="dash", line_color="#64748b", row=row, col=1)
    if result.startup_end_s is not None:
        fig.add_vline(x=result.startup_end_s, line_dash="dot", line_color="#059669")
    fig.update_layout(height=2800, template="plotly_white", hovermode="x unified",
                      margin=dict(t=180, b=50), legend=dict(orientation="h", y=1.02))
    fig.update_xaxes(title_text="Time (s)", row=10, col=1)
    metadata = dict(config=asdict(c), termination=result.termination,
                    startup_end_s=result.startup_end_s,
                    minimum_frequency_hz=float(d["frequency_hz"].min()),
                    maximum_frequency_hz=float(d["frequency_hz"].max()),
                    final_soc_pct=float(d["soc_pct"][-1]),
                    grid_comparison=comparison_metrics(result))
    (output/"run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    np.savetxt(output/"results.csv", np.column_stack(list(d.values())),
               delimiter=",", header=",".join(d), comments="")
    figure = fig.to_html(full_html=False, include_plotlyjs=True,
                         config={"responsive": True, "displaylogo": False})
    status = escape(result.termination)
    parameters = escape(json.dumps(metadata, indent=2))
    comparison = metadata["grid_comparison"]
    metric_html = f"<p>{escape(comparison['status'])}</p>"
    if "buffered" in comparison:
        metric_html += (f"<p>Comparison window: {comparison['window_start_s']:.2f}–"
                        f"{comparison['window_end_s']:.2f} s. Both cases use the same grid assumptions.</p>"
                        "<table><tr><th>Metric</th><th>Direct load</th><th>Buffered</th></tr>")
        for key, label in [("power_std_mw", "Grid power standard deviation (MW)"),
                           ("rms_ramp_mw_s", "Grid power RMS ramp (MW/s)"),
                           ("pcc_voltage_std_v", "PCC voltage standard deviation (V)"),
                           ("frequency_std_mhz", "Utility frequency standard deviation (mHz)")]:
            metric_html += (f"<tr><td>{label}</td><td>{comparison['direct'][key]:.5g}</td>"
                            f"<td>{comparison['buffered'][key]:.5g}</td></tr>")
        metric_html += "</table>"
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Double-conversion BESS simulation</title>
<style>body{{font:16px system-ui;max-width:1450px;margin:32px auto;padding:0 24px;color:#172033}}
aside{{background:#fff7df;padding:18px;border-radius:10px}}pre{{overflow:auto}}
table{{border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}</style></head>
<body><h1>Double-conversion BESS for an AI data center</h1>
<p>{status}. Final SoC: {metadata['final_soc_pct']:.2f}%.
VSM: Tj = {c.inertia_time_s:g} s, D = {c.damping_pu:g} (per-unit speed convention).</p>
<aside>Provisional reduced-order model. OCV is an assumed resting-voltage curve, not dynamic DC bus voltage.
Grid voltage and frequency use assumed utility parameters, not site measurements. Voltage is a balanced
quasi-steady unity-PF PCC solution; frequency is a regional swing/governor response, not local PLL frequency.
Transformer leakage remains outside the dynamic circuit. Direct load means the same effective AI demand
at the PCC without BESS or converter/transformer losses. Startup charging is included in all plots.
The grid is observed in post-processing; voltage/frequency do not feed back into PCS limits.</aside>
<h2>Grid buffering comparison</h2>
<p>Grid reference filter: {c.grid_power_filter_s:g} s. Assumed fault level:
{c.grid_short_circuit_va/1e6:g} MVA; X/R: {c.grid_x_over_r:g}.
Frequency-area base: {c.grid_frequency_base_va/1e6:g} MVA; H: {c.grid_inertia_h_s:g} s.
Dashed green markers show the end of startup charging.</p>
{metric_html}
{figure}<details><summary>Run parameters and metrics</summary><pre>{parameters}</pre></details>
</body></html>'''
    path = output/"report.html"
    path.write_text(html, encoding="utf-8")
    return path.resolve()
