"""Optional UI smoke test; does not run the solver or start a web server."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_app_opens_without_automatically_simulating():
    path = Path(__file__).resolve().parents[1]/"app.py"
    app = AppTest.from_file(str(path)).run(timeout=30)
    assert not app.exception
    assert app.session_state["runs"] == []
    app.sidebar.selectbox[0].select("5 s filter · Tj 10 / D 1").run(timeout=30)
    assert not app.exception
    assert app.session_state["runs"] == []
