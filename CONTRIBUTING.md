# Contributing

Development requires Python 3, PyQt6, Poppler tools and pytest. Run checks from
the repository root:

```bash
PYTHONPATH=src pytest
python3 -m compileall src tests
```

Visible strings should be written in English and marked with Qt translation
helpers such as `self.tr()` in widgets.
