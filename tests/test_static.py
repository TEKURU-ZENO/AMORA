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


def test_vercel_uses_writable_tmp(monkeypatch):
    # Vercel's deployed files are read-only: a DB under the project dir broke /discovery there
    from app import config
    monkeypatch.setenv("VERCEL", "1")
    assert str(config._default_data_dir()).replace("\\", "/") == "/tmp/amora"
    monkeypatch.delenv("VERCEL")
    assert config._default_data_dir() == config.ROOT / "data"


def test_old_env_names_still_work(monkeypatch):
    from app import config
    monkeypatch.setenv("AMORA_DEMO", "")
    monkeypatch.setenv("AGENTDATE_DEMO", "1")
    assert config.demo_mode()
