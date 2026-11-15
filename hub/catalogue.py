"""`hub-catalogue`: the hub's catalogue, `site/catalogue.json`, and its page, `site/index.html`, from every listing.

teabot's `teabot hub` commands read the catalogue. The page lists each plugin with what it contacts and the line
that installs exactly the reviewed commit.
"""

import html
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hub.inspect import Plugin, fetch, inspect
from hub.manifest import listings

SITE = Path("site")
INSTALL = 'docker compose run --rm uv add "{requirement}"'


def entry(plugin: Plugin) -> dict[str, Any]:
    """One plugin as the catalogue lists it."""
    listing = plugin.listing
    return {
        "id": listing.id,
        "package": plugin.package,
        "version": plugin.version,
        "description": plugin.description,
        "teabot": plugin.teabot,
        "repository": listing.repository.removesuffix(".git"),
        "commit": listing.commit,
        "requirement": listing.requirement,
        "external_connections": plugin.connections,
        "dependencies": plugin.dependencies,
        "licence": plugin.licence,
        "readme": plugin.readme,
    }


def page(entries: list[dict[str, Any]], generated: str) -> str:
    """The catalogue as a web page, with no scripts."""
    cards = "\n".join(_card(e) for e in entries) or "<p>No plugins are listed yet.</p>"
    return PAGE.format(cards=cards, count=len(entries), generated=html.escape(generated))


def _card(e: dict[str, Any]) -> str:
    install = html.escape(INSTALL.format(requirement=e["requirement"]))
    return CARD.format(
        id=html.escape(e["id"]),
        version=html.escape(e["version"]),
        description=html.escape(e["description"]),
        repository=html.escape(e["repository"]),
        connections=html.escape(e["external_connections"] or "none given"),
        teabot=html.escape(e["teabot"]),
        install=install,
        id_short=html.escape(e["id"]),
    )


CARD = """<article id="{id}">
  <h2>{id} <small>{version}</small></h2>
  <p>{description}</p>
  <dl>
    <dt>Contacts</dt><dd>{connections}</dd>
    <dt>teabot</dt><dd>{teabot}</dd>
    <dt>Source</dt><dd><a href="{repository}">{repository}</a></dd>
  </dl>
  <p>Install, in your instance's folder, then rebuild with <code>docker compose up -d --build</code>:</p>
  <pre><code>{install}</code></pre>
  <p>Or, with uv: <code>uv run teabot hub add {id_short}</code></p>
</article>"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>teabot plugin hub</title>
<style>
:root {{ --bg: #ffffff; --fg: #1d1d1f; --muted: #5f6368; --card: #f5f5f7; --link: #0a58ca; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #111214; --fg: #e8e8ea; --muted: #a0a3a8; --card: #1c1d20; --link: #7ab7ff; }}
}}
body {{ margin: 0 auto; max-width: 52rem; padding: 2rem 1rem; background: var(--bg); color: var(--fg);
  font: 16px/1.5 system-ui, sans-serif; }}
a {{ color: var(--link); }}
article {{ background: var(--card); border-radius: 12px; padding: 1rem 1.25rem; margin: 1rem 0; }}
h2 small {{ color: var(--muted); font-weight: normal; font-size: 0.8em; }}
dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; }}
dt {{ color: var(--muted); }}
dd {{ margin: 0; overflow-wrap: anywhere; }}
pre {{ overflow-x: auto; padding: 0.75rem; background: var(--bg); border-radius: 8px; }}
</style>
</head>
<body>
<h1>teabot plugin hub</h1>
<p>{count} plugins, each reviewed by teabot's maintainers at the commit listed. A plugin runs inside your bot, so
read what it contacts before you install it. To list yours, see
<a href="https://github.com/teabot-dev/plugin-hub">the hub's repository</a>.</p>
{cards}
<p><small>Built {generated}. The catalogue for <code>teabot hub</code> is
<a href="catalogue.json">catalogue.json</a>.</small></p>
</body>
</html>
"""


def main() -> None:
    entries: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as folder:
        for listing in listings(Path("plugins")):
            plugin = inspect(listing, fetch(listing, Path(folder) / listing.id))
            entries.append(entry(plugin))
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    SITE.mkdir(exist_ok=True)
    (SITE / "catalogue.json").write_text(json.dumps({"generated": generated, "plugins": entries}, indent=2) + "\n")
    (SITE / "index.html").write_text(page(entries, generated))
    print(f"catalogued {len(entries)} plugins")
