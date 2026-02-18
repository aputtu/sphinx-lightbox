# Testing Framework Quick Reference

## Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Or just dev requirements
pip install -r requirements-dev.txt
pip install -e .
```

## Running Tests

### Quick Commands (Development)

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_latex.py

# Run specific test class
pytest tests/test_latex.py::TestHtmlOutput

# Run specific test
pytest tests/test_latex.py::TestCaptionEscaping::test_percent_sign_escaped

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only fast unit tests
pytest -m unit

# Run only LaTeX tests
pytest -m latex

# Run tests excluding slow ones
pytest -m "not slow"

# Run with coverage report
pytest --cov --cov-report=html
```

### Full Test Matrix (CI/Release)

```bash
# Run all Python × Sphinx combinations
tox

# Run in parallel (faster)
tox -p auto

# Run specific environment
tox -e py310-sphinx7

# Run just linting
tox -e lint

# Run just type checking
tox -e type

# Build documentation
tox -e docs
```

## Test Organisation

All tests currently live in a single file:

```
tests/
├── conftest.py       ← Shared fixtures (mock_builder, sphinx_env)
└── test_latex.py     ← Full test suite: LaTeX, HTML, directive, regression
    ├── TestCaptionEscaping      (6 tests)
    ├── TestLatexOutput          (6 tests)
    ├── TestDirectiveIntegration (2 tests)
    ├── TestEdgeCases            (5 tests)
    ├── TestHtmlOutput           (13 tests)
    └── TestRegressionBugs       (1 test)
```

Each class is independently runnable:

```bash
pytest tests/test_latex.py::TestHtmlOutput
pytest tests/test_latex.py::TestLatexOutput
```

## Writing Tests

### Test File Template

```python
"""Tests for [component name]."""

import pytest
from lightbox.lightbox import YourClass


class TestFeatureName:
    """Test [feature description]."""

    @pytest.mark.unit
    def test_specific_behavior(self):
        """One-line description of what's tested."""
        # Given: Setup test data
        input_data = "test"

        # When: Execute code under test
        result = function_under_test(input_data)

        # Then: Assert expected behavior
        assert result == expected_value
```

### Using Fixtures

```python
def test_with_mock_builder(mock_builder):
    """Use mock_builder fixture for LaTeX tests."""
    # mock_builder provides a minimal Sphinx LaTeX translator
    translator = mock_builder
    translator.body.append("test")
    assert "test" in "".join(translator.body)


def test_with_sphinx_env(sphinx_env):
    """Use sphinx_env fixture for directive tests."""
    # sphinx_env provides environment with docname, srcdir, etc.
    assert sphinx_env.docname == "test"
    serial = sphinx_env.new_serialno("lightbox")
    assert serial == 1
```

### Test Markers

```python
@pytest.mark.unit        # Fast, no Sphinx
@pytest.mark.integration # Requires Sphinx
@pytest.mark.latex       # Tests LaTeX output
@pytest.mark.html        # Tests HTML output
@pytest.mark.slow        # Full builds (skip in quick runs)
```

## Coverage

```bash
# Run tests with coverage
pytest --cov

# Generate HTML coverage report
pytest --cov --cov-report=html
# Open htmlcov/index.html

# Check coverage meets threshold (85%)
pytest --cov --cov-fail-under=85

# Show missing lines
pytest --cov --cov-report=term-missing
```

Current coverage: **87%** (33 tests). Uncovered lines are intentional:
- `setup()` — requires a real Sphinx app to test meaningfully
- `visit_noop` / `skip_departure` — trivial one-liners
- Missing-file warning branch in `_resolve_image_path`

## Code Quality

```bash
# Check code style
ruff check lightbox tests

# Auto-fix issues
ruff check --fix lightbox tests

# Format code
ruff format lightbox tests

# Type checking
mypy lightbox

# All checks via tox
tox -e lint,type
```

## Common Patterns

### Testing LaTeX Output

LaTeX visitor functions raise `nodes.SkipNode` as their final action (Sphinx
protocol for "I handled children myself"). Always wrap the call:

```python
def test_latex_output(mock_builder):
    """Test LaTeX generation."""
    import pytest
    from docutils import nodes
    from lightbox.lightbox import (
        LightboxContainer,
        visit_lightbox_container_latex,
    )

    node = LightboxContainer()
    node["uri"] = "images/test.png"
    node["caption"] = "Test caption"
    node["latex_width"] = "0.90"

    with pytest.raises(nodes.SkipNode):
        visit_lightbox_container_latex(mock_builder, node)

    output = "".join(mock_builder.body)
    assert r"\begin{figure}" in output
    assert r"\adjustbox{max width=0.90\linewidth}" in output
    assert r"\caption{Test caption}" in output
```

