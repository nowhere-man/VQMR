"""Wrapper so Streamlit can find metrics comparison page under ./pages."""

import pathlib
import runpy
import sys

project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

runpy.run_module("src.pages.metrics_comparison", run_name="__main__")
