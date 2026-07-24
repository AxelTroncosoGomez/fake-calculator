# Plan: user-facing release notes via towncrier (template for the real product)

## Context

`CHAT.md` asks two things: (1) stop losing "what changed and why" at squash-merge, and
(2) produce **user-facing** release notes for geologists/mining engineers (Spanish, with
GIFs/PNGs) that `git-cliff` structurally cannot generate from git history.

Ground truth after reading the real repo - several `CHAT.md` §3 claims are **already wrong,
in the user's favor**:

- **A release pipeline already exists.** `.github/workflows/release.yml` runs on `push: tags:['v*']`
  via `softprops/action-gh-release@v2` (`generate_release_notes: true`). Tags `v1.0.0`, `v1.0.1`
  already exist and have fired. §3's "nothing runs on tags" and §4.5's "release will silently
  never fire" are **false for this repo** (that GITHUB_TOKEN caveat applies to the `changelog.yml`
  *bot push*, not to human tag pushes).
- **`.github/release.yml` already exists** - the label→section map §4.6 said to create. Only the
  *labels themselves* still need creating in the GitHub UI.
- **Version lives in exactly ONE place:** `pyproject.toml:7` (`version = "1.0.0"`). `src/__init__.py`
  is empty; no `_version.py`/`importlib.metadata`. So §4.5's "commitizen for multi-file version
  sync" argument does **not** apply here → decision: **keep manual `git tag`**, defer commitizen
  to the real desktop-app repo.
- **Real drift exists:** `pyproject.toml` = `1.0.0` but tags reached `v1.0.1`. Nobody bumped the
  file. The release runbook below fixes this and prevents recurrence.
- **`pull_request_target` in `semantic-pr-check.yml` is safe** (§7.3 confirmed): it has **no
  `actions/checkout`**, so it never runs untrusted PR code. Keep as-is.
- **`disallowScopes: release` - no conflict** (§7.3): we add no tool that emits a `release`-scoped
  PR title.
- This repo is `fake-calculator` (2 source files) - a **sandbox**. The real audience (geólogos,
  PyQt5, GIFs) is a different repo. Goal here: build a **clean, portable template**.

## Approach (MVP, enforced towncrier + manual tag)

Two documents, two audiences, kept separate:

| Document | Tool | Audience | Generated |
|---|---|---|---|
| `CHANGELOG.md` | git-cliff | developers | at **release time** (runbook), not on every push |
| `docs/releases/CHANGELOG-USUARIO.md` | towncrier fragments + editing | geólogos/clientes | at release time |

Intent is captured **at PR time** in `changelog.d/` fragments (markdown → holds GIFs/PNGs),
enforced by CI. Releases are cut by a documented runbook that collapses fragments, regenerates
both changelogs in one commit, bumps `pyproject.toml`, tags, and pushes - no bot-commit-to-main
loop, works under branch protection.

## File plan

### Create

- **`pyproject.toml`** → add `[tool.towncrier]` + Spanish type tables (`rompe`, `nuevo`, `arreglo`,
  `interno`), `directory="changelog.d"`, `filename="docs/releases/CHANGELOG-USUARIO.md"`,
  `start_string="<!-- towncrier release notes start -->\n"`,
  `issue_format` pointing at the repo PR URL (leave a `# TODO: swap org/repo when porting` note).
  Also add `towncrier` to `[dependency-groups].dev`. *Reason: core of the user-facing pipeline.*
- **`changelog.d/README.md`** - fragment naming (`<PR#>.<tipo>.md`), the four types, asset guidance.
  *Reason: keep the dir tracked + document convention for the team.*
- **`docs/releases/CHANGELOG-USUARIO.md`** - seed file containing only the
  `<!-- towncrier release notes start -->` marker + a title. *Reason: towncrier's append target.*
- **`docs/releases/assets/.gitkeep`** - convention for `docs/releases/assets/<version>/` GIFs/PNGs.
  *Reason: fragments reference assets relatively (§4.3).*
