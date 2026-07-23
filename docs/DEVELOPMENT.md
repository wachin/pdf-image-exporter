# Development Notes

The project uses a `src/` layout and separates pure core logic from Qt widgets.
The GUI invokes Poppler through services based on `QProcess`; argument vectors
are built by core/service helpers and never passed through a shell.

Current module boundaries:

- `core/`: page ranges, dimensions, PDF info parsing, format models, naming and
  conversion settings, profiles, collision policies and conversion planning.
- `services/`: executable discovery and Qt process wrappers for `pdfinfo` and
  `pdftocairo`, QSettings persistence and application logging.
- `ui/`: PyQt6 widgets and windows.
- `cli/`: command-line entry points that reuse core configuration.

Conversion planning is handled in `core.queue`. It expands page ranges,
calculates expected output dimensions, resolves output-name collisions, and
returns immutable planned pages that can be passed to a process execution layer.
The current GUI still executes sequentially through `PdfToCairoRunner`; a fuller
queue executor with concurrency, pause/resume and retries remains pending.
