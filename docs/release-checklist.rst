Release Checklist
=================

Use this checklist before tagging a release.

1. Confirm the package version in ``pyproject.toml`` and
   ``lightbox/lightbox.py``.
2. Add a dated entry to ``docs/changelog.rst`` with user-visible changes,
   support notes, and security-relevant updates.
3. Run the local quality gates:

   .. code-block:: bash

      python -m ruff check lightbox tests docs/_ext scripts
      python -m ruff format --check lightbox tests docs/_ext scripts
      python -m mypy lightbox
      python -m pytest
      node --check lightbox/static/lightbox.js
      bash -n scripts/*.sh

4. Build and validate the HTML documentation:

   .. code-block:: bash

      python -m sphinx -W --keep-going -E -a -d docs/_build/doctrees/html -b html docs docs/_build/html
      python scripts/validate_docs.py docs/_build/html
      bash scripts/validate_standards.sh docs/_build/html

5. Run the browser keyboard and focus checks after installing Playwright and
   its Chromium browser:

   .. code-block:: bash

      python -m playwright install chromium
      python scripts/browser_smoke.py docs/_build/html/index.html

6. Rebuild the PDF download and then rebuild HTML so the download link points
   to the fresh PDF:

   .. code-block:: bash

      ./scripts/dev.sh docs

7. Build and check distributions:

   .. code-block:: bash

      rm -rf build dist ./*.egg-info
      python -m build
      python -m twine check dist/*
      python scripts/validate_dist.py dist

8. Install the built wheel in a fresh environment and build a minimal Sphinx
   project using ``extensions = ["lightbox"]``.
9. Run ``pip-audit`` for the release environment.
10. Confirm the release version is not already present on PyPI immediately
    before publishing.
11. Create the release commit, tag it as ``vX.Y.Z``, and push the tag.
12. Verify that GitHub Actions finishes the test matrix, docs validation,
    GitHub Pages deployment, and PyPI trusted-publishing job.
