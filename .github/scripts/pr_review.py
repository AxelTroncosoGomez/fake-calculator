"""
Gemini PR Code Reviewer

Reviews a GitHub Pull Request diff using Vertex AI Gemini API and posts
structured findings as PR comments.

Authentication: Uses Application Default Credentials (ADC) set by
google-github-actions/auth in the calling workflow. No explicit key needed.

Environment variables expected:
  GCP_PROJECT_ID        - GCP project ID
  GCP_REGION            - Vertex AI region (default: us-central1)
  GEMINI_MODEL          - Model ID (default: gemini-2.5-pro)
  GITHUB_TOKEN          - GitHub PAT for posting comments
  GITHUB_REPOSITORY     - owner/repo (set by GitHub Actions)
  GITHUB_PULL_REQUEST_NUMBER - PR number (set by GitHub Actions)
  REVIEW_MAX_TOKENS     - Max output tokens (default: 4096)
  REVIEW_TEMPERATURE    - Model temperature (default: 0.3)
"""

import json
import os
import subprocess
import sys
from urllib import error, request


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
    """Build a structured prompt for the Gemini model to review code."""
    file_list = "\n".join(f"  - {f}" for f in changed_files[:50])
    truncated = ""
    if len(changed_files) > 50:
        truncated = f"  ... and {len(changed_files) - 50} more files"

    prompt = f"""You are a senior software engineer performing a thorough code review.

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
      "file": "path/to/file.js",
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
    return prompt


def call_gemini(prompt):
    """Call Vertex AI Gemini API using ADC auth token."""
    project_id = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_REGION", "us-central1")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    max_tokens = int(os.environ.get("REVIEW_MAX_TOKENS", "4096"))
    temperature = float(os.environ.get("REVIEW_TEMPERATURE", "0.3"))

    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/"
        f"publishers/google/models/{model}:generateContent"
    )

    # Get ADC access token via gcloud
    token_result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
    )
    if token_result.returncode != 0:
        raise RuntimeError(f"Failed to get auth token: {token_result.stderr}")
    access_token = token_result.stdout.strip()

    payload = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
            },
        }
    ).encode("utf-8")

    req = request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")

    try:
        with request.urlopen(req, timeout=120) as resp:
            response_body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        raise RuntimeError(f"Gemini API error {e.code}: {e.read().decode()}")

    # Parse the response
    try:
        text = response_body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(
            f"Unexpected response format: {json.dumps(response_body, indent=2)}"
        )

    return text


def extract_json(text):
    """Extract JSON object from model response text."""
    # Find JSON block between ```json ... ``` or raw { ... }
    text = text.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif text.startswith("{"):
        pass
    else:
        # Try to find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def format_comment(review_data):
    """Format review findings into a GitHub comment body."""
    findings = review_data.get("findings", [])
    summary = review_data.get("summary", "No summary provided.")
    verdict = review_data.get("verdict", "comment")
    suggestions = review_data.get("suggestions", [])

    severity_icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "info": "⚪",
    }
    verdict_labels = {
        "approve": "✅ Approve",
        "request_changes": "❌ Request Changes",
        "comment": "💬 Comment",
    }

    lines = [
        "## 🤖 Gemini Code Review",
        "",
        f"**Verdict:** {verdict_labels.get(verdict, verdict)}",
        "",
        f"> {summary}",
        "",
    ]

    if not findings:
        lines.append("No issues found. Great work! 🎉")
        return "\n".join(lines)

    lines.append("### Findings")
    lines.append("")

    for i, finding in enumerate(findings, 1):
        icon = severity_icons.get(finding.get("severity", "info"), "⚪")
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
    lines.append("*Review generated by Gemini (Vertex AI) in CI/CD pipeline*")

    return "\n".join(lines)


def post_comment(body):
    """Post a review comment on the PR using gh CLI."""
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_number = os.environ["GITHUB_PULL_REQUEST_NUMBER"]

    tmpfile = "/tmp/gemini-review-comment.md"
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

    # Only post inline for critical and high severity
    inline = [
        f
        for f in findings
        if f.get("severity") in ("critical", "high") and f.get("file")
    ]

    for finding in inline[:10]:  # Limit to 10 inline comments
        body = (
            f"**{finding.get('severity', '').upper()}**: "
            f"{finding.get('title', '')}\n\n"
            f"{finding.get('description', '')}"
        )
        file_path = finding["file"]
        line = finding.get("line", "")

        # Try to extract line number from line info
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
                f"Warning: Failed to post inline comment "
                f"on {file_path}: {result.stderr}"
            )


def main():
    print("=== Gemini PR Code Reviewer ===")

    # Validate required env vars
    required = [
        "GCP_PROJECT_ID",
        "GITHUB_TOKEN",
        "GITHUB_REPOSITORY",
        "GITHUB_PULL_REQUEST_NUMBER",
    ]
    missing = [v for v in required if v not in os.environ]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    print(f"Model: {model}")
    print(f"Project: {os.environ['GCP_PROJECT_ID']}")
    print(f"Region: {os.environ.get('GCP_REGION', 'us-central1')}")

    # Fetch PR context
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

    # Build prompt and call Gemini
    print("Building review prompt...")
    prompt = build_review_prompt(diff, changed_files)

    print(f"Calling Gemini ({model})...")
    try:
        response_text = call_gemini(prompt)
    except RuntimeError as e:
        print(f"ERROR calling Gemini: {e}")
        # Post a failure comment on the PR
        post_comment(
            "## Gemini Code Review\n\n"
            "❌ **Review failed.** The AI model could not complete the review.\n\n"
            f"Error: {e}"
        )
        sys.exit(1)

    # Parse the response
    print("Parsing Gemini response...")
    try:
        review_data = extract_json(response_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR parsing JSON from model response: {e}")
        print(f"Raw response (first 1000 chars): {response_text[:1000]}")
        post_comment(
            "## Gemini Code Review\n\n"
            "❌ **Review failed.** The AI model returned an unexpected format.\n\n"
            "Raw response was logged but could not be parsed as JSON."
        )
        sys.exit(1)

    findings = review_data.get("findings", [])
    verdict = review_data.get("verdict", "comment")
    print(f"Findings: {len(findings)}, Verdict: {verdict}")

    # Build and post the summary comment
    comment = format_comment(review_data)
    print("Posting review comment...")
    post_comment(comment)

    # Post inline comments for critical/high findings
    if findings:
        post_inline_comments(findings)

    # Approve or request changes based on verdict
    if verdict == "approve":
        # Optionally auto-approve
        pass
    elif verdict == "request_changes":
        print("Verdict: REQUEST CHANGES (critical issues found)")

    print("Review complete.")


if __name__ == "__main__":
    main()
