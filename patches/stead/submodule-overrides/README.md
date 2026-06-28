# Submodule overrides

Stead changes that live **inside** the `helium-chromium` submodule (its build
tooling), which can't go through the normal `patches/` pipeline (that patches the
downloaded Chromium tree, not the submodule's own scripts). These are snapshotted
here so a `git push` of this repo doesn't lose them — the submodule is a separate
repo (upstream `imputnet/helium`) and we don't push to it.

## `helium-chromium-name-substitution.diff`

Retargets Helium's build-time name substitution to **Stead** (`Chrome/Chromium →
Stead`, `chrome://`/`helium:// → stead://`, `Helium → Stead`) in
`utils/name_substitution_utils.py` + updates the sanity asserts in
`utils/name_substitution.py`.

Re-apply after a fresh submodule checkout:

```sh
git -C helium-chromium apply patches/stead/submodule-overrides/helium-chromium-name-substitution.diff
```

(Longer term this should be relocated out of the submodule so it's not a manual
override — see project notes.)
