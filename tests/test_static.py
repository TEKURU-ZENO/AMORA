import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_app_js_parses():
    # one syntax error here silently breaks every page's scripts
    js = Path(__file__).resolve().parent.parent / "app" / "static" / "app.js"
    r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
