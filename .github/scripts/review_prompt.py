"""
Shared review utilities for AI PR code reviewers.

Provides prompt building, JSON extraction, PR diff fetching, and comment
posting logic used by both the OpenCode and Gemini review scripts.
"""

import json
import os
import subprocess


def get_pr_diff():
    """Fetch the PR diff using gh CLI."""
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]
    result = subprocess.run(
        ["gh", "pr", "diff", pr_number, "--repo", repo],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh pr diff failed: {result.stderr}")
    return result.stdout


def get_pr_changed_files():
    """Fetch list of files changed in the PR."""
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            pr_number,
            "--repo",
            repo,
            "--json",
            "files",
            "--jq",
            ".files[].path",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def build_review_prompt(diff, changed_files):
    """Build a structured prompt for the AI model to review code."""
    file_list = "\n".join(f"  - {f}" for f in changed_files[:50])
    truncated = ""
    if len(changed_files) > 50:
        truncated = f"  ... and {len(changed_files) - 50} more files"

    return f"""You are a senior software engineer performing a thorough code review.

Review the following Pull Request diff and provide structured feedback.
Focus on the categories below with specific, actionable advice.

## Files changed:
{file_list}{truncated}

## Review categories (check each):

1. **Test Quality & Coverage**
   - Are new/modified functions covered by tests?
   - Are edge cases tested? (null, empty, boundary values)
   - Do test names clearly describe what's being tested?
   - Are tests isolated and deterministic?

2. **Clean Code & Readability**
   - Are function names descriptive and consistent?
   - Is the code DRY (no duplication)?
   - Are functions small and single-purpose?
   - Are magic numbers/strings extracted as constants?

3. **Formatting & Style**
   - Is naming consistent with project conventions?
   - Is whitespace/indentation consistent?
   - Are imports organized?

4. **Error Handling & Robustness**
   - Are errors handled appropriately?
   - Is input validated?
   - Are there any potential null reference issues?

5. **Security**
   - Any hardcoded secrets or credentials?
   - Any unsafe input handling?
   - Are dependencies secure?

6. **Performance**
   - Any obvious N+1 query patterns?
   - Are there unnecessary allocations or loops?
   - Is async used where appropriate?

## Important constraints:
- NEVER check or flag version numbers in `uses:` fields of GitHub Actions
  workflow steps (e.g. `uses: actions/checkout@v6`). These versions are
  correct and maintained by the repository owners. Do not report version
  availability as an issue under any review category.

## Output format:
Return a JSON object with this structure:
{{
  "summary": "Brief 2-3 sentence overall assessment",
  "findings": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "testing|clean-code|formatting|error-handling|security|performance",
      "file": "path/to/file",
      "line": "approximate line mention from diff context",
      "title": "Short title (max 80 chars)",
      "description": "Detailed explanation with specific suggestion"
    }}
  ],
  "suggestions": ["1-3 overall improvement suggestions as strings"],
  "verdict": "approve|request_changes|comment"
}}

- severity: "critical" = bug/vulnerability, must fix. "high" = likely problem.
  "medium" = improvement. "low" = nitpick. "info" = observation.
- verdict: "approve" if code is ready to merge, "request_changes" if
  critical/high issues exist, "comment" for feedback only.
- Be specific: reference exact filenames, mention concrete line ranges,
  suggest concrete code changes.
- Do NOT suggest adding logging as a fix for real bugs.
- If there are no issues to report, return an empty findings array and
  verdict "approve".

## PR Diff:
```diff
{diff[:80000]}
```
"""


def extract_json(text):
    """Extract a JSON object from model response text.

    Handles preamble before ```json blocks, missing closing fences
    (truncated responses), and bare JSON objects.
    """
    text = text.strip()

    if "```json" in text:
        start = text.index("```json") + 7
        if text[start : start + 1] == "\n":
            start += 1
        # Use rfind to avoid crashing when the model response is
        # truncated and the closing ``` is missing.
        end = text.rfind("```")
        if end != -1 and end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Fallback: locate JSON object by matching braces.
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        return json.loads(text[brace_start : brace_end + 1])

    return json.loads(text)


def post_comment(body, tmpfile_prefix="review"):
    """Post a review comment on the PR using gh CLI."""
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]

    tmpfile = f"/tmp/{tmpfile_prefix}-comment.md"
    with open(tmpfile, "w") as f:
        f.write(body)

    result = subprocess.run(
        [
            "gh",
            "pr",
            "review",
            pr_number,
            "--repo",
            repo,
            "--comment",
            "--body-file",
            tmpfile,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to post review: {result.stderr}")
    print(f"Review posted: {result.stdout.strip()}")


def post_inline_comments(findings):
    """Post inline review comments on specific lines (best-effort)."""
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]

    inline = [
        f
        for f in findings
        if f.get("severity") in ("critical", "high") and f.get("file")
    ]

    for finding in inline[:10]:
        body = (
            f"**{finding.get('severity', '').upper()}**: "
            f"{finding.get('title', '')}\n\n"
            f"{finding.get('description', '')}"
        )
        file_path = finding["file"]
        line = finding.get("line", "")

        line_num = None
        if line and "L" in str(line):
            try:
                line_num = int(str(line).replace("L", "").split(",")[0])
            except ValueError:
                pass

        cmd = [
            "gh",
            "api",
            f"/repos/{repo}/pulls/{pr_number}/comments",
            "-f",
            f"body={body}",
            "-f",
            f"path={file_path}",
        ]
        if line_num:
            cmd += ["-f", f"line={line_num}"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Warning: Failed to post inline comment on "
                f"{file_path}: {result.stderr}"
            )
