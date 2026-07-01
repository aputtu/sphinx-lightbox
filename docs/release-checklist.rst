Release Checklist
=================

Use this checklist before tagging a release.

1. Confirm the package version in ``pyproject.toml`` and
   ``lightbox/lightbox.py``.
2. Add a dated entry to ``docs/changelog.rst`` with user-visible changes,
   support notes, and security-relevant updates.
3. Run the local quality gates:

   .. code-block:: bash

      python -m ruff check lightbox tests docs/_ext scripts/validate_docs.py
      python -m ruff format --check lightbox tests docs/_ext scripts/validate_docs.py
      python -m mypy lightbox
      python -m pytest

4. Build and validate the HTML documentation:

   .. code-block:: bash

      python -m sphinx -W --keep-going -E -a -b html docs docs/_build/html
      python scripts/validate_docs.py docs/_build/html

5. Rebuild the PDF download and then rebuild HTML so the download link points
   to the fresh PDF:

   .. code-block:: bash

      ./scripts/dev.sh docs

6. Build and check distributions:

   .. code-block:: bash

      python -m build
      python -m twine check dist/*
      python scripts/validate_dist.py dist

7. Install the built wheel in a fresh environment and build a minimal Sphinx
   project using ``extensions = ["lightbox"]``.
8. Run ``pip-audit`` for the release environment.
9. Confirm PyPI project name availability immediately before publishing.
10. Create the release commit, tag it as ``vX.Y.Z``, and push the tag.
11. Verify that GitHub Actions finishes the test matrix, docs validation,
    GitHub Pages deployment, and PyPI trusted-publishing job.
