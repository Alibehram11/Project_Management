"""
PythonAnywhere WSGI entrypoint.

In the PythonAnywhere Web tab, point the WSGI file at this module or copy the
three active lines below into their generated WSGI configuration file.
"""

from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from server import application  # noqa: E402
