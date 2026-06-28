# stead-macos
macOS packaging & development tooling for **Stead**, a performance-first
agentic web browser.

Stead is built as a Chromium fork. This repository forks
[helium-macos](https://github.com/imputnet/helium-macos) and embeds the shared
[Helium](https://github.com/imputnet/helium) patch tree as the `helium-chromium`
git submodule. Stead's own changes live in this repo: branding and packaging are
applied here, and Stead-specific Chromium patches are kept isolated in
`patches/stead/` so they stay portable across upstream churn.

## Building and development
macOS is the primary development platform.

[> See docs/building.md](docs/building.md)

## Credits

### Helium
Stead is based on [Helium](https://github.com/imputnet/helium) and
[helium-macos](https://github.com/imputnet/helium-macos) by imputnet. The
`helium-chromium` submodule tracks the upstream Helium patch tree. Huge thanks
to the Helium authors for the foundation this builds on.

### ungoogled-chromium-macos
Helium's macOS tooling is in turn based on
[ungoogled-chromium-macos](https://github.com/ungoogled-software/ungoogled-chromium-macos).
Special thanks to everyone behind ungoogled-chromium — they made working with
Chromium infinitely easier.

## License
All code, patches, modified portions of imported code or patches, and any other
content that is unique to this repository and not imported from other
repositories is licensed under GPL-3.0. See [LICENSE](LICENSE).

Any content imported from other projects retains its original license. Content
imported from Helium remains under GPL-3.0, and any original unmodified code
imported from ungoogled-chromium remains licensed under their
[BSD 3-Clause license](LICENSE.ungoogled_chromium).
