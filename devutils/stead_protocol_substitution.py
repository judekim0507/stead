#!/usr/bin/env python3
"""Rewrite Helium's custom chrome:// alias to Stead in Chromium sources.

Helium's upstream patch registers helium:// as a WebUI alias and displays
chrome:// pages as helium:// in the omnibox. Stead inherits that patch, but the
actual source-level protocol must be stead://, not helium://. Keep this narrowly
scoped to the files touched by helium/core/override-chrome-protocol.patch so the
broader helium namespace and service code stays untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path


TARGETS = [
    "content/public/common/url_constants.h",
    "chrome/browser/profiles/profile_io_data.cc",
    "content/common/url_schemes.cc",
    "content/renderer/render_thread_impl.cc",
    "chrome/browser/history/history_utils.cc",
    "chrome/browser/ui/incognito_allowed_url.cc",
    "chrome/browser/ui/navigator/browser_navigator.cc",
    "chrome/browser/extensions/extension_tab_util.cc",
    "chrome/browser/ui/browser.cc",
    "components/omnibox/browser/omnibox_text_util.cc",
    "components/url_formatter/url_formatter.cc",
    "components/url_formatter/url_formatter.h",
    "chrome/browser/ui/web_applications/app_browser_controller.cc",
    "components/omnibox/browser/location_bar_model_impl.cc",
    "components/url_formatter/elide_url.cc",
    "components/url_formatter/url_fixer.cc",
    "chrome/browser/autocomplete/chrome_autocomplete_provider_client.cc",
    "components/omnibox/browser/builtin_provider.cc",
    "chrome/browser/ui/browser_commands.cc",
    "chrome/browser/ui/views/tabs/hovercard/hover_card_anchor_target.cc",
    "chrome/browser/resources/tab_search/tab_search_item.ts",
]

FORWARD_REPLACEMENTS = [
    ("kHeliumUIScheme", "kSteadUIScheme"),
    ("HeliumUIScheme", "SteadUIScheme"),
    ("helium", "stead"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tree", type=Path, required=True)
    parser.add_argument(
        "--revert",
        action="store_true",
        help="restore Helium protocol names in the target files",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def main() -> None:
    args = parse_args()
    if not (args.tree / "OWNERS").exists():
        raise ValueError(f"wrong src directory: {args.tree}")

    replacements = FORWARD_REPLACEMENTS
    if args.revert:
        replacements = [(new, old) for old, new in reversed(FORWARD_REPLACEMENTS)]

    new_needles = [new for _, new in replacements]
    changed = 0
    already_applied = 0
    skipped_without_markers = 0

    for rel in TARGETS:
        path = args.tree / rel
        if not path.exists():
            raise FileNotFoundError(f"expected Chromium source file missing: {rel}")

        original = path.read_text(encoding="utf-8")
        updated = apply_replacements(original, replacements)

        if updated != original:
            changed += 1
            if not args.dry_run:
                path.write_text(updated, encoding="utf-8")
            print(f"rewrote Stead protocol source: {rel}")
        elif has_any(original, new_needles):
            already_applied += 1
        else:
            skipped_without_markers += 1

    if changed + already_applied < 10:
        raise RuntimeError(
            "too few protocol markers found; Chromium protocol patch may have "
            "drifted"
        )

    action = "reverted" if args.revert else "applied"
    print(
        f"Stead protocol substitution {action}: "
        f"{changed} changed, {already_applied} already current, "
        f"{skipped_without_markers} skipped without markers"
    )


if __name__ == "__main__":
    main()
