#!/bin/bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Cleaning previous local development artifacts..."
rm -rf venv .tox docs/_build _build build dist ./*.egg-info htmlcov .pytest_cache .coverage ./.coverage.*
rm -f docs/_downloads/*.pdf
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +

echo "Creating virtual environment with $PYTHON_BIN..."
"$PYTHON_BIN" -m venv venv

echo "Installing development dependencies..."
venv/bin/python -m pip install --upgrade pip setuptools wheel
venv/bin/python -m pip install -r requirements/dev.txt
venv/bin/python -m pip install -r requirements/docs.txt
venv/bin/python -m pip install -e .

echo "Making development scripts executable..."
find scripts -name "*.sh" -exec chmod +x {} \;

echo "Development environment ready."
echo "Run 'make check' for tests and quality gates, or 'make docs' for documentation."
