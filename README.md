# sphinx-lightbox

A Sphinx extension providing accessible, CSS-only click-to-enlarge images.
The lightbox uses a pure checkbox-toggle mechanism — no JavaScript required.

This directory contains both the extension source and its self-referential
documentation (the docs use the extension to render live examples).

## Quick Start

```bash
# Install dev dependencies (includes Sphinx):
pip install -e ".[dev]"

# Build HTML + PDF (recommended — PDF is linked from the HTML index):
make all

# Open in browser:
xdg-open _build/html/index.html    # Linux
open _build/html/index.html         # macOS
```

## Build Targets

| Command          | Output                                              |
|------------------|-----------------------------------------------------|
| `make all`       | PDF first, then HTML with PDF linked in index       |
| `make docs`      | HTML + LaTeX source (no PDF compilation)            |
| `make docs-pdf`  | HTML + compiled PDF (in `_build/latex/`)            |
| `make docs-live` | Auto-rebuild HTML on file changes                   |
| `make clean`     | Remove all build artifacts                          |

> **Note:** `make all` is the recommended documentation build — it ensures
> the PDF exists before the HTML is generated, so the download link in
> `index.rst` resolves correctly.

## Development Targets

| Command            | Description                                   |
|--------------------|-----------------------------------------------|
| `make test`        | Run test suite (pytest)                       |
| `make test-quick`  | Unit tests only (fastest)                     |
| `make test-all`    | Full matrix: Python 3.8/3.10/3.12 × Sphinx 7/8/9 |
| `make coverage`    | Tests with HTML coverage report               |
| `make lint`        | Code style check (ruff)                       |
| `make format`      | Auto-format code (ruff)                       |
| `make type`        | Type checking (mypy)                          |
| `make check`       | lint + type                                   |
| `make pre-commit`  | test-quick + lint                             |
| `make pre-push`    | test + check                                  |
| `make pre-release` | Full validation + all + build                 |

## Project Layout

```
sphinx-lightbox/
├── Makefile                 ← Build and development commands
├── pyproject.toml           ← Package metadata and tool config
├── requirements.txt         ← Production dependencies
├── requirements-dev.txt     ← Development dependencies
├── pytest.ini               ← Test configuration
├── tox.ini                  ← Multi-environment test matrix
├── lightbox/                ← Extension source code
│   ├── __init__.py
│   ├── lightbox.py
│   └── static/
│       └── lightbox.css
├── docs/                    ← Documentation source (RST files)
│   ├── conf.py              ← Sphinx configuration
│   ├── index.rst
│   ├── installation.rst
│   ├── usage.rst
│   ├── accessibility.rst
│   ├── directive.rst
│   ├── api.rst
│   ├── changelog.rst
│   ├── license.rst
│   └── images/              ← Example images for live demos
│       ├── example-screenshot.png
│       └── example-detail.png
└── tests/
    ├── conftest.py          ← Shared fixtures
    └── test_latex.py        ← Full test suite (LaTeX + HTML + directive)
```

## Self-Referential Design

`docs/conf.py` adds the project root to `sys.path` and loads the `lightbox`
extension from the source tree directly. Every `.. lightbox::` directive in
the documentation is rendered by the actual extension code — changes to the
extension are immediately visible when rebuilding the docs.

## Requirements

- Python 3.8 or later
- Sphinx 7.0 or later
- `pdflatex` + `texlive-latex-extra` (for PDF builds via `make all` or `make docs-pdf`)
