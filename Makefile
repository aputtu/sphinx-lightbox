# Makefile for sphinx-lightbox development
# Provides convenient shortcuts for common tasks

.PHONY: help install install-dev test test-quick test-all lint format type docs docs-pdf docs-live all clean build

# Default target
help:
	@echo ""
	@echo "sphinx-lightbox development commands"
	@echo "====================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run tests (quick, single environment)"
	@echo "  make test-quick     Run only unit tests (fastest)"
	@echo "  make test-all       Run full test matrix (all Python × Sphinx)"
	@echo "  make coverage       Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Check code style"
	@echo "  make format         Auto-format code"
	@echo "  make type           Run type checker"
	@echo "  make check          Run all quality checks (lint + type)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs           Build HTML + LaTeX source"
	@echo "  make docs-pdf       Build HTML + PDF (requires pdflatex)"
	@echo "  make all            Build PDF then HTML, with PDF linked in HTML output"
	@echo "  make docs-live      Auto-rebuild docs on changes"
	@echo ""
	@echo "Build:"
	@echo "  make build          Build distribution packages"
	@echo "  make clean          Remove build artifacts"
	@echo ""

# --- Setup ---

install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pip install -e .

# --- Testing ---

test:
	pytest

test-quick:
	pytest -m unit

test-all:
	tox

coverage:
	pytest --cov --cov-report=html
	@echo ""
	@echo "Coverage report: htmlcov/index.html"

# --- Code Quality ---

lint:
	ruff check lightbox tests

format:
	ruff format lightbox tests
	ruff check --fix lightbox tests

type:
	mypy lightbox

check: lint type
	@echo ""
	@echo "✓ All quality checks passed"

# --- Documentation ---

docs:
	sphinx-build -W -j auto -b html docs _build/html
	sphinx-build -W -j auto -b latex docs _build/latex
	@echo ""
	@echo "HTML docs: _build/html/index.html"
	@echo "LaTeX docs: _build/latex/"

docs-pdf:
	sphinx-build -W -j auto -b html docs _build/html
	sphinx-build -W -j auto -b latex docs _build/latex
	$(MAKE) -C _build/latex all-pdf
	@echo ""
	@echo "HTML docs: _build/html/index.html"
	@echo "PDF:       _build/latex/sphinx-lightbox.pdf"

all:
	sphinx-build -W -j auto -b latex docs _build/latex
	$(MAKE) -C _build/latex all-pdf
	sphinx-build -W -j auto -b html docs _build/html
	cp _build/latex/sphinx-lightbox.pdf _build/html/sphinx-lightbox.pdf
	@echo ""
	@echo "HTML docs: _build/html/index.html"
	@echo "PDF:       _build/html/sphinx-lightbox.pdf"

docs-live:
	sphinx-autobuild docs _build/html

# --- Build ---

build:
	python -m build

clean:
	rm -rf _build/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# --- Convenience targets ---

# Quick validation before commit
pre-commit: test-quick lint
	@echo ""
	@echo "✓ Pre-commit checks passed"

# Full validation before push
pre-push: test check
	@echo ""
	@echo "✓ Pre-push checks passed"

# Release preparation
pre-release: test-all check all build
	@echo ""
	@echo "✓ Release checks passed"
	@echo ""
	@echo "Distribution files:"
	@ls -lh dist/
