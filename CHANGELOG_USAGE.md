# How the automated changelog works

## Overview

This repository keeps **two** changelogs, for two audiences:

| Documento | Herramienta | Audiencia | Cuándo |
|---|---|---|---|
| `CHANGELOG.md` | git-cliff (Conventional Commits) | desarrolladores | al cortar la release |
| `docs/releases/CHANGELOG-USUARIO.md` | towncrier (fragments en `changelog.d/`) | geólogos / clientes | al cortar la release |

The pieces:

1. **Semantic PR Check** (`.github/workflows/semantic-pr-check.yml`)
   Validates that every PR title follows the Conventional Commits format.

2. **Changelog Fragment Check** (`.github/workflows/changelog-fragment.yml`)
   Requires every PR to add a user-facing news fragment under `changelog.d/`
   (escape hatch: the `sin-changelog` label). See [`changelog.d/README.md`](changelog.d/README.md).

3. **Release runbook** ([`docs/releases/RELEASE.md`](docs/releases/RELEASE.md))
   Both changelogs are regenerated **at release time**, in one commit - there is
   no longer a workflow that rewrites `CHANGELOG.md` on every push to `main`
   (that commit-back-to-`main` loop was removed).

[1]: https://www.conventionalcommits.org/en/v1.0.0/

---

## The end-to-end flow

```
You open a PR:
  Title: "feat(ui): add dark mode toggle button"

  ├─ semantic-pr-check.yml validates the title format
  └─ changelog-fragment.yml requires a changelog.d/ fragment
     (unless the PR is labeled `sin-changelog`)

You squash-merge the PR into main:

  └─ GitHub creates a single commit on main with the PR title as the message
     (no changelog is rewritten on push anymore)

At release time (see docs/releases/RELEASE.md):

  ├─ git-cliff regenerates CHANGELOG.md from the commit history
  └─ towncrier collapses changelog.d/ into docs/releases/CHANGELOG-USUARIO.md

      ### Features
      - *(ui)* Add dark mode toggle button

  All in one commit, then `git tag vX.Y.Z && git push` → release.yml publishes.
```

---

## Repository setup (one-time)

Go to **Settings → General → Pull Requests** and enable:

- ☑ **Allow squash merging**
- ☑ **Default to PR title for squash merge commits**

Without the second setting, GitHub uses the squash commit's own message (not
the PR title) as the merge commit message, and the changelog won't reflect what
you validated.

---

## Writing PR titles

Each PR title must follow this pattern:

```
type(scope): description
```

| Part        | Required | Examples                                          |
|-------------|----------|---------------------------------------------------|
| `type`      | Yes      | `feat`, `fix`, `perf`, `docs`, `test`, `chore`…  |
| `scope`     | No       | `ui`, `api`, `infra`, `deps`…                    |
| `description` | Yes   | Lowercase, ≥ 10 chars, no trailing period        |

### Allowed types (same list in both workflows)

`feat` `fix` `perf` `refactor` `docs` `test` `build` `ci` `chore` `revert`

### Good examples

```
feat(estimation): add ordinary kriging neighbourhood cache
fix: resolve overflow when grid size exceeds 10000 cells
docs: explain SGS algorithm parameters in the README
refactor(io): extract file reader into separate module
chore: bump ruff from 0.15.2 to 0.15.20
```

### Bad examples (will be rejected)

```
Add dark mode          ← missing type prefix
feat: fix.             ← trailing period
feat: add              ← too short (under 10 chars)
Feat: add dark mode    ← uppercase type
```

### Skipping validation

Add one of these labels to the PR to skip the semantic title check entirely:

- `dependencies`
- `bot`
- `skip-pr-lint`

---

## How commits are grouped in the changelog

`cliff.toml` maps each Conventional Commits type to a changelog section:

| Commit type   | Changelog section          |
|---------------|----------------------------|
| `feat`        | Features                   |
| `fix`         | Bug Fixes                  |
| `perf`        | Performance Improvements   |
| `refactor`    | Refactoring                |
| `docs`        | Documentation              |
| `test`        | Testing                    |
| `build`       | Build System               |
| `ci`          | Continuous Integration     |
| `chore`       | Miscellaneous Tasks        |
| `revert`      | Reverts                    |