### Testing HTML Output

HTML visitor tests need a translator with a real `builder.images` dict —
a bare `Mock()` is not iterable and will fail the `uri in builder.images`
check in `_resolve_output_uri`:

```python
from unittest.mock import Mock
from lightbox.lightbox import LightboxTrigger, visit_lightbox_trigger_html

def _make_translator():
    t = Mock()
    t.body = []
    t.builder = Mock()
    t.builder.images = {}   # must be a real dict, not Mock
    return t

def test_trigger_renders_label_and_img():
    t = _make_translator()
    node = LightboxTrigger()
    node["uri"] = "images/test.png"
    node["alt"] = "Test image"
    node["thumbnail_width"] = "100%"
    node["custom_class"] = ""
    node["checkbox_id"] = "lightbox-0"

    visit_lightbox_trigger_html(t, node)
    html = "".join(t.body)

    assert 'class="lightbox-trigger-label"' in html
    assert "<img" in html
```

### Testing Caption Escaping

`latex_escape()` requires `texescape.init()` to have been called first.
This is handled automatically in `conftest.py` — tests can call it directly:

```python
def test_caption_escaping():
    """Test LaTeX special character escaping."""
    from sphinx.util.texescape import escape as latex_escape

    caption = "40% & special $_#"
    escaped = latex_escape(caption)

    assert r"\%" in escaped
    assert r"\&" in escaped
    assert r"\$" in escaped
```

## Debugging Tests

```bash
# Run single test with detailed output
pytest tests/test_latex.py::TestHtmlOutput::test_trigger_renders_label_and_img -vv

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show local variables in tracebacks
pytest -l
```

## CI Integration

### GitHub Actions Example

The tox matrix is asymmetric: Python 3.10 only supports Sphinx 7 and 8
(Sphinx 9 requires Python ≥ 3.11), while Python 3.12 covers all three.
The workflow below mirrors this exactly using `tox-gh-actions`.

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - python-version: "3.10"
            tox-env: py310-sphinx7
          - python-version: "3.10"
            tox-env: py310-sphinx8
          - python-version: "3.12"
            tox-env: py312-sphinx7
          - python-version: "3.12"
            tox-env: py312-sphinx8
          - python-version: "3.12"
            tox-env: py312-sphinx9

    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - run: pip install tox
    - run: tox -e ${{ matrix.tox-env }}

  quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - run: pip install tox
    - run: tox -e lint,type,docs
```

## Performance

Expected test execution times:

- **Unit tests** (`pytest -m unit`): < 2 seconds
- **Full test suite** (`pytest`): < 5 seconds
- **Full tox matrix** (8 envs, parallel): < 30 seconds

## Troubleshooting

### "No module named 'lightbox'"

```bash
pip install -e .
```

### "Fixture 'mock_builder' not found"

```bash
# Ensure conftest.py is in tests/
ls tests/conftest.py
```

### "TypeError: argument of type 'Mock' is not iterable"

The HTML visitor calls `uri in builder.images`. Ensure the translator mock
has a real dict, not a `Mock()`:

```python
t.builder = Mock()
t.builder.images = {}   # ← real dict required
```

### Tests pass locally but fail in CI

```bash
# Check Python/Sphinx version mismatch
python --version
pip show sphinx

# Run same environment as CI
tox -e py310-sphinx7
```

### Coverage shows 0% in tox

Coverage must find the package by import name, not filesystem path. Ensure
`pyproject.toml` uses `source_pkgs` (not `source`) in `[tool.coverage.run]`:

```toml
[tool.coverage.run]
source_pkgs = ["lightbox"]
```

### Coverage below threshold

```bash
# See missing lines
pytest --cov --cov-report=term-missing
```

## Best Practices

✅ **DO:**
- Wrap LaTeX visitor calls in `pytest.raises(nodes.SkipNode)`
- Give HTML translator mocks a real `builder.images = {}` dict
- Test behaviour, not implementation details
- Use descriptive test names
- Keep tests fast (mock Sphinx rather than running full builds)
- Add a regression test whenever a bug is fixed

❌ **DON'T:**
- Call `visit_lightbox_container_latex()` without catching `SkipNode`
- Use a bare `Mock()` for `builder.images` in HTML tests
- Test Sphinx's own code
- Share mutable state between tests
- Mock the code under test

## Release Checklist

Before releasing a new version:

```bash
# 1. Run full test suite
tox

# 2. Check code quality
tox -e lint,type

# 3. Build docs and PDF
make all

# 4. Verify coverage
pytest --cov --cov-report=term-missing

# 5. Build distribution
python -m build

# 6. Test installation
pip install dist/*.whl
python -c "import lightbox; print(lightbox.__version__)"
```
