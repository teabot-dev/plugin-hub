"""Every reviewed version of a listed plugin, from the git history of its listing: each merged change to
`plugins/<id>` is a version the maintainers reviewed."""

import subprocess
from pathlib import Path

from hub.manifest import Listing, ListingError, parse_listing


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def history(listing: Listing, directory: Path = Path("plugins")) -> list[Listing]:
    """The listing's versions, newest first, the current one included, each commit once."""
    path = (directory / listing.id).as_posix()
    found: list[Listing] = [listing]
    for hub_commit in _git("log", "--format=%H", "--", path).split():
        try:
            text = _git("show", f"{hub_commit}:{path}")
        except subprocess.CalledProcessError:
            continue
        try:
            older = parse_listing(listing.id, text)
        except ListingError:
            continue
        if all(o.commit != older.commit for o in found):
            found.append(older)
    return found
