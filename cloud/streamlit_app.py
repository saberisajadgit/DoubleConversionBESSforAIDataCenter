"""Cloud entry point; keeps cloud pip dependencies separate from local Conda."""
from pathlib import Path
import runpy
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
runpy.run_path(str(PROJECT / "app.py"), run_name="__main__")