- **`.github/PULL_REQUEST_TEMPLATE.md`** - the §4.2 block ("Qué cambia para el usuario / Detalle
  técnico / Cómo probarlo") + a checkbox: "☐ Agregué un fragment en `changelog.d/` (o etiqueté
  `sin-changelog`)". *Reason: prompt the author while intent is fresh.*
- **`.github/workflows/changelog-fragment.yml`** - `on: pull_request`; skip if PR carries label
  `sin-changelog`; else checkout (fetch-depth 0) + `astral-sh/setup-uv` + `uv sync --group dev` +
  `uv run towncrier check --compare-with origin/${{ github.base_ref }}`. *Reason: the mandatory
  enforcement the user chose. Uses towncrier's built-in `check` (no hand-rolled diff).* Note: this
  is slightly **stricter** than §4.4 (fires on any PR, not only `src/` changes) - the `sin-changelog`
  label is the escape hatch; can be narrowed later with `dorny/paths-filter` if noisy.
- **`docs/releases/RELEASE.md`** - the release runbook (see below). *Reason: with manual tagging,
  the runbook IS the release mechanism.*

### Modify

- **`.github/workflows/ci.yml` (or leave, see gotcha):** no change needed *if* `uv.lock` is
  regenerated. The new dev dep (`towncrier`) means **`uv.lock` must be updated** or every
  `uv sync --frozen`/`--group dev` fails. → run `uv lock` and commit `uv.lock` as part of this change.
- **`pyproject.toml` version** → bump `1.0.0` → `1.0.1` to match the latest existing tag
  (housekeeping; fixes current drift). *Optional but recommended.*

### Delete

- **`.github/workflows/changelog.yml`** - remove the push-to-main → git-cliff → commit-back loop.
  It's fragile (breaks under branch protection, relies on `[skip ci]`, wastes CI). `CHANGELOG.md`
  is instead regenerated in the release runbook. Implements §4.5. *This is the one deletion - flag
  for user review.* (`CHANGELOG_USAGE.md` describes this workflow and will need a doc update too.)

### Leave unchanged (verified fine)

- `semantic-pr-check.yml` (safe, load-bearing), `.github/release.yml` (already correct),
  `release.yml` (already fires on tags; optional later enhancement: `body_path` to prepend user
  highlights), `cliff.toml` (works; the two non-conventional historical commits land harmlessly in
  "Other Changes").

## Release runbook (docs/releases/RELEASE.md)

```bash
git checkout main && git pull
VERSION=1.1.0

uv run towncrier build --yes --version "$VERSION"     # collapses changelog.d/, git-rm's fragments
# → edit docs/releases/CHANGELOG-USUARIO.md (~20 min human polish, add GIFs)

git-cliff --tag "v$VERSION" --output CHANGELOG.md      # regenerate dev changelog
# bump version in pyproject.toml to $VERSION

git commit -am "chore: release v$VERSION"
git tag "v$VERSION" && git push && git push --tags     # release.yml publishes the GitHub Release
```

## Gotchas to surface at execution time

1. **`uv.lock` must be regenerated** after adding `towncrier` - otherwise `--frozen` CI breaks.
2. **`main` branch protection is unverified** - `gh` CLI is not installed here. Confirm in GitHub
   Settings. Deleting `changelog.yml` removes the only workflow that pushes to `main`, so protection
   becomes strictly easier, not harder.
3. **GitHub labels are manual, one-time UI work** (not files): create `sin-changelog` (escape hatch)
   and `feat`/`fix`/`docs` (for `.github/release.yml` categories).
4. **`towncrier check` is stricter than "touched src/"** - every PR needs a fragment unless labeled.
   Acceptable per the user's "enforced" choice; narrow later if needed.

## Verification

- `uv sync --group dev` succeeds with `towncrier` present; `uv run towncrier --version` works.
- Add `changelog.d/999.nuevo.md`, run `uv run towncrier build --draft --version 9.9.9` → the entry
  renders under "Novedades"; `--draft` leaves fragments in place.
- `uv run towncrier check --compare-with origin/main` returns non-zero on a branch that adds a
  `src/` change with no fragment, zero once a fragment is added.
- Open a throwaway PR: `changelog-fragment.yml` fails with no fragment, passes after adding one or
  applying `sin-changelog`; PR template renders.
- Dry-run the runbook on a scratch tag; confirm `release.yml` produces a GitHub Release.

## Notes for the real-product port (out of scope here)

- Reconsider `cz bump` there - multiple version locations (pyproject + PyQt about-dialog) make its
  multi-file sync worth it.
- PyQt5 in-app notes: `QTextBrowser.setMarkdown()` shows static PNGs but **won't animate GIFs**;
  GIFs go on the web `/novedades` page (§4.6).
- Swap `issue_format` org/repo and `assets/` paths for the real repo.
