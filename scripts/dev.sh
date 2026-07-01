#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_BIN="$PROJECT_ROOT/venv/bin"

if [ ! -f "$VENV_BIN/python" ]; then
    echo "Virtual environment not found. Run 'make setup' first."
    exit 1
fi

PYTHON="$VENV_BIN/python"
PIP="$VENV_BIN/pip"
PYTEST="$VENV_BIN/pytest"
RUFF="$VENV_BIN/ruff"
MYPY="$VENV_BIN/mypy"
SPHINX_BUILD="$VENV_BIN/sphinx-build"
PDF_DOWNLOAD="$PROJECT_ROOT/docs/_downloads/sphinx-lightbox.pdf"
DOCS_VALIDATOR="$PROJECT_ROOT/scripts/validate_docs.py"
DIST_VALIDATOR="$PROJECT_ROOT/scripts/validate_dist.py"

print_status() {
    echo "[$(date +'%H:%M:%S')] $1"
}

install_package() {
    print_status "Installing package in development mode..."
    "$PIP" install -e .
}

run_tests() {
    print_status "Running tests..."
    "$PYTEST"
}

run_lint() {
    print_status "Running ruff..."
    "$RUFF" check lightbox tests docs/_ext scripts/validate_docs.py scripts/validate_dist.py
    "$RUFF" format --check lightbox tests docs/_ext scripts/validate_docs.py scripts/validate_dist.py
}

run_typecheck() {
    print_status "Running mypy..."
    "$MYPY" lightbox
}

pdf_download_is_stale() {
    if [ ! -s "$PDF_DOWNLOAD" ]; then
        return 0
    fi

    local newer_file
    newer_file=$(
        find docs lightbox \
            \( -path "docs/_build" -o -path "docs/_downloads" -o -path "*/__pycache__" \) -prune \
            -o -type f \
            \( -name "*.rst" -o -name "*.py" -o -name "*.css" -o -name "*.js" \) \
            -newer "$PDF_DOWNLOAD" \
            -print -quit
    )

    [ -n "$newer_file" ]
}

build_pdf() {
    print_status "Building LaTeX documentation..."
    mkdir -p "$(dirname "$PDF_DOWNLOAD")"
    touch "$PDF_DOWNLOAD"
    "$SPHINX_BUILD" -W --keep-going -E -a -b latex docs docs/_build/latex

    print_status "Compiling PDF..."
    (cd docs/_build/latex && make)

    print_status "Refreshing PDF download..."
    mkdir -p docs/_downloads
    cp docs/_build/latex/*.pdf "$PDF_DOWNLOAD"
}

refresh_pdf_download() {
    if pdf_download_is_stale; then
        print_status "PDF download is missing or stale; rebuilding it first..."
        build_pdf
    else
        print_status "PDF download is up to date"
    fi
}

build_html() {
    refresh_pdf_download
    print_status "Building HTML documentation..."
    "$SPHINX_BUILD" -W --keep-going -E -a -b html docs docs/_build/html
}

validate_docs() {
    print_status "Validating generated HTML documentation..."
    "$PYTHON" "$DOCS_VALIDATOR" docs/_build/html
}

build_dist() {
    print_status "Building package distributions..."
    "$PYTHON" -m build
    "$PYTHON" -m twine check dist/*
    "$PYTHON" "$DIST_VALIDATOR" dist
}

audit_dependencies() {
    print_status "Running dependency audit..."
    "$PYTHON" -m pip_audit
}

clean_build() {
    print_status "Cleaning build artifacts..."
    rm -rf docs/_build _build build dist *.egg-info htmlcov .pytest_cache .coverage .coverage.*
    rm -f docs/_downloads/*.pdf
    find . -type d -name "__pycache__" -prune -exec rm -rf {} +
    find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
}

watch_changes() {
    print_status "Watching documentation sources..."
    "$VENV_BIN/sphinx-autobuild" docs docs/_build/html
}

show_help() {
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  test       Install package and run pytest"
    echo "  lint       Run ruff check and format check"
    echo "  type       Run mypy"
    echo "  check      Run lint, type, and tests"
    echo "  html       Refresh PDF if needed, then build HTML docs"
    echo "  pdf        Build PDF docs"
    echo "  docs       Build PDF docs, HTML docs, and validate generated HTML"
    echo "  validate   Validate generated HTML docs"
    echo "  build      Build sdist/wheel, run twine check, and validate contents"
    echo "  audit      Run pip-audit"
    echo "  all        Run check, docs, build, and audit"
    echo "  clean      Remove build artifacts"
    echo "  clean-all  Clean, then run all"
    echo "  watch      Auto-rebuild HTML docs"
}

case "${1:-}" in
    test)
        install_package
        run_tests
        ;;
    lint)
        run_lint
        ;;
    type)
        run_typecheck
        ;;
    check)
        run_lint
        run_typecheck
        install_package
        run_tests
        ;;
    html)
        install_package
        build_html
        validate_docs
        ;;
    pdf)
        install_package
        build_pdf
        ;;
    docs)
        install_package
        build_pdf
        build_html
        validate_docs
        ;;
    validate)
        validate_docs
        ;;
    build)
        build_dist
        ;;
    audit)
        audit_dependencies
        ;;
    all)
        run_lint
        run_typecheck
        install_package
        run_tests
        build_pdf
        build_html
        validate_docs
        build_dist
        audit_dependencies
        ;;
    clean)
        clean_build
        ;;
    clean-all)
        clean_build
        install_package
        run_lint
        run_typecheck
        run_tests
        build_pdf
        build_html
        validate_docs
        build_dist
        audit_dependencies
        ;;
    watch)
        install_package
        watch_changes
        ;;
    help | --help | -h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
