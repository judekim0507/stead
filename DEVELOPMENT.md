# Stead — how the pieces fit (dev map)

Two folders, each with one job, connected by one script. That's the whole thing.

```
  ../ui                  ── sync script ──>   stead (this repo)        ── launches ──>   brain
  the LOOK                copies built UI       the BROWSER                                the agent (Pi)
  SvelteKit app           into this repo        Chromium fork + patches                   separate process (later)
```

## Which folder do I edit?

| To change…                                              | Edit in…                 | See it via…                          |
| ------------------------------------------------------- | ------------------------ | ------------------------------------ |
| How the **UI** looks/works (chat, sidebar, new-tab)     | **`../ui`** (Svelte)     | `bun dev` — instant, in any browser  |
| **Browser-level** stuff (new page surface, native, brain wiring) | **this repo** (`patches/stead/…`) | a Stead build               |
| The **brain** (the agent itself)                        | its own thing (Pi, later)| runs as a side process               |

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

## The brain (later)

A separate process (the Pi agent) that the browser launches and talks to. The UI
talks to the browser; the browser talks to the brain. Wiring it touches *this*
repo a little (the glue) — not your Svelte UI. It does not make the UI side messier.
