"""Wrapper so Streamlit can find report details page under ./pages."""

import pathlib
import runpy
import sys

project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

runpy.run_module("src.pages.report_details", run_name="__main__")
