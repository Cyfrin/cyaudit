# List available commands
list:
    @just --list

# Run typecheck
typecheck:
    uv run mypy . --implicit-optional

# Run formatter
format:
    uv run ruff check --select I --fix
    uv run ruff check . --fix

# Run formatter - no fix
format-check:
    uv run ruff check --select I 
    uv run ruff check .

test: 
    uv run pytest -x --ignore=tests/integration/

test-i: 
    uv run pytest tests/integration/

test-ig:
    uv run pytest tests/integration_github_fixtures -s

# # Build documentation
# docs:
#     rm -rf built_docs
#     uv sync --extra docs
#     uv run python docs/source/_generate_vars.py
#     uv run sphinx-build -M html docs/source built_docs -v
#     @echo "\nDocumentation link:"
#     @echo "http://127.0.0.1:5500/built_docs/html/index.html"

# docs-watch:
#     watchmedo shell-command --patterns="*.rst" --recursive --command='uv run sphinx-build -M html docs/source built_docs' docs/source

# build-requirements:
#     uv pip compile pyproject.toml -o requirements.txt