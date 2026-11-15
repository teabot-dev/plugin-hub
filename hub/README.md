# hub

- `manifest.py`: reads a listing, `plugins/<id>`, and refuses one that is not two well-formed lines.
- `inspect.py`: clones a listed plugin at its commit and reads its package, README and licence, running nothing.
- `check.py`: `hub-check`, the pull request's checks and their report, including each plugin's dependencies against `allowed-dependencies.txt`.
- `catalogue.py`: `hub-catalogue`, the catalogue JSON and the hub's page.
- `resolve.py`: `hub-resolve`, whether the newest teabot and every listed plugin install together.
