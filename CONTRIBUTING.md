# Contributing

Contributions are welcome. A few expectations:

1. **Issues first for big changes** — open an issue (or discuss in an existing one) before large refactors or new features so direction stays aligned.
2. **Focused pull requests** — one logical change per PR; keep diffs easy to review.
3. **No secrets** — never commit real API keys or personal data. Use `ats_agent/.env.example` as a template; keep local config in `ats_agent/.env` (gitignored).
4. **Match the codebase** — follow existing layout, typing, and patterns in `ats_agent/src/`. The dev extra in `ats_agent/pyproject.toml` includes **ruff**, **black**, **isort**, **mypy**, and **pytest**; run what applies to your change before submitting.
5. **Smoke check** — from the repo root, `make test` runs a quick bytecode compile of package sources.
