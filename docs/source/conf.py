# Sphinx configuration for the slimv documentation.
#
# Self-contained, bilingual (English + Arabic) build. The English/Arabic split
# is driven by the SPHINX_LANG environment variable, set by the Makefile
# targets (`make html` -> en, `make html-ar` -> ar) — never call sphinx-build
# by hand without it, or pages land in the wrong language directory.
#
# Methodology adapted from the repo's shared/conf_base.py (gettext i18n +
# sphinx_rtd_theme + RTL), but this project is standalone and imports nothing
# from the hub.

import os
import sys

# Make the `slimv` package importable so autodoc can read its docstrings.
# docs/source/conf.py  ->  ../..  ==  AV_kit/  (which contains slimv/).
sys.path.insert(0, os.path.abspath("../.."))

# -- Build language ----------------------------------------------------------

_build_lang = os.environ.get("SPHINX_LANG", "en")

# -- Project information -----------------------------------------------------

project = "slimv"
copyright = "2026, Haleem"
author = "Haleem"
release = "0.2.2"
version = "0.2.2"

language = _build_lang
html_title = f"slimv {release}"
if _build_lang == "ar":
    html_title = f"slimv {release} — التوثيق العربي"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",      # pull docstrings from the slimv package
    "sphinx.ext.napoleon",     # understand Google/NumPy-style docstrings
    "sphinx.ext.viewcode",     # add "view source" links to the API pages
    "sphinx.ext.autosummary",  # summary tables for modules/functions
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

source_suffix = {".rst": "restructuredtext"}
master_doc = "index"
templates_path = ["_templates"]
exclude_patterns = ["locale"]

# -- Internationalization (gettext pipeline) ---------------------------------
# `make gettext` extracts strings to build/gettext; `make update-po` writes
# source/locale/ar/LC_MESSAGES/*.po; translate those, then `make html-ar`.

locale_dirs = ["locale/"]
gettext_compact = False
gettext_uuid = True
gettext_location = True

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "titles_only": False,
}

# Language-conditional assets: Arabic gets the RTL override stylesheet.
html_css_files = ["lang-switch.css"]
html_js_files = ["lang-switch.js"]
if _build_lang == "ar":
    html_css_files = ["lang-switch.css", "rtl.css"]

# No external intersphinx targets — this machine builds offline.
intersphinx_mapping = {}

highlight_language = "bash"
pygments_style = "monokai"
todo_include_todos = True
