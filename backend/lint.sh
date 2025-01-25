#!/bin/bash
# lint.sh
set -e

echo "Running Ruff..."
poetry run ruff check .

echo "Running Black..."
poetry run black .

echo "Running MyPy..."
poetry run mypy .