# teabot plugin hub

The plugins teabot's maintainers have reviewed, for any teabot instance to install. Browse them at
**https://teabot-dev.github.io/plugin-hub/**, or from an instance with `uv run teabot hub search`.

The plugins that ship inside teabot, such as announcements, giveaways and roles, are not listed here: every
instance has them already.

## Install a plugin

In your instance's folder, with the plugin's id in place of `wom`:

```bash
uv run teabot hub add wom
docker compose up -d --build
```

Without uv on the machine, copy the plugin's install line from the hub's page instead. It looks like this:

```bash
docker compose run --rm uv add "teabot-wom @ git+https://github.com/someone/teabot-wom@9db374f..."
docker compose up -d --build
```

Either way, you install exactly the commit that was reviewed. `uv run teabot hub outdated` lists installed hub
plugins with a newer reviewed commit, and `uv run teabot hub add <id>` again moves one to it. Then turn the plugin
on in each server that wants it, with `/plugins enable`.

## List your plugin

1. Write the plugin, and check it, as in teabot's guide to
   [writing plugins](https://teabot-dev.github.io/teabot/plugins/) and
   [publishing them](https://teabot-dev.github.io/teabot/plugins/publishing/). Its repository must be public, with
   a licence, and its package named `teabot-<id>`.
2. Fork this repository and make a branch for your plugin.
3. Add a file `plugins/<id>`, named for your plugin's id, with two lines:

    ```text
    repository=https://github.com/someone/teabot-wom.git
    commit=9db374fc205c5aae1f99bd5fd127266076f40ec8
    ```

    - `repository` is the HTTPS address you would clone it from.
    - `commit` is the full 40-character hash of the commit to list. That commit is what is reviewed and what
      instances install.

4. Open a pull request. Its checks clone your plugin at that commit, then install it, run `teabot check` and run
   its tests against Postgres. They post a report on the pull request: what passed, what to change, the plugin's
   External connections, and any dependencies beyond teabot's own.
5. If something needs changing, push a fix to your plugin's repository, then update `commit=` in the same pull
   request. Keep one pull request per plugin.
6. A maintainer reviews the code at that commit and merges. Within minutes, the plugin is on the hub's page and in
   the catalogue that `teabot hub` reads.

## Update your plugin

Change `commit=` in `plugins/<id>` to the new commit, in a pull request. The report links the difference since the
listed commit, which is what the maintainer reviews.

```bash
git remote add upstream https://github.com/teabot-dev/plugin-hub.git
git fetch upstream
git checkout -B wom upstream/main
# change commit= in plugins/wom
git commit -am "Update wom"
git push -f -u origin wom
gh pr create --repo teabot-dev/plugin-hub --fill
```

## What review checks

A plugin runs inside the bot of every instance that installs it, with the bot's power in each server that turns
it on. So review asks:

- Is it what it says, and nothing else? Code that is hard to follow is not merged, since it cannot be checked.
- Does it contact only the hosts it declares, through `ctx.http`?
- Does it keep to teabot's rules for plugins: imports only from `teabot.sdk`, the clock from `ctx.now`, no `SET`
  in SQL, migrations never changed once released, and jobs safe to run twice?
- Does it add dependencies? Each one beyond teabot's own is a package every installing instance trusts, so each
  needs a reason. Fewer is better.
- Does it duplicate a listed plugin? Contributing to that one is better than listing a second.

## Removal

Maintainers delist a plugin that turns out harmful, that stops working with the current teabot and is not fixed,
or whose author asks. Delisting removes its file. Instances that installed it keep the commit they have, and
`teabot hub outdated` tells them it is no longer listed.

## This repository

- `plugins/`: the listings, one file per plugin.
- `hub/`: the tools the workflows run. `hub-check` checks a pull request's listings; `hub-catalogue` builds the
  catalogue and the page. They are a uv project: `uv run pytest` tests them.
- `.github/workflows/`: `check.yml` runs a pull request's plugins with no rights and no secrets; `comment.yml`
  posts their report; `publish.yml` publishes the catalogue on GitHub Pages; `ci.yml` tests the tools.

The plugins are provided as they are. Review lowers the risk of a plugin, and does not remove it.
