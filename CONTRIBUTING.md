# Contributing to sphinx-lightbox

This project keeps local development commands behind the Makefile so checks run
through the project virtual environment and match CI closely.

## Development Setup

```bash
git clone https://github.com/aputtu/sphinx-lightbox.git
cd sphinx-lightbox
make setup
```

To choose a specific Python interpreter:

```bash
PYTHON_BIN=python3.12 make setup
```

## Local Workflow

Run the main quality gate:

```bash
make check
```

The pytest configuration enforces 100% line and branch coverage for the
`lightbox` package.

Build and validate documentation:

```bash
make docs
```

Build the package artifacts and verify their contents:

```bash
make build
```

Run the targeted tox checks used during release preparation:

```bash
python -m tox -p auto -e lint,mypy,docs,py312-sphinx91
```

Run the full configured tox matrix when the required Python interpreters are
available:

```bash
python -m tox -p auto
```

## Documentation

Documentation source lives in `docs/`. Behavior changes should update the
relevant user guide or reference page. The generated HTML is validated by
`scripts/validate_docs.py`.

The published GitHub Pages site includes a downloadable PDF. `make html` and
`make docs` refresh `docs/_downloads/sphinx-lightbox.pdf` when needed before
building HTML, so those targets require LaTeX.

## Pull Requests

Before submitting a change:

1. Add or update tests for behavior changes.
2. Update documentation for user-visible changes.
3. Run `make check`.
4. Run `make docs` when documentation or rendered output changed.
5. Run `make build` before release-related changes.
