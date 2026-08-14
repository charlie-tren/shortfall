"""Puts the repo root on sys.path so tests can import the modules directly.

pytest inserts the test file's own directory, not the rootdir, so without this
`from edgar import ...` fails from tests/.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
