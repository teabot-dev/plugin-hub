"""What a listed plugin is, read from its repository at the listed commit: its package, its README and what it
contacts. Nothing of the plugin's runs here."""

import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from hub.manifest import Listing

TEABOT = re.compile(r"^teabot(\[[^\]]*\])?\s*(?P<spec>.*)$")
SECTION = re.compile(r"^#+\s*External connections\s*$", re.IGNORECASE | re.MULTILINE)
INLINE = re.compile(r"^\s*[-*]?\s*External connections\s*:\s*(?P<text>.+)$", re.IGNORECASE | re.MULTILINE)


@dataclass
class Plugin:
    """A listed plugin as its repository describes it, and what is wrong with it, if anything."""

    listing: Listing
    package: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    teabot: str = ""
    dependencies: list[str] = field(default_factory=list[str])
    readme: str = ""
    connections: str = ""
    licence: str = ""
    problems: list[str] = field(default_factory=list[str])


def fetch(listing: Listing, into: Path) -> Path:
    """Clone the plugin's repository into `into`, at the listed commit, without its history."""
    into.mkdir(parents=True, exist_ok=True)
    git = ["git", "-c", "advice.detachedHead=false", "-C", str(into)]
    subprocess.run(["git", "init", "-q", str(into)], check=True)
    subprocess.run([*git, "fetch", "-q", "--depth", "1", listing.repository, listing.commit], check=True)
    subprocess.run([*git, "checkout", "-q", "FETCH_HEAD"], check=True)
    return into


def connections(readme: str) -> str:
    """The README's "External connections", as written: an inline line, or the section under that heading."""
    inline = INLINE.search(readme)
    if inline is not None:
        return inline.group("text").strip()
    heading = SECTION.search(readme)
    if heading is None:
        return ""
    rest = readme[heading.end() :]
    following = re.search(r"^#", rest, re.MULTILINE)
    return (rest[: following.start()] if following else rest).strip()


def _teabot_range(dependencies: list[str]) -> str | None:
    for dependency in dependencies:
        found = TEABOT.match(dependency.strip())
        if found is not None:
            return found.group("spec").strip()
    return None


def _project(plugin: Plugin, project: dict[str, Any]) -> None:
    listing = plugin.listing
    plugin.package = str(project.get("name", ""))
    plugin.version = str(project.get("version", ""))
    plugin.description = str(project.get("description", ""))
    entries: list[Any] = list(project.get("authors", []))
    authors = [str(cast(dict[str, Any], a).get("name", "")).strip() for a in entries if isinstance(a, dict)]
    plugin.author = ", ".join(a for a in authors if a)
    if not plugin.author:
        plugin.problems.append('its pyproject.toml names its author, which the hub shows: authors = [{ name = "you" }]')
    if plugin.package != f"teabot-{listing.id}":
        plugin.problems.append(f"the package is named {plugin.package!r}; name it teabot-{listing.id}")
    entry_points = project.get("entry-points", {}).get("teabot.plugins", {})
    if list(entry_points) != [listing.id]:
        plugin.problems.append(f'its one [project.entry-points."teabot.plugins"] entry is named {listing.id}')
    dependencies = [str(d) for d in project.get("dependencies", [])]
    found = _teabot_range(dependencies)
    if found is None or "<" not in found:
        plugin.problems.append('it depends on a range of teabot with an upper bound, such as "teabot>=1.4,<2"')
    plugin.teabot = found or ""
    plugin.dependencies = [d for d in dependencies if _teabot_range([d]) is None]


def inspect(listing: Listing, root: Path) -> Plugin:
    """What the repository checked out at `root` says about the listed plugin."""
    plugin = Plugin(listing)
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        plugin.problems.append("there is no pyproject.toml at the repository's root")
        return plugin
    _project(plugin, tomllib.loads(pyproject.read_text()).get("project", {}))
    readme = root / "README.md"
    plugin.readme = readme.read_text() if readme.exists() else ""
    plugin.connections = connections(plugin.readme)
    if not plugin.connections:
        plugin.problems.append('the README has no "External connections", which lists every host it contacts, or none')
    licence = next((p for p in root.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE"))), None)
    plugin.licence = licence.read_text().splitlines()[0].strip() if licence is not None and licence.is_file() else ""
    if not plugin.licence:
        plugin.problems.append("there is no LICENSE file; the hub lists open-source plugins only")
    return plugin
