# AI PR Reviewer Setup Guide

Automated AI code review on every Pull Request using OpenCode Go (DeepSeek V4 Pro)
and Google Vertex AI (Gemini). Both are label-gated, secure, and run in GitHub Actions.

---

## What You Get

| Reviewer | Model | Cost | Setup Time | Label |
|----------|-------|------|------------|-------|
| OpenCode | DeepSeek V4 Pro | $10/mo flat (included in Go plan) | 5 min | `opencode-review` |
| Gemini | Gemini 2.5 Pro | GCP credits (~$0.05-2.50/review) | 15 min | `gemini-review` |
| All at once | Both | Mixed | Both setups | `ai-review` |

Each review checks: test coverage, clean code, formatting, error handling, security,
and performance. Findings are posted as structured PR comments with severity levels
(`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).

---

## Prerequisites

- A GitHub repository (public or private)
- GitHub Actions enabled (Settings > Actions > General > Read and write permissions)
- Python 3.12+ with `uv` installed locally (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- For Gemini: a GCP project with billing enabled and `gcloud` CLI authenticated

---

## Quick Start: OpenCode Go (5 minutes)

### Step 1: Subscribe to OpenCode Go

Go to https://opencode.ai/auth, sign in, subscribe to Go ($5 first month, $10/month
after). Copy the generated API key.

### Step 2: Add the API key as a GitHub Secret

In your repo: **Settings > Secrets and variables > Actions > New repository secret**

| Name | Value |
|------|-------|
| `OPENCODE_API_KEY` | Your API key from opencode.ai/auth |

### Step 3: Add these files to your repo

Create the following directory structure:

```
.github/
  workflows/
    opencode-pr-review.yml
  scripts/
    opencode_review.py
```

**`.github/workflows/opencode-pr-review.yml`:**

```yaml
name: OpenCode AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened, labeled]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    if: |
      (
        contains(github.event.pull_request.labels.*.name, 'opencode-review') ||
        contains(github.event.pull_request.labels.*.name, 'ai-review')
      ) &&
      github.event.pull_request.draft == false
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install OpenCode CLI
        run: curl -fsSL https://opencode.ai/install | bash

      - name: Install GitHub CLI
        run: |
          type -p gh || (sudo apt-get update && sudo apt-get install -y gh)

      - name: Run OpenCode PR Code Review
        env:
          OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_PULL_REQUEST_NUMBER: ${{ github.event.pull_request.number }}
        run: python .github/scripts/opencode_review.py
```

The review script is at `.github/scripts/opencode_review.py`. Copy it from the
reference repository or see the appendix at the end of this guide.

### Step 4: Push and test

```bash
git switch -c feature/test-review
# make any code change
git add -A && git commit -m "Test AI review"
git push origin feature/test-review
```

Open a Pull Request on GitHub. Add the label `opencode-review` on the PR page
(right sidebar > Labels). Within 30-60 seconds, the review comment appears.

To re-review after fixing issues: remove the label, push changes, re-add the label.

---

## Advanced: Gemini via Vertex AI (15 minutes)

### Step 1: Prepare your GCP project

Pick or create a GCP project. You need billing enabled and `gcloud` authenticated.

```bash
# Log in
gcloud auth login

# List existing projects (or create one)
gcloud projects list

# Set the project you want to use
gcloud config set project YOUR_PROJECT_ID

# If creating a new project:
gcloud projects create my-ai-reviewer --name="AI PR Code Review"
# Then enable billing at:
# https://console.cloud.google.com/billing/linkedaccount?project=my-ai-reviewer
```

### Step 2: Download the setup script

Copy `scripts/gcp-setup.sh` from this repository into your own repo. This script
automates all the GCP infrastructure: Workload Identity Pool, OIDC Provider,
Service Account, and IAM bindings. It works idempotently (safe to re-run).

### Step 3: Run the setup script

```bash
export GCP_PROJECT_ID="your-project-id"
export GITHUB_ORG="your-github-username-or-org"
export GITHUB_REPO="your-repo-name"
bash scripts/gcp-setup.sh
```

**Example** (real values from a working setup):

```
export GCP_PROJECT_ID="andesite-pr-reviewer"
export GITHUB_ORG="AxelTroncosoGomez"
export GITHUB_REPO="fake-calculator"
bash scripts/gcp-setup.sh
```

The script output will look like:

```
==============================================
  GCP Setup Complete
