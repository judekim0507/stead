# Stead sidebar WebUI

Hosts the Stead agent UI as a native Chromium WebUI in the browser side panel —
no extension, content script, or service worker. The UI is the SvelteKit app in
the sibling `ui/` repo, built as a static SPA and packed into Chromium.

Internal URL is **`chrome://sidebar.top-chrome/`** (real scheme
`content::kChromeUIScheme`; the `.top-chrome` suffix marks it as a Top Chrome
WebUI, the class all side-panel/bubble WebUIs use — e.g. `read-later.top-chrome`).
Build-time name substitution displays `chrome://` as `stead://`, so it reads as
**`stead://sidebar.top-chrome`** in any user-facing string — the same trick
Helium uses for `helium://`. The side panel has no address bar, so the scheme is
invisible in normal use.

`SteadSidebarUI` is a **`TopChromeWebUIController`** with a
`DefaultTopChromeWebUIConfig` (not the full-page `DefaultWebUIConfig`) — required
so it can be hosted by `WebUIContentsWrapperT` in the side panel, exactly like
`ReadingListUI`.

## How the bundle gets in

1. `resources/stead/sync_sidebar_ui.sh` — builds `ui/` (SvelteKit → static SPA)
   and vendors the output into `resources/stead/sidebar/`. Re-run when the UI
   changes. (`ui/svelte.config.js` uses adapter-static, SPA fallback, absolute
   asset paths, `ssr=false`.)
2. `resources/stead/install_sidebar_to_tree.sh <src>` — copies the vendored
   bundle into `chrome/browser/resources/stead_sidebar/` and regenerates
   `stead_sidebar_resources.grd` (via `gen_sidebar_grd.py`) for the hash-named
   files. Called from `build.sh` and `dev.sh` (`he resources`) before `gn gen`.

## Patches

- **`stead-sidebar-webui-files.patch`** — all new files (always apply cleanly):
  - `chrome/browser/ui/webui/side_panel/stead_sidebar/stead_sidebar_ui.{h,cc}`
    — `SteadSidebarUI` controller + `SteadSidebarUIConfig`. Sets up the
    `WebUIDataSource`, relaxes CSP (`script-src`/`style-src` allow
    `'unsafe-inline'` for SvelteKit's inline bootstrap script + inline
    `style=""` attrs) and calls `DisableTrustedTypesCSP()` for Svelte hydration.
    `SetupWebUIDataSource` makes `index.html` the default resource, so any
    client route the panel opens (e.g. `/ai-sidebar`) falls back to the SPA
    shell and SvelteKit's router renders it.
  - `chrome/browser/resources/stead_sidebar/BUILD.gn` — `grit("resources")` over
    the generated `.grd` → `stead_sidebar_resources.pak` + resource map.
- **`register-stead-sidebar.patch`** — hunks into shared files (see validation):
  `webui_url_constants.h` (host/URL consts), `chrome_web_ui_configs.cc`
  (register the config), `chrome/browser/ui/BUILD.gn` (sources + resources dep),
  `chrome/chrome_paks.gni` (pak + dep), `tools/gritsettings/resource_ids.spec`
  (ID range).

## Replace reading list — `repurpose-reading-list-side-panel.patch`

Implemented (verified against the exact Chromium 149 source — Helium doesn't
patch these files, so the hunks apply against vanilla):

- New `chrome/browser/ui/views/side_panel/stead_sidebar/stead_sidebar_side_panel_web_view.{h,cc}`
  — a minimal `SidePanelWebUIViewT<SteadSidebarUI>` loading
  `GURL(chrome::kSteadSidebarURL)` (chrome://sidebar), mirroring
  `ReadLaterSidePanelWebView` without the reading-list/tab-strip plumbing.
- `reading_list_side_panel_coordinator.cc` — its `CreateReadingListWebView`
  factory now builds the Stead view, so the existing `kReadingList` side-panel
  slot renders the Stead sidebar. (Reuses the slot rather than adding a new
  `SidePanelEntry::Id`, which would touch the id enum + histograms.)
- `chrome/browser/ui/views/side_panel/BUILD.gn` — adds the new sources.
- Helium's `remove-reading-list-from-app-menu.patch` already drops the reading
  list app-menu item, so this completes the removal.

## "Ask Stead" button — `ask-stead-button.patch`

The side-panel toolbar button + header label/icon come from the actions
framework, not the coordinator: `browser_actions.cc` registers the reading-list
slot via `SidePanelAction(kReadingList, IDS_READ_LATER_TITLE, …, kReadingListIcon,
kActionSidePanelShowReadingList, …)`. This patch:

- adds `IDS_STEAD_SIDEBAR_TITLE` = **"Ask Stead"** to `generated_resources.grd`
  (next to `IDS_READ_LATER_TITLE`), and
- points that `SidePanelAction` at `IDS_STEAD_SIDEBAR_TITLE` + `vector_icons::kChatIcon`
  (a chat bubble; already used in this file by the comments panel, so no new
  include).

So the button reads **Ask Stead** with a chat icon, and opening it shows the
Stead sidebar. The web view also uses `IDS_STEAD_SIDEBAR_TITLE` for its
WebContents title. All hunks diff-generated against the real 149 source.

## Pinned to the toolbar by default — `pin-ask-stead-by-default.patch`

`toolbar::RegisterProfilePrefs` (`toolbar_pref_names.cc`) builds the default
value of the `kPinnedActions` pref — it already default-pins Chrome Labs. This
patch appends `kActionSidePanelShowReadingList` (the "Ask Stead" action) to that
default list, so a fresh profile shows the **Ask Stead** chat button in the
toolbar out of the box (like Aside's "Ask Aside"). Because it's the pref
*default*, unpinning sticks (the pref gets an explicit value; it won't re-pin).
No migration / new pref needed; `kActionSidePanelShowReadingList` and
`actions::ActionIdMap` are already in scope in that file.

## Build-time validation (nothing is compiled yet — no build box)

All hunks were generated by `diff` against the **exact Chromium 149.0.7827.200
source** (fetched from googlesource) and re-anchored on lines Helium does *not*
patch (reading-list / read-later / side-panel comments), so they should apply
cleanly rather than with fuzz. Counts are verified. Still confirm at first build:

- **`ui` target grit-header dep (the one known gap).** `register-stead-sidebar.patch`
  adds `stead_sidebar_ui.{cc,h}` to the desktop side-panel sources and the pak +
  pak-dep to `chrome_paks.gni`, but the `ui` static_library needs a dep on
  `//chrome/browser/resources/stead_sidebar:resources` in its **desktop** deps
  block so the generated `chrome/grit/stead_sidebar_resources*.h` resolve. The
  reading-list equivalent is pulled in transitively (not a direct, greppable
  dep), so the exact spot couldn't be pinned without the tree — a
  "grit header not found" error will point right at it.
- **`resource_ids.spec` id.** Uses `includes: [9500]`, size `60`. grit validates
  ranges at build and prints a free range if it collides — adjust then.
- **grit resource-map symbol.** The data source uses
  `kSteadSidebarResources`; confirm that's the array name grit emits in
  `stead_sidebar_resources_map.h` (adjust if it differs).
- **`.top-chrome` host registration.** Confirm the side panel's
  `WebUIContentsWrapperT<SteadSidebarUI>` resolves `chrome://sidebar.top-chrome/`
  (host must match `kSteadSidebarHost`).
