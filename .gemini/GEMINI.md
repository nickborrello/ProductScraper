# Gemini Instructions

- Before each commit, please run `ruff format .` to ensure the code is formatted correctly.
- Before each commit, please run `uv run ruff check src/ tests/` and debug all linting errors. Use `uv run ruff check src/ tests/ --fix` to automatically fix simple errors first.
- Commit after each major implementation and testing of the feature.