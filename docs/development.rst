Development Workflow
====================

This project includes a small Makefile and shell helpers for repeatable local
development. The Makefile is the public entry point; the scripts underneath it
are useful when a single command needs to be run directly.

Environment Setup
-----------------

Create the local virtual environment and install development, documentation,
and editable package dependencies:

.. code-block:: bash

   make setup

``make setup`` recreates ``venv/`` and removes local build, tox, coverage, and
packaging artifacts before installing dependencies. By default it uses
``python3``. To choose another interpreter, set ``PYTHON_BIN``:

.. code-block:: bash

   PYTHON_BIN=python3.12 make setup

After setup, Makefile targets use tools from ``venv/bin`` instead of relying on
globally installed commands.

The pytest configuration enforces 100% line and branch coverage for the
``lightbox`` package.

Make Targets
------------

Run ``make`` or ``make help`` to print the available targets.

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Target
     - Purpose
   * - ``make setup``
     - Recreate ``venv/`` and install development dependencies.
   * - ``make test``
     - Install the package in editable mode and run pytest.
   * - ``make lint``
     - Run ``ruff check`` and ``ruff format --check``.
   * - ``make type``
     - Run ``mypy lightbox``.
   * - ``make check``
     - Run lint, type checks, and tests.
   * - ``make html``
     - Refresh the PDF download if needed, build HTML docs, then validate the
       generated HTML.
   * - ``make pdf``
     - Build the LaTeX documentation and compile the PDF download.
   * - ``make docs``
     - Build PDF docs, build HTML docs, and validate the generated HTML.
   * - ``make validate``
     - Validate an existing ``docs/_build/html`` tree.
   * - ``make standards``
     - Validate generated HTML, CSS, and SVG with the current Nu checker.
   * - ``make build``
     - Build source and wheel distributions, run ``twine check``, and validate
       archive contents.
   * - ``make audit``
     - Run ``pip-audit`` against the local environment.
   * - ``make all``
     - Run checks, docs, Nu standards validation, package build, and dependency
       audit.
   * - ``make watch``
     - Start ``sphinx-autobuild`` for the documentation.
   * - ``make clean``
     - Remove generated build, cache, coverage, and packaging artifacts.
   * - ``make clean-all``
     - Clean generated artifacts, then run the full local gate.

Documentation Builds
--------------------

The published GitHub Pages site includes a downloadable PDF, so the local docs
targets keep the PDF and HTML output in sync. ``make html`` rebuilds the PDF
first when ``docs/_downloads/sphinx-lightbox.pdf`` is missing or older than the
documentation, Python, CSS, or JavaScript sources. That path requires a working
LaTeX installation.

For HTML-only validation without LaTeX, use the same pattern as the CI docs
check:

.. code-block:: bash

   mkdir -p docs/_downloads
   touch docs/_downloads/sphinx-lightbox.pdf
   python -m sphinx -W --keep-going -E -a -d docs/_build/doctrees/html -b html docs docs/_build/html
   python scripts/validate_docs.py docs/_build/html

``tox -e docs`` also uses an HTML-only path with a placeholder PDF download.

For strict HTML Living Standard and CSS/SVG syntax checks, run ``make
standards`` after the HTML build. This downloads the current command-line Nu
checker to a temporary file, verifies its release-published SHA-256 digest, and
treats its warnings as failures. Java 17 or newer, ``curl``, and ``sha256sum``
are required. Set both ``VNU_JAR_URL`` and ``VNU_JAR_SHA256`` when deliberately
testing a different validator build.

Browser Accessibility Checks
----------------------------

After building the HTML documentation, run the same Chromium keyboard and
focus checks used by CI:

.. code-block:: bash

   python -m pip install playwright
   python -m playwright install chromium
   python scripts/browser_smoke.py docs/_build/html/index.html

The browser check covers keyboard activation, modal focus entry and return,
gallery switching, forward and reverse focus trapping, accessible control
roles and names, visible focus indicators, and focused controls that remain
rendered and unobscured at desktop and compact viewport sizes.

Direct Script Usage
-------------------

The Makefile delegates most commands to ``scripts/dev.sh``. The direct form is
useful in CI experiments or when invoking the workflow from another script:

.. code-block:: bash

   ./scripts/dev.sh check
   ./scripts/dev.sh docs
   ./scripts/dev.sh build

The script supports the same command names as the Makefile targets, without the
``make`` prefix.

Tox Matrix
----------

Use tox when checking the supported Python and Sphinx combinations:

.. code-block:: bash

   tox -p auto

The default matrix includes linting, type checking, documentation validation,
and tests across Python 3.10 through 3.14 with supported Sphinx releases.

Release-Quality Local Gate
--------------------------

Before tagging a release, run the broad local gate when the system has the
required tooling:

.. code-block:: bash

   make all
   tox -p auto

``make all`` expects LaTeX for PDF generation, Java, ``curl``, and
``sha256sum`` for Nu validation, and ``pip-audit`` for dependency auditing. The
release checklist has the complete tagging and publishing steps.
