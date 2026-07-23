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
`ConversionQueueRunner` in `services.pdftocairo_service` executes those pages
with bounded concurrency through `QProcess`, supports pause/resume, cancellation
and retrying failed pages, and continues collecting failures instead of stopping
the whole batch at the first failed page.

PDF folder discovery lives in `core.discovery` so the GUI and future CLI can
share the same deterministic non-recursive/recursive import behavior. The GUI
uses the visible table order as the first priority mechanism: moving documents
up or down changes the order passed to conversion planning.