The sections always appear in this order (controlled by invisible HTML comment
prefixes in `cliff.toml`).

---

## What happens at release time

`CHANGELOG.md` is **not** rewritten on every push to `main` anymore - the old
`changelog.yml` (which committed the regenerated file back to `main` with
`[skip ci]`) was removed because that loop is fragile under branch protection
and wasteful. Instead, at release time the runbook
([`docs/releases/RELEASE.md`](docs/releases/RELEASE.md)) runs, in one commit:

1. `git-cliff --tag vX.Y.Z --output CHANGELOG.md` regenerates the dev changelog.
2. `towncrier build --version X.Y.Z` collapses `changelog.d/` fragments into
   `docs/releases/CHANGELOG-USUARIO.md` and removes the fragments.
3. `pyproject.toml`'s version is bumped, then the commit is tagged and pushed;
   `release.yml` publishes the GitHub Release.

---

## Adding or changing commit types

Two files must stay in sync:

1. **`cliff.toml`** - `[git.commit_parsers]` section. Add a new entry:
   ```toml
   { message = "^newtype", group = "<!-- N -->New Section Name" },
   ```

2. **`.github/workflows/semantic-pr-check.yml`** - `types:` list. Add the
   new type to the allowed list.

---

## Viewing the changelog

`CHANGELOG.md` is written to the repository root and is always up to date with
`main`. You can link to headings directly:

```
https://github.com/AxelTroncosoGomez/fake-calculator/blob/main/CHANGELOG.md#features
```

---

## How releases work

This repo has **two changelogs for two audiences**:

| Output | Tool | Audience | Updated by |
|---|---|---|---|
| `CHANGELOG.md` | git-cliff | Developers, tooling | `changelog.yml` (every push to `main`) |
| GitHub Release body | GitHub's native generator | Users reading the [Releases page][2] | `release.yml` (on tag push) |

`CHANGELOG.md` is the definitive machine-readable record. The Release body is
the polished, human-readable version with PR links and author attribution.

### Creating a release

```bash
git checkout main
git pull

# Bump the version in pyproject.toml first, then commit + push, then:

git tag v1.0.0
git push origin v1.0.0
```

That's it. Pushing the tag triggers `release.yml`, which uses GitHub's
auto-generated release notes (configured by `.github/release.yml`). The
release appears automatically with:

```
## What's Changed
* feat: add tax calculator by @AxelTroncosoGomez in #1
* fix: reject bool inputs by @AxelTroncosoGomez in #2

**Full Changelog**: v0.0.0...v1.0.0
```

### Adding highlights and screenshots (optional)

After the release is created, you can edit it to add:

1. A **Highlights** section summarizing the most important changes
2. **Screenshots or GIFs** of UI changes
3. **Migration notes** for breaking changes

Go to [Releases][2], click the release, then **Edit release**. Write your
highlights above the `## What's Changed` line:

```markdown
## Highlights

- The new Dark Mode toggle under Settings > Appearance turns the whole app dark
- Export now supports PNG with transparent backgrounds
- Keyboard shortcut `Ctrl+K` opens the command palette

## What's Changed
* feat: add dark mode by @you in #12
* feat: add PNG export by @you in #13
* fix: tooltip overflow by @you in #14
...
```

Screenshots: drag-and-drop images into the release body editor while editing.
They appear inline in the release.

### How categorization works

Create these labels on your repo (one-time setup) to group PRs into sections:

| Label | Release section |
|---|---|
| `feat` | Features |
| `fix` | Bug Fixes |
| `docs` | Documentation |
| *(any other)* | Other Changes |

`.github/release.yml` maps labels to sections. Without labels, all PRs appear
under "Other Changes" (which is fine for small repos).

To create labels: **Issues > Labels > New label**.

[2]: https://github.com/AxelTroncosoGomez/fake-calculator/releases
