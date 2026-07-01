# sphinx-lightbox

`sphinx-lightbox` is a Sphinx extension that turns standard `.. image::`
and `.. figure::` directives into click-to-enlarge images in HTML output.
It uses a CSS checkbox-toggle mechanism, progressively enhanced with a small
JavaScript file for keyboard activation, focus management, Escape-to-close,
and optional gallery navigation.

Documentation is published at <https://aputtu.github.io/sphinx-lightbox/>.

## Quick Start

```bash
pip install sphinx-lightbox
```

Enable the extension in `conf.py`:

```python
extensions = ["lightbox"]
```

Opt a standard image into lightbox behavior:

```rst
.. image:: /images/example.png
   :alt: Example image.
   :class: lightbox
```

Figures are transformed by default and keep their normal page caption:

```rst
.. figure:: /images/example.png
   :alt: Example figure.

   This caption is also shown in the lightbox overlay.
```

## Development

Create a local virtual environment and install development dependencies:

```bash
make setup
```

Common commands:

| Command | Description |
| --- | --- |
| `make test` | Run the pytest suite |
| `make lint` | Run `ruff check` and `ruff format --check` |
| `make type` | Run `mypy` |
| `make check` | Run lint, type checks, and tests |
| `make docs` | Build PDF docs, HTML docs, and validate generated HTML |
| `make build` | Build distributions, run `twine check`, and validate archive contents |
| `make all` | Run check, docs, build, and dependency audit |

The documentation build writes HTML to `docs/_build/html/` and copies the PDF
download into `docs/_downloads/sphinx-lightbox.pdf` before rebuilding HTML, the
same pattern used by the GitHub Pages deployment workflow.

## Project Layout

```text
sphinx-lightbox/
|-- lightbox/                 Extension package
|   |-- lightbox.py
|   |-- py.typed
|   `-- static/
|       |-- lightbox.css
|       `-- lightbox.js
|-- docs/                     Sphinx documentation source
|   |-- _ext/                 Docs-only validation fixes
|   |-- _templates/           Accessible theme template overrides
|   |-- _downloads/           Generated PDF download location
|   `-- images/               Example images
|-- requirements/             Base, development, and docs requirements
|-- scripts/                  Local development and validation helpers
|-- tests/                    Unit and integration tests
|-- pyproject.toml
|-- tox.ini
`-- Makefile
```

## Requirements

- Python 3.10 or later
- Sphinx 7.0 through 9.x
- LaTeX tooling such as `latexmk` and `texlive-latex-extra` for PDF docs

## License

GPL-3.0-or-later.
