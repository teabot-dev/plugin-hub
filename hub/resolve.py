"""`hub-resolve`: whether the newest teabot and every listed plugin install together, as one instance would hold
them. The nightly workflow runs it, since an upstream release can break the resolve with no pull request here."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hub.manifest import Listing, listings

PROJECT = """[project]
name = "hub-catalogue-resolve"
version = "0"
requires-python = ">=3.12"
dependencies = {dependencies}
"""


def project(entries: list[Listing]) -> str:
    """A pyproject.toml for an instance holding the newest teabot and every listed plugin."""
    return PROJECT.format(dependencies=json.dumps(["teabot", *[e.requirement for e in entries]]))


def main() -> None:
    entries = listings(Path("plugins"))
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "pyproject.toml").write_text(project(entries))
        done = subprocess.run(["uv", "lock"], cwd=folder, capture_output=True, text=True, check=False)
    if done.returncode == 0:
        print(f"teabot and all {len(entries)} listed plugins install together.")
        return
    print(f"teabot and the {len(entries)} listed plugins no longer install together:\n\n{done.stderr.strip()}")
    sys.exit(1)
