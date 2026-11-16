"""The hub's tools: listings, inspecting a plugin's checkout, and the catalogue."""

import textwrap
from pathlib import Path

import pytest

from hub import check
from hub.catalogue import REDIRECT
from hub.inspect import connections, inspect
from hub.manifest import Listing, ListingError, read_listing
from hub.resolve import project

COMMIT = "9db374fc205c5aae1f99bd5fd127266076f40ec8"


def listing_file(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def test_a_listing_is_two_lines_naming_a_repository_and_a_commit(tmp_path: Path) -> None:
    path = listing_file(tmp_path, "wom", f"repository=https://github.com/someone/teabot-wom.git\ncommit={COMMIT}\n")
    found = read_listing(path)
    assert found == Listing("wom", "https://github.com/someone/teabot-wom.git", COMMIT)
    assert found.requirement == f"teabot-wom @ git+https://github.com/someone/teabot-wom.git@{COMMIT}"


@pytest.mark.parametrize(
    ("name", "text", "says"),
    [
        ("Wom", f"repository=https://github.com/a/b\ncommit={COMMIT}", "named for its plugin's id"),
        ("wom", "repository=https://github.com/a/b\n", "missing commit"),
        ("wom", f"repository=http://example.com/a\ncommit={COMMIT}", "public HTTPS clone URL"),
        ("wom", "repository=https://github.com/a/b\ncommit=main", "40-character hash"),
        ("wom", f"repository=https://github.com/a/b\ncommit={COMMIT}\nbranch=main", "write only"),
    ],
)
def test_a_wrong_listing_says_what_to_write(tmp_path: Path, name: str, text: str, says: str) -> None:
    with pytest.raises(ListingError, match=says):
        read_listing(listing_file(tmp_path, name, text))


def plugin_checkout(root: Path, *, name: str = "teabot-wom", teabot: str = "teabot>=1.4,<2") -> Path:
    root.mkdir()
    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            f"""
            [project]
            name = "{name}"
            version = "1.0.0"
            authors = [{{ name = "Sam" }}]
            description = "Wise Old Man lookups"
            dependencies = ["{teabot}", "rapidfuzz>=3"]

            [project.entry-points."teabot.plugins"]
            wom = "teabot_wom:plugin"
            """
        )
    )
    (root / "README.md").write_text("# wom\n\n## External connections\n\napi.wiseoldman.net\n\n## Settings\n\nNone.\n")
    (root / "LICENSE").write_text("MIT License\n")
    return root


def test_a_checkout_is_read_without_running_it(tmp_path: Path) -> None:
    listing = Listing("wom", "https://github.com/someone/teabot-wom.git", COMMIT)
    plugin = inspect(listing, plugin_checkout(tmp_path / "wom"))
    assert plugin.problems == []
    assert (plugin.package, plugin.version, plugin.teabot) == ("teabot-wom", "1.0.0", ">=1.4,<2")
    assert plugin.connections == "api.wiseoldman.net"
    assert plugin.dependencies == ["rapidfuzz>=3"]
    assert plugin.licence == "MIT License"


def test_a_misnamed_package_and_an_open_range_are_problems(tmp_path: Path) -> None:
    listing = Listing("wom", "https://github.com/someone/teabot-wom.git", COMMIT)
    plugin = inspect(listing, plugin_checkout(tmp_path / "wom", name="wom", teabot="teabot>=1.4"))
    assert any("name it teabot-wom" in p for p in plugin.problems)
    assert any("upper bound" in p for p in plugin.problems)


def test_external_connections_are_read_inline_or_as_a_section() -> None:
    assert connections("- External connections: none\n") == "none"
    assert connections("# x\n\n## External connections\n\nA and B.\n\n## Next\n") == "A and B."


def test_a_dependency_outside_the_allowlist_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def found(root: Path) -> list[str]:
        return ["rapidfuzz", "typing-extensions"]

    monkeypatch.setattr(check, "beyond_teabot", found)
    step = check.dependency_step(tmp_path, frozenset({"typing-extensions"}))
    assert not step.passed and "rapidfuzz" in step.output and "typing-extensions" not in step.output
    assert check.dependency_step(tmp_path, frozenset({"rapidfuzz", "typing-extensions"})).passed


def test_the_resolve_project_holds_teabot_and_every_listing() -> None:

    listing = Listing("wom", "https://github.com/someone/teabot-wom.git", COMMIT)
    text = project([listing])
    assert '"teabot"' in text and listing.requirement in text


def test_every_reviewed_version_comes_from_the_listings_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from hub.history import history

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (tmp_path / "plugins").mkdir()
    older, newer = "a" * 40, "b" * 40
    for commit in (older, newer):
        (tmp_path / "plugins" / "wom").write_text(f"repository=https://github.com/s/teabot-wom.git\ncommit={commit}\n")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", commit[:4])
    monkeypatch.chdir(tmp_path)
    current = read_listing(Path("plugins/wom"))
    assert [v.commit for v in history(current)] == [newer, older]


def test_a_plugin_must_name_its_author(tmp_path: Path) -> None:
    listing = Listing("wom", "https://github.com/someone/teabot-wom.git", COMMIT)
    root = plugin_checkout(tmp_path / "wom")
    named = inspect(listing, root)
    assert named.author == "Sam" and named.problems == []
    project = (root / "pyproject.toml").read_text().replace('authors = [{ name = "Sam" }]\n', "")
    (root / "pyproject.toml").write_text(project)
    assert any("names its author" in p for p in inspect(listing, root).problems)


def test_the_hubs_own_page_sends_readers_to_the_docs() -> None:
    assert "https://teabot-dev.github.io/teabot/hub/" in REDIRECT and 'http-equiv="refresh"' in REDIRECT
