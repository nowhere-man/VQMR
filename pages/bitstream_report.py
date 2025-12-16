"""
Streamlit multipage wrapper for bitstream report.

This file lives in ./pages so Streamlit can discover it; it simply runs the
implementation in src.pages.bitstream_report.
"""

import pathlib
import runpy
import sys

project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

runpy.run_module("src.pages.bitstream_report", run_name="__main__")
