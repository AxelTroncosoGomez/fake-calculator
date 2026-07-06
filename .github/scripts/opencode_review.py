"""
OpenCode PR Code Reviewer (DeepSeek V4 Pro via OpenCode Go)

Reviews a GitHub Pull Request diff using opencode CLI with the Go subscription
model opencode-go/deepseek-v4-pro. Posts structured findings as PR comments.

Authentication: Uses OPENCODE_API_KEY environment variable set by the calling
workflow from GitHub Secrets.

Environment variables expected:
  OPENCODE_API_KEY          - OpenCode Go/Zen API key
  GITHUB_TOKEN              - GitHub PAT for posting comments
  GITHUB_REPOSITORY         - owner/repo (set by GitHub Actions)
  GITHUB_PULL_REQUEST_NUMBER - PR number (set by GitHub Actions)
  OPENCODE_MODEL            - Model ID (default: opencode-go/deepseek-v4-pro)
"""

import json
import os
import subprocess
import sys
import tempfile


def get_pr_diff():
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

## Output format:
Return a JSON object with this structure:
{{
  "summary": "Brief 2-3 sentence overall assessment",
  "findings": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "testing|clean-code|formatting|error-handling|security|performance",
      "file": "path/to/file.py",
      "line": "approximate line mention from diff context",
      "title": "Short title (max 80 chars)",
      "description": "Detailed explanation with specific suggestion"
    }}
  ],
  "suggestions": ["1-3 overall improvement suggestions as strings"],
  "verdict": "approve|request_changes|comment"
}}

- severity: "critical" = bug/vulnerability, must fix. "high" = likely problem. "medium" = improvement. "low" = nitpick. "info" = observation.
- verdict: "approve" if code is ready to merge, "request_changes" if critical/high issues exist, "comment" for feedback only.
- Be specific: reference exact filenames, mention concrete line ranges, suggest concrete code changes.
- Do NOT suggest adding logging as a fix for real bugs.
- If there are no issues to report, return an empty findings array and verdict "approve".

## PR Diff:
```diff
{diff[:80000]}
```
"""


def call_opencode(prompt):
    model = os.environ.get("OPENCODE_MODEL", "opencode-go/deepseek-v4-pro")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="pr-review-"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        result = subprocess.run(
            [
                "opencode",
                "run",
                "--model",
                model,
                "--format",
                "json",
                "--file",
                prompt_file,
                "Review the attached PR diff and return JSON findings.",
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env={
                **os.environ,
                "OPENCODE_API_KEY": os.environ.get("OPENCODE_API_KEY", ""),
            },
        )
    finally:
        os.unlink(prompt_file)

    if result.returncode != 0:
        raise RuntimeError(f"opencode run failed: {result.stderr}")

    return result.stdout


def extract_json(text):
    text = text.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif text.startswith("{"):
        pass
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def format_comment(review_data):
    findings = review_data.get("findings", [])
    summary = review_data.get("summary", "No summary provided.")
    verdict = review_data.get("verdict", "comment")
    suggestions = review_data.get("suggestions", [])

    severity_icons = {
        "critical": "red_circle",
        "high": "orange_circle",
        "medium": "yellow_circle",
        "low": "blue_circle",
        "info": "white_circle",
    }
    verdict_labels = {
        "approve": "Approve",
        "request_changes": "Request Changes",
        "comment": "Comment",
    }

    model = os.environ.get("OPENCODE_MODEL", "deepseek-v4-pro")
    short_name = model.split("/")[-1]

    lines = [
        "## OpenCode AI Code Review",
        "",
        f"**Model:** `{short_name}` | **Verdict:** {verdict_labels.get(verdict, verdict)}",
        "",
        f"> {summary}",
        "",
    ]

    if not findings:
        lines.append("No issues found. Great work!")
        return "\n".join(lines)

    lines.append("### Findings")
    lines.append("")

    for i, finding in enumerate(findings, 1):
        icon = severity_icons.get(finding.get("severity", "info"), "white_circle")
        category = finding.get("category", "general")
        title = finding.get("title", "Issue")
        description = finding.get("description", "")
        file_path = finding.get("file", "")
        line_info = finding.get("line", "")

        location = f"`{file_path}`"
        if line_info:
            location += f" (near {line_info})"

        lines.append(
            f"#### {i}. {icon} [{finding.get('severity', 'info').upper()}] {title}"
        )
        lines.append(f"**Category:** {category} | **File:** {location}")
        lines.append("")
        lines.append(description)
        lines.append("")

    if suggestions:
        lines.append("### Suggestions")
        for s in suggestions:
            lines.append(f"- {s}")

    lines.append("")
    lines.append("---")
    lines.append(f"*Review generated by OpenCode ({short_name}) via Go subscription*")

    return "\n".join(lines)


def post_comment(body):
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]

    tmpfile = "/tmp/opencode-review-comment.md"
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


def main():
    print("=== OpenCode PR Code Reviewer ===")

    required = [
        "OPENCODE_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_REPOSITORY",
        "GITHUB_PULL_REQUEST_NUMBER",
    ]
    missing = [v for v in required if v not in os.environ]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    model = os.environ.get("OPENCODE_MODEL", "opencode-go/deepseek-v4-pro")
    print(f"Model: {model}")

    print("Fetching PR diff...")
    try:
        diff = get_pr_diff()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not diff.strip():
        print("No diff found. Skipping review.")
        return

    print(f"Diff size: {len(diff)} chars across {diff.count('diff --git')} files")
    changed_files = get_pr_changed_files()
    print(f"Changed files: {len(changed_files)}")

    print("Building review prompt...")
    prompt = build_review_prompt(diff, changed_files)

    print(f"Running OpenCode ({model})...")
    try:
        response_text = call_opencode(prompt)
    except RuntimeError as e:
        print(f"ERROR calling opencode: {e}")
        post_comment(
            "## OpenCode AI Code Review\n\n"
            "The AI model could not complete the review.\n\n"
            f"Error: {e}"
        )
        sys.exit(1)

    print("Parsing response...")
    try:
        review_data = extract_json(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR parsing JSON from model response: {e}")
        print(f"Raw response (first 1000 chars): {response_text[:1000]}")
        post_comment(
            "## OpenCode AI Code Review\n\n"
            "The AI model returned an unexpected format.\n\n"
            "Raw response was logged but could not be parsed as JSON."
        )
        sys.exit(1)

    findings = review_data.get("findings", [])
    verdict = review_data.get("verdict", "comment")
    print(f"Findings: {len(findings)}, Verdict: {verdict}")

    comment = format_comment(review_data)
    print("Posting review comment...")
    post_comment(comment)

    if findings:
        post_inline_comments(findings)

    if verdict == "request_changes":
        print("Verdict: REQUEST CHANGES (critical issues found)")

    print("Review complete.")


if __name__ == "__main__":
    main()
