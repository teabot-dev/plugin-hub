# allowed-dependencies

The packages, beyond teabot's own dependencies, that listed plugins may install. Each is a file here:

- Its name is the package's name as PyPI normalises it: lower case, with `-` for any run of `-`, `_` and `.`, such as `yt-dlp`.
- Its text says which plugin needs the package and why.
- Each is added in its own pull request, which a maintainer reviews on its own. Native extensions get a closer look, since one crash in them stops a whole teabot.

The hub's tests check every file here is named that way and gives a reason.
