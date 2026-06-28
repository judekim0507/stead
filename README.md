# Stead

**Stead** is a performance-first, agentic web browser built as a Chromium fork.

Its goal: keep the *full* agentic capability of any website — the agent can
perceive and act on any page — while being one of the most performant AI browsers
out there. The thesis is that the bottleneck in today's AI browsers isn't the
model, it's the **overhead layer** stacked around it (extension service-workers,
per-tab content scripts, JSON message-passing, local proxies, CDP automation, an
external daemon). Stead's fix: make everything the user touches **native**, and
keep only the inference host out-of-process.

This repository is the **macOS browser** — the Chromium fork itself. It forks
[helium-macos](https://github.com/imputnet/helium-macos) and embeds the shared
[Helium](https://github.com/imputnet/helium) patch tree as the `helium-chromium`
submodule. All of Stead's own Chromium changes are isolated in `patches/stead/`
so they stay portable across upstream churn.

The **UI** lives in a separate repo,
[stead-ui](https://github.com/judekim0507/stead-ui) (SvelteKit). It's built to
static assets and served as native Chromium **WebUI** surfaces — no extension,
no content scripts. The built bundle is vendored here under `resources/stead/`.

## Status

UI layer wired (the agent "brain" is the next phase):

- Helium → Stead rebrand (app, packaging, in-browser strings, internal `stead://` scheme)
- **Ask Stead** side panel (pinned toolbar button → the agent sidebar)
- Full-page chat at `stead://chat`
- Custom **new tab page** (prerendered, paints instantly), replacing Chrome's NTP

## Build & develop

- **Workflow / repo map:** [DEVELOPMENT.md](DEVELOPMENT.md)
- **Compiling the browser** (needs macOS): [docs/building.md](docs/building.md)

## Credits

### Helium
Stead is based on [Helium](https://github.com/imputnet/helium) and
[helium-macos](https://github.com/imputnet/helium-macos) by imputnet. The
`helium-chromium` submodule tracks the upstream Helium patch tree — huge thanks
to the Helium authors for the foundation this builds on.

### ungoogled-chromium-macos
Helium's macOS tooling is in turn based on
[ungoogled-chromium-macos](https://github.com/ungoogled-software/ungoogled-chromium-macos).
Thanks to everyone behind ungoogled-chromium.

## License

Stead is open source under the **GNU General Public License v3.0**. All code,
patches, and modified portions unique to this repository are licensed under
GPL-3.0 — see [LICENSE](LICENSE).

Imported content keeps its original license: content from Helium remains
GPL-3.0, and unmodified code from ungoogled-chromium remains under its
[BSD 3-Clause license](LICENSE.ungoogled_chromium). GPL-3.0 (unlike AGPL) does
not reach across the network, so Stead's open client pairs with a separate
proprietary cloud/subscription backend.
