"""`hub-check plugins/<id> ...`: the checks every pull request's listings must pass before a maintainer reviews it.

For each listing: it is well formed, its id is free, and the plugin at the listed commit is a teabot plugin with a
range of teabot, a README with its External connections, and a licence. Then, in the plugin's own environment,
`teabot check` and its tests run against Postgres. The report goes to the job's summary and to `report.md`, which
a separate workflow posts on the pull request, so no step that runs a plugin's code can write to the hub.
"""

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from teabot.sdk.ids import RESERVED_PLUGIN_IDS

from hub.inspect import Plugin, fetch, inspect
from hub.manifest import Listing, ListingError, read_listing

TAIL = 40
REPORT = Path("report.md")
ALLOWED = Path("allowed-dependencies.txt")
REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass(frozen=True)
class Step:
    """One command run in the plugin's checkout: its name, whether it passed, and the end of its output."""

    name: str
    passed: bool
    output: str


def taken_ids() -> frozenset[str]:
    """Ids a listing may not use: teabot's reserved ones, and the plugins that ship inside teabot."""
    bundled = {ep.name for ep in entry_points(group="teabot.plugins")}
    return RESERVED_PLUGIN_IDS | bundled


def run(name: str, command: list[str], cwd: Path) -> Step:
    """Run `command` in the plugin's checkout, in its own environment rather than the hub's."""
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    lines = (done.stdout + done.stderr).strip().splitlines()
    return Step(name, done.returncode == 0, "\n".join(lines[-TAIL:]))


def allowed() -> frozenset[str]:
    """The packages, beyond teabot's own, that listed plugins may depend on, as normalised names."""
    lines = ALLOWED.read_text().splitlines() if ALLOWED.exists() else []
    return frozenset(_normal(line) for line in lines if line.strip() and not line.lstrip().startswith("#"))


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def beyond_teabot(root: Path) -> list[str] | None:
    """Every package the plugin installs that teabot does not, transitive ones included, from its lock; None
    when uv cannot say."""
    command = ["uv", "export", "--no-dev", "--no-hashes", "--no-emit-project", "--prune", "teabot"]
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    done = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    lines = [line for line in done.stdout.splitlines() if line and not line.startswith(("#", " "))]
    names = [REQUIREMENT_NAME.match(line) for line in lines]
    return sorted({_normal(m.group(1)) for m in names if m is not None})


def dependency_step(root: Path, permitted: frozenset[str]) -> Step:
    """Whether every package the plugin adds to an instance is on the hub's allowlist."""
    found = beyond_teabot(root)
    if found is None:
        return Step("dependencies", False, "uv could not list the plugin's dependencies")
    outside = [name for name in found if name not in permitted]
    if outside:
        listed = ", ".join(outside)
        return Step(
            "dependencies",
            False,
            f"Not on the hub's allowlist: {listed}. Each needs a reason, in a pull request adding it to "
            f"{ALLOWED}, which a maintainer reviews on its own.",
        )
    return Step("dependencies", True, f"Beyond teabot's own: {', '.join(found) or 'none'}")


def checked(root: Path) -> list[Step]:
    """The plugin's own checks, in its own environment: install, its dependencies against the allowlist,
    `teabot check`, then its tests."""
    steps = [run("install", ["uv", "sync"], root)]
    if steps[0].passed:
        steps.append(dependency_step(root, allowed()))
        steps.append(run("teabot check", ["uv", "run", "teabot", "check", "."], root))
        steps.append(run("tests", ["uv", "run", "pytest", "-q"], root))
    return steps


def previous(listing: Listing, base: str) -> str | None:
    """The commit the hub listed before this pull request, for an update."""
    shown = subprocess.run(["git", "show", f"{base}:plugins/{listing.id}"], capture_output=True, text=True, check=False)
    if shown.returncode != 0:
        return None
    for line in shown.stdout.splitlines():
        if line.startswith("commit="):
            return line.partition("=")[2].strip()
    return None


def section(plugin: Plugin, steps: list[Step], before: str | None) -> list[str]:
    """One listing's part of the report."""
    listing = plugin.listing
    passed = not plugin.problems and all(s.passed for s in steps)
    lines = [f"## {listing.id} {'passes' if passed else 'needs changes'}", ""]
    lines.append(f"- Repository: {listing.repository.removesuffix('.git')}, at `{listing.commit[:12]}`")
    if before is not None and before != listing.commit:
        lines.append(
            f"- An update. The changes: {listing.repository.removesuffix('.git')}/compare/{before}...{listing.commit}"
        )
    elif before is None:
        lines.append("- A new plugin.")
    lines.append(f"- Package `{plugin.package}` {plugin.version}, for teabot `{plugin.teabot}`")
    lines.append(f"- Author: {plugin.author or 'not named'}")
    lines.append(f"- External connections: {plugin.connections or 'not given'}")
    others = ", ".join(f"`{d}`" for d in plugin.dependencies) or "none"
    lines.append(f"- Dependencies beyond teabot, for a maintainer to review: {others}")
    lines.append(f"- Licence: {plugin.licence or 'none'}")
    lines += ["", *[f"- [ ] {p}" for p in plugin.problems]]
    for step in steps:
        mark = "passed" if step.passed else "failed"
        lines += [f"<details><summary>{step.name}: {mark}</summary>", "", "```text", step.output, "```", "</details>"]
    return [*lines, ""]


def check(path: Path, base: str, taken: frozenset[str]) -> tuple[bool, list[str]]:
    """Whether one listing passes, and its part of the report."""
    try:
        listing = read_listing(path)
    except ListingError as exc:
        return False, [f"## {path.name} needs changes", "", f"- [ ] {exc}", ""]
    if listing.id in taken:
        return False, [f"## {listing.id} needs changes", "", f"- [ ] {listing.id} is taken by teabot itself", ""]
    with tempfile.TemporaryDirectory() as folder:
        root = fetch(listing, Path(folder) / listing.id)
        plugin = inspect(listing, root)
        steps = [] if plugin.problems else checked(root)
    passed = not plugin.problems and all(s.passed for s in steps)
    return passed, section(plugin, steps, previous(listing, base))


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:] if Path(a).name != "README.md"]
    base = os.environ.get("HUB_BASE", "origin/main")
    taken = taken_ids()
    results = [check(p, base, taken) for p in paths if p.exists()]
    gone = [p.name for p in paths if not p.exists()]
    lines = ["# Plugin hub checks", ""]
    lines += [f"- {name} is delisted." for name in gone]
    for _, part in results:
        lines += part
    report = "\n".join(lines) + "\n"
    REPORT.write_text(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(report)
    print(report)
    raise SystemExit(0 if all(passed for passed, _ in results) else 1)
