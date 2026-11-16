<!-- One plugin per pull request, as a new or changed file in plugins/. Keep fixing in this pull request,
by pushing new commits that change commit=, rather than opening another. -->

What the plugin does, in a sentence or two:

- [ ] The repository is public, and its licence lets others use it.
- [ ] Its README says what it does, its commands, its settings, and its "External connections".
- [ ] Every host it contacts is in `Plugin(..., hosts=[...])` and in the README, and nothing else is contacted. A plugin that streams media may reach its media hosts through its media library, such as yt-dlp, when the README lists those hosts and the library.
- [ ] `uv run pytest` and `uv run teabot check .` pass in its repository.
