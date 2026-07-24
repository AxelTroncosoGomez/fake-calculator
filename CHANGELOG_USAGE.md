# How the automated changelog works

## Overview

This repository generates `CHANGELOG.md` automatically from commit messages that
follow the [Conventional Commits][1] specification. There are two pieces:

1. **Semantic PR Check** (`.github/workflows/semantic-pr-check.yml`)
   Validates that every PR title follows the Conventional Commits format.

2. **Generate Changelog** (`.github/workflows/changelog.yml`)
   Reads the git history on `main`, parses every commit, and writes a grouped
   `CHANGELOG.md`. Runs automatically after every push to `main`.

[1]: https://www.conventionalcommits.org/en/v1.0.0/

---

## The end-to-end flow

```
You open a PR:
  Title: "feat(ui): add dark mode toggle button"

  └─ semantic-pr-check.yml runs, validates the title format

You squash-merge the PR into main:

  └─ GitHub creates a single commit on main with the PR title as the message

  └─ changelog.yml triggers (push to main)

      └─ git-cliff reads every commit on main, parses Conventional Commits

      └─ Generates CHANGELOG.md with sections like:

          ### Features
          - *(ui)* Add dark mode toggle button

          ### Bug Fixes
          - *(api)* Prevent null pointer in request parser

      └─ Auto-commits the updated CHANGELOG.md back to main
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

## What happens on each push to main

1. The `changelog.yml` workflow checks out the full git history.
2. `git-cliff` reads every commit from the oldest to the newest, parses type
   and scope from each Conventional Commits message.
3. It generates a complete `CHANGELOG.md` with grouped entries.
4. If `CHANGELOG.md` changed, the workflow commits and pushes it back to
   `main` as `github-actions[bot]`.

The push from the bot does **not** re-trigger the workflow (GitHub prevents
recursive workflow runs when using the default `GITHUB_TOKEN`).

---

## Adding or changing commit types

Two files must stay in sync:

1. **`cliff.toml`** — `[git.commit_parsers]` section. Add a new entry:
   ```toml
   { message = "^newtype", group = "<!-- N -->New Section Name" },
   ```

2. **`.github/workflows/semantic-pr-check.yml`** — `types:` list. Add the
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

### Option A: Automated (recommended)

When you push a git tag matching `v*` (e.g. `v1.1.0`), the `release.yml`
workflow runs automatically:

```
You push a tag:
  git tag v1.1.0 && git push origin v1.1.0

  └─ release.yml triggers (on push of tag v*)

      ├─ git-cliff --latest generates the changelog for v1.0.0..v1.1.0

      └─ Creates a GitHub Release with that changelog as the body
```

The release appears on the [Releases page][2] with the full changelog for that
version, grouped by type, exactly as it appears in `CHANGELOG.md`.

Nothing else is needed — the workflow handles everything. To issue a release:

```bash
# 1. Make sure you're on main
git checkout main
git pull

# 2. Tag the current commit
git tag v1.1.0

# 3. Push the tag
git push origin v1.1.0
```

The workflow produces:

```
[Releases page]
┌────────────────────────────────────────────────┐
│ v1.1.0                                          │
│                                                 │
│ ### Features                                    │
│ - *(ui)* Add dark mode toggle                   │
│ - *(api)* Add pagination to list endpoint       │
│                                                 │
│ ### Bug Fixes                                   │
│ - *(parser)* Fix null reference on empty input  │
│                                                 │
│ ### Continuous Integration                      │
│ - Add release workflow                          │
│                                                 │
│ Assets: (none)                                  │
└────────────────────────────────────────────────┘
```

### Option B: Manual

If you prefer creating releases by hand through the GitHub UI:

1. Open the [Releases page][2] and click **"Draft a new release"**
2. In the **"Choose a tag"** dropdown, type your version tag (e.g. `v1.1.0`)
   and select **"Create new tag: v1.1.0 on publish"**
3. Set the **Release title** to the tag name (e.g. `v1.1.0`)
4. Open `CHANGELOG.md` on `main`, copy the section for your version (from
   `## [1.1.0]` down to the next `## [version]` heading), and paste it into
   the **"Describe this release"** textarea
5. Click **"Publish release"**

The result is identical — the changelog content appears as the release body
on the Releases page.

[2]: https://github.com/AxelTroncosoGomez/fake-calculator/releases
