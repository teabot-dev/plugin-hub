# teabot plugin hub

This repository contains markers for Teabot plugins that are not supported by Teabot developers. Plugins are provided "as is"; we make no guarantees about any plugin. Core plugins are shipped insied Teabot and are not listed here.

You can browse 3rd-part plugins at
**https://teabot-dev.github.io/teabot/hub/**. 

Self-hosted instances can also browse with `uv run teabot hub search`.

## Creating and submitting plugins

Please see the relevant guides in the documentation:

- [Writing plugins](https://teabot-dev.github.io/teabot/plugins/) 
- [Submitting plugins](https://teabot-dev.github.io/teabot/plugins/publishing/)

## Reviewing

We will review your plugin to ensure it isn't malicious, doesn't break Discord's rules, and isn't one of our previously rejected or rolledback features. All plugin repositories must be public.

## Third party dependencies

We require any dependencies to have their cryptographic hash verified during build to prevent supply chain attacks and ensure build reproducability. We recommend avoiding adding new dependencies that are not absolutely necessary.

## Removal

We reserve the right to delist any 3rd party plugin at our own discretion.
