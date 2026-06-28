# Stead chat WebUI (full page)

Wires the SvelteKit `/ai-chat` route up as a **full-page** Chromium WebUI —
the standalone chat surface (top bar, new-chat, optional artifact/agent panel),
as opposed to the compact side panel in `../sidebar/`.

Internal URL **`chrome://chat/ai-chat`** (shown as `stead://chat/ai-chat` via
name substitution). `SteadChatUI` is a plain `content::WebUIController` with a
`DefaultWebUIConfig` (a normal page/tab, **not** the side panel's TopChrome
config), modeled on Helium's full-page onboarding WebUI.

**Reuses the existing bundle.** The SvelteKit build is one SPA containing every
route, already vendored and packed into `stead_sidebar_resources.pak` by the
sidebar work. So the chat host serves the *same* `kSteadSidebarResources` and
just opens at `/ai-chat` — no new bundle, pak, or grd, and **no UI rebuild**.
(The pak name is sidebar-flavored but it's the shared Stead WebUI bundle; rename
to `stead_webui_resources` later if you want it generic across surfaces.)

## Patches
- `chat-webui-files.patch` — new `chrome/browser/ui/webui/stead_chat/stead_chat_ui.{h,cc}`
  (controller + config; same CSP relaxations + `DisableTrustedTypesCSP()` as the
  sidebar).
- `register-stead-chat.patch` — `webui_url_constants.h` (host/URL), register the
  config in `chrome_web_ui_configs.cc`, add sources to `chrome/browser/ui/BUILD.gn`.
  Stacks on top of `../sidebar/register-stead-sidebar.patch` (anchors on the
  sidebar's additions), so it must apply after it (series order handles this).

## Opening it
Once built, navigate any tab to `stead://chat/ai-chat`. A first-class entry point
(a "pop out to full chat" button in the sidebar, a toolbar action, or making it
the new-tab page) is a small follow-up — opening a real browser tab from WebUI JS
needs a tiny browser-side handler, so it pairs naturally with the first Mojo wire.

## Build-time note
Same shared gap as the sidebar: the `ui` target needs the
`//chrome/browser/resources/stead_sidebar:resources` dep so the grit headers
resolve (this controller includes them too). One `deps +=` line; the build
points at the exact spot.
