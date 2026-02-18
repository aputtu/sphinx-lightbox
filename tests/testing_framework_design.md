# Conservative Testing Framework Design for sphinx-lightbox

## Philosophy: Keep It Simple, Stupid (KISS)

**Core Principles:**
- Test what matters: directive parsing, LaTeX output, HTML output
- No infrastructure complexity (mock Sphinx, no image processing)
- Fast execution (unit tests run in milliseconds)
- Easy maintenance (minimal dependencies, clear test names)
- Comprehensive coverage of failure modes

## Test Categories

### 1. Unit Tests (Fast, Isolated)
- Directive argument parsing
- Option validation
- LaTeX escape function behavior
- Image path resolution logic
- Node attribute assignment

### 2. Integration Tests (Medium, Sphinx-dependent)
- Full directive → node → HTML transformation
- Full directive → node → LaTeX transformation
- Multiple output format consistency
- Caption rendering
- Image sizing calculations

### 3. Validation Tests (Fast, Static)
- RST syntax validation
- Malformed directive detection
- Missing required arguments
- Invalid option values

## What We DON'T Test
❌ Actual image file processing (not our responsibility)
❌ LaTeX compilation (TeX Live's responsibility)
❌ Browser rendering (user's browser's responsibility)
❌ CSS styling specifics (visual testing is expensive)
❌ File I/O edge cases (Sphinx handles this)

## What We DO Test
✅ Caption escaping (prevents compilation errors)
✅ Node structure (ensures correct tree)
✅ HTML output structure (ensures valid markup)
✅ LaTeX output structure (ensures valid commands)
✅ Option parsing (prevents user errors)
✅ Path resolution logic (prevents file not found)
✅ Error messages (helps users debug)

---

## Test Matrix

### Python Versions
- 3.10 (minimum supported, Ubuntu 22.04 / Debian 12 default)
- 3.12 (latest stable, future-proofing)

**Why these?**
- 3.10: Default on Ubuntu 22.04 and Debian 12; still widely deployed
- 3.12: Latest stable release; catches forward-compatibility issues early

**Why not others?**
- 3.8 / 3.9: EOL or near-EOL; no longer tested by this project
- 3.11: Covered by the 3.10 ↔ 3.12 range

### Sphinx Versions
- 7.x (current LTS, widest deployment)
- 8.x (current stable)
- 9.x (latest; requires Python ≥ 3.11, so only tested on Python 3.12)

**Why these?**
- 7.x: Used in production, stable APIs
- 8.x: Current recommended version
- 9.x: Catch breaking changes early

### Test Combinations

The matrix is **asymmetric** because Sphinx 9 requires Python ≥ 3.11:

| Python | Sphinx 7 | Sphinx 8 | Sphinx 9 |
|--------|----------|----------|----------|
| 3.10   | ✅        | ✅        | ❌ (incompatible) |
| 3.12   | ✅        | ✅        | ✅        |

Total: **5 test environments** (plus lint, type, docs = 8 tox environments).

**Optimization:** Run `py310-sphinx7` first — most common deployment, catches
the majority of issues quickly.

---

## File Structure

```
lightbox/
├── lightbox/
│   ├── __init__.py
│   └── lightbox.py
├── tests/
│   ├── conftest.py           # pytest fixtures
│   └── test_latex.py         # full test suite (LaTeX, HTML, directive, regression)
├── tox.ini
├── pyproject.toml
└── TESTING_QUICK_REFERENCE.md
```

**Key Points:**
- Tests live in `tests/` directory (not inside package)
- Fixtures separated from tests (conftest.py)
- All tests in one file — split only if it grows unwieldy
- No real images (use dummy paths, test logic not files)
- `pyproject.toml` is the single source of truth for pytest and coverage config
  (no `pytest.ini` — having both causes pytest to ignore `pyproject.toml`)

---

## Coverage Configuration Note

Coverage is measured with `source_pkgs = ["lightbox"]` (not `source`).
This is essential for tox: when the package is installed into an isolated
venv from an sdist, the executed code lives in `site-packages/lightbox/`,
not `./lightbox/`. `source_pkgs` finds it by import name rather than
filesystem path, so data is actually collected.

---

## Example Test Structure

### Test 1: Caption Escaping (Critical)
```python
def test_latex_caption_escaping():
    """LaTeX special characters in captions must be escaped."""
    # Given: A caption with special characters
    caption = "40% width & special: $_#^~\\"

    # When: Building LaTeX output
    result = build_latex_with_caption(caption)

    # Then: Special characters are escaped
    assert r"\%" in result
    assert r"\&" in result
    assert r"\$" in result
    assert r"\_" in result
    assert r"\#" in result
```

### Test 2: Image Sizing (Critical)
```python
def test_latex_uses_adjustbox_max_width():
    """Small images should not upscale (use max width)."""
    # Given: A lightbox directive with percentage
    directive = """
    .. lightbox:: /images/test.png
       :percentage: 50 90
    """

    # When: Building LaTeX
    result = build_latex(directive)

    # Then: Uses adjustbox with max width
    assert r"\adjustbox{max width=0.90\linewidth}" in result
    assert r"\includegraphics" in result
```

### Test 3: HTML Structure (Important)
```python
def test_html_checkbox_toggle_structure():
    """HTML should use checkbox toggle pattern."""
    # Given: A basic lightbox directive
    directive = """
    .. lightbox:: /images/test.png
       :alt: Test image
    """

    # When: Building HTML
    result = build_html(directive)

    # Then: Contains required elements
    assert 'class="lightbox-container"' in result
    assert 'type="checkbox"' in result
    assert 'class="lightbox-toggle"' in result
    assert 'class="lightbox-overlay"' in result
```

### Test 4: Error Handling (Important)
```python
def test_missing_required_argument():
    """Directive without image path should raise warning."""
    # Given: A lightbox without required argument
    directive = """
    .. lightbox::
       :alt: Oops, no image
    """

    # When/Then: Should raise Sphinx warning
    with pytest.warns(SphinxWarning):
        build_html(directive)
```

### Test 5: Option Validation (Nice-to-have)
```python
def test_percentage_option_validation():
    """Percentage option should accept 1-2 positive integers."""
    # Valid cases
    assert_valid(".. lightbox:: img.png\n   :percentage: 50")
    assert_valid(".. lightbox:: img.png\n   :percentage: 50 90")

    # Invalid cases
    assert_invalid(".. lightbox:: img.png\n   :percentage: -50")
    assert_invalid(".. lightbox:: img.png\n   :percentage: 150 50 25")
```

---

## Mocking Strategy (Minimal)

### What to Mock
1. **Sphinx App** - Mock just enough to register directive
2. **Environment** - Mock docname, srcdir, images collection
3. **Builder** - Mock images dict for LaTeX path resolution

### What NOT to Mock
- Docutils nodes (use real ones)
- RST parser (use real one)
- String operations (test real code)

### Example Fixture
```python
@pytest.fixture
def sphinx_app(tmp_path):
    """Minimal Sphinx app for testing."""
    # Create minimal conf.py
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    (conf_dir / "conf.py").write_text("extensions = ['lightbox']")

    app = Mock()
    app.confdir = str(conf_dir)
    return app
```
