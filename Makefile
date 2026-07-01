VENV    := venv
PYTHON  := $(VENV)/bin/python
SCRIPTS := scripts

.DEFAULT_GOAL := help

$(PYTHON):
	@echo "No virtual environment found. Run 'make setup' first."
	@exit 1

.PHONY: help setup test lint type check html pdf docs validate build audit all clean clean-all watch

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  setup      Create venv and install development dependencies"
	@echo ""
	@echo "Development"
	@echo "  test       Run tests"
	@echo "  lint       Run ruff check and format check"
	@echo "  type       Run mypy"
	@echo "  check      Run lint, type, and tests"
	@echo "  html       Refresh PDF if needed, then build and validate HTML docs"
	@echo "  pdf        Build PDF docs"
	@echo "  docs       Build PDF docs, HTML docs, and validate generated HTML"
	@echo "  validate   Validate generated HTML docs"
	@echo "  build      Build package distributions and validate contents"
	@echo "  audit      Run pip-audit"
	@echo "  all        Run check, docs, build, and audit"
	@echo "  watch      Watch docs for changes"
	@echo ""
	@echo "Maintenance"
	@echo "  clean      Remove build artifacts"
	@echo "  clean-all  Clean, then run all"

setup:
	@bash $(SCRIPTS)/setup_dev.sh

test lint type check html pdf docs validate build audit all watch: $(PYTHON)
	@bash $(SCRIPTS)/dev.sh $@

clean:
	@bash $(SCRIPTS)/dev.sh clean

clean-all: $(PYTHON)
	@bash $(SCRIPTS)/dev.sh clean-all
