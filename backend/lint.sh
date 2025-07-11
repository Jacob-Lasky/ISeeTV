#!/bin/bash
# lint.sh
set -e

echo "Running Ruff..."
uv run ruff check .

echo "Running Black..."
uv run black .

echo "Running MyPy..."
uv run mypy .