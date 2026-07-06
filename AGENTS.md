# Architecture

## Project Structure

```
src/
  calculator.py   - Core business logic (calculate_total, apply_discount, format_currency)
  utils.py        - Utility functions (validate_email, truncate_string, debounce)
tests/
  test_calculator.py  - Unit tests for calculator.py
  test_utils.py       - Unit tests for utils.py
.github/
  workflows/    - CI workflows (basic CI + Gemini + OpenCode AI review)
  scripts/      - Review automation scripts
docs/           - Documentation
scripts/        - GCP setup automation
```

## Critical Rules

- ALL public functions must have corresponding unit tests
- Use `raise` for invalid inputs (TypeError, ValueError), never silent failures
- Functions must be pure when possible (no side effects)
- No external dependencies for core logic
- Test coverage must not decrease with new PRs
- Type hints required on all public functions

## Conventions

- pytest for testing, with `class TestXxx` and `def test_*` methods
- snake_case naming for all Python identifiers
- Files: lowercase with underscores for multi-word names
- Test files: match source filename with `test_` prefix
- Docstrings on public functions describing parameters and return values
- Ruff for linting and formatting (line length 88, double quotes)
