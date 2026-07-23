# Development Notes

The project uses a `src/` layout and separates pure core logic from Qt widgets.
The GUI invokes Poppler through services based on `QProcess`; argument vectors
are built by core/service helpers and never passed through a shell.

Current module boundaries:

- `core/`: page ranges, dimensions, PDF info parsing, format models, naming and
  conversion settings.
- `services/`: executable discovery and Qt process wrappers for `pdfinfo` and
  `pdftocairo`.
- `ui/`: PyQt6 widgets and windows.
- `cli/`: command-line entry points that reuse core configuration.
