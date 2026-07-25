"""Guard: parity reference readers must not import meteoscape (even transitively)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_parity_readers_import_no_meteoscape() -> None:
    repo = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(repo / p) for p in ("src", "tests"))}
    script = r"""
import pkgutil
import sys

import parity.readers as readers_pkg

for info in pkgutil.iter_modules(readers_pkg.__path__, readers_pkg.__name__ + "."):
    __import__(info.name)

leaked = sorted(
    name
    for name in sys.modules
    if name == "meteoscape" or name.startswith("meteoscape.")
)
if leaked:
    raise SystemExit(f"parity.readers imported meteoscape: {leaked}")
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
