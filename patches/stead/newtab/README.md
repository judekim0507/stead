# Stead new tab page (replaces Chrome's NTP)

Makes every new tab show the SvelteKit `/new-tab` route instead of Chrome's New
Tab Page. There is **one** new-tab experience — Stead's. (Chrome's NTP WebUI
still exists in the binary but the browser never navigates to it for a new tab.)

## How it works

The browser decides the new-tab URL in `NewTabURLDetails::ForProfile` in
`chrome/browser/search/search.cc`. Helium's `always-use-better-ntp.patch` already
simplifies that to `chrome://new-tab-page/`. `newtab-ntp-redirect.patch` stacks
on top and points it at **`chrome://stead-newtab/new-tab`** instead.

The win: `GetNewTabPageURL()` returns that same URL, and NTP detection
(`IsNTPOrRelatedURL`) matches against `GetNewTabPageURL()` — so Stead's page is
automatically treated as the real NTP (empty/focused omnibox, etc.). No
hardcoded-URL fight.

## Patches
- `newtab-webui-files.patch` — new `chrome/browser/ui/webui/stead_newtab/stead_newtab_ui.{h,cc}`
  (full-page `DefaultWebUIConfig`, serves the shared SPA bundle at `/new-tab`;
  same CSP relaxations as the other surfaces).
- `register-stead-newtab.patch` — `webui_url_constants.h` (host/URL), register the
  config in `chrome_web_ui_configs.cc`, add sources to `chrome/browser/ui/BUILD.gn`.
  Stacks after the chat patches.
- `newtab-ntp-redirect.patch` — the one-line `search.cc` chokepoint change.
  Stacks after Helium's `always-use-better-ntp.patch` (submodule), so it applies
  cleanly against the post-Helium tree.

## Performance: prerendered, paints instantly

A new tab is shown constantly, so it must not wait for the SPA to boot. The
`/new-tab` route is **prerendered** to static HTML at build time
(`ui/src/routes/new-tab/+page.ts` → `ssr=true; prerender=true`, overriding the
app-wide `ssr=false`). The build emits `new-tab.html` containing the fully
rendered UI, and `SteadNewTabUI` serves that as its **default resource**
(`IDR_STEAD_SIDEBAR_NEW_TAB_HTML`, not the blank `index.html` shell). So a new
tab paints the real page with **zero JS**; the client only loads to hydrate it
for interactivity. (The sidebar/chat surfaces stay client-rendered SPA — they
open on user action, so instant-paint matters less; same prerender trick applies
if wanted.)

CSS is intentionally left as an external `<link>` (it's ~50KB Tailwind served
from the local pak — inlining it would bloat the HTML for a near-zero gain on a
no-network resource). Revisit only if profiling says so.

## Notes
- Reuses the shared `stead_sidebar_resources.pak` (the SPA has every route) — no
  new bundle.
- Chrome's `NewTabPageUIConfig` is intentionally left registered (lots of code
  references `chrome://new-tab-page`); it's just never reached for a new tab. If
  you later want `chrome://new-tab-page` / `chrome://newtab` typed in the omnibox
  to also land on Stead's page, add redirects for those hosts.
- Same shared build-time dep as the other surfaces (`stead_sidebar:resources` on
  the `ui` target).