==============================================

Add these to your GitHub repo secrets
(Settings > Secrets and variables > Actions):

  GCP_PROJECT_ID:                  andesite-pr-reviewer
  GCP_WORKLOAD_IDENTITY_PROVIDER:  projects/1078911076312/locations/global/...
  GCP_SERVICE_ACCOUNT:             pr-reviewer@andesite-pr-reviewer.iam...
  GCP_REGION:                      us-central1
==============================================
```

**Important:** After running the script, wait 2 minutes for IAM propagation before
testing. The `NOT_FOUND` error on the provider `describe` command is a propagation
delay, not a failure - the resources were created successfully.

**Note on GCP email vs GitHub email:** They do not need to match. The Workload
Identity Federation authenticates based on your GitHub repo name
(`AxelTroncosoGomez/fake-calculator`), not your email address.

### Step 4: Add GCP GitHub Secrets

In your repo: **Settings > Secrets and variables > Actions > New repository secret**

| Name | Value (from script output) |
|------|---------------------------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full path: `projects/.../providers/github` |
| `GCP_SERVICE_ACCOUNT` | `pr-reviewer@PROJECT.iam.gserviceaccount.com` |

Optional:

| Name | Value | Default |
|------|-------|---------|
| `GCP_REGION` | `us-central1` | `us-central1` |
| `GEMINI_MODEL` | `gemini-2.5-flash` (cheaper) | `gemini-2.5-pro` |

### Step 5: Add the Gemini workflow files

Create these files in your repo:

**`.github/workflows/gemini-pr-review.yml`:**

```yaml
name: Gemini AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened, labeled]

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  review:
    if: |
      (
        contains(github.event.pull_request.labels.*.name, 'gemini-review') ||
        contains(github.event.pull_request.labels.*.name, 'ai-review')
      ) &&
      github.event.pull_request.draft == false
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Set up gcloud CLI
        uses: google-github-actions/setup-gcloud@v2

      - name: Install GitHub CLI
        run: |
          type -p gh || (sudo apt-get update && sudo apt-get install -y gh)

      - name: Run Gemini PR Code Review
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_REGION: ${{ secrets.GCP_REGION || 'us-central1' }}
          GEMINI_MODEL: ${{ secrets.GEMINI_MODEL || 'gemini-2.5-pro' }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_PULL_REQUEST_NUMBER: ${{ github.event.pull_request.number }}
        run: python .github/scripts/pr_review.py
```

The Gemini review script is at `.github/scripts/pr_review.py`. Copy it from the
reference repository.

### Step 6: Trigger the Gemini review

Add the label `gemini-review` to any PR. The workflow authenticates to GCP using
Workload Identity Federation (no long-lived keys stored in GitHub) and calls
Gemini via the Vertex AI REST API.

---

## How Labels Work

| Label | Effect |
|-------|--------|
| `opencode-review` | Triggers OpenCode (DeepSeek V4 Pro) review only |
| `gemini-review` | Triggers Gemini (Vertex AI) review only |
| `ai-review` | Triggers BOTH reviewers simultaneously |

Each workflow's `if` condition checks for its specific label OR the universal
`ai-review` label. Draft PRs are excluded by default.

Label gating prevents wasted API calls on WIP commits. Only add a label when
you want a review. To re-review after fixing issues: remove the label, push
your changes, then re-add the label.

---

## Full Walkthrough (Simulated PR)

Here's the complete flow from feature branch to AI-reviewed PR:

```bash
# 1. Create a feature branch
git switch -c feature/add-calculate-tax

# 2. Make a code change (e.g., add a function to src/calculator.py)
#    Example: adding calculate_tax(amount, tax_rate) without tests

# 3. Commit and push
git add -A
git commit -m "Add calculate_tax function"
git push origin feature/add-calculate-tax

# 4. Open a Pull Request on GitHub
#    Visit: https://github.com/YOUR_ORG/YOUR_REPO/pull/new/feature/add-calculate-tax

# 5. Basic CI runs automatically (if you have ci.yml)
#    - pytest with coverage
#    - ruff lint
#    - ruff format check

# 6. Add a review label on the PR page (right sidebar > Labels)
#    - opencode-review  (for OpenCode)
#    - gemini-review    (for Gemini)
#    - ai-review        (for both)

# 7. Wait 30-60 seconds. The review comment appears on the PR with findings like:
#    - [CRITICAL] Missing tests (AGENTS.md violation)
#    - [HIGH] No input validation (inconsistent pattern)
#    - [MEDIUM] Missing type hints/docstring
#
#    Each finding includes: severity, category, file path, description,
#    and specific fix suggestions.

# 8. Fix the issues based on review feedback
#    - Add tests, validation, type hints, docstrings
git add -A && git commit -m "Fix review findings"
git push

# 9. Re-request review
#    - Remove the review label from the PR
#    - Re-add it → fresh review fires
#    - If fixes are good, verdict changes from "Request Changes" to "Approve"
```

---

## Cost Tracking

### OpenCode Go

Your $10/month subscription includes $60 of monthly usage. DeepSeek V4 Pro costs
approximately $0.0035 per review (one-third of one cent). At that rate, you get
~17,000 reviews per month before hitting the cap.

Track usage at: https://opencode.ai/auth

Limits:
- 5-hour: $12 (~3,450 reviews)
- Weekly: $30 (~8,550 reviews)
- Monthly: $60 (~17,150 reviews)

If you hit a limit, requests are blocked until the window resets. You can enable
"Use balance" in the console to fall back to any Zen credits you have.

### Gemini (Vertex AI)

Pay-per-use via GCP billing. Estimated costs per model:

| Model | Cost per review |
|-------|---------------|
| `gemini-2.5-pro` | ~$1.25-2.50 |
| `gemini-2.5-flash` | ~$0.04-0.07 |
| `gemini-2.5-flash-lite` | ~$0.02-0.04 |

Monitor spending in the GCP Console: https://console.cloud.google.com/apis/api/aiplatform.googleapis.com

Set budget alerts to avoid surprise bills.

---

## Customization

### Changing the model

**OpenCode:** Set the `OPENCODE_MODEL` GitHub Secret to any Go model:

| Model ID | Reviews/month |
|----------|-------------|
| `opencode-go/deepseek-v4-pro` (default) | ~3,450 |
| `opencode-go/deepseek-v4-flash` (cheapest) | ~31,650 |
| `opencode-go/kimi-k2.7-code` | ~1,350 |

**Gemini:** Set the `GEMINI_MODEL` GitHub Secret:
- `gemini-2.5-pro` (default): deep review, large diffs
- `gemini-2.5-flash`: cheaper, faster
- `gemini-2.5-flash-lite`: cheapest, quickest

### Editing review categories

Both review scripts use the same prompt template. Edit the "Review categories"
section in `build_review_prompt()` to add/remove categories. The prompt is in:
- `opencode_review.py` lines 85-136
- `pr_review.py` lines 62-135

### Project conventions (AGENTS.md)

Both reviewers read `AGENTS.md` for your project's rules. Keep this file
up-to-date with your coding standards. Example conventions:

```
## Critical Rules
- ALL public functions must have corresponding unit tests
- Use raise for invalid inputs (TypeError, ValueError)
- Type hints required on all public functions
- Test coverage must not decrease with new PRs

## Conventions
- pytest with class TestXxx and def test_* methods
- snake_case naming for all Python identifiers
- Ruff for linting and formatting (line length 88, double quotes)
```

---

## Security

### OpenCode

- API key stored as encrypted GitHub Secret
- Runs in read-only CI environment
- No GCP infrastructure needed
- Go providers follow zero-retention policy

### Gemini

- Uses Workload Identity Federation (no long-lived service account keys)
- GitHub's OIDC token is short-lived (5-10 minutes)
- Service account impersonation requires `roles/iam.workloadIdentityUser`
- Access restricted to specific repos via attribute condition
  (`assertion.repository_owner == 'YOUR_ORG'`)

---

## Troubleshooting

### OpenCode: "File not found" or empty response

**Symptom:** `opencode run failed: Error: File not found` or empty stdout.

**Fix:** The review script passes the prompt directly as a message argument
(not via `--file`). Ensure `call_opencode()` looks like:

```python
result = subprocess.run(
    ["opencode", "run", "--model", model, prompt],
    capture_output=True, text=True, timeout=300,
    env={**os.environ, "OPENCODE_API_KEY": os.environ.get("OPENCODE_API_KEY", "")},
)
```

Also check stdout is populated; fall back to stderr if stdout is empty.

### OpenCode: JSON parsing fails

**Symptom:** `ERROR parsing JSON: Expecting value: line 1 column 1 (char 0)`

**Fix:** The model returned empty or non-JSON output. Check the raw response
logged in the workflow run. If it returned markdown instead of JSON, the prompt
may be too large (truncated at 80K chars for the diff, but the instructions
also need room). Try using a model with larger context or shorten the diff.

### GCP: NOT_FOUND on provider describe

**Symptom:** `ERROR: (gcloud.iam.workload-identity-pools.providers.describe) NOT_FOUND`

**Fix:** This is a known propagation delay. Wait 2-5 minutes and the resource
becomes queryable. The provider was created successfully (the line before the
error confirms it).

### Gemini: 403 error

**Symptom:** `Gemini API error 403`

**Fix:**
1. Verify Vertex AI API is enabled:
   `gcloud services list --enabled | grep aiplatform`
2. Check the service account has `roles/aiplatform.user` on the project
3. Wait 5 minutes after creating Workload Identity Federation (propagation)

### Gemini: 429 error (rate limit)

Use a different region or switch to `gemini-2.5-flash` which has higher quotas.

### Workflow not triggering

1. Ensure `pull_request` event types include `labeled`
2. Check the `if` condition matches your label name exactly
3. Verify the PR is not a draft
4. Confirm GitHub Actions has **Read and write permissions** in repo settings

---

## Review Output Format

Each review comment follows this structure:

```markdown
## OpenCode AI Code Review

**Model:** deepseek-v4-pro | **Verdict:** Request Changes

> Brief 2-3 sentence overall assessment.

### Findings

#### 1. [CRITICAL] Issue title here
**Category:** testing | **File:** src/calculator.py (near 13-14)

Detailed explanation with specific suggestion for how to fix.

### Suggestions
- Overall improvement suggestion 1
- Overall improvement suggestion 2

---
Review generated by OpenCode (deepseek-v4-pro) via Go subscription
```

No emojis or icons are used in the PR comment - severity is indicated by
`[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]` text tags only.

---

## File Checklist for a New Repo

To replicate this setup in any repository, copy these files:

```
.github/
  workflows/
    ci.yml                     # Basic CI: pytest + ruff (optional)
    opencode-pr-review.yml      # OpenCode review workflow
    gemini-pr-review.yml        # Gemini review workflow
  scripts/
    opencode_review.py          # OpenCode review engine
    pr_review.py                # Gemini review engine
scripts/
  gcp-setup.sh                 # GCP infrastructure automation
AGENTS.md                      # Project conventions (read by AI reviewers)
CLAUDE.md                      # Quick reference for human contributors
pyproject.toml                 # Python project config (uv, pytest, ruff)
src/
  __init__.py
  calculator.py                # Example business logic
  utils.py                     # Example utilities
tests/
  __init__.py
  test_calculator.py           # Example tests
  test_utils.py                # Example tests
.gitignore
```

The reference implementation is in this repository at every path listed above.

---

## Cleanup (Removing GCP Resources)

If you ever need to tear down the GCP setup:

```bash
# Delete the service account
gcloud iam service-accounts delete pr-reviewer@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID

# Delete the OIDC provider
gcloud iam workload-identity-pools providers delete github \
  --project=PROJECT_ID --location=global --workload-identity-pool=github-actions

# Delete the workload identity pool
gcloud iam workload-identity-pools delete github-actions \
  --project=PROJECT_ID --location=global
```

---

## References

- [OpenCode Docs](https://opencode.ai/docs/)
- [OpenCode Go Subscription](https://opencode.ai/docs/go/)
- [Vertex AI Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/overview)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [google-github-actions/auth](https://github.com/marketplace/actions/authenticate-to-google-cloud)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
