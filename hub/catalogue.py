"""`hub-catalogue`: the hub's catalogue, `site/catalogue.json`, from every listing, and `site/index.html`, which sends
readers to the hub's pages in Teabot's documentation. Those pages are built from this catalogue.

teabot's `teabot hub` commands, its dashboard and its documentation read the catalogue.
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hub.history import history
from hub.inspect import Plugin, fetch, inspect
from hub.manifest import listings

SITE = Path("site")


def version(plugin: Plugin) -> dict[str, Any]:
    """One reviewed version of a plugin: what an instance installs, and what teabot it needs."""
    return {
        "commit": plugin.listing.commit,
        "version": plugin.version,
        "teabot": plugin.teabot,
        "requirement": plugin.listing.requirement,
        "external_connections": plugin.connections,
        "dependencies": plugin.dependencies,
    }


def entry(plugin: Plugin, versions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """One plugin as the catalogue lists it: its newest version at the top level, for teabot 1.4, and every
    reviewed version, newest first, in `versions`, so an instance picks the newest its teabot runs."""
    listing = plugin.listing
    return {
        "id": listing.id,
        "package": plugin.package,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "teabot": plugin.teabot,
        "repository": listing.repository.removesuffix(".git"),
        "commit": listing.commit,
        "requirement": listing.requirement,
        "external_connections": plugin.connections,
        "dependencies": plugin.dependencies,
        "licence": plugin.licence,
        "readme": plugin.readme,
        "versions": versions if versions is not None else [version(plugin)],
    }


DOCS = "https://teabot-dev.github.io/teabot/hub/"
REDIRECT = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Teabot plugin hub</title>
<meta http-equiv="refresh" content="0; url={DOCS}">
<link rel="canonical" href="{DOCS}">
</head>
<body><p>The plugin hub is part of Teabot's documentation: <a href="{DOCS}">{DOCS}</a></p></body>
</html>
"""


def main() -> None:
    entries: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as folder:
        for listing in listings(Path("plugins")):
            found = [inspect(v, fetch(v, Path(folder) / f"{v.id}-{v.commit}")) for v in history(listing)]
            entries.append(entry(found[0], [version(p) for p in found]))
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    SITE.mkdir(exist_ok=True)
    (SITE / "catalogue.json").write_text(json.dumps({"generated": generated, "plugins": entries}, indent=2) + "\n")
    (SITE / "index.html").write_text(REDIRECT)
    print(f"catalogued {len(entries)} plugins")
