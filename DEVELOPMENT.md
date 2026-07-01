# Stead — how the pieces fit (dev map)

Two folders, each with one job, connected by one script. That's the whole thing.

```
  ../ui                  ── sync script ──>   stead (this repo)        ── launches ──>   ../brain
  the LOOK                copies built UI       the BROWSER                                the agent helper
  SvelteKit app           into this repo        Chromium fork + patches                   bundled Rust + Pie
```

## Repos

- **`stead`** (this one) — the browser. https://github.com/judekim0507/stead
- **`stead-ui`** — the Svelte UI source (`../ui`). https://github.com/judekim0507/stead-ui

This repo vendors the *built* UI (`resources/stead/sidebar/`); `stead-ui` holds
the *source*. Edit source in `stead-ui`, then sync (below) to bring the build here.

## Which folder do I edit?

| To change…                                              | Edit in…                 | See it via…                          |
| ------------------------------------------------------- | ------------------------ | ------------------------------------ |
| How the **UI** looks/works (chat, sidebar, new-tab)     | **`../ui`** (Svelte)     | `bun dev` — instant, in any browser  |
| **Browser-level** stuff (new page surface, native, brain wiring) | **this repo** (`patches/stead/…`) | a Stead build               |
| The **brain** (the agent itself)                        | **`../brain`** (Rust + Pie)| runs as a bundled helper process   |

You'll spend ~all your time in `../ui`. You rarely touch this repo for UI work.

## Day-to-day UI loop (the common case)

```sh
cd ../ui
bun dev          # edit Svelte, see it live in a normal browser. No Chromium build.
```

When you want those UI changes **inside the Stead browser**, run one command from
this repo:

```sh
resources/stead/sync_sidebar_ui.sh    # rebuilds ../ui and vendors the bundle in
```

(Override the UI location with `STEAD_UI_DIR=/path/to/ui` if it ever moves.)

## The one rule

The built UI inside this repo — `resources/stead/sidebar/` — is a **generated
copy**, like a compiled file. **Never edit it by hand.** Only edit the source in
`../ui`, then re-run the sync script to regenerate it.

## Building the actual browser

Needs a Mac (see [docs/building.md](docs/building.md)). The dev flow:

```sh
source dev.sh
he setup          # first time: fetch Chromium, apply patches, etc.
he build
he run            # launches Stead with a dev profile
```

`build.sh` / `he` automatically run the sync-into-tree step, so a build always
picks up whatever is in `resources/stead/sidebar/`.

## The WebUI surfaces (all from the one Svelte app)

| Svelte route   | Shows up as                          | Status                     |
| -------------- | ------------------------------------ | -------------------------- |
| `/ai-sidebar`  | **Ask Stead** side panel (toolbar)   | wired                      |
| `/ai-chat`     | full-page chat, `stead://chat/ai-chat` | wired                    |
| `/new-tab`     | new-tab page                         | not wired yet              |
| `/`            | (placeholder)                        | —                          |

Each surface is one small patch in `patches/stead/…` that points the **same**
bundle at a different route. Adding `/new-tab` later = the same pattern, no UI
rebuild.

## Where the branding lives

The "Chrome/Chromium/Helium → Stead" rename is `devutils/stead_name_substitution.py`,
run automatically by the build. The `helium-chromium` submodule stays untouched.
You don't need to think about it.

## The brain

A bundled Rust helper process that the browser launches and talks to over framed
JSON stdio. The UI talks to the browser; the browser talks to the brain. The
brain source lives in `../brain`, vendors pinned Pie under `../brain/vendor/pie`,
and keeps browser tools mediated through the browser-side broker.

The Rust side is scaffolded and testable now:

```sh
cd ../brain
cargo test --workspace
cargo build --release -p stead-brain
```

The browser wiring now has a `BrainBroker`/`BrainConsole` Chromium patch that
launches `stead-brain` and bridges WebUI session/auth calls to the helper. The
patch also routes browser tool calls from `BrainBroker` back through
`AgentControl`. `sign_and_package_app.sh` installs the release helper into
`Stead.app/Contents/MacOS/stead-brain` before signing, so the helper is bundled
with the app; the remaining browser work is verifying the launch/routing path in
a Chromium build.
