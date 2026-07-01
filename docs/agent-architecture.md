# Stead — Agent & Native Control Layer (design)

> The #1 goal is **performance + a super-light footprint**. This is an
> **agent-native** browser: the agent should be able to do basically everything.
> Design notes, refined with external review. Build-ready where marked "pinned."
>
> **The one-line thesis:** the moat is **not** "native Playwright." It is a
> *compact, native, observable browser-control substrate with model-friendly
> code ergonomics.* The **typed primitives are the contract**; the REPL is a
> thin ergonomic layer on top of them.

---

## 1. North star: beat Aside at *substrate*, not *brain*

```
Aside  = Pi (agent core) + pi-ai (OAuth/providers) + (Asidewright/CDP + MV3 extensions)
Stead  = Pi (or a port)  + pi-ai (or a port)        + (NATIVE control + NATIVE WebUI)
```

Aside's daemon is built on **Pi** (`earendil-works/pi`) + **pi-ai**; ours is the
same lineage. The brain is *shared* — we are **not** out-thinking Aside's agent.
**Stead's entire edge is the substrate:** native control instead of
Playwright/CDP/Node, native WebUI instead of extensions. Same intelligence, a
fraction of the weight.

Corollary: **the moat = "Aside's delta over Pi."** Stock Pi gives the agent core
+ OAuth + harness tools. What Aside *added* — the `repl`, the optimized a11y
snapshot, tab control — is exactly what Stead rebuilds natively.

---

## 2. Diagnostic — what Aside actually costs (measured, live)

- **~3,862 MB across 45 processes** total.
- **"Aside Daemon" (Node, = Pi): ~140 MB**, resident.
- **~470–550 MB in `--extension-process` renderers** (4 of them: 143/119/112/98 MB).
- Manifest: **MV3, content scripts on `<all_urls>`, the `debugger` permission**
  → content-script perception + **CDP automation**.

Aside's *agent overhead* over vanilla Chromium ≈ **600–700 MB**.

**The footprint reframe:** **~550 MB is won by architecture alone** (no extensions
→ no extension renderers → no content scripts) — independent of the brain. The
brain is the *smaller* ~130 MB lever. And because Stead is **agent-native**
(agent ≈ always-on), a Node/Pi brain is effectively always-resident (~140 MB) —
lazy-spawn won't save it — so for the *last mile* the **Rust port of Pi's
`agent`+`ai`** is justified (you've already crushed Aside by ~500 MB regardless).

---

## 3. Performance model: two things, opposite answers

- **Latency (responsiveness)** is **model-bound** — the harness language adds
  single-digit ms against hundreds of ms of inference. Node is fine here.
- **Footprint** is where the harness bites (~+50 MB download + ~50–140 MB RAM).
  This is the real lever and what "super lightweight" points at.

The real perf wins are **in the data path, not the brain's language**: native
perception/action in the browser process, the brain only reasons and ships small
tool-call messages, streaming end-to-end.

---

## 4. The SOTA lesson — and where it stops

From Aside's blog. **Perception = a custom-optimized accessibility tree** (not
DOM, not vision): *"70% smaller with key information packed upfront."* DOM-dumping
loses (*"divs and styles make up 90% of the content… the model degrades fast"*);
vision is **fallback only**. **Action = the agent writes code:** *"follow the
model's training data — what data have LLMs seen the most? Code."* Their prompt
*"does not teach Playwright."* Whole prompt+tools = **10K tokens** (Claude Code = 20K).

**Where it stops (correction):** Aside can be *Playwright-identical* because they
wrap real Playwright/CDP — they get it free. We are native, so reimplementing
Playwright's full surface (auto-wait, locators, frames, dialogs, downloads, file
chooser, network events, nav races, actionability) is the **wrong target**.
We define a **small, Playwright-*shaped* dialect** — familiar enough to be
training-aligned, not a clone. Training-alignment comes from *shape and naming*,
not from a 1:1 API.

---

## 5. The control layer (the moat): a compact, native, *observable* substrate

This is #1 — the novel/risky part, and where the footprint + speed + (per §6)
*accuracy* wins live. Two framings to hold:

- **The typed primitives are the real contract** (§11). The REPL/dialect is a
  thin ergonomic layer above them — don't over-invest in it early.
- **"Observable" is part of the moat,** not just safety: structured events (§9),
  an audit log, and the lock overlay (§12) are how a user *trusts* an agent
  driving their real session. Trust is a differentiator.

