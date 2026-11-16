"""A listing: `plugins/<id>`, two lines naming the plugin's repository and the commit the hub reviewed.

```text
repository=https://github.com/someone/teabot-wom.git
commit=9db374fc205c5aae1f99bd5fd127266076f40ec8
```
"""

import re
from dataclasses import dataclass
from pathlib import Path

ID = re.compile(r"[a-z][a-z0-9_]{1,31}")
COMMIT = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"https://(github\.com|gitlab\.com|codeberg\.org)/[\w.-]+/[\w.-]+?(\.git)?")
FIELDS = ("repository", "commit")


class ListingError(ValueError):
    """A listing that does not say what the hub needs, with what to write instead."""


@dataclass(frozen=True)
class Listing:
    """One listed plugin: its `id`, the file's name; its public `repository`; and the reviewed `commit`."""

    id: str
    repository: str
    commit: str

    @property
    def requirement(self) -> str:
        """What an instance adds to install exactly the reviewed commit."""
        return f"teabot-{self.id} @ git+{self.repository}@{self.commit}"


def read_listing(path: Path) -> Listing:
    """The listing in `path`. Raises `ListingError` naming each problem."""
    if not ID.fullmatch(path.name):
        raise ListingError(f"{path.name}: a listing is named for its plugin's id, such as plugins/wom")
    return parse_listing(path.name, path.read_text())


def parse_listing(plugin_id: str, text: str) -> Listing:
    """A listing's text, for the plugin `plugin_id`. Raises `ListingError` naming each problem."""
    values: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name.strip() not in FIELDS:
            raise ListingError(f"{plugin_id}:{number}: write only {' and '.join(f'{f}=' for f in FIELDS)} lines")
        values[name.strip()] = value.strip()
    missing = [f for f in FIELDS if f not in values]
    if missing:
        raise ListingError(f"{plugin_id}: missing {', '.join(missing)}")
    if not REPOSITORY.fullmatch(values["repository"]):
        raise ListingError(f"{plugin_id}: repository is the public HTTPS clone URL, on GitHub, GitLab or Codeberg")
    if not COMMIT.fullmatch(values["commit"]):
        raise ListingError(f"{plugin_id}: commit is the full 40-character hash of the commit to list")
    return Listing(plugin_id, values["repository"], values["commit"])


def listings(directory: Path) -> list[Listing]:
    """Every listing in the hub's `plugins/` folder, by id. README.md is the folder's own."""
    return [read_listing(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name != "README.md"]
