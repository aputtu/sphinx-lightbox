# Configuration file for the Sphinx documentation builder.
#
# This documentation is self-referential: it uses the lightbox extension
# to display its own example images.

import os
import sys

from lightbox.lightbox import __version__ as _version

# -- Path setup ---------------------------------------------------------------
# conf.py lives in docs/; the lightbox package is one level up at the
# project root.  Add the project root to sys.path so Sphinx can import it.
sys.path.insert(0, os.path.abspath(".."))

# -- Project information ------------------------------------------------------
project = "sphinx-lightbox"
copyright = "2024–2026, Aputsiak Niels Janussen"
author = "Aputsiak Niels Janussen"
release = _version
version = ".".join(_version.split(".")[:2])

# -- General configuration ----------------------------------------------------
extensions = [
    "lightbox",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "venv*", "env*"]

# -- Options for HTML output --------------------------------------------------
html_theme = "alabaster"
html_title = "sphinx-lightbox"
html_short_title = "sphinx-lightbox"

# -- Options for LaTeX output -------------------------------------------------
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "11pt",
    "extraclassoptions": "oneside",
    "preamble": r"""
        \setlength{\headheight}{14pt}
        \addtolength{\topmargin}{-2pt}
        \usepackage{needspace}
        \usepackage{etoolbox}
        \preto{\sphinxVerbatim}{\needspace{6\baselineskip}}
    """,
}

latex_documents = [
    (
        "index",
        "sphinx-lightbox.tex",
        "sphinx-lightbox Documentation",
        author,
        "manual",
    ),
]

# -- Options for intersphinx --------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}
