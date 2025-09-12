#!/bin/bash
# lint.sh
set -e

echo "Running Ruff Format..."
uv run ruff format .

echo "Running Ruff..."
uv run ruff check .

echo "Running Pyright..."
uv run pyright .