"""Reusable presentation helpers for the local engineering application."""
from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

import plotly.graph_objects as go

from .report import write_report


COLORS = ["#087f8c", "#e69243", "#7763b5", "#3373b6"]


def line_chart(result, series, unit, title):
    fig = go.Figure()
    for i, (key, name) in enumerate(series):
        fig.add_trace(go.Scatter(x=result.columns["time_s"], y=result.columns[key],
                                name=name, mode="lines",
                                line=dict(color=COLORS[i % len(COLORS)], width=2,
                                          dash="dot" if key.startswith("direct_") else "solid")))
    if result.startup_end_s is not None:
        fig.add_vline(x=result.startup_end_s, line_color="#94a3b8", line_dash="dash")
    fig.update_layout(title=title, height=340, template="plotly_white",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff",
                      font=dict(family="Arial", color="#14243b"), hovermode="x unified",
                      margin=dict(l=12, r=16, t=55, b=35),
                      legend=dict(orientation="h", y=-0.22),
                      xaxis_title="Time (s)", yaxis_title=unit)
    return fig


def export_bundle(result, profile_bytes):
    """Build downloads without overwriting CLI output or user files."""
    stream = BytesIO()
    with TemporaryDirectory(prefix="bess-report-") as directory:
        report = write_report(result, directory)
        html = report.read_bytes()
        with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
            for path in Path(directory).iterdir():
                archive.write(path, path.name)
            archive.writestr("input-profile.csv", profile_bytes)
            archive.writestr("config.json", json.dumps(asdict(result.config), indent=2))
    return html, stream.getvalue()


def system_diagram(config):
    """Responsive code-native single-line diagram, no external assets."""
    c = config
    blocks = [
        (20, "UTILITY PCC", f"{c.mv_voltage_ll_v/1000:g} kV · {c.nominal_frequency_hz:g} Hz", "#e9eff8"),
        (198, "GRID TRANSFORMER", "MV Δ / PCS Y · no neutral", "#edf1f7"),
        (376, "GRID PCS", f"GFL · {c.rated_power_w/1e6:g} MW", "#e6f4f3"),
        (554, "DC LINK", "416S LFP battery interface", "#e6f4f3"),
        (732, "LOAD PCS", "GFM · VSM frequency", "#e6f4f3"),
        (910, "LOAD TRANSFORMER", "PCS Y / MV Δ · no neutral", "#edf1f7"),
        (1088, "AI DATA CENTER", "Isolated load AC bus", "#e9eff8"),
    ]
    shapes = []
    for i, (x, title, detail, color) in enumerate(blocks):
        shapes.append(f'<rect x="{x}" y="65" width="158" height="80" rx="10" fill="{color}" stroke="#cfdae5"/>'
                      f'<text x="{x+79}" y="96" text-anchor="middle" font-size="11" font-weight="700">{title}</text>'
                      f'<text x="{x+79}" y="119" text-anchor="middle" font-size="10">{detail}</text>')
        if i < len(blocks)-1:
            shapes.append(f'<path d="M{x+158} 105 H{x+174}" stroke="#087f8c" stroke-width="2" marker-end="url(#a)"/>')
    return f'''<div style="background:white;border:1px solid #e0e7ef;border-radius:16px;padding:12px;overflow-x:auto">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1270 310" role="img"
aria-label="Utility transformer, GFL rectifier, DC battery, GFM inverter and load transformer in series"
style="width:100%;min-width:820px;font-family:Arial;fill:#14243b">
<defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto-start-reverse"><path d="M0 0 L6 3 L0 6" fill="#087f8c"/></marker></defs>
<text x="20" y="30" font-size="13" fill="#65758b">ONE DOUBLE-CONVERSION UNIT · SEPARATE UTILITY AND LOAD AC NETWORKS</text>
{''.join(shapes)}
<path d="M633 146 V189" stroke="#087f8c" stroke-width="2" marker-start="url(#a)" marker-end="url(#a)"/>
<rect x="535" y="195" width="196" height="65" rx="10" fill="#e6f4f3" stroke="#b7dcd8"/>
<text x="633" y="220" text-anchor="middle" font-size="12" font-weight="700">LFP ENERGY STORAGE</text>
<text x="633" y="241" text-anchor="middle" font-size="11">{c.battery_energy_mwh*c.battery_scale:.3f} MWh modeled capacity</text>
<text x="20" y="293" font-size="11" fill="#65758b">Transformer X = {100*c.transformer_x_pu:g}% specified; AC leakage and vector-group phase shift are not dynamically solved.</text>
</svg></div>'''
