# slimv documentation build — bilingual (English + Arabic).
#
# Methodology (from the repo's book workflow): the en/ar split lives HERE in the
# Makefile, not in conf.py. Always build through these targets; never call
# sphinx-build by hand with an output path, or pages land in build/html/ instead
# of build/html/en/ and the language switch breaks.
#
#   make html       -> build/html/en/      (English)
#   make html-ar    -> build/html/ar/      (Arabic)
#   make html-all   -> both
#   make gettext    -> extract translatable strings to build/gettext/
#   make update-po  -> create/refresh source/locale/ar/LC_MESSAGES/*.po
#   make clean      -> remove the build directory

SPHINXBUILD ?= python -m sphinx
SOURCEDIR    = source
BUILDDIR     = build

.PHONY: help clean html html-ar html-all gettext update-po linkcheck

help:
	@echo "html       Build English HTML  -> $(BUILDDIR)/html/en"
	@echo "html-ar    Build Arabic HTML   -> $(BUILDDIR)/html/ar"
	@echo "html-all   Build both languages"
	@echo "gettext    Extract translatable strings"
	@echo "update-po  Create/refresh Arabic .po files"
	@echo "clean      Remove the build directory"

clean:
	rm -rf $(BUILDDIR)

html:
	SPHINX_LANG=en $(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html/en

html-ar:
	SPHINX_LANG=ar $(SPHINXBUILD) -b html -D language=ar $(SOURCEDIR) $(BUILDDIR)/html/ar

html-all: html html-ar

gettext:
	$(SPHINXBUILD) -b gettext $(SOURCEDIR) $(BUILDDIR)/gettext

update-po:
	python -m sphinx_intl update -p $(BUILDDIR)/gettext -l ar -d $(SOURCEDIR)/locale

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(SOURCEDIR) $(BUILDDIR)/linkcheck
