# ShortUrls

A small Flask app for shortening URLs and changing their destinations later. I built it to see what a simple redirect can reveal about a visit.

[Run it locally](#run-it-locally) · [Full landing-page screenshot](.github/images/shorturls-landing-screenshot.png)

[![Open GitHub issues](https://img.shields.io/github/issues/Pop101/ShortUrls?style=flat-square)](https://github.com/Pop101/ShortUrls/issues)

![ShortUrls poster: a short path branches to a destination and a visit log](.github/images/readme-hero.svg)

## Overview

**Create** gives a destination a short ID. The same ID and key let you change that destination later. **Track** looks up the link’s creation and expiration times. Its matching key unlocks the visit log.

I use this as a local experiment. Visit logs can contain IP addresses and browser details. Use synthetic or consenting test traffic and keep the app off the public internet.

## Run it locally

Use an isolated environment with [Poetry](https://python-poetry.org/). The entry point is `web_interface.py`:

```sh
git clone https://github.com/Pop101/ShortUrls.git
cd ShortUrls
poetry install
poetry run python web_interface.py
```

Open `http://localhost:8484` on the same machine. The launcher binds to all interfaces, so don't run it on an exposed host. The startup command was checked against the source; a fresh dependency install and browser run have not been verified for this revision.

## Try a link

1. In **Create**, enter a synthetic destination such as `http://example.test/`, choose a disposable key, and optionally set an ID. The response shows the short ID.
2. In **Track**, look up that ID to see its metadata. Add the matching test key to see any visit records from your own test traffic.

Use the local HTTP address directly. The UI's preview links assume HTTPS, and the Create form currently rewrites destinations to HTTP.
