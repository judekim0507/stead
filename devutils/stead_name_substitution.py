#!/usr/bin/env python3
"""Stead brand substitution, without modifying the helium-chromium submodule.

build.sh / dev.sh call this instead of the submodule's name_substitution.py.
We reuse Helium's substitution machinery verbatim (so .grd/.xtb fingerprint
remapping etc. stay in lockstep with upstream) but swap in Stead's replacement
target. The submodule stays pristine; nothing here needs to be re-applied after
a fresh clone or a submodule bump.

Drop-in CLI: takes the exact same arguments as name_substitution.py
(--sub / --unsub, -t <tree>, --backup-path, --dry-run, --workers).
"""
import os
import re
import sys

# Make the submodule's util modules importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo_root, "helium-chromium", "utils"))

import name_substitution_utils as util  # noqa: E402
import name_substitution as ns  # noqa: E402

# Stead's brand target. Same shape as Helium's regexes, but emits Stead /
# stead://, and additionally rewrites Helium's own inherited strings.
_STEAD_REGEXES_STR = [
    # protect names we must NOT rewrite
    (r'(\w+) Root Program', r'\1_unreplace Root Program'),
    (r'(\w+) Web( S|s)tore', r'\1_unreplace Web Store'),
    (r'(\w+) Remote Desktop', r'\1_unreplace Remote Desktop'),
    # Chromium-origin names -> Stead
    (r'(\b)chrome://', r'\1stead://'),
    (r'(?:Google )?Chrom(e|ium)(?!\w)', r'Stead'),
    # Helium-origin names (inherited from the upstream patch tree) -> Stead
    (r'(\b)helium://', r'\1stead://'),
    (r'"helium"', r'"stead"'),
    (r"'helium:'", r"'stead:'"),
    (r'Helium', r'Stead'),
    # restore the protected names
    (r'((?:Google )?Chrom(e|ium))_unreplace', r'\1'),
    (r'_unreplace', r''),
]

util.REPLACEMENT_REGEXES = [
    (re.compile(p), r) for p, r in _STEAD_REGEXES_STR
]


def _stead_sanity():
    cases = [
        ('chrome://about', 'stead://about'),
        ('Chrome Root Program', 'Chrome Root Program'),
        ('Chrome Web Store', 'Chrome Web Store'),
        ('Google Chrome', 'Stead'),
        ('Chromium', 'Stead'),
        ('helium://about', 'stead://about'),
        ('content::kHeliumUIScheme[] = "helium";',
         'content::kSteadUIScheme[] = "stead";'),
        ('protocol === \'helium:\'', 'protocol === \'stead:\''),
        ('Helium services', 'Stead services'),
    ]
    for src, expected in cases:
        out, match = util.replace_text(src)
        assert match and out == expected, f"stead sanity: {out!r} != {expected!r}"


# Replace Helium's (Helium-targeted) sanity check with Stead's.
ns.replacement_sanity = _stead_sanity


if __name__ == '__main__':
    ns.main()