Honest catch: this is the first phase that **needs the Chromium build** to
develop (C++ wired into Blink/content — can't be faked dry like the WebUI).

---

## 6. Perception — 3-tier, AX-first (pinned to 149)

A hybrid pipeline; cheap tiers first, expensive last.

**Tier 1 — accessibility-tree snapshot (primary):**
- Enable scoped `ui::kAXModeBasic`, then read each active frame's live
  browser-side `AXTreeManager` via `RenderFrameHost::GetAXTreeID()`. Walk the
  frame-local `ui::AXTree` roots and stitch child frames by
  `AXTreeManager::ForChildTree(...)` / `kChildTreeId`.
- Do **not** mint actionable refs from Chromium's combined snapshot output:
  `AXTreeCombiner` renumbers node ids across trees, which is correct for a
  single display tree but wrong for `AccessibilityPerformAction` against a
  frame-local `AXTreeID`. `RequestAXTreeSnapshot(cb)` is acceptable as a cold
  AX warmup/retry signal; its combined result is not the source of `NodeRef`s.
- Per node from `AXNode`/`AXNodeData`:
  - `data().role` → `ax::mojom::Role` (string via `ui::ToString`).
  - **`data().IsClickable()`** — native clickability that *should* include JS
    click listeners (the exact thing Aside must guess at with `cursor:pointer`).
    **Treat this as a hypothesis, not a bet** — validate with the §16 clickability
    fixture before relying on it; if it proves incomplete, the 3-tier fallback
    (DOM probe → vision) covers the gap. The architecture does not depend on it.
  - `GetStringAttribute(kName)` / `kValue`; `IsTextField()`; `GetCheckedState()`;
    `kFocusable` state; `GetRestriction()==kDisabled`.
  - **strip** `IsIgnored()`/`IsInvisibleOrIgnored()`, collapse
    `kGenericContainer`/`kNone` → the "70%-smaller / high-signal" filter (the AX
    tree is already pre-semantic, so we start cleaner than a DOM dump). Ignored
    containers are collapsed with Chromium's unignored child traversal, not
    pruned wholesale.
  - bounds via `AXTree::GetTreeBounds(...)`, treated as tree/viewport geometry
    for screenshots and a **hint** for probes. Do not treat these as universal
    screen coordinates; node screenshots transform the owning frame's bounds
    through `RenderWidgetHostView::TransformPointToRootCoordSpaceF(...)` before
    `CopyFromSurface`, and fail closed if the transform is unavailable.
    OOPIF/iframe local probing still needs DOM hints.

**Tier 2 — targeted DOM/style probe (for ambiguous refs only):** an on-demand,
*per-node* isolated-world JS probe (computed style, geometry, occlusion via
`elementsFromPoint`) to disambiguate hostile/custom UIs the AX tree distorts. It
uses AX bounds as a fast hit-test hint, then falls back to DOM hints
(`id`/`name`, or `tag+class`), and can still run when AX has no usable bounds if
strong hints exist. Tag-only/class-only fallback is too broad and should fail
closed. Iframe/OOPIF coordinate-space ambiguity should not make the probe report
a false miss. Cheap because it's targeted, not a full-page walk.

**Tier 3 — screenshot + vision (Computer Use):** last resort for AX-opaque
custom widgets. (`Screenshot` op, optionally annotated with refs.) Browser-side
screenshots stay taint-gated and capped; the brain protocol may forward a small
PNG as a Pie image tool-result block, while oversized images are omitted with
metadata instead of being streamed as unbounded JSON/base64 text.

---

## 7. Refs — compound, not a bare id (correction)

A bare `AXNodeID` is too thin, and a single combined ref conflates *frame* and
*node* identity — but a frame target (for `evaluate`) isn't an AX node. **Split them:**

```
FrameRef = { tab_id, frame_token /*stable frame id; maps to AXTreeID/RFH internally; handles OOPIF*/, snapshot_generation }
NodeRef  = { FrameRef frame, ax_node_id }
```

Why: across **OOPIFs / cross-origin iframes** node ids aren't globally unique;
trees regenerate (stale-ref detection via `snapshot_generation`); actions must
route to the owning `RenderFrameHost` (via `frame_token`). **Node** ops take a
`NodeRef`; **`evaluate`/frame** ops take a `FrameRef`. MVP populates the
main-frame case first, but when Chromium exposes a child frame through AX
`kChildTreeId`, descendants inherit that child `frame_token`. Snapshot indexes
are keyed by `{frame_token, ax_node_id}`, never by bare node id, and `ax_node_id`
is always the owning frame tree's native node id, never an `AXTreeCombiner`
renumbered id. The contract carries the OOPIF shape from day 1.

Committed navigations bump/clear the tab's snapshot generation immediately so
old refs become stale before the next action. Same-document navigations still
stale refs, but do not clear credential taint. Taint is document/RFH-token
scoped: active tainted documents block reads and raw input; inactive
back-forward-cache documents keep their taint but do not block the active page,
and become blocking again if restored. `RenderFrameHost` deletion or explicit
post-submit cleanup clears that frame's taint. Same-RFH document replacement
needs a lifecycle-accurate hook before it may clear taint; `DidFinishNavigation`
alone is not authoritative enough because Chromium can keep the old document in
BFCache.

---

## 8. Action — two tiers, both native + trusted (pinned)

1. **Semantic (primary), by `ref`:**
   `RenderFrameHost::AccessibilityPerformAction(ui::AXActionData{action, target_node_id})`
   (routed to the ref's frame). No coordinate math, cross-frame, trusted:
   `kDoDefault` (click) · `kFocus` · `kSetValue`/`kReplaceSelectedText` (fill) ·
   `kScrollToMakeVisible` · `kScrollUp/Down` · `kShowContextMenu`.
   Dispatch first checks the latest snapshot index and the frame's live
   `AXTreeManager` by `frame_token`, so `ok=true` means "accepted for dispatch,"
   not "blindly sent to a possibly-dead node."
2. **Synthetic real input (fallback), by coords:**
   `RenderWidgetHost::ForwardMouseEvent / ForwardKeyboardEvent / ForwardWheelEvent
   / ForwardGestureEvent` (`blink::WebMouseEvent` etc.). **Trusted**
   (`isTrusted=true`) — unlike Aside's `content.js` synthetic events. For
   mousedown/up sequences, hover, drag, pixel clicks, key combos, custom widgets
   that ignore `kDoDefault`.

Navigation: `WebContents::GetController().LoadURLWithParams(...)`; tabs via
`TabStripModel`.

---

## 9. Events — structured + ordered (correction)

Not `OnTabEvent(kind: string)`. Async events are **typed, payload-bearing,
correlated, and ordered** — part of agent correctness *and* audit:

- **Every event carries** `{event_id, sequence /*profile-global monotonic*/, tab_id, frame_token,
  originating_action_id?}`. Actions return an `action_id`; the events they cause
  reference it. This is how the agent reasons about **causality** (a click → the
  navigation/popup/download it triggered), how nav races are disambiguated, and
  how **audit replay** reconstructs "what did the agent just do."
- Variants: `navigated{url, same_doc}` · `popup{new_tab_id}` ·
  `download{filename, mime, bytes}` · `dialog{type, message, handle}` (alert/
  confirm/prompt/beforeunload — needs accept/dismiss) · `permission_prompt{kind}`
  · `auth_redirect{origin}` · `file_chooser{handle}` · `tab_opened` ·
  `tab_closed` · `action_dispatched` (instrumentation).

Delivered **in order** over a `ControlObserver` as `OnEvent(ControlEvent)`: one
typed envelope with `ControlEventType` plus typed optional payload fields. This
is still not `kind: string`; the enum and payload structs are the contract.
Subscribing to `ControlObserver` also warms observation for current profile tabs
and enables the scoped AX mode, so event capture does not depend on a prior
`ListTabs()` call.
High-frequency progress events are coalesced before they reach the observer:
downloads emit creation, terminal/state changes, and coarse byte-progress
milestones rather than every backend progress tick.

---

## 10. The REPL & the **two distinct JS worlds** (correction)

These are different trust/performance/failure domains; keep them separate:

- **The agent REPL/dialect** runs in a **utility-process V8 isolate** with async
  Mojo bindings to **`AgentControl`** (the brokered surface, §11 — never raw
  `BrowserControl`). Isolated from the browser process — a hung or runaway agent
  script can't take the browser down.
- **`page.evaluate(js)`** marshals code into the **renderer's isolated world**
  via `RenderFrameHost::ExecuteJavaScriptInIsolatedWorld(...)` (page DOM access,
  runs in the page's process), routed by the ref's `frame_token`.

The **dialect** is small + Playwright-shaped and is *thin sugar* over the §11
primitives: `snapshot()`, `click(ref)`, `fill(ref, text)`, `focus(ref)`,
`evaluate(js)`, `goto(url)`, tabs; `locator()` later. No CDP, no Node, no
Playwright npm.

---

## 11. The contract — three layers (security is *topology*, not convention)

The surface that *approves* a permission must not be able to *drive* the page.
So the raw primitives are **private**, and everyone talks to a **broker**:

```
  WebUI ──BrainConsole────┐                         brain ──AgentControl──┐
  (chat / sessions /      │                         (gated page-driving)  │
   provider auth)         ▼                                               ▼
              ┌──────────── BrainBroker (browser process) ──────────────────┐
              │  launches bundled stead-brain · framed JSON stdio · streams │
              │  session/model events · mediates tool calls                  │
              └───────────────────────────┬──────────────────────────────────┘
                                          │
  WebUI ──ControlConsole──┐              │
  (approve / audit /      │              │
   cancel; NO driving)    ▼              ▼
              ┌──────────── ControlBroker (browser process) ─────────────────┐
              │  action-class · confirmation gates · redaction · audit log ·  │
              │  cancel/interrupt · scoped capabilities                       │
              └───────────────────────────┬───────────────────────────────────┘
                                          │  holds the ONLY Remote (private)
                                  ┌───────▼────────┐
                                  │ BrowserControl │  raw primitives (§6–§10):
                                  │ (browser proc) │  AX snapshot, AX actions,
                                  └────────────────┘  trusted input, eval, tabs
```

- **`BrowserControl`** (private) — raw primitives, **no policy**. Only the broker
  holds a `Remote`.
- **`AgentControl`** (brain ↔ broker) — gated page-driving. Every call is
  classified → gated → redacted → audited → cancellable before it reaches
  `BrowserControl`.
- **`ControlConsole`** (WebUI ↔ broker) — approve/deny, audit,
  cancel; subscribe to events *to display*. **No `Click`/`Fill`/`Eval`** — the
  WebUI structurally cannot drive the page.
- **`BrainConsole`** (WebUI ↔ BrainBroker) — create/load sessions, send/cancel
  turns, list the Pie-backed model catalog, list provider auth, start
  Anthropic/Codex OAuth, import Codex auth, and subscribe to streamed brain
  events. **No `AgentControl` binding**.

Implementation wiring: the Stead WebUI controllers (sidebar, full-page chat,
new-tab) register `ControlConsole` and `BrainConsole` with Chromium's WebUI
binder map / broker registry. `AgentControl` is not registered for WebUI; it is
the brain-side browser-control surface.

```
struct FrameRef { int32 tab_id; string frame_token; uint32 snapshot_generation; };
                                  // frame_token maps internally to AXTreeID/RFH
struct NodeRef  { FrameRef frame; int32 ax_node_id; };

struct AxNode { NodeRef ref; string role; string name; string? value;
  bool clickable;            // AXNodeData::IsClickable() — a HYPOTHESIS (§6/§16)
  bool editable; bool focused; bool disabled; string? checked;
  gfx.mojom.Rect? bounds;    // AX tree/viewport geometry; not screen coords
  array<AxNode> children; };
struct Snapshot { int32 tab_id; string url; string title; uint32 generation; AxNode root; };
struct FileChooserInfo { string handle; string state; string mode; string title;
  string default_file_name; array<string> accept_types; bool allow_multiple;
  bool upload_folder; bool need_local_path; bool use_media_capture; };

struct ActionResult {        // shapes the agent loop
  int32 action_id;           // the events this action causes reference it
  bool ok; string code; string message;
  bool stale; bool needs_snapshot;     // ref generation old -> re-snapshot
  bool needs_confirmation;             // hit a security gate (§12)
  bool target_missing; string? blocked_by;  // "overlay"|"dialog"|"permission"|null
  uint32 new_generation;
};
struct ReadResult { bool ok; string? blocked_by; };  // gated/tainted reads can be denied (§12/§15)

// EventMeta.sequence is PROFILE-GLOBAL monotonic (one ordering across all tabs),
// so cross-tab causality (click in tab A -> popup tab B) and audit replay are
// unambiguous. { event_id, sequence, tab_id, frame_token, originating_action_id? }.
enum ControlEventType { Navigated, TabOpened, TabClosed, Popup, Download,
  Dialog, PermissionPrompt, AuthRedirect, FileChooser, ActionDispatched };
struct ControlEvent { EventMeta meta; ControlEventType type;
  string url; string title; string code; string message; int32 related_tab_id;
  DownloadInfo? download; DialogInfo? dialog;
  PermissionPromptInfo? permission_prompt; AuthRedirectInfo? auth_redirect;
  FileChooserInfo? file_chooser; };
interface ControlObserver {
  OnEvent(ControlEvent event);
};

Implementation note: the native layer now observes Chromium
`PermissionRequestManager` prompts per tab and emits typed, ordered
`permission_prompt` events. It is perception-only: the event stream reports
shown/removed/finalized/decided states, but accepting/denying stays out of
`AgentControl` until the broker policy surface explicitly grows that capability.
Committed primary-frame auth redirects are also surfaced as typed events, but
privacy-scoped to `{origin, provider_hint, reason}` so OAuth/SAML query tokens
and account-identifying URL parameters are not exposed to the model.
The dialog path currently covers `beforeunload` via `WebContentsObserver`;
alert/confirm/prompt are observed through a minimal production observer hook on
Chromium's `TabModalDialogManager`; active dialogs get opaque broker handles and
are accepted/dismissed only through `AgentControl.HandleDialog`.
File chooser perception follows the same brokered-handle pattern via
Chromium's `FileSelectHelper`: `file_chooser` events expose mode/title/accept
metadata but never local paths, and selection/cancel flows only through
`AgentControl.HandleFileChooser`.

struct CredentialRef { string handle; string label; string source; bool has_totp; bool has_passkey; };
                       // handle = opaque; label = coarse/user-set; NO username until approved (§15)

// brain-facing: gated page-driving. EVERY mutating call is action-shaped
// (returns ActionResult = action_id + gate/audit). Mirrors the primitives, BROKERED.
interface AgentControl {
  GetSnapshot(int32 tab_id) => (Snapshot s);                 // Tier 1
  ProbeNode(NodeRef ref) => (ReadResult r, NodeProbe? p);    // Tier 2 (denied on tainted frames, §15)
  Screenshot(int32 tab_id, NodeRef? ref) => (ReadResult r, mojo_base.mojom.BigBuffer? png);  // Tier 3 (denied on tainted frames, §15)
  Click(NodeRef ref) => (ActionResult r);
  Fill(NodeRef ref, string text) => (ActionResult r);
  Focus(NodeRef ref) => (ActionResult r);
  ScrollIntoView(NodeRef ref) => (ActionResult r);
  ShowContextMenu(NodeRef ref) => (ActionResult r);
  MouseMove(int32 tab_id, gfx.mojom.Point pt) => (ActionResult r);  // HIGH-RISK (§12)
  MouseDown(int32 tab_id, gfx.mojom.Point pt, int32 button, int32 click_count) => (ActionResult r);  // HIGH-RISK
  MouseUp(int32 tab_id, gfx.mojom.Point pt, int32 button, int32 click_count) => (ActionResult r);  // HIGH-RISK
  MouseClick(int32 tab_id, gfx.mojom.Point pt, int32 button, int32 click_count) => (ActionResult r);  // HIGH-RISK (§12)
  MouseDrag(int32 tab_id, gfx.mojom.Point from, gfx.mojom.Point to, int32 button, int32 steps) => (ActionResult r);  // HIGH-RISK
  Key(int32 tab_id, string key, int32 modifiers) => (ActionResult r);  // HIGH-RISK
  Scroll(int32 tab_id, int32 dx, int32 dy) => (ActionResult r);  // HIGH-RISK raw wheel input (§12)
  Navigate(int32 tab_id, url.mojom.Url url) => (ActionResult r);
  OpenTab(url.mojom.Url url, bool agent_owned) => (ActionResult r, int32 tab_id);  // navigation-class, audited
  CloseTab(int32 tab_id) => (ActionResult r);
  HandleDialog(string handle, bool accept, string prompt_text) => (ActionResult r); // audited; confirm accept gates
  HandleFileChooser(string handle, array<string> paths) => (ActionResult r); // file-access gated; empty paths = cancel
  ListTabs() => (array<TabInfo> tabs);                       // COARSE auth hint only (§14)
  Eval(FrameRef frame, string js) => (ActionResult r, string? json_result);  // HIGH-RISK: gated+audited (§12); null if denied/tainted (§15)
  // credentials — never-reveal; origin-scoped + intent-gated (§15)
  ListCredentials(int32 tab_id, url.mojom.Origin origin) => (ReadResult r, array<CredentialRef> creds);  // opaque handles, NO secrets/usernames
  FillCredential(CredentialRef cred, NodeRef username_field, NodeRef password_field) => (ActionResult r);  // credential-class; TAINTS frame
  FillTotp(CredentialRef cred, NodeRef field) => (ActionResult r);            // credential-class; TAINTS frame
  MarkCredentialInjection(FrameRef frame) => (ActionResult r);               // skill-driven 3rd-party fill: taint trigger (§15)
  AddObserver(pending_remote<ControlObserver> observer);     // events for the agent
};

// WebUI-facing: approval / audit / cancellation — NO page driving.
interface ControlConsole {
  RespondToConfirmation(int32 action_id, bool approve);
  GetAuditLog(...) => (array<AuditEntry> entries);
  Cancel(int32 tab_id);                                       // interrupt the agent
  AddObserver(pending_remote<ConsoleObserver> observer);      // confirmations + status to render
};

// WebUI-facing: brain sessions / provider auth / chat — NO page driving.
interface BrainConsole {
  Initialize() => (BrainResult r);
  CreateSession(string? title, string origin_surface) => (BrainResult r);
  ListSessions() => (BrainResult r);
  LoadSession(string session_id) => (BrainResult r);
  SendMessage(string session_id, string text, BrainTabContext? tab_context,
              BrainModelSelection? model) => (BrainResult r);
  CancelTurn(string session_id) => (BrainResult r);
  ListModels() => (BrainResult r);        // Pie registry + auth capabilities
  ListProviderAuth() => (BrainResult r);
  StartProviderOAuth(string provider) => (BrainResult r);
  ImportCodexAuth(string? path) => (BrainResult r);
  SetProviderApiKey(string provider, string api_key) => (BrainResult r);
  RespondToUserPrompt(string session_id, string tool_call_id,
                      string response_json, bool cancelled) => (BrainResult r);
  AddObserver(pending_remote<BrainObserver> observer);
};
```

(`BrowserControl`, the private raw interface, is the broker's internal impl —
same driving methods, no policy. Not shown.)

---

## 12. Security — enforced by the broker, not just described

Policy is enforced by the §11 **topology**, not convention: the broker is the
single chokepoint; the WebUI structurally can't drive, and the brain can't reach
`BrowserControl` except through it. Per call the broker applies:

- **Action class** — `read-only · navigation · form-entry · destructive ·
  payment/money · credential · file-access`, inferred from the op + the target
  node's semantics (role/name/field type).
- **Confirmation gates** for high-risk classes → `needs_confirmation`, surfaced
  in the chat (the permission bar) and answered via
  `ControlConsole.RespondToConfirmation`. "Cancel my flight" = destructive/money
  → must confirm. Approval grants are scoped to the action class/op/target
  material, single-use, short-lived, and bounded.
- **`Eval` + raw input are high-risk by default.** `Eval` is arbitrary code — it
  can read hidden DOM, inspect/submit forms, mutate state, and **bypass snapshot
  redaction** → gate + heavily audit (or require an explicit capability).
  `MouseClick`/`Key` bypass *semantic* classification (a pixel click carries no
  "payment button" meaning) → treat as elevated / require a justifying ref.
- **Redaction** — password/OTP/payment values are stripped at snapshot-build
  time using AX field type plus non-secret DOM metadata (`name`/`id`/class like
  `cc-number`, `cvv`, `expiry`) and Chromium form hints (`autocomplete`,
  `input_type`, placeholder/description/tooltip); the model never sees cookie
  values or account metadata (only coarse `likely_authenticated`).
- **Broker input/output caps** — bounded snapshot strings, `Eval`
  scripts/results, semantic fill values, dialog prompt text, file chooser
  paths/counts, screenshot dimensions, drag steps, and scroll deltas. The
  control layer is performance-first; no unbounded payload gets to a browser
  primitive.
- **Post-fill taint** — after a credential fill the frame is secret-tainted;
  reads (snapshot/screenshot/`Eval`/probe) on it are restricted until the taint
  clears (§15). Raw input (mouse/key/wheel) is treated more conservatively: if
  any active frame in the tab is tainted, tab-wide raw input is blocked. Stops
  the agent reading back or manipulating a just-filled password/OTP.
- **Mode-dependent strictness** — borrowed-tab (your real session, §14) stricter
  than an isolated agent tab.
- **Audit log** — every action (class, target, result, `action_id`) + the events
  it caused (via `originating_action_id`), replayable.
- **Cancel/interrupt + visible lock** while driving. Cancellation must also cut
  off late async completions (cold snapshots, probes, screenshots, `Eval`) so a
  cancelled tab cannot resume the agent loop with stale perception or results.

Building the broker **before** the primitives is deliberate — retrofitting policy
around raw browser-control later is painful and leaky.

This isn't bolt-on: it's how a user can *let* an agent touch their logged-in
sessions at all.

---

## 13. The brain (v1 runtime)

V1 is a **bundled Rust helper**, not in-process browser Rust and not a
user-managed daemon:

```
Stead WebUI ──BrainConsole──► Browser BrainBroker
Browser BrainBroker ◄──framed JSON stdio──► bundled stead-brain
stead-brain ──Pie agent/core + pie-ai──► providers
stead-brain tool calls ──JSON──► BrainBroker ──AgentControl──► ControlBroker
```

- **Lineage:** `c4pt0r/pie` provides the agent loop/runtime base. Stead vendors a
  pinned Pie copy under `../brain/vendor/pie` and builds a product helper around
  `crates/agent`/`crates/ai` concepts, not Pi's coding-agent shell.
- **Process model:** the browser owns the helper lifecycle. Lazy-start on first
  chat/auth use, keep warm per profile, kill on profile shutdown, restart on
  crash. It is "baked in" because the binary ships inside `Stead.app`; there is
  no separate install, extension, Node daemon, or user-managed service.
- **Protocol:** newline-delimited JSON over stdio for V1. Every message carries
  `protocol_version` and `request_id`; streamed brain events are forwarded to
  WebUI over `BrainConsole`.
- **Provider auth:** `pie-ai` provider streaming is used directly. Anthropic
  OAuth goes through Pie's PKCE helper; OpenAI Codex OAuth uses the Codex-compatible
  PKCE flow and can import `~/.codex/auth.json`. Provider credentials are stored
  in macOS Keychain by default; JSON file storage is only an explicit dev/test
  fallback and legacy migration source.
- **Model catalog:** the WebUI does not hardcode provider/model lists. It calls
  `BrainConsole.ListModels()`, which forwards `list_models` to the bundled helper;
  the helper returns a catalog derived from Pie's compiled `list_models()` registry
  plus auth capabilities/status for the product-supported providers.
- **Tool boundary:** the helper never opens Mojo. Browser/page tools are requested
  as JSON tool calls and must be fulfilled by the browser-side `BrainBroker`
  through `AgentControl`.
- **Skills:** the helper loads Pie-style markdown skills from
  `agents/main/skills` into Pie's native skill catalog and exposes the matching
  `Skill` invocation tool. Stead also compiles in an initial browser-native skill
  library for credential handoff, Gmail, GitHub, Notion, and artifact creation;
  user-authored skills can override a bundled skill by name.
- **Memory:** the helper owns `agents/main/memory` and exposes a single Pie-style
  `memory` tool with `save/list/read/search/forget` actions. Memory is for
  durable, non-secret user/project facts only; provider secrets, credentials,
  cookies, TOTP codes, payment data, and tainted browser-control payloads are
  forbidden and remain outside transcripts/memory.

### Session persistence (on-disk) — §14's "shared store," made concrete

The brain owns a directory tree (the Pi/Aside model — Aside's daemon *is* Pi, so
this is verified against its live on-disk layout):

```
<root>/u/<id>/agents/main/             # agent home
  AGENTS.md   SOUL.md                  # instructions + persona
  memory/                              # persistent non-secret agent memory
  skills/                              # the skills library (§15)
  sessions/<YYYY-MM-DD>_<rand>/        # ONE dir per chat
    messages.jsonl                     # append-only transcript
    attachments/                       # user-provided inputs for THIS chat
    tmp/                               # scratch files for THIS chat
    artifacts/                         # files the agent created in THIS chat
    meta.json                          # title, created/updated, origin surface, tab ctx
```

- **`messages.jsonl`** — append-only, one JSON object per line, flushed per turn
  (crash-safe). Three roles:
  - `user`       — `{role, content, timestamp}`
  - `assistant`  — `{role, content, timestamp, model, provider, usage, stopReason, responseId}`
  - `toolResult` — `{role, content, timestamp, toolName, toolCallId, isError, details}`

  The assistant metadata (model / provider / `usage`) makes cost and resume
  reconstructable. **Resume = replay** the file into context; **list = scan**
  `sessions/` by `meta.json`.
- **`artifacts/`** — the default landing spot for the agent's `write_file`;
  scoped to the conversation, travels with it, browsable from the UI.
- **`tmp/` / `artifacts/` tool ergonomics** — when the Pie-facing file tools
  are installed for a turn, the current chat id is supplied automatically for
  `session_tmp` / `session_artifacts`; models do not need to manually thread a
  `session_id` for normal artifact creation.
- **Working folder and file modes** — the current chat session directory is
  always the agent's working folder. Bare relative paths resolve inside that
  session directory, so `tmp/foo.py` and `artifacts/report.docx` are ordinary
  file-tool paths. Default file access is **session-only**: no Downloads shortcut,
  no arbitrary absolute paths, and `attachments/` is read-only. Approved folders
  require an explicit `approved_roots` mode; full-computer access requires an
  explicit `full_disk` mode. Both modes keep the session directory as the working
  folder and continue to canonicalize paths and reject escapes.

Ties to the rest:
- **§14 surfaces are views into `sessions/`** — `SessionSelector` and the new-tab
  "Recent chats" list it. The WebUI reads session list/history **via the brain's
  session surface**, not raw FS — same broker discipline: the UI asks, it isn't
  handed filesystem access.
- **Secret-free by construction** — the never-reveal boundary + snapshot redaction
  (§12/§15) mean credentials never enter the agent's context, so they're never
  written to `messages.jsonl` either. The transcript inherits redaction for free.
- **Root:** Mac-native `~/Library/Application Support/Stead/` (or a `~/.stead/`
  dotdir), with the Pi-style `agents/main/sessions/…` layout underneath so the
  brain — Pi or a Rust port — works unchanged.

---

## 14. Usage model — surfaces, sessions & the two tab modes

**Surfaces are views into ONE shared session store.** Sidebar (`stead://sidebar`,
*bound* to a tab), full-screen chat (`stead://chat`, *unbound*), and the new-tab
"Recent chats" are entry points into a surface-agnostic session store. Start a
chat in one, continue it in another — the `SessionSelector` and the new-tab list
browse the same store. The conversation is durable; the surface is just the view.

**Two tab modes:**
- **A — agent tab:** agent `OpenTab(agent_owned=true)` → a **"Stead" tab group** +
  lock/dim overlay. The agent owns its lifecycle. Its workspace.
- **B — take over (borrow):** the agent operates on an **existing** tab (from
  context or `ListTabs`). Overlay only **while acting**; control returns on
  done/stop; the tab **stays the user's** (never reclassified).

Same mechanism (tab-scoped ops); only the target tab + UI dressing differ.

**Surface sets the default; the resolution tree overrides it:**
1. explicit mention ("my united tab") → resolve via `ListTabs` → use it
2. else the **sidebar's bound tab**
3. else `ListTabs()` → **adopt a relevant existing tab** (esp. authenticated) → B
4. else **open a fresh agent tab** → A

**Session inheritance — "acts as you":** adopting an already-open tab inherits the
user's **real session** (cookies/account). "Cancel my flight" *requires* it (a
cold tab hits a login wall). So prefer adopting an **authenticated** existing tab;
spin a fresh agent tab only when there's nothing to adopt. This is the payoff of
running inside the user's real profile — the agent acts **as you**, unlike a
sandboxed/headless cloud agent. `ListTabs` returns only **coarse** hints —
URL/title/domain and a `likely_authenticated` boolean (derived from cookie
*presence* for the origin or visible logged-in UI). It **never** exposes cookie
names/values or account metadata to the model (privacy boundary — see §12).

---

## 15. Credentials, the Stead Vault & skills

The agent should **log in as you without ever seeing the secret.** Not a new
subsystem — it's the §11 broker's highest-sensitivity action class (`credential`)
plus a native credential store.

### The Stead Vault (built-in, native — not an extension)

Aside ships a **Bitwarden-fork extension** for its vault — which lives in the
`--extension-process` renderers we're killing (§2). Stead is a native Chromium
fork, so it gets *most of a vault* without an extension: `components/password_manager`
(already in the binary, OS-keychain-backed via `OSCrypt`), branded the **Stead
Vault**. Chromium reliably gives **logins + autofill + generation + WebAuthn
pieces** locally; **TOTP and local (non-synced) passkey storage are NOT assumed** —
they may be Google-account-tied, so **verify against the Helium/ungoogled patch set
(a spike, §18) before promising them.** What's confirmed is native, ~0 extra
footprint, local-first. Surfaced as a native WebUI (`stead://vault`, the same Svelte
app) for view/edit/add, managing agent grants, and the audit log.

### How the agent uses the Vault — the never-reveal fill

Three structural guarantees keep the plaintext out of the model — defense in depth:

1. **The fill is native.** The secret lives in the browser process
   (`PasswordStore` / `OSCrypt`); `FillCredential` hands it to Chromium's native
   autofill, which fills the renderer directly. It never crosses into the agent's
   V8 isolate or the model context.
2. **The interface has no secret field.** `FillCredential` returns an
   `ActionResult` — there is *structurally no channel* to return a password.
3. **Snapshots redact field values** (§12) — even reading a filled password,
   OTP, or payment field reports no value.

The flow, entirely through the broker as the **`credential`** class:

```
agent → ListCredentials(origin)
   broker → Vault → [{handle, label:"work", source:"stead_vault", has_totp, has_passkey}]  // opaque; NO username/secret
agent → FillCredential(handle, {username_ref, password_ref})
   broker: class=credential → gate (confirm / pre-authorized?) → ensure Vault unlocked
         → read secret IN browser process → native autofill into the two field refs
         → ActionResult{ok}  (no secret) → audit{cred used, origin, action_id}
```

Implementation status: the native control layer already exposes these brokered
credential methods and routes them through the credential-class gate/audit path,
but the Vault backend is intentionally fail-closed until the §18 spike verifies
the password-manager/TOTP/passkey pieces in the Helium patch set. Third-party
manager skills can still call `MarkCredentialInjection(frame)` to trigger the
same post-fill taint path.

- **Enumerate, don't reveal:** `ListCredentials` is **origin-scoped + intent-gated**
  and returns **opaque handles + coarse labels** (a user-set nickname, or "Account 1")
  + capability flags — **not the username** by default (usernames are account
  metadata; revealed only after the user approves credential use for that origin).
  Enough for the agent to *choose* ("my work account" → that handle), never the
  password/TOTP/passkey secret.
- **TOTP & passkeys:** `FillTotp(cred_id, ref)` generates and fills the current
  code natively; passkey logins run the native WebAuthn ceremony (Touch ID /
  user-presence is a built-in gate). The agent never sees a code or key.
- **Sign-up / generation:** the agent can request a generated password — the Vault
  generates, fills the password + confirm fields, and offers to save the new
  entry. The agent orchestrates "generate → fill → save"; the value stays native.

### Post-fill tainting — the secret is now *in* the page

Never-reveal covers *injection*, not *afterward*: once filled, the secret sits in
the field (a **TOTP especially** may land in plain visible text). So `FillCredential`
/ `FillTotp`, third-party `MarkCredentialInjection`, and any brokered semantic
`Fill` into a credential/payment-looking field **taint the target frame**. While
tainted the broker tightens every *read*: snapshots redact the tainted fields,
`Screenshot` is blocked, and `Eval` / `ProbeNode` on that frame are gated or
denied. Full-tab screenshots and raw `Key`·`MouseClick`/drag/wheel are blocked
tab-wide if any active frame is tainted, because raw input cannot safely prove
which frame will consume it.
Late async read completions are checked again and dropped if the frame becomes
tainted after dispatch but before the result returns.
Taint is retained on inactive BFCache documents, ignored while inactive, and
re-applied if restored; it clears only when the tainted RFH is actually deleted
or once an explicit post-submit cleanup proves the secret field is gone.
**This is what actually keeps the secret from the agent after the fill** — in both
the Vault and third-party paths.

### The Vault lock is the user's, not the agent's

Critical property: **the agent can *use* an unlocked Vault but cannot *unlock* it.**
If the Vault is locked when a credential is needed, the broker triggers a system
unlock (Touch ID / master password) — a **user-presence gate the agent can't
satisfy on its own.** The human is always in the loop for unlocking; after that,
per-site / per-credential grants (confirm-on-first-use, remembered, revocable, in
`ControlConsole`) govern reuse. The agent never holds the master key.

### Third-party managers (1Password, Proton Pass, Bitwarden…) — via skills

Many users keep credentials in a third-party **extension**, not the Vault. Stead
ships **no** password extension, but it's still Chromium — users install whatever
they want, and the agent **drives any of them** through the control layer (their
UI is just DOM). A per-manager **skill** encodes the procedure:

```
1Password skill:  focus the login field → Key("Cmd+\")  → snapshot the inline menu
                  → Click the right entry → the EXTENSION injects the secret
```

The secret goes **extension → form**; the agent only drove the UI, like a human.
So the *injection* is never-reveal in **both** paths — **the injector is never the
agent** (native autofill, or the extension). What keeps it never-reveal *after*
injection is the post-fill taint above — the secret is now in the page either way. **One asymmetry:** native `FillCredential` taints
automatically, but the broker can't *see* an extension inject — so a credential
skill must **declare itself** (skill metadata `credential: true`) or call
`MarkCredentialInjection(frame)` around its fill step with the current
`FrameRef` (main frame or iframe), and the broker taints conservatively.
Bonus: the manager's own lock fires
normally (1Password's Touch ID prompt), so its security is preserved and the agent
can't bypass it. (On macOS, AuthenticationServices can also surface a registered
provider's *passkeys* through the native Path-A flow.)

### Skills, generally

The password-manager skills are the canonical instance of the **skills layer**:

- A **skill** = a markdown procedure (+ optional helper code) teaching the agent a
  specific flow, **executed on top of the browser-native primitives**
  (snapshot/click/fill/key/eval) + harness tools. It's **data loaded on demand** —
  no process, no persistent footprint (the opposite of Aside shipping an
  extension). Lightweight by construction.
- Stead ships a **skills library** (1Password, Proton Pass, Bitwarden, Dashlane…
  plus Gmail, Notion, GitHub…) and supports **author-your-own** (agent- or
  user-written).
- The point: thin procedural knowledge that lets the *one* universal control layer
  operate any tool — native or third-party — on your behalf.

Implementation status: the Rust brain ships initial bundled Pie-style skills for
credential handoff, Gmail, GitHub, Notion, and artifact creation; it also loads
user-authored `SKILL.md` files from `agents/main/skills` and adds the combined
catalog + `Skill` invocation tool to each harness run. User skills override
bundled skills by name.

### Sync (deferred, optional)

Local-first day one (OS keychain). Later, an **E2EE cloud sync** (zero-knowledge,
Stead's backend) gives the cross-device, monetizable vault Aside gets from its
Bitwarden server — built *on top of* the native store, not as an extension.

---

## 16. Performance & correctness — benchmark targets + fixtures

**Measure AX cost early (don't assume "small/on-demand").** Enabling accessibility
makes Chromium maintain extra trees; on heavy pages (Google Docs) it can be real.
Benchmark per page (Gmail, Linear, GitHub, YouTube, Google Docs):
**snapshot time · node count · serialized bytes · token count · RAM delta ·
post-action latency.** Mitigation lever to test: granular `ui::AXMode` bits — use
the **leanest** mode that yields a usable tree, not the full screen-reader set.

**Fixture suite (makes correctness measurable, not vibes):** React/Vue *controlled*
inputs, **shadow DOM**, **iframe/OOPIF**, **occlusion**, custom dropdowns/comboboxes,
infinite scroll, **dialogs**, **permission prompts**, **auth redirects**,
**file choosers**, **popups**, **downloads**, and a **clickability**
page (`addEventListener`, delegated listeners, React synthetic events, shadow-DOM
hosts, disabled-ish custom buttons, default-cursor `<button>`s) — this one exists
specifically to **prove or disprove `IsClickable()`** before §6 relies on it. The
substrate must pass these before the brain is worth tuning. Include explicit
regressions for OOPIF/frame-local AX ids (`AXTreeCombiner` ids must never be
action refs), ignored-container collapse, and scroll-triggered event causality
(`Scroll` → lazy navigation/download/dialog retains `originating_action_id`).
Include a cold-subscribe event fixture: call `Observe()` without `ListTabs()`,
then trigger navigation/dialog/download in an existing tab and verify the event
arrives with a nonempty frame token once AX is available.
Also test multi-event causal bursts: one action that causes
navigation-plus-download, navigation-plus-dialog, or popup-plus-navigation must
keep the same `originating_action_id` across every caused event, not just the
first committed navigation. Add a duplicate-URL download fixture too: when two
tabs share the same URL, download attribution must use the unique pending-action
tab or report no tab rather than guessing.
Also include a taint-race fixture: start `GetSnapshot`/`ProbeNode`/`Screenshot`
/ `Eval`, taint the frame before the callback, and verify no secret-bearing
result is released. Add a taint-lifecycle fixture covering BFCache restore and
same-RFH document replacement: taint must be retained while the RFH survives,
ignored while inactive, and cleared only on RFH deletion or explicit cleanup.
For iframe/OOPIF dialogs and file choosers, assert `EventMeta.frame_token`
matches the source frame, not the tab's current main frame.

---

## 17. Build order

1. **Broker-first:** the `ControlBroker` skeleton + a *private* `BrowserControl`
   MVP (`ListTabs`, `GetSnapshot`, `Click`, `Fill`, `Focus`, `Navigate`,
   `Screenshot`) + the public `AgentControl` surface — so the gate/audit path
   exists from the very first action (no raw primitives without the broker, §12).
2. **Fixture suite** (§16) — the correctness bar.
3. **Tiny JS REPL dialect** over the primitives (§10).
4. **BrainBroker + bundled Rust helper** — `BrainConsole` for WebUI sessions/auth,
   framed JSON stdio to `stead-brain`, and tool-call routing through
   `AgentControl`.

(Build-gated from step 1 — this is where the Mac build box earns its keep. The
design above is pinned to real 149 APIs so the build day is execution.)

---

## 18. Open decisions

- **Inference source:** user's own Claude/Codex sub (needs pi-ai OAuth — fragile,
  ToS-gray) vs Stead's own backend (`api.stead`, simple native HTTPS) vs both.
- **Brain runtime:** Node Pi vs Rust port vs hybrid (decide after §17.4).
- **AX mode level:** which `ui::AXMode` bits — pending the §16 benchmark.
- **Vault capabilities spike:** confirm what `components/password_manager` provides
  *locally* in the Helium/ungoogled base — esp. **TOTP** and non-synced **passkey**
  storage (don't assume; §15).

---

## Appendix A — Aside's control layer, reverse-engineered

From `aside-extensions/AsideAgentManager` (minified, mined by signal). Key
finding: **perception/action is injected JS, NOT the CDP Accessibility domain.**
CDP/Playwright lives in the Node daemon; the extension is a thin bridge
(`chrome.debugger.getTargets`).

**Perception — `react-grab-bridge.js` (hand-rolled DOM walk):** `tagName` (×59),
`getBoundingClientRect` (×24), `shadowRoot` (×10), `getComputedStyle` (×8),
`elementsFromPoint` (occlusion). Schema: `{role,name,value,placeholder,bounds,
cursor,visible,disabled/checked/selected,ref,children,iframe}`. Refs via
`WeakMap` element↔id.

**Clickability — a UNION (the `cursor` correction):** `cursor:pointer` (×90)
alone is **insufficient** — native `<button>`, shadcn, Tailwind v4 use
`cursor:default`. Robust set: semantic (`a[href]`/`button`/`input`/`select`/
`textarea`/role/`tabindex`/`contenteditable`/`onclick`) **∪** `cursor:pointer`
(the supplement for `<div>`+JS-`addEventListener` that page-JS can't see), minus
disabled/`pointer-events:none`/invisible/occluded. Residual (div+listener+default
cursor) → vision fallback.

**Possible native advantage (a hypothesis, not a bet):** that residual is
invisible to *page JS* but *may* be visible to Blink — `AXNodeData::IsClickable()`
is documented to factor in click handlers (how screen readers flag interactive
divs). *If* it holds, Stead's native AX read detects JS-listener clickables
directly — more accurate, not just lighter. **Prove it with the §16 clickability
fixture** (`addEventListener`, delegated listeners, React synthetic events, shadow
DOM, disabled-ish custom buttons, default cursors) before relying on it; §6's
fallback tiers cover it if it proves incomplete.

**Action — `content/content.js` + daemon:** primary = CDP trusted input
(`Input.dispatchMouseEvent`/`dispatchKeyEvent`/`insertText`); plus an in-page
framework helper (`.value=`+`dispatchEvent`, `execCommand('insertText')`,
`setRangeText`) for React/Vue controlled inputs.

---

## Appendix B — tool surface, sorted

| Bucket | Tools | Provided by |
|---|---|---|
| **Harness** | scoped `files.*`, `memory`, `Skill`, `get_time`, `ask_user`, `notification`, credentialless capped `WebFetch`; deferred: `WebSearch`; excluded from v1: shell/subagents | bundled Rust brain on Pie agent core |
| **Browser-native** ⭐ | the REPL dialect, AX snapshot, tabs (open/close/list/adopt), `browsing_history_search`, screenshots, fetch-with-cookies, `pdf`, structured events | **#1 — the moat (`BrowserControl`)** |
| **Skills** | Gmail, Notion, Slack, GitHub, 1Password… | later, on top of browser-native |

Mirror Aside's minimalism: a couple of core tools (the REPL + `bash`); everything
page-related is "write code" against the dialect — which is why the prompt stays
~10K tokens, not 20K.
