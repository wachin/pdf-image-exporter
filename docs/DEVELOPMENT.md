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
stopping after the currently active page batch, retrying failed pages, and
continues collecting failures instead of stopping the whole batch at the first
failed page.

PDF folder discovery lives in `core.discovery` so the GUI and future CLI can
share the same deterministic non-recursive/recursive import behavior. The GUI
uses the visible table order as the first priority mechanism: moving documents
up or down changes the order passed to conversion planning.

Preview generation lives in `services.thumbnail_service`. It uses `pdftocairo`
through `QProcess`, writes low-resolution PNG files to a `QTemporaryDir`, caches
requests by PDF/page/size, and removes temporary files when the main window
closes. The GUI requests only the selected page preview instead of rasterizing
whole documents.

`PdfInfoService` first performs a lightweight metadata read and, when a document
has multiple pages but only one generic page size is returned, performs a second
`pdfinfo -box -f 1 -l <pages>` call to collect per-page dimensions. The preview
uses `PdfDocumentInfo.page_size()` to show the selected page size and to flag
documents with mixed dimensions.

User profiles are stored by `services.profile_store.ProfileStore` as JSON under
the XDG configuration directory. Built-in profiles come from `core.profiles` and
are never modified; user profiles are loaded alongside them and are the only
profiles that can be replaced or deleted.
