import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version
from pathlib import Path

# Make the package importable when building docs without installing it first.
_DOCS_DIR = Path(__file__).parent
sys.path.insert(0, str(_DOCS_DIR.parent))
sys.path.insert(0, str(_DOCS_DIR / "_ext"))

# -- Project information ------------------------------------------------------
project = "sphinx-lightbox"
copyright = "2024-2026, Aputsiak Niels Janussen"
author = "Aputsiak Niels Janussen"

try:
    release = _get_version("sphinx-lightbox")
except PackageNotFoundError:
    release = "unknown"
version = ".".join(release.split(".")[:2]) if release != "unknown" else release

# -- General configuration ----------------------------------------------------
extensions = [
    "lightbox",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "validation_fixes",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "venv*", "env*"]

# -- Options for HTML output --------------------------------------------------
html_theme = "alabaster"
html_title = "sphinx-lightbox"
html_short_title = "sphinx-lightbox"
html_static_path = ["_static"]
html_css_files = ["accessibility.css"]

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
