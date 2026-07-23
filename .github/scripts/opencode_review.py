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

from review_prompt import (
    build_review_prompt,
    extract_json,
    get_pr_changed_files,
    get_pr_diff,
    post_comment,
    post_inline_comments,
)


def call_opencode(prompt):
    """Call opencode CLI with the review prompt."""
    model = os.environ.get("OPENCODE_MODEL", "opencode-go/deepseek-v4-pro")

    result = subprocess.run(
        [
            "opencode",
            "run",
            "--model",
            model,
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=300,
        env={
            **os.environ,
            "OPENCODE_API_KEY": os.environ.get("OPENCODE_API_KEY", ""),
        },
    )

    if result.returncode != 0:
        raise RuntimeError(f"opencode run failed: {result.stderr}")

    output = result.stdout.strip()
    if not output and result.stderr.strip():
        output = result.stderr.strip()

    if not output:
        raise RuntimeError("opencode returned empty response")

    return output


def format_comment(review_data):
    """Format review findings into a GitHub comment body."""
    findings = review_data.get("findings", [])
    summary = review_data.get("summary", "No summary provided.")
    verdict = review_data.get("verdict", "comment")
    suggestions = review_data.get("suggestions", [])

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
        (
            f"**Model:** `{short_name}` "
            f"| **Verdict:** {verdict_labels.get(verdict, verdict)}"
        ),
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
        category = finding.get("category", "general")
        title = finding.get("title", "Issue")
        description = finding.get("description", "")
        file_path = finding.get("file", "")
        line_info = finding.get("line", "")

        location = f"`{file_path}`"
        if line_info:
            location += f" (near {line_info})"

        lines.append(f"#### {i}. [{finding.get('severity', 'info').upper()}] {title}")
        lines.append(f"**Category:** {category} | **File:** {location}")
        lines.append("")
        lines.append(description)
        lines.append("")

    if suggestions:
        lines.append("### Suggestions")
        for s in suggestions:
            lines.append(f"- {s}")

    return "\n".join(lines)


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
            f"Error: {e}",
            tmpfile_prefix="opencode-review",
        )
        sys.exit(1)

    print("Parsing response...")
    try:
        review_data = extract_json(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR parsing JSON from model response: {e}")
        print(f"Raw response (first 1000 chars): {response_text[:1000]}")
        print(f"Raw response (last 500 chars): {response_text[-500:]}")
        post_comment(
            "## OpenCode AI Code Review\n\n"
            "The AI model returned an unexpected format.\n\n"
            "Raw response was logged but could not be parsed as JSON.",
            tmpfile_prefix="opencode-review",
        )
        sys.exit(1)

    findings = review_data.get("findings", [])
    verdict = review_data.get("verdict", "comment")
    print(f"Findings: {len(findings)}, Verdict: {verdict}")

    comment = format_comment(review_data)
    print("Posting review comment...")
    post_comment(comment, tmpfile_prefix="opencode-review")

    if findings:
        post_inline_comments(findings)

    if verdict == "request_changes":
        print("Verdict: REQUEST CHANGES (critical issues found)")

    print("Review complete.")


if __name__ == "__main__":
    main()
